from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from intent_parser import IntentParser
from schemas import StructuredIntent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("intent-api")

app = FastAPI(title="Intent Parser API", version="1.0.0")

# Allow the WPF app (running locally, no browser origin) to call this freely.
# Tighten allow_origins if you ever expose this beyond localhost.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Build the parser once at startup, not per-request — ChatOllama / the model
# connection is reused across calls instead of being re-created each time.
parser = IntentParser()


class ParseRequest(BaseModel):
    text: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/parse", response_model=StructuredIntent)
def parse_text(request: ParseRequest) -> StructuredIntent:
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="`text` must not be empty.")

    try:
        return parser.parse(request.text)
    except Exception as exc:  # noqa: BLE001 - surface as a clean 500 to the client
        logger.exception("Failed to parse text: %s", request.text)
        raise HTTPException(status_code=500, detail=f"Intent parsing failed: {exc}") from exc


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)