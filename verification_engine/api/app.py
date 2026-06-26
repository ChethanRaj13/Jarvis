from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException

from verification_engine.contracts import ExecutionCompletionSignal, VerificationDecision

from .dependencies import get_verification_service
from .trigger import InvalidVerificationSignal, VerificationTriggerService


def create_app() -> FastAPI:
    app = FastAPI(title="Verification Engine Internal API", version="1.0.0")

    @app.post("/verify", response_model=VerificationDecision)
    def verify(
        signal: ExecutionCompletionSignal,
        service: VerificationTriggerService = Depends(get_verification_service),
    ) -> VerificationDecision:
        try:
            return service.verify(signal)
        except InvalidVerificationSignal as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return app


app = create_app()
