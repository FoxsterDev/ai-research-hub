from __future__ import annotations

import fnmatch
import json
import zipfile
from pathlib import Path
from typing import Any, Callable


def load_artifact_probe_config(
    *,
    artifact_probe_file: str = "",
    artifact_probe_json: str = "",
    tool_error_type: type[Exception],
) -> dict[str, Any] | None:
    if artifact_probe_file:
        path = Path(artifact_probe_file).expanduser().resolve()
        if not path.is_file():
            raise tool_error_type("artifact_probe_file_not_found", f"Artifact probe file not found: {path}")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise tool_error_type("artifact_probe_file_invalid", str(exc)) from exc
        if not isinstance(payload, dict):
            raise tool_error_type("artifact_probe_file_invalid", "Artifact probe file must contain a JSON object.")
        return payload

    if artifact_probe_json:
        try:
            payload = json.loads(artifact_probe_json)
        except json.JSONDecodeError as exc:
            raise tool_error_type("artifact_probe_json_invalid", str(exc)) from exc
        if not isinstance(payload, dict):
            raise tool_error_type("artifact_probe_json_invalid", "Artifact probe JSON must be an object.")
        return payload

    return None


def run_artifact_probe(
    config: dict[str, Any] | None,
    *,
    artifact_path_override: str = "",
    truncate_text: Callable[[Any, int], str],
) -> dict[str, Any]:
    artifact_path_text = str(artifact_path_override or (config or {}).get("artifactPath") or "")
    artifact_path = Path(artifact_path_text).expanduser().resolve() if artifact_path_text else None
    expectations = (config or {}).get("expectations") if isinstance(config, dict) else []
    expectation_items = expectations if isinstance(expectations, list) else []
    stop_on_first_failure = bool((config or {}).get("stopOnFirstFailure", False)) if isinstance(config, dict) else False

    results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    artifact_exists = artifact_path.exists() if artifact_path is not None else False

    for index, raw_expectation in enumerate(expectation_items):
        if not isinstance(raw_expectation, dict):
            result = _result(
                expectation_id=f"expectation_{index + 1}",
                kind="invalid",
                passed=False,
                message="Expectation must be a JSON object.",
            )
        else:
            result = _run_expectation(raw_expectation, artifact_path, artifact_exists, truncate_text=truncate_text)

        results.append(result)
        if not bool(result.get("passed")) and not bool(result.get("skipped")):
            failures.append(_failure(result))
            if stop_on_first_failure:
                break

    passed_count = sum(1 for item in results if bool(item.get("passed")))
    skipped_count = sum(1 for item in results if bool(item.get("skipped")))
    failed_count = sum(1 for item in results if not bool(item.get("passed")) and not bool(item.get("skipped")))

    return {
        "enabled": config is not None,
        "artifact_path": str(artifact_path) if artifact_path is not None else "",
        "artifact_exists": artifact_exists,
        "expectation_count": len(expectation_items),
        "passed_count": passed_count,
        "failed_count": failed_count,
        "skipped_count": skipped_count,
        "succeeded": config is not None and failed_count == 0 and (artifact_exists or len(expectation_items) == 0),
        "failures": failures,
        "results": results,
    }


def _result(
    *,
    expectation_id: str,
    kind: str,
    passed: bool,
    message: str,
    path: str = "",
    skipped: bool = False,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": expectation_id,
        "kind": kind,
        "passed": passed,
        "message": message,
    }
    if path:
        result["path"] = path
    if skipped:
        result["skipped"] = True
    return result


def _failure(result: dict[str, Any]) -> dict[str, Any]:
    failure = {
        "id": str(result.get("id") or ""),
        "kind": str(result.get("kind") or ""),
        "message": str(result.get("message") or ""),
    }
    if result.get("path"):
        failure["path"] = str(result.get("path") or "")
    return failure


