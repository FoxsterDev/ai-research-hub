import json
from pathlib import Path
from typing import Any

from server_bridge_runtime import parse_journal_utc_timestamp, request_journal_dir
from server_core import ToolInvocationError, read_json

LIGHTWEIGHT_PACKAGE_NAME = "com.xuunity.light-mcp"
LIGHTWEIGHT_PACKAGE_TEMPLATE_MARKER = Path(
    "AIRoot/Operations/XUUnityLightUnityMcp/templates/unity-package/package.json"
)


def ensure_project_root(project_root: str) -> Path:
    root = Path(project_root).expanduser().resolve()
    if not (root / "Assets").is_dir() or not (root / "ProjectSettings" / "ProjectVersion.txt").is_file():
        raise ToolInvocationError("project_not_found", f"Not a Unity project root: {root}")
    return root


def find_latest_request_event(
    project_root: Path,
    operations: list[str] | None = None,
) -> dict[str, Any] | None:
    journal_dir = request_journal_dir(project_root)
    if not journal_dir.is_dir():
        return None

    normalized_operations = {
        str(operation).strip()
        for operation in (operations or [])
        if str(operation).strip()
    }

    matched: list[dict[str, Any]] = []
    for path in journal_dir.glob("*.json"):
        try:
            payload = read_json(path)
        except Exception:
            continue

        if not isinstance(payload, dict):
            continue

        request_id = str(payload.get("request_id") or "").strip()
        if not request_id:
            continue

        operation = str(payload.get("operation") or "").strip()
        if normalized_operations and operation not in normalized_operations:
            continue

        event = dict(payload)
        event["_path"] = str(path)
        matched.append(event)

    matched.sort(
        key=lambda item: (
            parse_journal_utc_timestamp(item.get("event_at_utc")),
            str(item.get("event_id") or ""),
        )
    )
    return matched[-1] if matched else None


def find_repo_local_package_source(project_root: Path) -> Path | None:
    for candidate_root in (project_root, *project_root.parents):
        marker = candidate_root / LIGHTWEIGHT_PACKAGE_TEMPLATE_MARKER
        if marker.is_file():
            return marker.parent.resolve()
    return None


def inspect_package_dependency_alignment(project_root: Path) -> dict[str, Any]:
    manifest_path = project_root / "Packages" / "manifest.json"
    package_source = find_repo_local_package_source(project_root)
    result: dict[str, Any] = {
        "package_name": LIGHTWEIGHT_PACKAGE_NAME,
        "manifest_path": str(manifest_path),
        "dependency": "",
        "dependency_mode": "missing",
        "repo_local_package_source": str(package_source) if package_source else "",
        "repo_local_package_source_present": package_source is not None,
        "alignment": "unknown",
        "warning": "",
    }

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        result["alignment"] = "manifest_unreadable"
        result["warning"] = f"Could not inspect manifest dependency: {exc}"
        return result

    dependencies = manifest.get("dependencies")
    if not isinstance(dependencies, dict):
        result["alignment"] = "dependencies_missing"
        result["warning"] = "Packages/manifest.json does not contain a dependencies object."
        return result

    dependency_value = dependencies.get(LIGHTWEIGHT_PACKAGE_NAME)
    if not isinstance(dependency_value, str) or not dependency_value.strip():
        result["alignment"] = "dependency_missing"
        result["warning"] = f"{LIGHTWEIGHT_PACKAGE_NAME} is not declared in Packages/manifest.json."
        return result

    dependency_value = dependency_value.strip()
    result["dependency"] = dependency_value

    if dependency_value.startswith("file:"):
        result["dependency_mode"] = "file"
        dependency_path = (manifest_path.parent / dependency_value[len("file:"):]).resolve()
        result["resolved_dependency_path"] = str(dependency_path)
        if package_source is None:
            result["alignment"] = "file_no_repo_local_reference"
        elif dependency_path == package_source:
            result["alignment"] = "aligned"
        else:
            result["alignment"] = "file_mismatch"
            result["warning"] = (
                "The project uses a file dependency, but it does not point at the repo-local "
                "AIRoot XUUnityLightUnityMcp template package."
            )
        return result

    if dependency_value.startswith(("http://", "https://", "git@", "ssh://")):
        result["dependency_mode"] = "git_or_remote"
    else:
        result["dependency_mode"] = "other"

    if package_source is not None:
        result["alignment"] = "repo_local_source_not_loaded"
        result["warning"] = (
            "A repo-local AIRoot XUUnityLightUnityMcp package source exists, but the project manifest "
            "does not currently load it through a file dependency."
        )
    else:
        result["alignment"] = "external_only"

    return result
