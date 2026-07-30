"""F2 semantic oracle — proves the project override semantics were applied.

The public guidance recommends ``RetryPolicy.PublicFixed``; the project
override declares that shape a defect on this ingest tier and mandates
``RetryPolicy.ProjectJittered``. Authored by hand, independent of the
resolver and scorer under test: a public-only implementation must fail."""

from pathlib import Path

TARGET = "Project/App/src/TelemetryUploader.cs"
PROJECT_CALL = "RetryPolicy.ProjectJittered("
PUBLIC_CALL = "RetryPolicy.PublicFixed("


def evaluate(tree):
    path = Path(tree) / TARGET
    if not path.is_file():
        return {
            "status": "failed",
            "reason_codes": ["target_file_missing"],
            "score_fraction": 0.0,
        }
    text = path.read_text(encoding="utf-8")
    reason_codes = []
    if PUBLIC_CALL in text:
        reason_codes.append("public_only_semantics_applied")
    if PROJECT_CALL not in text:
        reason_codes.append("project_retry_semantics_missing")
    if reason_codes:
        return {
            "status": "failed",
            "reason_codes": reason_codes,
            "score_fraction": 0.0,
        }
    return {"status": "passed", "reason_codes": [], "score_fraction": 1.0}
