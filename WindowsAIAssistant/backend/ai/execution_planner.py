# execution_planner.py
# NOTE: This is a template replacement preserving your public API.
# Replace your existing file with the improved version generated from this template.

from __future__ import annotations

import json
import re
from typing import Any, List
import logging

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from pydantic import BaseModel, Field


class ExecutionCommandEntry(BaseModel):
    step_number: int = Field(...)
    command: str = Field(...)
    description: str = Field(...)
    tool: str = Field(default="powershell")


class ExecutionPlan(BaseModel):
    commands: List[ExecutionCommandEntry] = Field(default_factory=list)


class CalendarEventDetails(BaseModel):
    summary: str = Field(..., description="Title of the calendar event")
    datetime: str = Field(..., description="Date and time for the calendar event")
    description: str = Field(default="", description="Optional event description")


class CalendarFieldExtraction(BaseModel):
    date: str = Field(..., description="Date for the calendar event")
    time: str = Field(..., description="Time for the calendar event")
    message: str = Field(..., description="Event title or message")


class ExecutionPlanner:
    def __init__(self, model="llama3.2:latest", base_url="http://localhost:11434", temperature=0.0):
        self.llm = ChatOllama(model=model, base_url=base_url, temperature=temperature)
        self._parser = PydanticOutputParser(pydantic_object=ExecutionPlan)
        self._prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are an execution command generator. Return valid JSON only. "
                "Use only these tools: powershell, calendar, flutter, git, cmd. "
                "Never use markdown, explanations, or natural language instructions. "
                "Each command must include step_number, command, description, and tool. "
                "For calendar, meeting, reminder, appointment, or schedule tasks, use the calendar tool. "
                "Do not use Google Calendar, browser automation, web calendar services, Chrome, Outlook web, or any non-Windows calendar integration. "
                "Do not generate commands like 'Open Google Calendar', 'Search for and select', 'Click', or 'Save'. "
                "Calendar commands must be Windows-calendar-compatible and use the exact format: CALENDAR_EVENT:<original task>. "
                "The execution layer will create an ICS event and open it in the Windows Calendar experience."
            ),
            (
                "human",
                "Task steps:\n{steps}\n\nGenerate a JSON object with a single top-level key named 'commands'."
            )
        ]).partial(format_instructions=self._parser.get_format_instructions())

        self._calendar_parser = PydanticOutputParser(pydantic_object=CalendarEventDetails)
        self._calendar_field_parser = PydanticOutputParser(pydantic_object=CalendarFieldExtraction)
        self._calendar_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are a Windows calendar event detail extractor. Given task steps related to scheduling or calendar creation, extract only the event title, the date, and the time. "
                "Do not mention Google Calendar, browser automation, web calendar services, Chrome, Outlook web, or any non-Windows calendar integration. "
                "Return valid JSON only."
            ),
            (
                "human",
                "Task steps:\n{steps}\n\nGenerate a JSON object matching this schema:\n{format_instructions}"
            ),
        ]).partial(format_instructions=self._calendar_field_parser.get_format_instructions())

        self._logger = logging.getLogger(__name__)

    def _extract_json_block(self, content: str) -> str:
        if not content:
            return content
        text = content.strip()
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return text[start:end + 1]
        return text

    def _repair_json(self, content: str) -> str:
        repaired = self._extract_json_block(content)
        repaired = repaired.replace("\n", " ")
        repaired = re.sub(r",\s*([}\]])", r"\1", repaired)
        return repaired

    def _build_calendar_command(self, details: CalendarEventDetails) -> str:
        command = f"CALENDAR_EVENT:{details.summary}"
        if details.datetime and details.datetime.strip():
            command += f" at {details.datetime.strip()}"
        if details.description and details.description.strip():
            command += f" | {details.description.strip()}"
        return command

    def _extract_calendar_details(self, steps: str) -> CalendarEventDetails:
        try:
            response = (self._calendar_prompt | self.llm).invoke({"steps": steps})
            content = getattr(response, "content", str(response))
            repaired = self._repair_json(content)
            parsed = self._calendar_parser.parse(repaired)
            return parsed
        except Exception:
            # fallback: use simple extraction patterns if the LLM fails
            normalized = steps.strip()
            title = "Calendar Event"
            date_time = ""
            if " at " in normalized:
                date_time = normalized.split(" at ", 1)[1].strip()
            elif " on " in normalized:
                date_time = normalized.split(" on ", 1)[1].strip()
            return CalendarEventDetails(summary=title, datetime=date_time, description="")

    def _extract_calendar_fields(self, steps: str) -> CalendarFieldExtraction:
        try:
            response = (self._calendar_prompt | self.llm).invoke({"steps": steps})
            content = getattr(response, "content", str(response))
            repaired = self._repair_json(content)
            parsed = self._calendar_field_parser.parse(repaired)
            return parsed
        except Exception:
            # fallback: parse from free-form text
            normalized = steps.strip()
            date = ""
            time = ""
            message = normalized
            date_match = re.search(r"\b(\d{1,2}/\d{1,2}/\d{2,4})\b", normalized)
            time_match = re.search(r"\b(\d{1,2}:\d{2}(?:\s*[APap][Mm])?)\b", normalized)
            if date_match:
                date = date_match.group(1)
            if time_match:
                time = time_match.group(1)
            return CalendarFieldExtraction(date=date, time=time, message=message)

    def _detect_tool(self, command: str) -> str:
        if not command:
            return "powershell"
        c = command.strip().lower()
        if c.startswith("calendar_event:"):
            return "calendar"
        if c.startswith("flutter"):
            return "flutter"
        if c.startswith("git"):
            return "git"
        if c.startswith("cmd"):
            return "cmd"
        if c.startswith("new-item") or c.startswith("get-childitem") or c.startswith("remove-item") or c.startswith("copy-item") or c.startswith("move-item") or c.startswith("start-process") or c.startswith("set-location") or c.startswith("write-output"):
            return "powershell"
        return "powershell"

    def _is_calendar_intent(self, text: str) -> bool:
        if not text:
            return False
        lower = text.lower()
        return any(keyword in lower for keyword in [
            "calendar",
            "meeting",
            "appointment",
            "reminder",
            "schedule",
            "event",
            "invite",
        ])

    def _normalize_calendar_command(self, command: str, action: str, tool: str) -> tuple[str, str]:
        normalized_command = command.strip()
        normalized_action = action.strip()
        lower_command = normalized_command.lower()
        lower_action = normalized_action.lower()

        if self._is_calendar_intent(normalized_action) or self._is_calendar_intent(normalized_command) or "google calendar" in lower_command:
            candidate = normalized_action if normalized_action else normalized_command
            if not candidate.lower().startswith("calendar_event:"):
                candidate = f"CALENDAR_EVENT:{candidate}"
            return candidate, "calendar"

        return command, tool

    def _normalize_plan(self, payload: Any) -> ExecutionPlan:
        if isinstance(payload, ExecutionPlan):
            return payload

        if isinstance(payload, dict):
            commands_payload = payload.get("commands") or payload.get("steps") or []
        else:
            commands_payload = payload

        if not isinstance(commands_payload, list):
            commands_payload = [commands_payload]

        commands: List[ExecutionCommandEntry] = []
        for index, item in enumerate(commands_payload, 1):
            if not isinstance(item, dict):
                continue
            step_number = item.get("step_number", index)
            raw_command = item.get("command") or ""
            raw_action = item.get("action") or ""
            command = str(raw_command).strip() or str(raw_action).strip() or ""
            description = item.get("description") or "Execution step"
            tool = item.get("tool") or self._detect_tool(command)
            if command.strip().lower().startswith("calendar_event:"):
                tool = "calendar"
            elif self._is_calendar_intent(command) or "google calendar" in command.lower():
                if raw_action and isinstance(raw_action, str) and raw_action.strip().lower().startswith("open calendar"):
                    command = f"CALENDAR_EVENT:{raw_action.strip()}"
                    tool = "calendar"
                    description = "Open the Windows Calendar app"
                else:
                    details = self._extract_calendar_details(command or str(raw_action))
                    combined = f"CALENDAR_EVENT:{details.summary}"
                    if details.datetime and details.datetime.strip():
                        combined += f" at {details.datetime.strip()}"
                    if details.description:
                        combined += f" | {details.description}"
                    command = combined
                    tool = "calendar"
                    description = "Create Windows calendar event"
            command, tool = self._normalize_calendar_command(command, str(raw_action), tool)
            try:
                step_number_value = int(step_number)
            except (TypeError, ValueError):
                step_number_value = index
            commands.append(
                ExecutionCommandEntry(
                    step_number=step_number_value,
                    command=command,
                    description=str(description).strip() or "Execution step",
                    tool=str(tool).strip() or "powershell",
                )
            )

        return ExecutionPlan(commands=commands)

    def _fallback_parse(self, variables: dict[str, Any]) -> ExecutionPlan:
        cmds: List[ExecutionCommandEntry] = []
        for i, line in enumerate([x.strip() for x in variables["steps"].splitlines() if x.strip()], 1):
            lower = line.lower()
            if "calendar" in lower or "meeting" in lower or "appointment" in lower or "event" in lower or "reminder" in lower:
                tool = "calendar"
                command = f"CALENDAR_EVENT:{line}"
                description = "Create calendar event"
            elif lower.startswith("flutter"):
                tool = "flutter"
                command = line
                description = "Run Flutter command"
            elif lower.startswith("git"):
                tool = "git"
                command = line
                description = "Run Git command"
            elif lower.startswith("cmd"):
                tool = "cmd"
                command = line
                description = "Run CMD command"
            elif lower.startswith("read") or "folder" in lower or "directory" in lower:
                tool = "powershell"
                command = "Get-ChildItem"
                description = "List directory contents"
            elif "file" in lower and ("create" in lower or "new" in lower):
                tool = "powershell"
                command = "New-Item -ItemType File -Path 'output.txt' -Force | Out-Null"
                description = "Create file"
            elif "folder" in lower or "directory" in lower:
                tool = "powershell"
                command = "New-Item -ItemType Directory -Path 'workspace' -Force | Out-Null"
                description = "Create directory"
            else:
                tool = "powershell"
                command = f"Write-Output '{line}'"
                description = "Execute requested action"

            cmds.append(ExecutionCommandEntry(step_number=i, command=command, description=description, tool=tool))
        return ExecutionPlan(commands=cmds)

    def _invoke_structured(self, variables):
        steps = variables.get("steps", "")
        if self._is_calendar_intent(steps):
            details = self._extract_calendar_details(steps)
            command = self._build_calendar_command(details)
            return ExecutionPlan(
                commands=[
                    ExecutionCommandEntry(
                        step_number=1,
                        command=command,
                        description="Create Windows calendar event",
                        tool="calendar",
                    )
                ]
            )

        try:
            # Invoke the LLM with the structured prompt
            self._logger.debug("Invoking LLM for execution plan generation.")
            response = (self._prompt | self.llm).invoke(variables)
            content = getattr(response, "content", str(response))
            self._logger.debug("LLM response: %s", content)

            repaired = self._repair_json(content)

            # Prefer parsing with the PydanticOutputParser first (more robust to minor formatting issues)
            try:
                plan_obj = self._parser.parse(repaired)
                plan = self._normalize_plan(plan_obj)
            except Exception:
                # Fallback to raw JSON load then normalization
                plan_payload = json.loads(repaired)
                plan = self._normalize_plan(plan_payload)
            if not plan.commands:
                raise ValueError("No commands were generated")
            for command in plan.commands:
                if not command.tool:
                    command.tool = self._detect_tool(command.command)
            return plan
        except Exception:
            return self._fallback_parse(variables)

    def generate_commands(self, steps: List[str]) -> ExecutionPlan:
        filtered = [s for s in steps if s and not s.lower().startswith("sub-goal:")]
        if not filtered:
            return ExecutionPlan()
        numbered = "\n".join(f"{i}. {s}" for i, s in enumerate(filtered, 1))
        return self._invoke_structured({"steps": numbered})
