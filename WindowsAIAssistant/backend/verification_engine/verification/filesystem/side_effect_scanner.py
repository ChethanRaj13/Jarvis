from WindowsAIAssistant.backend.verification_engine.verification._base import ComparisonOutcome


class FilesystemSideEffectScanner:
    def scan(self, payload: dict) -> ComparisonOutcome:
        unexpected = tuple(payload.get("unexpected_files", ())) + tuple(payload.get("unexpected_directories", ()))
        if not unexpected:
            return ComparisonOutcome(rationale=("no unexpected filesystem entries detected",))
        return ComparisonOutcome(
            partial=("unexpected_filesystem_entries",),
            rationale=(f"unexpected filesystem entries detected: {len(unexpected)}",),
        )
