#!/usr/bin/env python3
import os
from pathlib import Path
from typing import Any

from server_core import read_json

RUNTIME_DEFAULTS_FILE_NAME = "xuunity_light_unity_mcp_runtime_defaults.json"
RUNTIME_ENV_OVERRIDE = "XUUNITY_LIGHT_UNITY_MCP_RUNTIME_CONFIG"
RUNTIME_USER_OVERRIDE_PATH = Path.home() / ".codex" / "xuunity-light-unity-mcp.runtime_config.json"
RUNTIME_REPO_OVERRIDE_RELATIVE_PATH = Path("AIOutput/Operations/XUUnityLightUnityMcp/runtime_config.json")


def runtime_defaults_path() -> Path:
    return Path(__file__).resolve().with_name(RUNTIME_DEFAULTS_FILE_NAME)


def bridge_runtime_config_path(project_root: Path) -> Path:
    return project_root / "Library" / "XUUnityLightMcp" / "config" / "runtime_config.json"


def find_repo_root(project_root: Path) -> Path | None:
    for candidate in (project_root.resolve(), *project_root.resolve().parents):
        if (candidate / "AIOutput" / "Operations" / "XUUnityLightUnityMcp").is_dir():
            return candidate
        if (candidate / "AIRoot" / "Operations" / "XUUnityLightUnityMcp").is_dir():
            return candidate
    return None


def runtime_project_override_path(project_root: Path) -> Path | None:
    repo_root = find_repo_root(project_root)
    if repo_root is None:
        return None
    return (
        repo_root
        / "AIOutput"
        / "Projects"
        / project_root.name
        / "Operations"
        / "XUUnityLightUnityMcp"
        / "runtime_config.json"
    )


def repo_runtime_override_path(project_root: Path) -> Path | None:
    repo_root = find_repo_root(project_root)
    if repo_root is None:
        return None
    return repo_root / RUNTIME_REPO_OVERRIDE_RELATIVE_PATH


def try_read_runtime_config_file(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.is_file():
        return None

    try:
        data = read_json(path)
    except Exception:
        return None

    return data if isinstance(data, dict) else None


def merge_dicts(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = dict(base)
    for key, value in overlay.items():
        existing = merged.get(key)
        if isinstance(existing, dict) and isinstance(value, dict):
            merged[key] = merge_dicts(existing, value)
        else:
            merged[key] = value
    return merged


def runtime_config_sources(project_root: Path) -> list[Path]:
    sources: list[Path] = [runtime_defaults_path()]

    repo_override = repo_runtime_override_path(project_root)
    if repo_override is not None:
        sources.append(repo_override)

    project_override = runtime_project_override_path(project_root)
    if project_override is not None:
        sources.append(project_override)

    sources.append(bridge_runtime_config_path(project_root))

    if RUNTIME_USER_OVERRIDE_PATH.is_file():
        sources.append(RUNTIME_USER_OVERRIDE_PATH)

    env_override = os.environ.get(RUNTIME_ENV_OVERRIDE, "").strip()
    if env_override:
        sources.append(Path(env_override).expanduser().resolve())

    return sources


def load_runtime_config(project_root: Path) -> tuple[dict[str, Any], list[str]]:
    merged: dict[str, Any] = {}
    loaded_paths: list[str] = []

    for path in runtime_config_sources(project_root):
        payload = try_read_runtime_config_file(path)
        if payload is None:
            continue
        merged = merge_dicts(merged, payload)
        loaded_paths.append(str(path))

    return merged, loaded_paths


def resolve_operation_runtime_settings(project_root: Path, operation: str) -> dict[str, Any]:
    config, _ = load_runtime_config(project_root)
    operations = config.get("operations")
    if not isinstance(operations, dict):
        return {}
    settings = operations.get(operation)
    return dict(settings) if isinstance(settings, dict) else {}


def resolve_operation_default_timeout_ms(project_root: Path, operation: str, fallback: int) -> int:
    settings = resolve_operation_runtime_settings(project_root, operation)
    value = settings.get("default_timeout_ms")
    return int(value) if isinstance(value, int) and value > 0 else fallback


def resolve_operation_lifecycle_policy_overrides(project_root: Path, operation: str) -> dict[str, Any]:
    settings = resolve_operation_runtime_settings(project_root, operation)
    overrides: dict[str, Any] = {}
    cap_ms = settings.get("post_reset_recovery_cap_ms")
    if isinstance(cap_ms, int) and cap_ms > 0:
        overrides["post_reset_recovery_cap_ms"] = cap_ms
    return overrides


def build_runtime_config_report(project_root: Path) -> dict[str, Any]:
    config, loaded_paths = load_runtime_config(project_root)
    return {
        "project_root": str(project_root),
        "loaded_paths": loaded_paths,
        "config": config,
    }
