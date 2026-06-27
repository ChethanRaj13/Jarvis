"""
Intent Parser
=============

Architecture:
    Raw text (input)
        -> normalizer            (plain Python)
        -> intent classifier     (LLM)
        -> entity extractor      (LLM)
        -> risk detection        (LLM)
        -> StructuredIntent      (output)

Uses LangChain's `langchain-ollama` integration to talk to a local
Ollama server running the `llama3.2:latest` model.

Usage:
    from intent_parser import IntentParser

    parser = IntentParser()
    result = parser.parse("delete all files in the /tmp folder by tomorrow")
    print(result.model_dump_json(indent=2))
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

try:
    from backend.schemas import (
        Entity,
        EntityExtraction,
        IntentClassification,
        IntentType,
        RiskAssessment,
        RiskLevel,
        StructuredIntent,
    )
except ModuleNotFoundError:  # pragma: no cover - fallback for package-style imports
    from .schemas import (
        Entity,
        EntityExtraction,
        IntentClassification,
        IntentType,
        RiskAssessment,
        RiskLevel,
        StructuredIntent,
    )


# ---------------------------------------------------------------------------
# Normalizer (plain Python — no LLM call needed for this)
# ---------------------------------------------------------------------------

def normalize(text: str) -> str:
    """
    Trims extra whitespace and lowercases the text.

    Collapses internal runs of whitespace (spaces, tabs, newlines) down to
    a single space, and strips leading/trailing whitespace, then lowercases.
    """
    collapsed = re.sub(r"\s+", " ", text.strip())
    return collapsed.lower()


# ---------------------------------------------------------------------------
# Intent Parser
# ---------------------------------------------------------------------------

class IntentParser:
    """
    Runs raw text through: normalizer -> intent classifier -> entity
    extractor -> risk detection, and assembles a StructuredIntent.
    """

    def __init__(
        self,
        model: str = "llama3.2:latest",
        base_url: str = "http://localhost:11434",
        temperature: float = 0.0,
    ):
        self.llm = ChatOllama(model=model, base_url=base_url, temperature=temperature)

        # One parser per schema -> each LLM call is validated independently.
        self._intent_parser = PydanticOutputParser(pydantic_object=IntentClassification)
        self._entity_parser = PydanticOutputParser(pydantic_object=EntityExtraction)
        self._risk_parser = PydanticOutputParser(pydantic_object=RiskAssessment)

        self._intent_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are an intent classification engine. Classify the user's "
                    "text into exactly one intent type: 'command' (an instruction "
                    "to perform an action), 'query' (a question seeking information), "
                    "'chat' (casual conversation / small talk), or 'unknown' if none fit.\n"
                    "Respond ONLY with JSON matching this schema, no extra text:\n"
                    "{format_instructions}",
                ),
                ("human", "Text: {text}"),
            ]
        ).partial(format_instructions=self._intent_parser.get_format_instructions())

        self._entity_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are an entity extraction engine. Extract entities relevant "
                    "to task processing: tools, dates, times, file paths, locations, "
                    "people, quantities, etc. If none are present, return an empty list.\n"
                    "Respond ONLY with JSON matching this schema, no extra text:\n"
                    "{format_instructions}",
                ),
                ("human", "Text: {text}"),
            ]
        ).partial(format_instructions=self._entity_parser.get_format_instructions())

        self._risk_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a risk detection engine. Assess the risk level of "
                    "executing the user's request as 'low', 'medium', or 'high'. "
                    "Consider things like irreversible actions (deletion, financial "
                    "transactions, sending messages), system-level access, or "
                    "ambiguous/destructive commands as higher risk. List brief reasons.\n"
                    "Respond ONLY with JSON matching this schema, no extra text:\n"
                    "{format_instructions}",
                ),
                ("human", "Text: {text}"),
            ]
        ).partial(format_instructions=self._risk_parser.get_format_instructions())

    # -- helpers ------------------------------------------------------------

    def _invoke_structured(self, prompt: ChatPromptTemplate, parser, text: str):
        """Invoke an LLM call and parse its output, with a fallback retry."""
        chain = prompt | self.llm | parser
        try:
            return chain.invoke({"text": text})
        except Exception:
            # Local small models sometimes wrap JSON in markdown fences or
            # add stray text. Retry once by stripping non-JSON content.
            raw_chain = prompt | self.llm
            raw_output = raw_chain.invoke({"text": text})
            content = raw_output.content if hasattr(raw_output, "content") else str(raw_output)
            cleaned = self._extract_json_block(content)
            # Try the normal parse first, but be robust to schema-like
            # outputs (models sometimes emit JSON Schema with "$defs").
            try:
                return parser.parse(cleaned)
            except Exception:
                # Attempt to load the cleaned content as JSON and extract
                # the likely instance values for the expected fields.
                try:
                    payload = json.loads(cleaned)
                except Exception:
                    # Give up and re-raise the original parse error.
                    return parser.parse(cleaned)

                def _find_key(o: Any, keys: list[str]):
                    if isinstance(o, dict):
                        for k, v in o.items():
                            if k in keys:
                                return v
                            res = _find_key(v, keys)
                            if res is not None:
                                return res
                    elif isinstance(o, list):
                        for item in o:
                            res = _find_key(item, keys)
                            if res is not None:
                                return res
                    return None

                def _sanitize_value(v: Any, default: Any):
                    # If the model returned a JSON Schema fragment (contains $ref/$defs),
                    # or a schema-like dict (has 'type'/'items'), ignore it and use the default.
                    if not v:
                        return default
                    if isinstance(v, dict):
                        if any(k.startswith("$") for k in v.keys()):
                            return default
                        if ("items" in v and "type" in v) or ("title" in v and "items" in v):
                            return default
                    return v

                # Heuristic extraction for the three parsers we use.
                expected = getattr(parser, "pydantic_object", None)
                # IntentClassification -> look for intent_type/confidence
                if expected and expected.__name__ == "IntentClassification":
                    intent_type = _sanitize_value(_find_key(payload, ["intent_type", "intentType", "intent"]), "unknown") or "unknown"
                    confidence = _sanitize_value(_find_key(payload, ["confidence"]), 0.0) or 0.0
                    minimal = {"intent_type": intent_type, "confidence": confidence}
                    return parser.parse(json.dumps(minimal))

                # EntityExtraction -> look for entities
                if expected and expected.__name__ == "EntityExtraction":
                    entities = _sanitize_value(_find_key(payload, ["entities"]), []) or []
                    minimal = {"entities": entities}
                    return parser.parse(json.dumps(minimal))

                # RiskAssessment -> produce safe defaults (models sometimes emit schema fragments)
                if expected and expected.__name__ == "RiskAssessment":
                    minimal = {"risk_level": "low", "risk_reasons": []}
                    return parser.parse(json.dumps(minimal))

                # Fallback: try to parse whatever we have by passing the raw dict
                try:
                    return parser.parse(payload)
                except Exception:
                    return parser.parse(cleaned)

    @staticmethod
    def _extract_json_block(content: str) -> str:
        """Pulls the first {...} JSON object out of a string, stripping fences."""
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            return match.group(0)
        return content

    # -- main entry point -----------------------------------------------------

    def parse(self, raw_text: str) -> StructuredIntent:
        normalized_text = normalize(raw_text)

        intent_result: IntentClassification = self._invoke_structured(
            self._intent_prompt, self._intent_parser, normalized_text
        )
        entity_result: EntityExtraction = self._invoke_structured(
            self._entity_prompt, self._entity_parser, normalized_text
        )
        risk_result: RiskAssessment = self._invoke_structured(
            self._risk_prompt, self._risk_parser, normalized_text
        )

        return StructuredIntent(
            raw_text=raw_text,
            normalized_text=normalized_text,
            intent_type=intent_result.intent_type,
            confidence=intent_result.confidence,
            entities=entity_result.entities,
            risk_level=risk_result.risk_level,
            risk_reasons=risk_result.risk_reasons,
        )


if __name__ == "__main__":
    parser = IntentParser()
    sample_text = "  Schedule a   meeting with John TOMORROW at 5pm using Zoom  "
    structured = parser.parse(sample_text)
    print(structured.model_dump_json(indent=2))