def _run_expectation(
    expectation: dict[str, Any],
    artifact_path: Path | None,
    artifact_exists: bool,
    *,
    truncate_text: Callable[[Any, int], str],
) -> dict[str, Any]:
    expectation_id = str(expectation.get("id") or "expectation")
    kind = str(expectation.get("kind") or "").strip()
    probe_path = str(expectation.get("path") or "").strip()

    if artifact_path is None:
        return _result(
            expectation_id=expectation_id,
            kind=kind,
            passed=False,
            message="No artifact path was provided.",
            path=probe_path,
        )
    if not artifact_exists:
        return _result(
            expectation_id=expectation_id,
            kind=kind,
            passed=False,
            message="Artifact does not exist.",
            path=probe_path,
        )

    if kind in {"zip_entry_exists", "zip_entry_absent", "zip_entry_glob_exists", "android_manifest_contains"}:
        return _run_zip_expectation(
            expectation,
            artifact_path,
            expectation_id=expectation_id,
            kind=kind,
            probe_path=probe_path,
            truncate_text=truncate_text,
        )

    if kind == "file_exists":
        target = _resolve_file_target(artifact_path, probe_path)
        return _result(
            expectation_id=expectation_id,
            kind=kind,
            passed=target.exists(),
            message="File exists." if target.exists() else "File is missing.",
            path=str(target),
        )

    if kind == "file_contains":
        target = _resolve_file_target(artifact_path, probe_path)
        expected_value = str(expectation.get("value") or "")
        if not target.is_file():
            return _result(
                expectation_id=expectation_id,
                kind=kind,
                passed=False,
                message="File is missing.",
                path=str(target),
            )
        try:
            content = target.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            return _result(
                expectation_id=expectation_id,
                kind=kind,
                passed=False,
                message=truncate_text(str(exc), 240),
                path=str(target),
            )
        return _result(
            expectation_id=expectation_id,
            kind=kind,
            passed=expected_value in content,
            message="Required text was found." if expected_value in content else "Required text was not found.",
            path=str(target),
        )

    return _result(
        expectation_id=expectation_id,
        kind=kind or "missing",
        passed=False,
        message=f"Unsupported artifact probe kind '{kind}'.",
        path=probe_path,
    )


def _run_zip_expectation(
    expectation: dict[str, Any],
    artifact_path: Path,
    *,
    expectation_id: str,
    kind: str,
    probe_path: str,
    truncate_text: Callable[[Any, int], str],
) -> dict[str, Any]:
    try:
        with zipfile.ZipFile(artifact_path, "r") as archive:
            names = archive.namelist()
            if kind == "zip_entry_exists":
                passed = probe_path in names
                return _result(
                    expectation_id=expectation_id,
                    kind=kind,
                    passed=passed,
                    message="Entry exists." if passed else "Entry is missing.",
                    path=probe_path,
                )
            if kind == "zip_entry_absent":
                passed = probe_path not in names
                return _result(
                    expectation_id=expectation_id,
                    kind=kind,
                    passed=passed,
                    message="Entry is absent." if passed else "Entry exists.",
                    path=probe_path,
                )
            if kind == "zip_entry_glob_exists":
                passed = any(fnmatch.fnmatch(name, probe_path) for name in names)
                return _result(
                    expectation_id=expectation_id,
                    kind=kind,
                    passed=passed,
                    message="Matching entry exists." if passed else "Matching entry is missing.",
                    path=probe_path,
                )

            expected_value = str(expectation.get("value") or "")
            manifest_paths = [name for name in names if name.endswith("AndroidManifest.xml")]
            for manifest_path in manifest_paths:
                content = archive.read(manifest_path)
                if expected_value.encode("utf-8") in content or expected_value in content.decode("utf-8", errors="ignore"):
                    return _result(
                        expectation_id=expectation_id,
                        kind=kind,
                        passed=True,
                        message="Manifest contains required text.",
                        path=manifest_path,
                    )
            return _result(
                expectation_id=expectation_id,
                kind=kind,
                passed=False,
                message="Manifest does not contain required text.",
                path="AndroidManifest.xml",
            )
    except (OSError, zipfile.BadZipFile) as exc:
        return _result(
            expectation_id=expectation_id,
            kind=kind,
            passed=False,
            message=truncate_text(str(exc), 240),
            path=probe_path,
        )


def _resolve_file_target(artifact_path: Path, probe_path: str) -> Path:
    if artifact_path.is_dir():
        return (artifact_path / probe_path).resolve()
    if probe_path:
        return (artifact_path.parent / probe_path).resolve()
    return artifact_path
