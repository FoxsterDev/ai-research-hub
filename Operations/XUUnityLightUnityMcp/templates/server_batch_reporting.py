import json
from pathlib import Path
from typing import Any, Callable


def first_non_empty_line(
    text: str,
    *,
    limit: int = 240,
    truncate_text: Callable[[Any, int], str],
) -> str:
    for line in str(text or "").splitlines():
        candidate = line.strip()
        if candidate:
            return truncate_text(candidate, limit)
    return ""


def batch_summary_artifact_path(result_path: Path) -> Path:
    suffix = result_path.suffix or ".json"
    stem = result_path.stem if result_path.suffix else result_path.name
    return result_path.with_name(f"{stem}_summary{suffix}")


def write_batch_summary_artifact(summary_path: Path, summary: dict[str, Any]) -> None:
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, ensure_ascii=True)
        handle.write("\n")


def batch_phase_for_action(action: str) -> str:
    if action == "plain_batch_build":
        return "build"
    if action.startswith("batch_"):
        return "validation"
    return "batch"


def derive_batch_unity_outcome(result_payload: dict[str, Any] | None, succeeded: bool) -> str:
    if not isinstance(result_payload, dict):
        return "completed_ok" if succeeded else "unknown"

    for key in ("outcome", "status", "build_result"):
        value = str(result_payload.get(key) or "").strip()
        if value:
            return value

    compile_result = ((result_payload.get("compile") or {}).get("result") or {}) if isinstance(result_payload.get("compile"), dict) else {}
    if isinstance(compile_result, dict):
        value = str(compile_result.get("status") or "").strip()
        if value:
            return value

    matrix_payload = result_payload.get("matrix") or {}
    if isinstance(matrix_payload, dict):
        value = str(matrix_payload.get("status") or "").strip()
        if value:
            return value

    tests_payload = result_payload.get("tests") or {}
    if isinstance(tests_payload, dict):
        value = str(tests_payload.get("status") or "").strip()
        if value:
            return value

    return "completed_ok" if succeeded else "unknown"


def summarize_batch_result_payload(
    result_payload: dict[str, Any] | None,
    *,
    truncate_text: Callable[[Any, int], str],
) -> dict[str, Any]:
    if not isinstance(result_payload, dict):
        return {}

    summary: dict[str, Any] = {}
    operation = str(result_payload.get("operation") or "")
    for key in (
        "action",
        "operation",
        "outcome",
        "succeeded",
        "build_result",
        "requested_build_target",
        "total_errors",
        "total_warnings",
        "total_size_bytes",
        "output_path",
        "output_directory",
    ):
        if key in result_payload:
            summary[key] = result_payload[key]

    compile_payload = result_payload.get("compile") or {}
    if operation == "compile-player-scripts" and isinstance(compile_payload, dict) and compile_payload:
        compile_result = compile_payload.get("result") or {}
        if isinstance(compile_result, dict) and compile_result:
            summary["compile"] = {
                "status": compile_result.get("status"),
                "compiled_assembly_count": compile_result.get("compiled_assembly_count"),
                "error_count": compile_result.get("error_count"),
            }
            if "warning_count" in compile_result and compile_result.get("warning_count") is not None:
                summary["compile"]["warning_count"] = compile_result.get("warning_count")

    matrix_payload = result_payload.get("matrix") or {}
    if operation == "compile-matrix" and isinstance(matrix_payload, dict) and matrix_payload:
        summary["matrix"] = {
            "status": matrix_payload.get("status"),
            "total": matrix_payload.get("total"),
            "passed": matrix_payload.get("passed"),
            "failed": matrix_payload.get("failed"),
            "skipped": matrix_payload.get("skipped"),
        }

    tests_payload = result_payload.get("tests") or {}
    if operation == "editmode-tests" and isinstance(tests_payload, dict) and tests_payload:
        summary["tests"] = {
            "status": tests_payload.get("status"),
            "total": tests_payload.get("total"),
            "passed": tests_payload.get("passed"),
            "failed": tests_payload.get("failed"),
            "skipped": tests_payload.get("skipped"),
        }

    top_actionable_error = first_non_empty_line(
        result_payload.get("top_actionable_error") or "",
        truncate_text=truncate_text,
    )
    if not top_actionable_error:
        top_actionable_error = first_non_empty_line(
            result_payload.get("exception_message") or "",
            truncate_text=truncate_text,
        )
    if top_actionable_error:
        summary["top_actionable_error"] = top_actionable_error

    return summary


def build_batch_execution_summary(
    *,
    action: str,
    result_payload: dict[str, Any] | None,
    batch_exit_code: int,
    succeeded: bool,
    result_path: Path,
    log_path: Path,
    log_excerpt_hint: str,
    truncate_text: Callable[[Any, int], str],
) -> dict[str, Any]:
    summary = {
        "action": action,
        "phase": batch_phase_for_action(action),
        "transport_outcome": "batch_process_exited_cleanly" if batch_exit_code == 0 else "batch_process_failed",
        "unity_outcome": derive_batch_unity_outcome(result_payload, succeeded),
        "succeeded": succeeded,
        "batch_exit_code": batch_exit_code,
        "result_file": str(result_path),
        "raw_log_path": str(log_path),
        "next_step": "Inspect raw_log_path only if result_file and this summary are insufficient.",
    }
    summary.update(
        summarize_batch_result_payload(
            result_payload,
            truncate_text=truncate_text,
        )
    )
    if log_excerpt_hint and "top_actionable_error" not in summary:
        summary["log_excerpt_hint"] = log_excerpt_hint
    return summary


def build_batch_prepare_failure_summary(
    *,
    action: str,
    result_path: Path,
    log_path: Path,
    exc: Any,
    truncate_text: Callable[[Any, int], str],
) -> dict[str, Any]:
    return {
        "action": action,
        "phase": "prepare",
        "transport_outcome": "batch_prepare_blocked",
        "unity_outcome": "not_started",
        "succeeded": False,
        "top_actionable_error": first_non_empty_line(
            exc.message or exc.code,
            limit=320,
            truncate_text=truncate_text,
        ),
        "result_file": str(result_path),
        "raw_log_path": str(log_path),
        "next_step": "Resolve the prepare blocker, then rerun the batch command.",
    }


def attach_batch_summary_to_error(
    exc: Any,
    *,
    summary_path: Path,
    summary: dict[str, Any],
    tool_invocation_error_type: type,
) -> Any:
    details = dict(exc.details or {})
    details["batch_summary_file"] = str(summary_path)
    details["batch_failure_summary"] = summary
    return tool_invocation_error_type(exc.code, exc.message, details)
