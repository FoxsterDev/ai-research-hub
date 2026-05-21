from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable


DEFAULT_BATCH_PROGRESS_INTERVAL_SECONDS = 30.0


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


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return slug.strip("._") or "batch"


def build_batch_run_id(operation: str, label: str = "") -> str:
    timestamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    suffix = _slug(label or operation)
    return f"{timestamp}_{suffix}"


def batch_progress_sidecar_path(project_root: Path, run_id: str) -> Path:
    return project_root / "Library" / "XUUnityLightMcp" / "logs" / "batch" / run_id / "progress.jsonl"


class BatchProgressReporter:
    def __init__(
        self,
        *,
        run_id: str,
        operation: str,
        log_path: Path,
        progress_path: Path,
        interval_seconds: float = DEFAULT_BATCH_PROGRESS_INTERVAL_SECONDS,
        stdout: bool = True,
    ) -> None:
        self.run_id = run_id
        self.operation = operation
        self.log_path = log_path
        self.progress_path = progress_path
        self.interval_seconds = max(0.1, float(interval_seconds or DEFAULT_BATCH_PROGRESS_INTERVAL_SECONDS))
        self.stdout = stdout
        self.started_at = time.time()

    def emit(
        self,
        phase: str,
        *,
        process_alive: bool = False,
        last_known_output_path: str = "",
        message: str = "",
    ) -> dict[str, Any]:
        event = {
            "event": "batch_progress",
            "run_id": self.run_id,
            "operation": self.operation,
            "phase": phase,
            "elapsed_seconds": int(max(0.0, time.time() - self.started_at)),
            "process_alive": process_alive,
            "log_path": str(self.log_path),
            "last_known_output_path": str(last_known_output_path or ""),
            "message": message or _default_progress_message(phase),
        }
        encoded = json.dumps(event, ensure_ascii=True, separators=(",", ":"))
        self.progress_path.parent.mkdir(parents=True, exist_ok=True)
        with self.progress_path.open("a", encoding="utf-8") as handle:
            handle.write(encoded)
            handle.write("\n")
        if self.stdout:
            print(encoded, flush=True)
        return event


def _default_progress_message(phase: str) -> str:
    if phase == "preflight":
        return "Batch operation preflight started."
    if phase == "prepare_started":
        return "Batch operation preparation started."
    if phase == "prepare_completed":
        return "Batch operation preparation completed."
    if phase == "unity_batch_started":
        return "Unity batch process started."
    if phase == "unity_batch_running":
        return "Unity batch process is still running."
    if phase == "unity_batch_completed":
        return "Unity batch process completed."
    if phase == "artifact_probe_started":
        return "Artifact probe started."
    if phase == "artifact_probe_completed":
        return "Artifact probe completed."
    if phase == "side_effect_scan_completed":
        return "Workspace side-effect scan completed."
    if phase == "summary_written":
        return "Batch summary was written."
    return "Batch operation progressed."


def run_subprocess_with_progress(
    command: list[str],
    *,
    reporter: BatchProgressReporter,
    timeout_ms: int | None = None,
    last_known_output_path: str = "",
) -> tuple[int, bool]:
    timeout_seconds = timeout_ms / 1000.0 if timeout_ms is not None and timeout_ms > 0 else None
    deadline = time.time() + timeout_seconds if timeout_seconds is not None else None
    next_heartbeat_at = time.time() + reporter.interval_seconds
    timed_out = False

    reporter.emit(
        "unity_batch_started",
        process_alive=False,
        last_known_output_path=last_known_output_path,
    )
    process = subprocess.Popen(command)
    batch_exit_code = 0
    try:
        while True:
            return_code = process.poll()
            if return_code is not None:
                batch_exit_code = int(return_code)
                break

            now = time.time()
            if deadline is not None and now >= deadline:
                timed_out = True
                batch_exit_code = 124
                process.kill()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    pass
                break

            if now >= next_heartbeat_at:
                reporter.emit(
                    "unity_batch_running",
                    process_alive=True,
                    last_known_output_path=last_known_output_path,
                )
                next_heartbeat_at = now + reporter.interval_seconds

            wait_slice = min(1.0, max(0.1, reporter.interval_seconds / 10.0))
            if deadline is not None:
                wait_slice = min(wait_slice, max(0.1, deadline - now))
            try:
                batch_exit_code = int(process.wait(timeout=wait_slice))
                break
            except subprocess.TimeoutExpired:
                continue
    finally:
        reporter.emit(
            "unity_batch_completed",
            process_alive=process.poll() is None,
            last_known_output_path=last_known_output_path,
        )

    return batch_exit_code, timed_out


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
    details = dict(getattr(exc, "details", None) or {})
    summary = {
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
    for key in (
        "recommended_next_action",
        "recommended_recovery_command",
        "closeout_verification_required",
        "closeout_verification_note",
    ):
        if key in details:
            summary[key] = details[key]
    if summary.get("recommended_recovery_command"):
        summary["next_step"] = (
            "Run recommended_recovery_command, verify editor process exit, then rerun the batch command."
        )
    return summary


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
