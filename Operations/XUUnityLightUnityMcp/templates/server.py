#!/usr/bin/env python3
import argparse
import calendar
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any

PROTOCOL_VERSION = "2025-06-18"
SERVER_INFO = {
    "name": "xuunity-light-unity-mcp",
    "version": "0.3.9",
}
LIGHTWEIGHT_PACKAGE_NAME = "com.xuunity.light-mcp"
LIGHTWEIGHT_PACKAGE_TEMPLATE_MARKER = Path(
    "AIRoot/Operations/XUUnityLightUnityMcp/templates/unity-package/package.json"
)

STARTUP_POLICIES = {
    "auto_enter_safe_mode_preferred",
    "batch_compile_lane",
    "fail_fast_on_interactive_compile_block",
}

DEFAULT_BRIDGE_TRANSPORT = "file_ipc"
TCP_LOOPBACK_BRIDGE_TRANSPORT = "tcp_loopback"
SUPPORTED_BRIDGE_TRANSPORTS = {
    DEFAULT_BRIDGE_TRANSPORT,
    TCP_LOOPBACK_BRIDGE_TRANSPORT,
}

ACTIVATION_DELAY_SECONDS = 0.35
DEFAULT_HEARTBEAT_MAX_AGE_SECONDS = 10
DEFAULT_IDLE_STABLE_CYCLES = 2
SCENARIO_TERMINAL_STATUSES = {"passed", "failed"}

OPERATION_LIFECYCLE_POLICIES: dict[str, dict[str, Any]] = {
    "unity.status": {
        "retry_on_lifecycle_reset": True,
    },
    "unity.capabilities.get": {
        "retry_on_lifecycle_reset": True,
    },
    "unity.health.probe": {
        "retry_on_lifecycle_reset": True,
    },
    "unity.project.refresh": {
        "activate_unity": True,
        "wait_for_idle_before": True,
        "wait_for_idle_after": True,
        "idle_stable_cycles_after": 2,
        "retry_on_lifecycle_reset": True,
    },
    "unity.scene.snapshot": {
        "retry_on_lifecycle_reset": True,
    },
    "unity.scenario.validate": {
        "retry_on_lifecycle_reset": True,
    },
    "unity.compile.player_scripts": {
        "activate_unity": True,
        "wait_for_idle_before": True,
        "wait_for_idle_after": True,
        "idle_stable_cycles_after": 2,
    },
    "unity.compile.matrix": {
        "activate_unity": True,
        "wait_for_idle_before": True,
        "wait_for_idle_after": True,
        "idle_stable_cycles_after": 2,
    },
    "unity.tests.run_editmode": {
        "activate_unity": True,
        "wait_for_idle_before": True,
        "wait_for_idle_after": True,
        "idle_stable_cycles_after": 2,
    },
    "unity.playmode.set": {
        "activate_unity": True,
        "wait_for_idle_before": True,
        "wait_for_idle_after": True,
        "idle_stable_cycles_after": 2,
    },
    "unity.game_view.configure": {
        "activate_unity": True,
        "wait_for_idle_before": True,
        "wait_for_idle_after": True,
        "idle_stable_cycles_after": 2,
    },
    "unity.game_view.screenshot": {
        "activate_unity": True,
        "wait_for_idle_before": True,
        "wait_for_idle_after": False,
        "idle_stable_cycles_after": 1,
    },
    "unity.scenario.run": {
        "activate_unity": True,
        "wait_for_idle_before": True,
        "wait_for_idle_after": False,
        "idle_stable_cycles_after": 1,
    },
}

SCENARIO_STEP_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "stepId": {"type": "string"},
        "kind": {
            "type": "string",
            "enum": [
                "status",
                "health_probe",
                "scene_snapshot",
                "project_refresh",
                "console_tail",
                "playmode_set",
                "wait",
                "wait_for_playmode_state",
                "assert_playmode_state",
                "game_view_screenshot",
                "compile_player_scripts",
                "tests_run_editmode",
                "game_view_configure",
                "project_defined_hook",
            ],
        },
        "action": {
            "type": "string",
            "enum": ["enter", "exit", "pause", "resume"],
        },
        "durationSeconds": {
            "type": "number",
            "minimum": 0.0,
        },
        "timeoutSeconds": {
            "type": "number",
            "minimum": 0.1,
        },
        "expectedPlaymodeState": {
            "type": "string",
            "enum": ["edit", "playing", "paused", "transitioning"],
        },
        "limit": {
            "type": "integer",
            "minimum": 1,
        },
        "includeTypes": {
            "type": "array",
            "items": {"type": "string"},
        },
        "fileName": {"type": "string"},
        "includeImage": {"type": "boolean"},
        "maxResolution": {"type": "integer", "minimum": 1},
        "target": {"type": "string"},
        "optionFlags": {"type": "array", "items": {"type": "string"}},
        "extraDefines": {"type": "array", "items": {"type": "string"}},
        "name": {"type": "string"},
        "width": {"type": "integer", "minimum": 1},
        "height": {"type": "integer", "minimum": 1},
        "group": {"type": "string"},
        "label": {"type": "string"},
        "allowCreateCustomSize": {"type": "boolean"},
        "forceAssetRefresh": {"type": "boolean"},
        "resolvePackages": {"type": "boolean"},
        "rerunHealthProbe": {"type": "boolean"},
        "hookName": {"type": "string"},
        "hookPayloadJson": {"type": "string"},
    },
    "required": ["kind"],
}

SCENARIO_DEFINITION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "description": {"type": "string"},
        "stopOnFirstFailure": {"type": "boolean", "default": True},
        "steps": {
            "type": "array",
            "items": SCENARIO_STEP_SCHEMA,
            "minItems": 1,
        },
    },
    "required": ["name", "steps"],
}

TOOLS: dict[str, dict[str, Any]] = {
    "unity_status": {
        "bridgeOperation": "unity.status",
        "description": "Return normalized Unity editor and bridge readiness state for one project.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "projectRoot": {
                    "type": "string",
                    "description": "Absolute or user-home-relative path to the Unity project root."
                },
                "timeoutMs": {
                    "type": "integer",
                    "description": "How long to wait for a bridge response.",
                    "default": 5000,
                    "minimum": 1000
                }
            },
            "required": ["projectRoot"]
        }
    },
    "unity_capabilities": {
        "bridgeOperation": "unity.capabilities.get",
        "description": "Return the persisted Unity capability and health report used to gate version-sensitive operations.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "projectRoot": {"type": "string"},
                "timeoutMs": {"type": "integer", "default": 5000, "minimum": 1000}
            },
            "required": ["projectRoot"]
        }
    },
    "unity_health_probe": {
        "bridgeOperation": "unity.health.probe",
        "description": "Re-run Unity-side health checks and persist a fresh capability report for this project and editor version.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "projectRoot": {"type": "string"},
                "timeoutMs": {"type": "integer", "default": 15000, "minimum": 1000}
            },
            "required": ["projectRoot"]
        }
    },
    "unity_project_refresh": {
        "bridgeOperation": "unity.project.refresh",
        "description": "Refresh AssetDatabase, optionally request package resolve, and optionally persist a fresh capability report.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "projectRoot": {"type": "string"},
                "forceAssetRefresh": {"type": "boolean", "default": True},
                "resolvePackages": {"type": "boolean", "default": True},
                "rerunHealthProbe": {"type": "boolean", "default": True},
                "timeoutMs": {"type": "integer", "default": 30000, "minimum": 1000}
            },
            "required": ["projectRoot"]
        }
    },
    "unity_console_tail": {
        "bridgeOperation": "unity.console.tail",
        "description": "Return recent Unity console items in normalized form.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "projectRoot": {"type": "string"},
                "limit": {"type": "integer", "default": 50, "minimum": 1},
                "includeTypes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Subset of log, warning, error, exception."
                },
                "timeoutMs": {"type": "integer", "default": 5000, "minimum": 1000}
            },
            "required": ["projectRoot"]
        }
    },
    "unity_scene_snapshot": {
        "bridgeOperation": "unity.scene.snapshot",
        "description": "Return a lightweight normalized snapshot of the currently active scene.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "projectRoot": {"type": "string"},
                "timeoutMs": {"type": "integer", "default": 5000, "minimum": 1000}
            },
            "required": ["projectRoot"]
        }
    },
    "unity_tests_run_editmode": {
        "bridgeOperation": "unity.tests.run_editmode",
        "description": "Run Unity EditMode tests and return normalized result accounting.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "projectRoot": {"type": "string"},
                "timeoutMs": {"type": "integer", "default": 600000, "minimum": 1000}
            },
            "required": ["projectRoot"]
        }
    },
    "unity_playmode_state": {
        "bridgeOperation": "unity.playmode.state",
        "description": "Return normalized Unity play mode state for one project.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "projectRoot": {"type": "string"},
                "timeoutMs": {"type": "integer", "default": 5000, "minimum": 1000}
            },
            "required": ["projectRoot"]
        }
    },
    "unity_playmode_set": {
        "bridgeOperation": "unity.playmode.set",
        "description": "Request a Unity play mode state transition or pause control.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "projectRoot": {"type": "string"},
                "action": {
                    "type": "string",
                    "enum": ["enter", "exit", "pause", "resume"]
                },
                "timeoutMs": {"type": "integer", "default": 15000, "minimum": 1000}
            },
            "required": ["projectRoot", "action"]
        }
    },
    "unity_game_view_configure": {
        "bridgeOperation": "unity.game_view.configure",
        "description": "Set the active Unity Game View to a specific fixed resolution.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "projectRoot": {"type": "string"},
                "width": {"type": "integer", "minimum": 1},
                "height": {"type": "integer", "minimum": 1},
                "group": {"type": "string", "description": "Optional active group override; must match the current build group."},
                "label": {"type": "string", "description": "Optional custom label for a newly created resolution entry."},
                "allowCreateCustomSize": {
                    "type": "boolean",
                    "default": False,
                    "description": "When false, fail if the requested size is not already available in Unity Game View."
                },
                "timeoutMs": {"type": "integer", "default": 10000, "minimum": 1000}
            },
            "required": ["projectRoot", "width", "height"]
        }
    },
    "unity_game_view_screenshot": {
        "bridgeOperation": "unity.game_view.screenshot",
        "description": "Capture a screenshot from the Unity Editor Game View.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "projectRoot": {"type": "string"},
                "fileName": {"type": "string"},
                "includeImage": {"type": "boolean", "default": False},
                "maxResolution": {"type": "integer", "default": 640, "minimum": 1},
                "timeoutMs": {"type": "integer", "default": 10000, "minimum": 1000}
            },
            "required": ["projectRoot"]
        }
    },
    "unity_compile_player_scripts": {
        "bridgeOperation": "unity.compile.player_scripts",
        "description": "Compile Unity player scripts for one target/options/defines combination without switching the active build target.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "projectRoot": {"type": "string"},
                "target": {"type": "string", "description": "Unity BuildTarget enum name, for example StandaloneOSX, StandaloneWindows64, Android, or iOS."},
                "optionFlags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional ScriptCompilationOptions flag names, for example DevelopmentBuild."
                },
                "extraDefines": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional extra scripting defines for this compile only."
                },
                "name": {"type": "string", "description": "Optional display name for this compile configuration."},
                "timeoutMs": {"type": "integer", "default": 120000, "minimum": 1000}
            },
            "required": ["projectRoot", "target"]
        }
    },
    "unity_compile_matrix": {
        "bridgeOperation": "unity.compile.matrix",
        "description": "Run a sequence of compile checks across multiple targets/options/defines combinations without switching active build target.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "projectRoot": {"type": "string"},
                "stopOnFirstFailure": {"type": "boolean", "default": False},
                "configurations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "target": {"type": "string"},
                            "optionFlags": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "extraDefines": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        },
                        "required": ["target"]
                    },
                    "minItems": 1
                },
                "timeoutMs": {"type": "integer", "default": 300000, "minimum": 1000}
            },
            "required": ["projectRoot", "configurations"]
        }
    },
    "unity_compile_build_config_matrix": {
        "description": "Resolve build profiles from the project's Unity build-config asset and run the Android/iOS compile matrix through unity.compile.matrix.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "projectRoot": {"type": "string"},
                "buildConfigAsset": {
                    "type": "string",
                    "description": "Optional project-relative or absolute path to the Unity *BuildConfiguration.asset. When omitted, the tool auto-detects a single matching asset in the project."
                },
                "profiles": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional subset of build profile names from the asset Configurations list."
                },
                "targets": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["Android", "iOS"]
                    },
                    "description": "Optional subset of compile targets. Defaults to Android and iOS."
                },
                "stopOnFirstFailure": {"type": "boolean", "default": False},
                "timeoutMs": {"type": "integer", "default": 300000, "minimum": 1000}
            },
            "required": ["projectRoot"]
        }
    },
    "unity_scenario_validate": {
        "bridgeOperation": "unity.scenario.validate",
        "description": "Validate a scripted Unity automation scenario before execution.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "projectRoot": {"type": "string"},
                "scenario": SCENARIO_DEFINITION_SCHEMA,
                "timeoutMs": {"type": "integer", "default": 5000, "minimum": 1000},
            },
            "required": ["projectRoot", "scenario"],
        },
    },
    "unity_scenario_run": {
        "bridgeOperation": "unity.scenario.run",
        "description": "Start a scripted Unity automation scenario. Execution continues asynchronously inside the Unity editor update loop.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "projectRoot": {"type": "string"},
                "scenario": SCENARIO_DEFINITION_SCHEMA,
                "timeoutMs": {"type": "integer", "default": 5000, "minimum": 1000},
            },
            "required": ["projectRoot", "scenario"],
        },
    },
    "unity_scenario_result": {
        "bridgeOperation": "unity.scenario.result",
        "description": "Read the current or completed result of a previously started Unity automation scenario.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "projectRoot": {"type": "string"},
                "runId": {"type": "string"},
                "scenarioName": {"type": "string"},
                "timeoutMs": {"type": "integer", "default": 5000, "minimum": 1000},
            },
            "required": ["projectRoot"],
        },
    },
    "unity_scenario_run_and_wait": {
        "description": "Start a Unity automation scenario and wait until it reaches a terminal state.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "projectRoot": {"type": "string"},
                "scenario": SCENARIO_DEFINITION_SCHEMA,
                "timeoutMs": {"type": "integer", "default": 120000, "minimum": 1000},
                "pollIntervalMs": {"type": "integer", "default": 1000, "minimum": 100},
            },
            "required": ["projectRoot", "scenario"],
        },
    }
}


def ensure_project_root(project_root: str) -> Path:
    root = Path(project_root).expanduser().resolve()
    if not (root / "Assets").is_dir() or not (root / "ProjectSettings" / "ProjectVersion.txt").is_file():
        raise ToolInvocationError("project_not_found", f"Not a Unity project root: {root}")
    return root


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


def bridge_root(project_root: Path) -> Path:
    return project_root / "Library" / "XUUnityLightMcp"


def bridge_state_path(project_root: Path) -> Path:
    return bridge_root(project_root) / "state" / "bridge_state.json"


def host_editor_session_state_path(project_root: Path) -> Path:
    return bridge_root(project_root) / "state" / "host_editor_session.json"


def bridge_config_path(project_root: Path) -> Path:
    return bridge_root(project_root) / "config" / "bridge_config.json"


def inbox_dir(project_root: Path) -> Path:
    return bridge_root(project_root) / "inbox"


def outbox_dir(project_root: Path) -> Path:
    return bridge_root(project_root) / "outbox"


def logs_dir(project_root: Path) -> Path:
    return bridge_root(project_root) / "logs"


def default_editor_log_path(project_root: Path) -> Path:
    return logs_dir(project_root) / "unity_editor.log"


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=True)
        handle.write("\n")


def print_json(data: Any) -> None:
    json.dump(data, sys.stdout, indent=2, ensure_ascii=True)
    sys.stdout.write("\n")


class ToolInvocationError(Exception):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


def request_journal_dir(project_root: Path) -> Path:
    return bridge_root(project_root) / "journal" / "requests"


def bridge_identity_from_state(state: dict[str, Any] | None) -> tuple[int, str]:
    if not state:
        return 0, ""

    generation = int(state.get("bridge_generation") or 0)
    session_id = str(state.get("bridge_session_id") or "")
    return generation, session_id


def bridge_identity_changed(
    initial_generation: int,
    initial_session_id: str,
    state: dict[str, Any] | None,
) -> bool:
    current_generation, current_session_id = bridge_identity_from_state(state)
    if current_generation <= 0 and not current_session_id:
        return False

    if initial_generation > 0 and current_generation != initial_generation:
        return True

    if initial_session_id and current_session_id and current_session_id != initial_session_id:
        return True

    return False


def write_host_request_journal_event(
    project_root: Path,
    event_type: str,
    payload: dict[str, Any],
) -> Path:
    journal_dir = request_journal_dir(project_root)
    journal_dir.mkdir(parents=True, exist_ok=True)
    compact_utc = time.strftime("%Y%m%dT%H%M%S", time.gmtime()) + f"{int((time.time() % 1) * 1000):03d}Z"
    event_id = f"{compact_utc}_{uuid.uuid4().hex}_{event_type}"
    path = journal_dir / f"{event_id}.json"
    data = dict(payload)
    data.setdefault("event_id", event_id)
    data.setdefault("event_type", event_type)
    data.setdefault("event_source", "host_wrapper")
    data.setdefault("event_at_utc", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    data.setdefault("project_root", str(project_root))
    write_json(path, data)
    return path


def maybe_record_settle_lifecycle_transition(
    project_root: Path,
    operation: str,
    request_id: str,
    before_state: dict[str, Any] | None,
    after_state: dict[str, Any] | None,
) -> dict[str, Any] | None:
    initial_generation, initial_session_id = bridge_identity_from_state(before_state)
    current_generation, current_session_id = bridge_identity_from_state(after_state)
    if not bridge_identity_changed(initial_generation, initial_session_id, after_state):
        return None

    journal_path = write_host_request_journal_event(
        project_root,
        "request_reclassified",
        {
            "request_id": request_id,
            "operation": operation,
            "reason": "bridge_generation_changed_during_post_request_settle",
            "retryable": False,
            "reclassified_status": "settled_after_lifecycle_reset",
            "previous_bridge_generation": initial_generation,
            "previous_bridge_session_id": initial_session_id,
            "bridge_generation": current_generation,
            "bridge_session_id": current_session_id,
        },
    )
    return {
        "request_id": request_id,
        "operation": operation,
        "previous_bridge_generation": initial_generation,
        "previous_bridge_session_id": initial_session_id,
        "current_bridge_generation": current_generation,
        "current_bridge_session_id": current_session_id,
        "journal_event_path": str(journal_path),
        "reclassified_status": "settled_after_lifecycle_reset",
    }


def bridge_enabled(project_root: Path) -> bool:
    config_path = bridge_config_path(project_root)
    if not config_path.is_file():
        return False

    try:
        data = read_json(config_path)
    except Exception:
        return False

    return bool(data.get("enabled"))


def try_read_bridge_config(project_root: Path) -> dict[str, Any] | None:
    config_path = bridge_config_path(project_root)
    if not config_path.is_file():
        return None

    try:
        data = read_json(config_path)
    except Exception:
        return None

    return data if isinstance(data, dict) else None


def try_read_host_editor_session_state(project_root: Path) -> dict[str, Any] | None:
    path = host_editor_session_state_path(project_root)
    if not path.is_file():
        return None

    try:
        data = read_json(path)
    except Exception:
        return None

    return data if isinstance(data, dict) else None


def write_host_editor_session_state(project_root: Path, data: dict[str, Any]) -> None:
    write_json(host_editor_session_state_path(project_root), data)


def clear_host_editor_session_state(project_root: Path) -> None:
    path = host_editor_session_state_path(project_root)
    try:
        if path.exists():
            path.unlink()
    except OSError:
        pass


def read_best_effort_bridge_state(project_root: Path) -> dict[str, Any] | None:
    live_state = try_read_live_editor_state(project_root)
    if live_state is not None:
        return live_state

    state = try_read_bridge_state(project_root)
    if state is None:
        return None

    pid = int(state.get("editor_pid") or 0)
    if pid > 0 and not pid_is_alive(pid):
        return None

    return state


class BridgeTransportAdapter:
    name = "unknown"

    def metadata(self, project_root: Path) -> dict[str, Any]:
        return {
            "name": self.name,
        }

    def invoke(
        self,
        project_root: Path,
        operation: str,
        args: dict[str, Any],
        timeout_ms: int,
    ) -> tuple[dict[str, Any], str, float]:
        raise NotImplementedError


class FileIpcBridgeTransport(BridgeTransportAdapter):
    name = DEFAULT_BRIDGE_TRANSPORT

    def metadata(self, project_root: Path) -> dict[str, Any]:
        return {
            "name": self.name,
            "state_path": str(bridge_state_path(project_root)),
            "request_directory": str(inbox_dir(project_root)),
            "response_directory": str(outbox_dir(project_root)),
            "journal_directory": str(request_journal_dir(project_root)),
        }

    def invoke(
        self,
        project_root: Path,
        operation: str,
        args: dict[str, Any],
        timeout_ms: int,
    ) -> tuple[dict[str, Any], str, float]:
        state_path = bridge_state_path(project_root)
        if not state_path.is_file():
            raise ToolInvocationError("editor_not_running", f"Bridge state file not found: {state_path}")

        in_dir = inbox_dir(project_root)
        out_dir = outbox_dir(project_root)
        in_dir.mkdir(parents=True, exist_ok=True)
        out_dir.mkdir(parents=True, exist_ok=True)

        request_id = str(uuid.uuid4())
        request_path = in_dir / f"{request_id}.json"
        response_path = out_dir / f"{request_id}.json"
        request_started_at = time.time()
        initial_state = read_best_effort_bridge_state(project_root)
        initial_generation, initial_session_id = bridge_identity_from_state(initial_state)
        observed_reset_state: dict[str, Any] | None = None

        request = {
            "request_id": request_id,
            "operation": operation,
            "project_root": str(project_root),
            "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "timeout_ms": timeout_ms,
            "args_json": json.dumps(args, ensure_ascii=True, separators=(",", ":")),
        }

        write_json(request_path, request)

        deadline = time.time() + (timeout_ms / 1000.0)
        while time.time() < deadline:
            if response_path.is_file():
                try:
                    response = read_json(response_path)
                finally:
                    try:
                        response_path.unlink()
                    except OSError:
                        pass
                return response, request_id, request_started_at

            current_state = read_best_effort_bridge_state(project_root)
            if observed_reset_state is None and bridge_identity_changed(initial_generation, initial_session_id, current_state):
                observed_reset_state = current_state

            time.sleep(0.2)

        state = read_best_effort_bridge_state(project_root)
        if observed_reset_state is not None:
            state = state or observed_reset_state
            current_generation, current_session_id = bridge_identity_from_state(state)
            processed = str((state or {}).get("last_processed_request_id") or "") == request_id
            retryable = not processed
            journal_path = write_host_request_journal_event(
                project_root,
                "request_reclassified",
                {
                    "request_id": request_id,
                    "operation": operation,
                    "reason": "bridge_generation_changed_before_response",
                    "retryable": retryable,
                    "reclassified_status": (
                        "retryable_after_lifecycle_reset"
                        if retryable
                        else "response_missing_after_lifecycle_reset"
                    ),
                    "previous_bridge_generation": initial_generation,
                    "previous_bridge_session_id": initial_session_id,
                    "bridge_generation": current_generation,
                    "bridge_session_id": current_session_id,
                },
            )
            try:
                if request_path.exists():
                    request_path.unlink()
            except OSError:
                pass
            details = {
                "request_id": request_id,
                "operation": operation,
                "transport": self.name,
                "initial_bridge_generation": initial_generation,
                "initial_bridge_session_id": initial_session_id,
                "current_bridge_generation": current_generation,
                "current_bridge_session_id": current_session_id,
                "retryable": retryable,
                "request_processed": processed,
                "journal_event_path": str(journal_path),
            }
            if retryable:
                raise ToolInvocationError(
                    "request_lifecycle_reset",
                    (
                        f"Request {request_id} for {operation} crossed a bridge lifecycle reset before a response was observed. "
                        f"Previous bridge_generation={initial_generation}, current bridge_generation={current_generation}. "
                        f"transport={self.name}. journal_event={journal_path}."
                    ),
                    details,
                )

            raise ToolInvocationError(
                "response_missing_after_lifecycle_reset",
                (
                    f"Request {request_id} for {operation} appears processed, but its response was not observed after a bridge lifecycle reset. "
                    f"Previous bridge_generation={initial_generation}, current bridge_generation={current_generation}. "
                    f"transport={self.name}. journal_event={journal_path}. {summarize_state_for_error(state)}"
                ),
                details,
            )

        raise ToolInvocationError(
            "operation_timeout",
            f"Timed out waiting for {response_path}. transport={self.name}. {summarize_state_for_error(state)}",
        )


class TcpLoopbackBridgeTransport(BridgeTransportAdapter):
    name = TCP_LOOPBACK_BRIDGE_TRANSPORT

    def metadata(self, project_root: Path) -> dict[str, Any]:
        state = read_best_effort_bridge_state(project_root) or try_read_bridge_state(project_root) or {}
        return {
            "name": self.name,
            "requested_transport": str(state.get("transport_requested") or self.name),
            "listener_state": str(state.get("transport_listener_state") or ""),
            "host": str(state.get("transport_host") or "127.0.0.1"),
            "port": int(state.get("transport_port") or 0),
            "state_path": str(bridge_state_path(project_root)),
            "journal_directory": str(request_journal_dir(project_root)),
        }

    def invoke(
        self,
        project_root: Path,
        operation: str,
        args: dict[str, Any],
        timeout_ms: int,
    ) -> tuple[dict[str, Any], str, float]:
        raw_state = try_read_bridge_state(project_root)
        state = read_best_effort_bridge_state(project_root)
        if state is None and raw_state is not None:
            liveness = inspect_bridge_state_liveness(raw_state)
            if not bool(liveness.get("editor_pid_alive")):
                stale_pid = int(liveness.get("editor_pid") or 0)
                stale_listener_state = str(raw_state.get("transport_listener_state") or "")
                stale_host = str(raw_state.get("transport_host") or "127.0.0.1")
                stale_port = int(raw_state.get("transport_port") or 0)
                raise ToolInvocationError(
                    "editor_not_running",
                    (
                        "Unity editor is not running for this project. "
                        f"Found stale bridge state with editor_pid={stale_pid}, "
                        f"listener_state={stale_listener_state or 'unknown'}, "
                        f"host={stale_host}, port={stale_port}. "
                        "Reopen Unity or run ensure-ready --open-editor."
                    ),
                    {
                        "transport": self.name,
                        "state_path": str(bridge_state_path(project_root)),
                        "state_liveness": liveness,
                    },
                )

        host = str((state or {}).get("transport_host") or "127.0.0.1")
        port = int((state or {}).get("transport_port") or 0)
        listener_state = str((state or {}).get("transport_listener_state") or "")
        if port <= 0:
            raise ToolInvocationError(
                "transport_not_ready",
                (
                    f"TCP loopback transport is not ready. "
                    f"listener_state={listener_state or 'unknown'} host={host} port={port}."
                ),
            )

        request_id = str(uuid.uuid4())
        request_started_at = time.time()
        initial_state = state
        initial_generation, initial_session_id = bridge_identity_from_state(initial_state)
        observed_reset_state: dict[str, Any] | None = None
        request = {
            "request_id": request_id,
            "operation": operation,
            "project_root": str(project_root),
            "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "timeout_ms": timeout_ms,
            "args_json": json.dumps(args, ensure_ascii=True, separators=(",", ":")),
        }
        payload = (json.dumps(request, ensure_ascii=True, separators=(",", ":")) + "\n").encode("utf-8")
        deadline = time.time() + (timeout_ms / 1000.0)
        chunks: list[bytes] = []

        try:
            connect_timeout = max(1.0, min(5.0, timeout_ms / 1000.0))
            with socket.create_connection((host, port), timeout=connect_timeout) as sock:
                sock.settimeout(0.2)
                sock.sendall(payload)
                try:
                    sock.shutdown(socket.SHUT_WR)
                except OSError:
                    pass

                while time.time() < deadline:
                    try:
                        chunk = sock.recv(65536)
                        if chunk:
                            chunks.append(chunk)
                            continue
                        break
                    except socket.timeout:
                        current_state = read_best_effort_bridge_state(project_root)
                        if observed_reset_state is None and bridge_identity_changed(initial_generation, initial_session_id, current_state):
                            observed_reset_state = current_state
                        continue
                    except OSError as exc:
                        current_state = read_best_effort_bridge_state(project_root)
                        if observed_reset_state is None and bridge_identity_changed(initial_generation, initial_session_id, current_state):
                            observed_reset_state = current_state
                            break
                        raise ToolInvocationError(
                            "transport_io_failed",
                            (
                                f"TCP loopback transport failed for {operation}: {exc}. "
                                f"host={host} port={port}."
                            ),
                            {
                                "request_id": request_id,
                                "operation": operation,
                                "transport": self.name,
                                "host": host,
                                "port": port,
                            },
                        ) from exc
        except ToolInvocationError:
            raise
        except OSError as exc:
            raise ToolInvocationError(
                "transport_connect_failed",
                (
                    f"Failed to connect to TCP loopback transport for {operation}: {exc}. "
                    f"host={host} port={port} listener_state={listener_state or 'unknown'}."
                ),
                {
                    "request_id": request_id,
                    "operation": operation,
                    "transport": self.name,
                    "host": host,
                    "port": port,
                    "listener_state": listener_state,
                },
            ) from exc

        if chunks:
            try:
                response = json.loads(b"".join(chunks).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ToolInvocationError(
                    "transport_response_invalid",
                    f"TCP loopback transport returned invalid JSON for {operation}: {exc}.",
                    {
                        "request_id": request_id,
                        "operation": operation,
                        "transport": self.name,
                        "host": host,
                        "port": port,
                    },
                ) from exc
            if response.get("status") == "error":
                error = response.get("error") or {}
                error_code = str(error.get("code") or "")
                if error_code == "transport_restarting":
                    current_state = read_best_effort_bridge_state(project_root)
                    current_generation, current_session_id = bridge_identity_from_state(current_state)
                    raise ToolInvocationError(
                        "request_lifecycle_reset",
                        (
                            f"Request {request_id} for {operation} crossed a TCP transport restart before a response was committed. "
                            f"Previous bridge_generation={initial_generation}, current bridge_generation={current_generation}. "
                            f"transport={self.name} host={host} port={port}."
                        ),
                        {
                            "request_id": request_id,
                            "operation": operation,
                            "transport": self.name,
                            "host": host,
                            "port": port,
                            "initial_bridge_generation": initial_generation,
                            "initial_bridge_session_id": initial_session_id,
                            "current_bridge_generation": current_generation,
                            "current_bridge_session_id": current_session_id,
                            "retryable": True,
                            "error_code": error_code,
                        },
                    )
            return response, request_id, request_started_at

        state = read_best_effort_bridge_state(project_root)
        if observed_reset_state is not None:
            state = state or observed_reset_state
            current_generation, current_session_id = bridge_identity_from_state(state)
            processed = str((state or {}).get("last_processed_request_id") or "") == request_id
            retryable = not processed
            journal_path = write_host_request_journal_event(
                project_root,
                "request_reclassified",
                {
                    "request_id": request_id,
                    "operation": operation,
                    "reason": "bridge_generation_changed_before_response",
                    "retryable": retryable,
                    "reclassified_status": (
                        "retryable_after_lifecycle_reset"
                        if retryable
                        else "response_missing_after_lifecycle_reset"
                    ),
                    "previous_bridge_generation": initial_generation,
                    "previous_bridge_session_id": initial_session_id,
                    "bridge_generation": current_generation,
                    "bridge_session_id": current_session_id,
                },
            )
            details = {
                "request_id": request_id,
                "operation": operation,
                "transport": self.name,
                "host": host,
                "port": port,
                "initial_bridge_generation": initial_generation,
                "initial_bridge_session_id": initial_session_id,
                "current_bridge_generation": current_generation,
                "current_bridge_session_id": current_session_id,
                "retryable": retryable,
                "request_processed": processed,
                "journal_event_path": str(journal_path),
            }
            if retryable:
                raise ToolInvocationError(
                    "request_lifecycle_reset",
                    (
                        f"Request {request_id} for {operation} crossed a bridge lifecycle reset before a response was observed. "
                        f"Previous bridge_generation={initial_generation}, current bridge_generation={current_generation}. "
                        f"transport={self.name}. journal_event={journal_path}."
                    ),
                    details,
                )

            raise ToolInvocationError(
                "response_missing_after_lifecycle_reset",
                (
                    f"Request {request_id} for {operation} appears processed, but its response was not observed after a bridge lifecycle reset. "
                    f"Previous bridge_generation={initial_generation}, current bridge_generation={current_generation}. "
                    f"transport={self.name}. journal_event={journal_path}. {summarize_state_for_error(state)}"
                ),
                details,
            )

        raise ToolInvocationError(
            "transport_response_missing",
            (
                f"TCP loopback transport closed without a response for {operation}. "
                f"host={host} port={port}. {summarize_state_for_error(state)}"
            ),
            {
                "request_id": request_id,
                "operation": operation,
                "transport": self.name,
                "host": host,
                "port": port,
            },
        )


def resolve_bridge_transport(project_root: Path) -> BridgeTransportAdapter:
    config = try_read_bridge_config(project_root) or {}
    state = read_best_effort_bridge_state(project_root) or {}
    state_transport = str(state.get("transport") or "").strip().lower()
    if state_transport:
        configured_transport = state_transport
    else:
        bridge_version = int(state.get("bridge_version") or 0)
        configured_transport = (
            DEFAULT_BRIDGE_TRANSPORT
            if bridge_version > 0
            else str(
                config.get("transport")
                or config.get("bridge_transport")
                or DEFAULT_BRIDGE_TRANSPORT
            ).strip().lower()
        )
    if not configured_transport:
        configured_transport = DEFAULT_BRIDGE_TRANSPORT

    if configured_transport == DEFAULT_BRIDGE_TRANSPORT:
        return FileIpcBridgeTransport()

    if configured_transport == TCP_LOOPBACK_BRIDGE_TRANSPORT:
        return TcpLoopbackBridgeTransport()

    supported = ", ".join(sorted(SUPPORTED_BRIDGE_TRANSPORTS))
    raise ToolInvocationError(
        "unsupported_bridge_transport",
        (
            f"Unsupported bridge transport '{configured_transport}'. "
            f"Supported transports: {supported}."
        ),
    )


def invoke_bridge_transport(
    project_root: Path,
    operation: str,
    args: dict[str, Any],
    timeout_ms: int,
) -> tuple[dict[str, Any], str, float, dict[str, Any]]:
    if not bridge_enabled(project_root):
        raise ToolInvocationError(
            "bridge_disabled",
            (
                "Unity bridge is disabled for this project. "
                "Enable it with init_xuunity_light_unity_mcp.sh --project-root <path> --enable-project "
                "and reopen Unity."
            ),
        )

    transport = resolve_bridge_transport(project_root)
    response, request_id, request_started_at = transport.invoke(project_root, operation, args, timeout_ms)
    return response, request_id, request_started_at, transport.metadata(project_root)


def try_read_bridge_state(project_root: Path) -> dict[str, Any] | None:
    path = bridge_state_path(project_root)
    if not path.is_file():
        return None

    try:
        return read_json(path)
    except Exception:
        return None


def pid_is_alive(pid: int) -> bool:
    if pid <= 0:
        return False

    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def find_running_unity_editors_for_project(project_root: Path) -> list[dict[str, Any]]:
    target_path = str(project_root)
    marker = f"-projectPath {target_path}"

    try:
        completed = subprocess.run(
            ["ps", "-axo", "pid=,command="],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return []

    matches: list[dict[str, Any]] = []
    seen_pids: set[int] = set()
    for line in completed.stdout.splitlines():
        line = line.rstrip()
        if not line:
            continue

        parts = line.lstrip().split(None, 1)
        if len(parts) != 2:
            continue

        raw_pid, command = parts
        try:
            pid = int(raw_pid)
        except ValueError:
            continue

        if pid <= 0 or pid in seen_pids or not pid_is_alive(pid):
            continue

        if "Unity.app/Contents/MacOS/Unity" not in command:
            continue

        normalized_command = command.replace("\\ ", " ")
        if marker not in normalized_command and target_path not in normalized_command:
            continue

        unity_app = ""
        unity_version = ""
        app_match = re.search(r"(.+?/Unity\.app)/Contents/MacOS/Unity", normalized_command)
        if app_match:
            unity_app = app_match.group(1)
            try:
                unity_version = Path(unity_app).parent.name
            except Exception:
                unity_version = ""

        matches.append(
            {
                "pid": pid,
                "command": normalized_command,
                "unity_app": unity_app,
                "unity_version": unity_version,
            }
        )
        seen_pids.add(pid)

    return matches


def list_live_project_editor_pids(project_root: Path) -> list[int]:
    pids: set[int] = set()

    bridge_state = try_read_live_editor_state(project_root)
    if bridge_state is not None:
        bridge_pid = int(bridge_state.get("editor_pid") or 0)
        if bridge_pid > 0 and pid_is_alive(bridge_pid):
            pids.add(bridge_pid)

    for editor in find_running_unity_editors_for_project(project_root):
        pid = int(editor.get("pid") or 0)
        if pid > 0 and pid_is_alive(pid):
            pids.add(pid)

    return sorted(pids)


def project_lock_path(project_root: Path) -> Path:
    return project_root / "Temp" / "UnityLockfile"


def try_list_path_owner_pids(path: Path) -> list[int]:
    if not path.is_file():
        return []

    lsof_path = shutil.which("lsof")
    if not lsof_path:
        return []

    try:
        completed = subprocess.run(
            [lsof_path, "-t", "--", str(path)],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return []

    owner_pids: list[int] = []
    for line in completed.stdout.splitlines():
        raw_value = line.strip()
        if not raw_value:
            continue
        try:
            pid = int(raw_value)
        except ValueError:
            continue
        if pid > 0 and pid not in owner_pids:
            owner_pids.append(pid)
    return owner_pids


def inspect_project_lock(project_root: Path) -> dict[str, Any]:
    lock_path = project_lock_path(project_root)
    present = lock_path.is_file()
    owner_pids = try_list_path_owner_pids(lock_path) if present else []
    live_owner_pids = [pid for pid in owner_pids if pid_is_alive(pid)]

    return {
        "path": str(lock_path),
        "present": present,
        "owner_pids": owner_pids,
        "live_owner_pids": live_owner_pids,
    }


def clear_stale_project_lock(project_root: Path) -> dict[str, Any]:
    lock_state = inspect_project_lock(project_root)
    if not lock_state["present"] or lock_state["live_owner_pids"]:
        lock_state["removed"] = False
        return lock_state

    try:
        Path(lock_state["path"]).unlink()
        lock_state["removed"] = True
        lock_state["present"] = False
    except OSError:
        lock_state["removed"] = False
    return lock_state


def build_host_editor_session_state(
    project_root: Path,
    unity_app: Path,
    log_path: Path,
    background_open: bool,
    editor_pid: int = 0,
) -> dict[str, Any]:
    return {
        "project_root": str(project_root),
        "unity_app": str(unity_app),
        "editor_log_path": str(log_path),
        "background_open": background_open,
        "opened_by_host": True,
        "opened_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "editor_pid": max(0, int(editor_pid or 0)),
    }


def update_host_editor_session_pid(project_root: Path, editor_pid: int) -> None:
    state = try_read_host_editor_session_state(project_root)
    if not state or not bool(state.get("opened_by_host")):
        return

    normalized = dict(state)
    normalized["editor_pid"] = max(0, int(editor_pid or 0))
    write_host_editor_session_state(project_root, normalized)


def heartbeat_age_seconds(state: dict[str, Any]) -> float | None:
    heartbeat_utc = state.get("heartbeat_utc")
    if not isinstance(heartbeat_utc, str) or not heartbeat_utc:
        return None

    try:
        heartbeat_unix = calendar.timegm(time.strptime(heartbeat_utc, "%Y-%m-%dT%H:%M:%SZ"))
    except ValueError:
        return None

    return max(0.0, time.time() - heartbeat_unix)


def inspect_bridge_state_liveness(state: dict[str, Any] | None) -> dict[str, Any]:
    if not state:
        return {
            "state_present": False,
            "state_is_live": False,
            "editor_pid": 0,
            "editor_pid_alive": False,
            "heartbeat_age_seconds": None,
            "stale_reason": "state_missing",
        }

    pid = int(state.get("editor_pid") or 0)
    pid_alive = pid > 0 and pid_is_alive(pid)
    heartbeat_age = heartbeat_age_seconds(state)
    stale_reason = ""

    if pid <= 0:
        stale_reason = "missing_editor_pid"
    elif not pid_alive:
        stale_reason = "editor_pid_not_alive"

    return {
        "state_present": True,
        "state_is_live": pid_alive,
        "editor_pid": pid,
        "editor_pid_alive": pid_alive,
        "heartbeat_age_seconds": round(heartbeat_age, 3) if heartbeat_age is not None else None,
        "stale_reason": stale_reason,
    }


def annotate_bridge_state_with_liveness(state: dict[str, Any] | None) -> dict[str, Any] | None:
    if not state:
        return None

    annotated = dict(state)
    annotated["_xuunity_bridge_state"] = inspect_bridge_state_liveness(state)
    return annotated


def parse_utc_timestamp(value: Any) -> float | None:
    if not isinstance(value, str) or not value:
        return None

    try:
        return float(calendar.timegm(time.strptime(value, "%Y-%m-%dT%H:%M:%SZ")))
    except ValueError:
        return None


def state_is_idle(state: dict[str, Any]) -> bool:
    return (
        not bool(state.get("domain_reload_in_progress"))
        and not bool(state.get("package_operation_in_progress"))
        and not bool(state.get("script_reload_pending"))
        and not bool(state.get("asset_import_in_progress"))
        and not bool(state.get("refresh_settle_pending"))
        and not bool(state.get("compile_settle_pending"))
        and not bool(state.get("playmode_transition_pending"))
        and not bool(state.get("is_compiling"))
        and not bool(state.get("is_updating"))
        and not bool(state.get("active_operation"))
        and (bool(state.get("is_playing")) or not bool(state.get("is_playing_or_will_change_playmode")))
    )


def derive_busy_reason(state: dict[str, Any] | None) -> str:
    if not state:
        return "bridge_state_missing"

    busy_reason = state.get("busy_reason")
    if isinstance(busy_reason, str) and busy_reason:
        return busy_reason

    if bool(state.get("domain_reload_in_progress")):
        return "domain_reload"

    if bool(state.get("package_operation_in_progress")):
        return "package_operation"

    if bool(state.get("refresh_settle_pending")):
        return "refresh_settle"

    if bool(state.get("compile_settle_pending")):
        return "compile_settle"

    if bool(state.get("playmode_transition_pending")):
        return "playmode_settle"

    if bool(state.get("is_compiling")):
        return "compiling"

    if bool(state.get("script_reload_pending")):
        return "script_reload_pending"

    if bool(state.get("asset_import_in_progress")):
        return "asset_import"

    if bool(state.get("is_updating")):
        return "updating"

    if state.get("active_operation"):
        return "processing_request"

    if not bool(state.get("is_playing")) and bool(state.get("is_playing_or_will_change_playmode")):
        return "playmode_transition"

    if int(state.get("pending_request_count") or 0) > 0:
        return "request_queue_pending"

    return "idle"


def summarize_state_for_error(state: dict[str, Any] | None) -> str:
    if not state:
        return "No live bridge state was available."

    heartbeat_age = heartbeat_age_seconds(state)
    heartbeat_summary = "unknown"
    if heartbeat_age is not None:
        heartbeat_summary = f"{round(heartbeat_age, 3)}s"

    return (
        f"bridge_version={state.get('bridge_version') or 'unknown'}, "
        f"bridge_generation={state.get('bridge_generation') or 'unknown'}, "
        f"bridge_session_id={state.get('bridge_session_id') or ''}, "
        f"busy_reason={derive_busy_reason(state)}, "
        f"heartbeat_age={heartbeat_summary}, "
        f"domain_reload_in_progress={bool(state.get('domain_reload_in_progress'))}, "
        f"package_operation_in_progress={bool(state.get('package_operation_in_progress'))}, "
        f"package_operation_name={state.get('package_operation_name') or ''}, "
        f"package_operation_phase={state.get('package_operation_phase') or ''}, "
        f"refresh_settle_pending={bool(state.get('refresh_settle_pending'))}, "
        f"refresh_settle_phase={state.get('refresh_settle_phase') or ''}, "
        f"compile_settle_pending={bool(state.get('compile_settle_pending'))}, "
        f"compile_settle_phase={state.get('compile_settle_phase') or ''}, "
        f"compile_settle_operation={state.get('compile_settle_operation') or ''}, "
        f"playmode_transition_pending={bool(state.get('playmode_transition_pending'))}, "
        f"playmode_transition_phase={state.get('playmode_transition_phase') or ''}, "
        f"playmode_transition_target_state={state.get('playmode_transition_target_state') or ''}, "
        f"script_reload_pending={bool(state.get('script_reload_pending'))}, "
        f"asset_import_in_progress={bool(state.get('asset_import_in_progress'))}, "
        f"is_compiling={bool(state.get('is_compiling'))}, "
        f"is_updating={bool(state.get('is_updating'))}, "
        f"is_playing={bool(state.get('is_playing'))}, "
        f"is_playing_or_will_change_playmode={bool(state.get('is_playing_or_will_change_playmode'))}, "
        f"health_status={state.get('health_status') or 'unknown'}, "
        f"active_operation={state.get('active_operation') or ''}, "
        f"busy_reason_detail={state.get('busy_reason_detail') or ''}, "
        f"last_processed_request_id={state.get('last_processed_request_id') or ''}, "
        f"request_journal_head={state.get('request_journal_head') or ''}, "
        f"pending_request_count={int(state.get('pending_request_count') or 0)}"
    )


def activate_unity_editor(project_root: Path, explicit_unity_app: Path | None = None) -> dict[str, Any]:
    unity_app = explicit_unity_app or detect_unity_app_path_for_project(project_root, None)
    subprocess.run(["open", "-a", str(unity_app)], check=True)
    time.sleep(ACTIVATION_DELAY_SECONDS)
    return {
        "unity_app": str(unity_app),
        "activation_delay_seconds": ACTIVATION_DELAY_SECONDS,
    }


def classify_editor_log(log_text: str, startup_policy: str) -> tuple[str, str] | None:
    if not log_text:
        return None

    if "Project has invalid dependencies:" in log_text or "An error occurred while resolving packages:" in log_text:
        return (
            "package_resolution_failed",
            "Unity package resolution failed. Inspect Editor.log for invalid dependencies, git package errors, or registry failures.",
        )

    if "Could not clone [" in log_text:
        return (
            "package_resolution_failed",
            "Unity could not clone a git package dependency. Inspect Editor.log for the failing dependency URL or commit hash.",
        )

    if "error CS" in log_text or "AssetDatabase: script compilation time:" in log_text and "error CS" in log_text:
        if startup_policy == "batch_compile_lane":
            return (
                "interactive_compile_block_detected",
                "Interactive Unity startup is blocked by compilation errors. Use the batch compile lane for compile-only validation or fix the compile errors first.",
            )

        if startup_policy == "auto_enter_safe_mode_preferred":
            return (
                "safe_mode_manual_required",
                "Compilation errors were detected during startup. This host-side wrapper cannot click the Safe Mode dialog. Prefer auto-enter Safe Mode in Unity preferences or reopen manually into Safe Mode.",
            )

        return (
            "interactive_compile_block_detected",
            "Compilation errors were detected during interactive startup. This wrapper is failing fast instead of waiting for a bridge heartbeat that cannot become healthy.",
        )

    return None


def resolve_editor_log_path(project_root: Path, explicit_path: str | None) -> Path:
    if explicit_path:
        return Path(explicit_path).expanduser().resolve()
    return default_editor_log_path(project_root)


def read_recent_editor_log(log_path: Path, command_started_at: float) -> str:
    if not log_path.is_file():
        return ""

    try:
        stat = log_path.stat()
    except OSError:
        return ""

    if stat.st_mtime < command_started_at - 1.0:
        return ""

    try:
        text = log_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""

    if len(text) > 200000:
        return text[-200000:]
    return text


def detect_unity_app_path(explicit_path: str | None) -> Path:
    if explicit_path:
        path = Path(explicit_path).expanduser().resolve()
        if not path.is_dir():
            raise ToolInvocationError("unity_app_not_found", f"Unity app not found: {path}")
        return path

    candidates = sorted(Path("/Applications/Unity/Hub/Editor").glob("*/Unity.app"))
    if not candidates:
        raise ToolInvocationError(
            "unity_app_not_found",
            "Could not auto-detect a Unity.app under /Applications/Unity/Hub/Editor. Pass --unity-app explicitly.",
    )
    return candidates[-1]


def read_project_unity_version(project_root: Path) -> str | None:
    version_path = project_root / "ProjectSettings" / "ProjectVersion.txt"
    if not version_path.is_file():
        return None

    try:
        for line in version_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith("m_EditorVersion:"):
                version = line.split(":", 1)[1].strip()
                return version or None
    except OSError:
        return None

    return None


def detect_unity_app_path_for_project(project_root: Path, explicit_path: str | None) -> Path:
    if explicit_path:
        return detect_unity_app_path(explicit_path)

    project_version = read_project_unity_version(project_root)
    if project_version:
        exact_match = Path("/Applications/Unity/Hub/Editor") / project_version / "Unity.app"
        if exact_match.is_dir():
            return exact_match.resolve()

    return detect_unity_app_path(None)


def resolve_unity_app_version(unity_app: Path) -> str:
    return unity_app.parent.name


def try_read_live_editor_state(project_root: Path) -> dict[str, Any] | None:
    state = try_read_bridge_state(project_root)
    if not state:
        return None

    pid = int(state.get("editor_pid") or 0)
    if not pid_is_alive(pid):
        return None

    return state


def open_unity_editor(project_root: Path, log_path: Path, unity_app: Path, background_open: bool) -> dict[str, Any]:
    log_path.parent.mkdir(parents=True, exist_ok=True)

    live_state = try_read_live_editor_state(project_root)
    if live_state is not None:
        requested_version = resolve_unity_app_version(unity_app)
        running_version = str(live_state.get("unity_version") or "")
        if requested_version and running_version and requested_version != running_version:
            raise ToolInvocationError(
                "project_already_open_with_different_unity_version",
                (
                    "This project already appears open in Unity "
                    f"{running_version} (pid {live_state.get('editor_pid')}). "
                    f"Requested Unity version is {requested_version}. "
                    "Close the running editor instance for this project before opening a different version."
                ),
            )

        return {
            "unity_app": str(unity_app),
            "editor_log_path": str(log_path),
            "background_open": background_open,
            "reused_existing_editor": True,
            "editor_pid": live_state.get("editor_pid"),
            "unity_version": running_version,
        }

    detected_editors = find_running_unity_editors_for_project(project_root)
    if detected_editors:
        requested_version = resolve_unity_app_version(unity_app)
        detected_versions = sorted(
            {
                str(editor.get("unity_version") or "").strip()
                for editor in detected_editors
                if str(editor.get("unity_version") or "").strip()
            }
        )
        if requested_version and detected_versions and requested_version not in detected_versions:
            raise ToolInvocationError(
                "project_already_open_with_different_unity_version",
                (
                    "This project already appears open in Unity "
                    f"{', '.join(detected_versions)} (pid {detected_editors[0]['pid']}). "
                    f"Requested Unity version is {requested_version}. "
                    "Close the running editor instance for this project before opening a different version."
                ),
            )

        detected_unity_app = str(detected_editors[0].get("unity_app") or unity_app)
        try:
            activate_unity_editor(project_root, Path(detected_unity_app))
        except Exception:
            pass

        return {
            "unity_app": detected_unity_app,
            "editor_log_path": str(log_path),
            "background_open": background_open,
            "reused_existing_editor": True,
            "reused_via": "project_process_detection",
            "bridge_available": False,
            "editor_pid": detected_editors[0]["pid"],
            "unity_version": str(detected_editors[0].get("unity_version") or requested_version or ""),
            "matching_editor_pids": [int(editor["pid"]) for editor in detected_editors],
        }

    lock_state = inspect_project_lock(project_root)
    if lock_state["present"]:
        live_owner_pids = lock_state["live_owner_pids"]
        if live_owner_pids:
            raise ToolInvocationError(
                "project_already_open_without_bridge",
                (
                    "This project already appears open in Unity, but no reusable MCP bridge session is currently "
                    f"available. Project lock: {lock_state['path']}. "
                    f"Live lock owner pid(s): {', '.join(str(pid) for pid in live_owner_pids)}. "
                    "Focus or recover the running editor instead of launching a second instance."
                ),
            )
        cleared_lock_state = clear_stale_project_lock(project_root)
        if cleared_lock_state.get("present"):
            raise ToolInvocationError(
                "project_lock_present_without_bridge",
                (
                    "This project has a Unity lock file, but no reusable MCP bridge session is currently available. "
                    f"Project lock: {lock_state['path']}. "
                    "Another Unity instance may already own the project, or the editor may have exited uncleanly. "
                    "Resolve the running editor or clear the stale lock before retrying."
                ),
            )

    command = ["open"]
    if background_open:
        command.append("-g")
    command.extend(
        [
            "-na",
            str(unity_app),
            "--args",
            "-projectPath",
            str(project_root),
            "-logFile",
            str(log_path),
        ]
    )

    subprocess.run(command, check=True)
    launched_editors = find_running_unity_editors_for_project(project_root)
    launched_pid = int(launched_editors[0]["pid"]) if launched_editors else 0
    write_host_editor_session_state(
        project_root,
        build_host_editor_session_state(project_root, unity_app, log_path, background_open, launched_pid),
    )
    return {
        "unity_app": str(unity_app),
        "editor_log_path": str(log_path),
        "background_open": background_open,
        "opened_by_host": True,
        "editor_pid": launched_pid,
    }


def request_editor_quit(project_root: Path, timeout_ms: int) -> dict[str, Any]:
    return invoke_bridge(project_root, "unity.editor.quit", {}, timeout_ms)


def terminate_editor_pid(pid: int, timeout_ms: int) -> bool:
    if pid <= 0 or not pid_is_alive(pid):
        return True

    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        return not pid_is_alive(pid)

    deadline = time.time() + (max(1000, timeout_ms) / 1000.0)
    while time.time() < deadline:
        if not pid_is_alive(pid):
            return True
        time.sleep(0.2)

    return not pid_is_alive(pid)


def restore_host_opened_editor_state(project_root: Path, timeout_ms: int) -> dict[str, Any]:
    session = try_read_host_editor_session_state(project_root)
    if not session or not bool(session.get("opened_by_host")):
        return {
            "project_root": str(project_root),
            "restored": False,
            "reason": "not_opened_by_host",
        }

    tracked_pid = int(session.get("editor_pid") or 0)
    live_state = try_read_live_editor_state(project_root)
    restoration = {
        "project_root": str(project_root),
        "tracked_editor_pid": tracked_pid,
        "restored": False,
        "reason": "",
        "close_path": "",
    }

    if live_state is not None:
        current_pid = int(live_state.get("editor_pid") or 0)
        if current_pid > 0 and (tracked_pid <= 0 or current_pid == tracked_pid):
            request_editor_quit(str(project_root), timeout_ms)
            deadline = time.time() + (max(1000, timeout_ms) / 1000.0)
            while time.time() < deadline:
                live_project_pids = list_live_project_editor_pids(project_root)
                if not pid_is_alive(current_pid) and current_pid not in live_project_pids:
                    clear_host_editor_session_state(project_root)
                    restoration["restored"] = True
                    restoration["reason"] = "host_opened_editor_closed"
                    restoration["close_path"] = "unity.editor.quit"
                    restoration["closed_editor_pid"] = current_pid
                    clear_stale_project_lock(project_root)
                    return restoration
                time.sleep(0.2)

    if tracked_pid > 0 and terminate_editor_pid(tracked_pid, timeout_ms):
        live_project_pids = list_live_project_editor_pids(project_root)
        if tracked_pid not in live_project_pids:
            clear_host_editor_session_state(project_root)
            restoration["restored"] = True
            restoration["reason"] = "host_opened_editor_closed"
            restoration["close_path"] = "host_sigterm"
            restoration["closed_editor_pid"] = tracked_pid
            clear_stale_project_lock(project_root)
            return restoration

    if tracked_pid > 0 and not pid_is_alive(tracked_pid):
        live_project_pids = list_live_project_editor_pids(project_root)
        if not live_project_pids:
            clear_host_editor_session_state(project_root)
            restoration["restored"] = False
            restoration["reason"] = "tracked_editor_already_closed"
            return restoration

        restoration["reason"] = "project_editor_still_running_untracked"
        restoration["live_project_editor_pids"] = live_project_pids
        return restoration

    restoration["reason"] = "tracked_editor_still_running"
    restoration["live_project_editor_pids"] = list_live_project_editor_pids(project_root)
    return restoration


def wait_for_editor_idle(
    project_root: Path,
    timeout_ms: int,
    heartbeat_max_age_seconds: int,
    reason: str,
    *,
    after_request_id: str | None = None,
    not_before_unix: float | None = None,
    require_healthy_bridge: bool = True,
    stable_cycles: int = DEFAULT_IDLE_STABLE_CYCLES,
) -> dict[str, Any]:
    started_at = time.time()
    deadline = started_at + (timeout_ms / 1000.0)
    stable_matches = 0
    last_state: dict[str, Any] | None = None

    while time.time() < deadline:
        state = try_read_live_editor_state(project_root)
        if state:
            last_state = state
            age_seconds = heartbeat_age_seconds(state)
            heartbeat_is_fresh = age_seconds is not None and age_seconds <= heartbeat_max_age_seconds
            bridge_is_healthy = not require_healthy_bridge or state.get("health_status") == "healthy"
            last_processed_request_id = str(state.get("last_processed_request_id") or "")
            last_pump_unix = parse_utc_timestamp(state.get("last_pump_utc"))
            request_match = (
                after_request_id is None
                or last_processed_request_id == after_request_id
                or (not_before_unix is not None and last_pump_unix is not None and last_pump_unix >= not_before_unix)
            )
            editor_is_idle = state_is_idle(state)

            if heartbeat_is_fresh and bridge_is_healthy and request_match and editor_is_idle:
                stable_matches += 1
                if stable_matches >= max(1, stable_cycles):
                    result = dict(state)
                    result["heartbeat_age_seconds"] = round(age_seconds or 0.0, 3)
                    result["idle_wait_reason"] = reason
                    result["idle_wait_duration_seconds"] = round(time.time() - started_at, 3)
                    return result
            else:
                stable_matches = 0
        else:
            stable_matches = 0

        time.sleep(0.5)

    request_summary = ""
    if after_request_id:
        request_summary = f" request_id={after_request_id}."

    raise ToolInvocationError(
        "editor_idle_timeout",
        (
            f"Timed out waiting for Unity editor idle ({reason})."
            f"{request_summary} {summarize_state_for_error(last_state)}"
        ),
    )


def wait_for_playmode_state(
    project_root: Path,
    timeout_ms: int,
    heartbeat_max_age_seconds: int,
    expected_state: str,
    reason: str,
    *,
    after_request_id: str | None = None,
    not_before_unix: float | None = None,
    stable_cycles: int = DEFAULT_IDLE_STABLE_CYCLES,
) -> dict[str, Any]:
    started_at = time.time()
    deadline = started_at + (timeout_ms / 1000.0)
    stable_matches = 0
    last_state: dict[str, Any] | None = None

    while time.time() < deadline:
        state = try_read_live_editor_state(project_root)
        if state:
            last_state = state
            age_seconds = heartbeat_age_seconds(state)
            heartbeat_is_fresh = age_seconds is not None and age_seconds <= heartbeat_max_age_seconds
            request_match = (
                after_request_id is None
                or str(state.get("last_processed_request_id") or "") == after_request_id
                or (
                    not_before_unix is not None
                    and parse_utc_timestamp(state.get("last_pump_utc")) is not None
                    and parse_utc_timestamp(state.get("last_pump_utc")) >= not_before_unix
                )
            )
            playmode_state = str(state.get("playmode_state") or "")
            transition_request_id = str(state.get("playmode_transition_request_id") or "")
            transition_phase = str(state.get("playmode_transition_phase") or "")
            transition_contract_applies = after_request_id is not None and transition_request_id == after_request_id
            transition_settled = (not transition_contract_applies) or transition_phase == "settled"

            if heartbeat_is_fresh and request_match and playmode_state == expected_state and transition_settled:
                stable_matches += 1
                if stable_matches >= max(1, stable_cycles):
                    result = dict(state)
                    result["heartbeat_age_seconds"] = round(age_seconds or 0.0, 3)
                    result["playmode_wait_reason"] = reason
                    result["playmode_wait_duration_seconds"] = round(time.time() - started_at, 3)
                    return result
            else:
                stable_matches = 0
        else:
            stable_matches = 0

        time.sleep(0.5)

    request_summary = ""
    if after_request_id:
        request_summary = f" request_id={after_request_id}."

    raise ToolInvocationError(
        "playmode_state_timeout",
        (
            f"Timed out waiting for play mode state '{expected_state}' ({reason})."
            f"{request_summary} {summarize_state_for_error(last_state)}"
        ),
    )


def wait_for_scenario_result(
    project_root: Path,
    run_id: str,
    scenario_name: str,
    timeout_ms: int,
    poll_interval_ms: int,
) -> dict[str, Any]:
    started_at = time.time()
    deadline = started_at + (timeout_ms / 1000.0)
    effective_poll_interval = max(0.1, poll_interval_ms / 1000.0)
    last_payload: dict[str, Any] | None = None
    transient_poll_error_codes = {
        "transport_not_ready",
        "transport_response_missing",
        "request_lifecycle_reset",
        "response_missing_after_lifecycle_reset",
    }

    while time.time() < deadline:
        live_state = try_read_live_editor_state(project_root)
        if isinstance(live_state, dict) and bool(live_state.get("playmode_transition_pending")):
            target_state = str(live_state.get("playmode_transition_target_state") or "")
            current_state = str(live_state.get("playmode_state") or "")
            if target_state in {"playing", "paused"} and current_state != target_state:
                try:
                    activate_unity_editor(project_root)
                except ToolInvocationError:
                    pass

        remaining_ms = max(1000, min(5000, int((deadline - time.time()) * 1000)))
        bridge_args: dict[str, Any] = {}
        if run_id:
            bridge_args["runId"] = run_id
        if scenario_name:
            bridge_args["scenarioName"] = scenario_name

        try:
            response = invoke_bridge(str(project_root), "unity.scenario.result", bridge_args, remaining_ms)
        except ToolInvocationError as exc:
            if exc.code in transient_poll_error_codes and time.time() + effective_poll_interval < deadline:
                time.sleep(effective_poll_interval)
                continue
            raise

        tool_result = bridge_response_to_tool_result(response)
        if tool_result.get("isError"):
            structured = tool_result.get("structuredContent") or {}
            error = structured.get("error") or {}
            raise ToolInvocationError(
                str(error.get("code") or "scenario_result_failed"),
                str(error.get("message") or "Scenario result polling failed."),
            )

        payload = tool_result.get("structuredContent") or {}
        if isinstance(payload, dict):
            payload = normalize_scenario_payload(payload)
        last_payload = payload

        if is_terminal_scenario_status(payload.get("status")):
            payload["waited_for_terminal_state"] = True
            payload["wait_duration_seconds"] = round(time.time() - started_at, 3)
            return payload

        time.sleep(effective_poll_interval)

    scenario_label = scenario_name or run_id or "unknown"
    suffix = ""
    if last_payload:
        suffix = f" Last observed status: {last_payload.get('status') or 'unknown'}."
    raise ToolInvocationError(
        "scenario_wait_timeout",
        f"Timed out waiting for scenario '{scenario_label}' to reach a terminal state.{suffix}",
    )


def expected_playmode_state_for_action(action: str) -> str | None:
    normalized = (action or "").strip().lower()
    mapping = {
        "enter": "playing",
        "exit": "edit",
        "pause": "paused",
        "resume": "playing",
    }
    return mapping.get(normalized)


def is_terminal_scenario_status(status: Any) -> bool:
    return isinstance(status, str) and status in SCENARIO_TERMINAL_STATUSES


def normalize_scenario_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    status = str(normalized.get("status") or "")
    terminal = is_terminal_scenario_status(status)
    normalized["terminal"] = terminal
    normalized["succeeded"] = status == "passed"
    normalized["terminal_status"] = status if terminal else ""
    normalized["terminal_statuses"] = sorted(SCENARIO_TERMINAL_STATUSES)
    return normalized


def normalize_refresh_payload_from_lifecycle(payload: dict[str, Any], lifecycle: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    requested_outcome = str(normalized.get("outcome") or "")
    idle_wait_after = lifecycle.get("idle_wait_after")
    if not isinstance(idle_wait_after, dict):
        return normalized

    settled_at_utc = str(idle_wait_after.get("heartbeat_utc") or "")
    normalized["requested_outcome"] = requested_outcome
    normalized["outcome"] = (
        "refresh_and_resolve_completed"
        if bool(normalized.get("package_resolve_requested"))
        else "refresh_completed"
    )
    normalized["settled_at_utc"] = settled_at_utc
    if (
        str(idle_wait_after.get("refresh_settle_phase") or "") == "settled"
        and str(idle_wait_after.get("refresh_settle_request_id") or "") == str(normalized.get("settle_request_id") or "")
    ):
        normalized["completion_basis"] = "unity_refresh_settle_watcher"
        normalized["settled_at_utc"] = str(idle_wait_after.get("refresh_settle_completed_utc") or settled_at_utc)
        normalized["settle_phase"] = "settled"
        normalized["settle_request_id"] = str(idle_wait_after.get("refresh_settle_request_id") or normalized.get("settle_request_id") or "")
    else:
        normalized["completion_basis"] = "host_waited_for_editor_idle"
    normalized["editor_is_compiling_after_settle"] = bool(idle_wait_after.get("is_compiling"))
    normalized["editor_is_updating_after_settle"] = bool(idle_wait_after.get("is_updating"))
    normalized["playmode_state_after_settle"] = str(idle_wait_after.get("playmode_state") or "")
    return normalized


def normalize_compile_payload_from_lifecycle(payload: dict[str, Any], lifecycle: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    idle_wait_after = lifecycle.get("idle_wait_after")
    if not isinstance(idle_wait_after, dict):
        return normalized

    settled_at_utc = str(idle_wait_after.get("heartbeat_utc") or "")
    request_id = str(normalized.get("settle_request_id") or "")
    if (
        str(idle_wait_after.get("compile_settle_phase") or "") == "settled"
        and str(idle_wait_after.get("compile_settle_request_id") or "") == request_id
    ):
        normalized["completion_basis"] = "unity_compile_settle_watcher"
        normalized["settled_at_utc"] = str(idle_wait_after.get("compile_settle_completed_utc") or settled_at_utc)
        normalized["settle_phase"] = "settled"
        normalized["settle_request_id"] = str(idle_wait_after.get("compile_settle_request_id") or request_id)
    else:
        normalized["completion_basis"] = "host_waited_for_editor_idle"
        normalized["settled_at_utc"] = settled_at_utc

    normalized["editor_is_compiling_after_settle"] = bool(idle_wait_after.get("is_compiling"))
    normalized["editor_is_updating_after_settle"] = bool(idle_wait_after.get("is_updating"))
    normalized["playmode_state_after_settle"] = str(idle_wait_after.get("playmode_state") or "")
    return normalized


def normalize_playmode_payload_from_lifecycle(payload: dict[str, Any], lifecycle: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    settled_state = lifecycle.get("playmode_wait_after")
    if not isinstance(settled_state, dict):
        return normalized

    settled_at_utc = str(settled_state.get("heartbeat_utc") or "")
    request_id = str(normalized.get("settle_request_id") or "")
    if (
        str(settled_state.get("playmode_transition_phase") or "") == "settled"
        and str(settled_state.get("playmode_transition_request_id") or "") == request_id
    ):
        normalized["completion_basis"] = "unity_playmode_transition_watcher"
        normalized["settled_at_utc"] = str(settled_state.get("playmode_transition_completed_utc") or settled_at_utc)
        normalized["settle_phase"] = "settled"
    else:
        normalized["completion_basis"] = "host_waited_for_playmode_state"
        normalized["settled_at_utc"] = settled_at_utc

    normalized["settle_target_state"] = str(
        settled_state.get("playmode_transition_target_state")
        or normalized.get("settle_target_state")
        or settled_state.get("playmode_state")
        or ""
    )
    normalized["settle_request_id"] = str(
        settled_state.get("playmode_transition_request_id")
        or request_id
    )
    normalized["is_playing"] = bool(settled_state.get("is_playing"))
    normalized["is_paused"] = bool(settled_state.get("is_paused"))
    normalized["is_playing_or_will_change_playmode"] = bool(settled_state.get("is_playing_or_will_change_playmode"))
    normalized["playmode_state"] = str(settled_state.get("playmode_state") or normalized.get("playmode_state") or "")
    return normalized


def normalize_response_payload_from_lifecycle(response: dict[str, Any], lifecycle: dict[str, Any]) -> dict[str, Any]:
    if response.get("status") != "ok":
        return response

    settled_state = lifecycle.get("playmode_wait_after")
    payload_json = response.get("payload_json")
    if not isinstance(payload_json, str) or not payload_json:
        return response

    try:
        payload = json.loads(payload_json)
    except json.JSONDecodeError:
        return response

    operation = str(lifecycle.get("operation") or "")
    payload_type = str(response.get("payload_type") or "")

    if operation == "unity.playmode.set" and isinstance(settled_state, dict):
        payload = normalize_playmode_payload_from_lifecycle(payload, lifecycle)
    elif operation == "unity.project.refresh":
        payload = normalize_refresh_payload_from_lifecycle(payload, lifecycle)
    elif operation in {"unity.compile.player_scripts", "unity.compile.matrix"}:
        payload = normalize_compile_payload_from_lifecycle(payload, lifecycle)

    if payload_type in {"unity.scenario.run", "unity.scenario.result"}:
        payload = normalize_scenario_payload(payload)

    normalized = dict(response)
    normalized["payload_json"] = json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
    return normalized


def resolve_operation_lifecycle_policy(operation: str) -> dict[str, Any]:
    policy = {
        "activate_unity": False,
        "wait_for_idle_before": False,
        "wait_for_idle_after": False,
        "idle_stable_cycles_after": DEFAULT_IDLE_STABLE_CYCLES,
        "retry_on_lifecycle_reset": False,
    }
    policy.update(OPERATION_LIFECYCLE_POLICIES.get(operation, {}))
    return policy


def invoke_bridge(project_root_value: str, operation: str, args: dict[str, Any], timeout_ms: int) -> dict[str, Any]:
    project_root = ensure_project_root(project_root_value)
    policy = resolve_operation_lifecycle_policy(operation)
    max_attempts = 2 if bool(policy.get("retry_on_lifecycle_reset")) else 1

    for attempt_index in range(max_attempts):
        pre_request_state = try_read_live_editor_state(project_root) or try_read_bridge_state(project_root)
        lifecycle: dict[str, Any] = {
            "operation": operation,
            "attempt_index": attempt_index,
            "max_attempts": max_attempts,
            "activation_requested": False,
            "idle_wait_before": None,
            "idle_wait_after": None,
            "transport": None,
            "bridge_identity_before_request": {
                "bridge_generation": bridge_identity_from_state(pre_request_state)[0],
                "bridge_session_id": bridge_identity_from_state(pre_request_state)[1],
            },
        }

        try:
            if policy["activate_unity"]:
                lifecycle["activation_requested"] = True
                lifecycle["activation"] = activate_unity_editor(project_root)

            if policy["wait_for_idle_before"]:
                lifecycle["idle_wait_before"] = wait_for_editor_idle(
                    project_root,
                    timeout_ms,
                    DEFAULT_HEARTBEAT_MAX_AGE_SECONDS,
                    f"before {operation}",
                    stable_cycles=1,
                )

            response, request_id, request_started_at, transport_metadata = invoke_bridge_transport(project_root, operation, args, timeout_ms)
            lifecycle["transport"] = transport_metadata

            if operation == "unity.playmode.set":
                expected_playmode_state = expected_playmode_state_for_action(str(args.get("action") or ""))
                if expected_playmode_state:
                    lifecycle["playmode_wait_after"] = wait_for_playmode_state(
                        project_root,
                        timeout_ms,
                        DEFAULT_HEARTBEAT_MAX_AGE_SECONDS,
                        expected_playmode_state,
                        f"after {operation}",
                        after_request_id=request_id,
                        not_before_unix=request_started_at,
                        stable_cycles=int(policy["idle_stable_cycles_after"]),
                    )
                elif policy["wait_for_idle_after"]:
                    lifecycle["idle_wait_after"] = wait_for_editor_idle(
                        project_root,
                        timeout_ms,
                        DEFAULT_HEARTBEAT_MAX_AGE_SECONDS,
                        f"after {operation}",
                        after_request_id=request_id,
                        not_before_unix=request_started_at,
                        stable_cycles=int(policy["idle_stable_cycles_after"]),
                    )
            elif policy["wait_for_idle_after"]:
                lifecycle["idle_wait_after"] = wait_for_editor_idle(
                    project_root,
                    timeout_ms,
                    DEFAULT_HEARTBEAT_MAX_AGE_SECONDS,
                    f"after {operation}",
                    after_request_id=request_id,
                    not_before_unix=request_started_at,
                    stable_cycles=int(policy["idle_stable_cycles_after"]),
                )

            settled_state = (
                lifecycle.get("playmode_wait_after")
                if isinstance(lifecycle.get("playmode_wait_after"), dict)
                else lifecycle.get("idle_wait_after")
            )
            if isinstance(settled_state, dict):
                transition = maybe_record_settle_lifecycle_transition(
                    project_root,
                    operation,
                    request_id,
                    pre_request_state,
                    settled_state,
                )
                if transition:
                    lifecycle["bridge_identity_transition"] = transition

            if response.get("status") == "ok":
                response = normalize_response_payload_from_lifecycle(dict(response), lifecycle)
                response["_xuunity_lifecycle"] = lifecycle

            return response
        except ToolInvocationError as exc:
            if exc.code == "request_lifecycle_reset" and attempt_index + 1 < max_attempts:
                lifecycle["lifecycle_reset_retry"] = exc.details
                continue
            raise

    raise ToolInvocationError("unreachable", f"Unexpected lifecycle retry state for {operation}.")


def wait_for_ready(
    project_root: Path,
    timeout_ms: int,
    heartbeat_max_age_seconds: int,
    startup_policy: str,
    editor_log_path: Path,
) -> dict[str, Any]:
    if startup_policy not in STARTUP_POLICIES:
        raise ToolInvocationError("invalid_startup_policy", f"Unknown startup policy: {startup_policy}")

    if not bridge_enabled(project_root):
        raise ToolInvocationError(
            "bridge_disabled",
            (
                "Unity bridge is disabled for this project. "
                "Enable it with init_xuunity_light_unity_mcp.sh --project-root <path> --enable-project "
                "and reopen Unity."
            ),
        )

    started_at = time.time()
    deadline = started_at + (timeout_ms / 1000.0)
    while time.time() < deadline:
        state = try_read_bridge_state(project_root)
        if state:
            pid = int(state.get("editor_pid") or 0)
            age_seconds = heartbeat_age_seconds(state)
            if (
                pid_is_alive(pid)
                and age_seconds is not None
                and age_seconds <= heartbeat_max_age_seconds
                and state.get("health_status") == "healthy"
                and not bool(state.get("is_compiling"))
            ):
                state["startup_policy"] = startup_policy
                state["editor_log_path"] = str(editor_log_path)
                state["heartbeat_age_seconds"] = round(age_seconds, 3)
                return state

        classification = classify_editor_log(read_recent_editor_log(editor_log_path, started_at), startup_policy)
        if classification:
            code, message = classification
            raise ToolInvocationError(code, message)

        time.sleep(1.0)

    raise ToolInvocationError(
        "editor_ready_timeout",
        (
            "Timed out waiting for a healthy Unity bridge heartbeat. "
            f"Last inspected log: {editor_log_path}"
        ),
    )


def resolve_build_config_asset_path(project_root: Path, build_config_asset: str | None) -> Path:
    if build_config_asset:
        candidate = Path(build_config_asset).expanduser()
        if not candidate.is_absolute():
            candidate = project_root / candidate
        candidate = candidate.resolve()
        if not candidate.is_file():
            raise ToolInvocationError("build_config_asset_not_found", f"Build config asset not found: {candidate}")
        return candidate

    candidates = sorted(project_root.glob("Assets/**/*BuildConfiguration.asset"))
    if not candidates:
        raise ToolInvocationError(
            "build_config_asset_not_found",
            "Could not auto-detect a *BuildConfiguration.asset under Assets/. Pass buildConfigAsset explicitly.",
        )

    if len(candidates) > 1:
        joined = ", ".join(str(path.relative_to(project_root)) for path in candidates[:10])
        raise ToolInvocationError(
            "build_config_asset_ambiguous",
            f"Found multiple *BuildConfiguration.asset files. Pass buildConfigAsset explicitly. Candidates: {joined}",
        )

    return candidates[0]


def parse_unity_build_config_profiles(asset_path: Path) -> list[dict[str, Any]]:
    try:
        lines = asset_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ToolInvocationError("build_config_asset_read_failed", str(exc)) from exc

    profiles: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    in_defines = False
    in_debugging = False

    for line in lines:
        if current is not None and line.startswith("  _playerBuildConfig:"):
            profiles.append(current)
            current = None
            in_defines = False
            in_debugging = False
            break

        if line.startswith("  - ConfigName: "):
            if current is not None:
                profiles.append(current)
            current = {
                "configName": line.split(":", 1)[1].strip(),
                "scriptingDefines": [],
                "enableDevelopmentBuild": False,
            }
            in_defines = False
            in_debugging = False
            continue

        if current is None:
            continue

        if line.startswith("    CompilationCSharpSettings:"):
            in_debugging = False
            continue

        if line.startswith("    DebuggingSettings:"):
            in_defines = False
            in_debugging = True
            continue

        if line.startswith("    ") and not line.startswith("      "):
            in_defines = False
            if not line.startswith("    DebuggingSettings:"):
                in_debugging = False

        if line.startswith("      ScriptingDefines:"):
            in_defines = True
            continue

        if in_defines:
            if line.startswith("      - "):
                current["scriptingDefines"].append(line[len("      - "):].strip())
                continue
            in_defines = False

        if in_debugging and line.strip().startswith("EnableDevelopmentBuild:"):
            value = line.split(":", 1)[1].strip()
            current["enableDevelopmentBuild"] = value not in {"0", "false", "False", ""}

    if current is not None:
        profiles.append(current)

    profiles = [profile for profile in profiles if profile.get("configName")]
    if not profiles:
        raise ToolInvocationError(
            "build_config_profiles_missing",
            f"No build profiles were parsed from {asset_path}. Expected Configurations entries with ConfigName.",
        )

    return profiles


def build_compile_matrix_args_from_build_config(
    project_root: Path,
    build_config_asset: str | None,
    requested_profiles: list[str] | None,
    requested_targets: list[str] | None,
    stop_on_first_failure: bool,
) -> dict[str, Any]:
    asset_path = resolve_build_config_asset_path(project_root, build_config_asset)
    profiles = parse_unity_build_config_profiles(asset_path)

    selected_targets = requested_targets or ["Android", "iOS"]
    invalid_targets = [target for target in selected_targets if target not in {"Android", "iOS"}]
    if invalid_targets:
        raise ToolInvocationError("invalid_targets", f"Unsupported targets: {', '.join(invalid_targets)}")

    selected_profile_names = requested_profiles or [profile["configName"] for profile in profiles]
    selected_profile_set = set(selected_profile_names)
    available_profile_names = {profile["configName"] for profile in profiles}
    missing_profiles = [name for name in selected_profile_names if name not in available_profile_names]
    if missing_profiles:
        raise ToolInvocationError(
            "unknown_build_profiles",
            f"Unknown build profiles: {', '.join(missing_profiles)}. Available: {', '.join(sorted(available_profile_names))}",
        )

    configurations: list[dict[str, Any]] = []
    resolved_profiles: list[dict[str, Any]] = []
    for profile in profiles:
        if profile["configName"] not in selected_profile_set:
            continue

        resolved_profiles.append(profile)
        option_flags = ["DevelopmentBuild"] if profile.get("enableDevelopmentBuild") else []
        extra_defines = list(profile.get("scriptingDefines") or [])
        for target in selected_targets:
            configurations.append(
                {
                    "name": f"{profile['configName']}-{target}",
                    "target": target,
                    "optionFlags": option_flags,
                    "extraDefines": extra_defines,
                }
            )

    if not configurations:
        raise ToolInvocationError("build_config_matrix_empty", "No compile configurations were generated from the selected build profiles.")

    relative_asset_path = str(asset_path.relative_to(project_root))
    return {
        "assetPath": relative_asset_path,
        "profiles": resolved_profiles,
        "matrixArgs": {
            "stopOnFirstFailure": stop_on_first_failure,
            "configurations": configurations,
        },
    }


def bridge_response_to_tool_result(response: dict[str, Any]) -> dict[str, Any]:
    if response.get("status") == "ok":
        payload = {}
        payload_json = response.get("payload_json") or "{}"
        payload_type = str(response.get("payload_type") or "")
        try:
            payload = json.loads(payload_json)
        except json.JSONDecodeError:
            payload = {"raw_payload_json": payload_json}

        lifecycle = response.get("_xuunity_lifecycle")
        if isinstance(lifecycle, dict) and lifecycle:
            payload["_xuunity_lifecycle"] = lifecycle
        elif payload_type in {"unity.scenario.run", "unity.scenario.result"} and isinstance(payload, dict):
            payload = normalize_scenario_payload(payload)

        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(payload, ensure_ascii=True)
                }
            ],
            "structuredContent": payload,
            "isError": False
        }

    error = response.get("error") or {}
    message = error.get("message") or "Unknown bridge error."
    code = error.get("code") or "unknown_bridge_error"
    structured = {
        "error": {
            "code": code,
            "message": message
        }
    }
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(structured, ensure_ascii=True)
            }
        ],
        "structuredContent": structured,
        "isError": True
    }


def scenario_failure_tool_result(result_payload: dict[str, Any]) -> dict[str, Any]:
    scenario_name = str(result_payload.get("scenario_name") or "unknown_scenario")
    status = str(result_payload.get("status") or result_payload.get("terminal_status") or "failed")
    structured = {
        "error": {
            "code": "scenario_failed",
            "message": f"Scenario '{scenario_name}' finished with status '{status}'.",
        },
        "scenario": result_payload,
    }
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(structured, ensure_ascii=True)
            }
        ],
        "structuredContent": structured,
        "isError": True,
    }


def call_unity_compile_build_config_matrix_tool(arguments: dict[str, Any]) -> dict[str, Any]:
    project_root_value = arguments.get("projectRoot")
    if not isinstance(project_root_value, str) or not project_root_value.strip():
        raise JsonRpcError(-32602, "projectRoot is required.")

    project_root = ensure_project_root(project_root_value)
    timeout_ms = arguments.get("timeoutMs", 300000)
    if not isinstance(timeout_ms, int):
        raise JsonRpcError(-32602, "timeoutMs must be an integer.")

    profiles = arguments.get("profiles")
    if profiles is not None and not isinstance(profiles, list):
        raise JsonRpcError(-32602, "profiles must be an array of strings when provided.")

    targets = arguments.get("targets")
    if targets is not None and not isinstance(targets, list):
        raise JsonRpcError(-32602, "targets must be an array of strings when provided.")

    stop_on_first_failure = arguments.get("stopOnFirstFailure", False)
    if not isinstance(stop_on_first_failure, bool):
        raise JsonRpcError(-32602, "stopOnFirstFailure must be a boolean when provided.")

    build_config_asset = arguments.get("buildConfigAsset")
    if build_config_asset is not None and not isinstance(build_config_asset, str):
        raise JsonRpcError(-32602, "buildConfigAsset must be a string when provided.")

    try:
        compile_plan = build_compile_matrix_args_from_build_config(
            project_root=project_root,
            build_config_asset=build_config_asset,
            requested_profiles=profiles,
            requested_targets=targets,
            stop_on_first_failure=stop_on_first_failure,
        )
        response = invoke_bridge(
            str(project_root),
            "unity.compile.matrix",
            compile_plan["matrixArgs"],
            timeout_ms,
        )
    except ToolInvocationError as exc:
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({"error": {"code": exc.code, "message": exc.message}}, ensure_ascii=True)
                }
            ],
            "structuredContent": {"error": {"code": exc.code, "message": exc.message}},
            "isError": True
        }

    tool_result = bridge_response_to_tool_result(response)
    structured = tool_result.get("structuredContent") or {}
    if not tool_result.get("isError"):
        structured = {
            "build_config_asset": compile_plan["assetPath"],
            "profiles": compile_plan["profiles"],
            "matrix": structured,
        }
        tool_result["structuredContent"] = structured
        tool_result["content"] = [
            {
                "type": "text",
                "text": json.dumps(structured, ensure_ascii=True)
            }
        ]
    return tool_result


def call_unity_scenario_run_and_wait_tool(arguments: dict[str, Any]) -> dict[str, Any]:
    project_root_value = arguments.get("projectRoot")
    if not isinstance(project_root_value, str) or not project_root_value.strip():
        raise JsonRpcError(-32602, "projectRoot is required.")

    project_root = ensure_project_root(project_root_value)
    scenario = arguments.get("scenario")
    if not isinstance(scenario, dict):
        raise JsonRpcError(-32602, "scenario must be an object.")

    timeout_ms = arguments.get("timeoutMs", 120000)
    if not isinstance(timeout_ms, int):
        raise JsonRpcError(-32602, "timeoutMs must be an integer.")

    poll_interval_ms = arguments.get("pollIntervalMs", 1000)
    if not isinstance(poll_interval_ms, int):
        raise JsonRpcError(-32602, "pollIntervalMs must be an integer.")

    try:
        run_response = invoke_bridge(
            str(project_root),
            "unity.scenario.run",
            {"scenario": scenario},
            max(5000, min(timeout_ms, 15000)),
        )
        run_tool_result = bridge_response_to_tool_result(run_response)
        if run_tool_result.get("isError"):
            return run_tool_result

        run_payload = run_tool_result.get("structuredContent") or {}
        run_id = str(run_payload.get("run_id") or "")
        scenario_name = str(run_payload.get("scenario_name") or scenario.get("name") or "")
        result_payload = wait_for_scenario_result(
            project_root=project_root,
            run_id=run_id,
            scenario_name=scenario_name,
            timeout_ms=timeout_ms,
            poll_interval_ms=poll_interval_ms,
        )
    except ToolInvocationError as exc:
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({"error": {"code": exc.code, "message": exc.message}}, ensure_ascii=True)
                }
            ],
            "structuredContent": {"error": {"code": exc.code, "message": exc.message}},
            "isError": True
        }

    result_payload["run_start"] = run_payload
    if not bool(result_payload.get("succeeded")):
        return scenario_failure_tool_result(result_payload)
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(result_payload, ensure_ascii=True)
            }
        ],
        "structuredContent": result_payload,
        "isError": False
    }


def call_tool(name: str, arguments: dict[str, Any] | None) -> dict[str, Any]:
    if name not in TOOLS:
        raise JsonRpcError(-32601, f"Unknown tool: {name}")

    args = arguments or {}
    if name == "unity_compile_build_config_matrix":
        return call_unity_compile_build_config_matrix_tool(args)
    if name == "unity_scenario_run_and_wait":
        return call_unity_scenario_run_and_wait_tool(args)

    tool = TOOLS[name]
    project_root = args.get("projectRoot")
    if not isinstance(project_root, str) or not project_root.strip():
        raise JsonRpcError(-32602, "projectRoot is required.")

    timeout_ms = args.get("timeoutMs", 5000)
    if not isinstance(timeout_ms, int):
        raise JsonRpcError(-32602, "timeoutMs must be an integer.")

    bridge_args = dict(args)
    bridge_args.pop("projectRoot", None)
    bridge_args.pop("timeoutMs", None)

    try:
        response = invoke_bridge(project_root, tool["bridgeOperation"], bridge_args, timeout_ms)
    except ToolInvocationError as exc:
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({"error": {"code": exc.code, "message": exc.message}}, ensure_ascii=True)
                }
            ],
            "structuredContent": {"error": {"code": exc.code, "message": exc.message}},
            "isError": True
        }

    return bridge_response_to_tool_result(response)


class JsonRpcError(Exception):
    def __init__(self, code: int, message: str, data: Any = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


def success_response(request_id: Any, result: Any) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": result
    }


def error_response(request_id: Any, code: int, message: str, data: Any = None) -> dict[str, Any]:
    payload = {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": code,
            "message": message
        }
    }
    if data is not None:
        payload["error"]["data"] = data
    return payload


def emit_message(message: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(message, ensure_ascii=True, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def log_stderr(message: str) -> None:
    sys.stderr.write(message + "\n")
    sys.stderr.flush()


def build_initialize_result(requested_version: str | None) -> dict[str, Any]:
    protocol_version = requested_version or PROTOCOL_VERSION
    if protocol_version != PROTOCOL_VERSION:
        protocol_version = PROTOCOL_VERSION

    return {
        "protocolVersion": protocol_version,
        "capabilities": {
            "tools": {
                "listChanged": False
            }
        },
        "serverInfo": SERVER_INFO,
        "instructions": (
            "Use these tools for Unity editor validation over a lightweight file-IPC bridge. "
            "Every tool requires an explicit projectRoot."
        )
    }


def list_tools_result() -> dict[str, Any]:
    tools = []
    for name, spec in TOOLS.items():
        tools.append(
            {
                "name": name,
                "title": name.replace("_", " ").title(),
                "description": spec["description"],
                "inputSchema": spec["inputSchema"]
            }
        )
    return {"tools": tools}


def handle_json_rpc_message(message: dict[str, Any], session: dict[str, Any]) -> dict[str, Any] | None:
    request_id = message.get("id")
    method = message.get("method")
    params = message.get("params") or {}

    if method == "initialize":
        if not isinstance(params, dict):
            raise JsonRpcError(-32602, "initialize params must be an object.")
        requested_version = params.get("protocolVersion")
        session["initialized"] = False
        session["protocolVersion"] = PROTOCOL_VERSION
        return success_response(request_id, build_initialize_result(requested_version))

    if method == "notifications/initialized":
        session["initialized"] = True
        return None

    if method == "ping":
        return success_response(request_id, {})

    if method == "tools/list":
        return success_response(request_id, list_tools_result())

    if method == "tools/call":
        if not isinstance(params, dict):
            raise JsonRpcError(-32602, "tools/call params must be an object.")
        name = params.get("name")
        arguments = params.get("arguments")
        if not isinstance(name, str) or not name:
            raise JsonRpcError(-32602, "tools/call requires a non-empty tool name.")
        if arguments is not None and not isinstance(arguments, dict):
            raise JsonRpcError(-32602, "tools/call arguments must be an object when provided.")
        return success_response(request_id, call_tool(name, arguments))

    raise JsonRpcError(-32601, f"Method not found: {method}")


def serve_stdio() -> int:
    session = {"initialized": False, "protocolVersion": PROTOCOL_VERSION}
    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue

        message = None
        try:
            message = json.loads(line)
            if not isinstance(message, dict):
                raise JsonRpcError(-32600, "Invalid JSON-RPC message.")

            response = handle_json_rpc_message(message, session)
            if response is not None:
                emit_message(response)
        except json.JSONDecodeError:
            emit_message(error_response(None, -32700, "Parse error"))
        except JsonRpcError as exc:
            msg_id = message.get("id") if isinstance(message, dict) else None
            emit_message(error_response(msg_id, exc.code, exc.message, exc.data))
        except Exception as exc:
            log_stderr(f"[xuunity-light-unity-mcp] internal error: {exc}")
            msg_id = None
            if isinstance(message, dict):
                msg_id = message.get("id")
            emit_message(error_response(msg_id, -32603, "Internal error"))

    return 0


def cmd_bridge_state(args):
    project_root = ensure_project_root(args.project_root)
    if not bridge_enabled(project_root):
        raise SystemExit(
            "Bridge is disabled for this project. Enable it with "
            "init_xuunity_light_unity_mcp.sh --project-root <path> --enable-project and reopen Unity."
        )
    state_path = bridge_state_path(project_root)
    if not state_path.is_file():
        raise SystemExit(f"Bridge state file not found: {state_path}")
    print_json(annotate_bridge_state_with_liveness(read_json(state_path)))


def cmd_request_status(args):
    response = invoke_bridge(args.project_root, "unity.status", {}, args.timeout_ms)
    print_json(response)


def cmd_request_playmode_state(args):
    response = invoke_bridge(args.project_root, "unity.playmode.state", {}, args.timeout_ms)
    print_json(response)


def cmd_request_playmode_set(args):
    response = invoke_bridge(
        args.project_root,
        "unity.playmode.set",
        {"action": args.action},
        args.timeout_ms,
    )
    print_json(response)


def cmd_request_capabilities(args):
    response = invoke_bridge(args.project_root, "unity.capabilities.get", {}, args.timeout_ms)
    print_json(response)


def cmd_request_health_probe(args):
    response = invoke_bridge(args.project_root, "unity.health.probe", {}, args.timeout_ms)
    print_json(response)


def cmd_request_editor_quit(args):
    response = request_editor_quit(args.project_root, args.timeout_ms)
    print_json(response)


def cmd_request_project_refresh(args):
    response = invoke_bridge(
        args.project_root,
        "unity.project.refresh",
        {
            "forceAssetRefresh": args.force_asset_refresh,
            "resolvePackages": args.resolve_packages,
            "rerunHealthProbe": args.rerun_health_probe,
        },
        args.timeout_ms,
    )
    print_json(response)


def cmd_request_compile(args):
    response = invoke_bridge(
        args.project_root,
        "unity.compile.player_scripts",
        {
            "name": args.name,
            "target": args.target,
            "optionFlags": args.option_flags,
            "extraDefines": args.extra_defines,
        },
        args.timeout_ms,
    )
    print_json(response)


def cmd_request_compile_matrix(args):
    config_file = Path(args.config_file).expanduser().resolve()
    if not config_file.is_file():
        raise ToolInvocationError("compile_matrix_config_not_found", f"Compile matrix config file not found: {config_file}")

    try:
        matrix_args = json.loads(config_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ToolInvocationError("compile_matrix_config_invalid", str(exc)) from exc

    response = invoke_bridge(
        args.project_root,
        "unity.compile.matrix",
        matrix_args,
        args.timeout_ms,
    )
    print_json(response)


def cmd_request_build_config_compile_matrix(args):
    project_root = ensure_project_root(args.project_root)
    compile_plan = build_compile_matrix_args_from_build_config(
        project_root=project_root,
        build_config_asset=args.build_config_asset,
        requested_profiles=args.profile,
        requested_targets=args.target,
        stop_on_first_failure=args.stop_on_first_failure,
    )
    response = invoke_bridge(
        str(project_root),
        "unity.compile.matrix",
        compile_plan["matrixArgs"],
        args.timeout_ms,
    )

    payload = {
        "build_config_asset": compile_plan["assetPath"],
        "profiles": compile_plan["profiles"],
        "bridge_response": response,
    }
    print_json(payload)


def load_json_file(path_value: str, error_code: str) -> Any:
    path = Path(path_value).expanduser().resolve()
    if not path.is_file():
        raise ToolInvocationError(error_code, f"JSON file not found: {path}")

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ToolInvocationError(error_code, str(exc)) from exc


def cmd_request_scenario_validate(args):
    scenario = load_json_file(args.scenario_file, "scenario_file_invalid")
    response = invoke_bridge(
        args.project_root,
        "unity.scenario.validate",
        {"scenario": scenario},
        args.timeout_ms,
    )
    print_json(response)


def cmd_request_scenario_run(args):
    scenario = load_json_file(args.scenario_file, "scenario_file_invalid")
    response = invoke_bridge(
        args.project_root,
        "unity.scenario.run",
        {"scenario": scenario},
        args.timeout_ms,
    )
    print_json(response)


def cmd_request_scenario_run_and_wait(args):
    scenario = load_json_file(args.scenario_file, "scenario_file_invalid")
    result = call_unity_scenario_run_and_wait_tool(
        {
            "projectRoot": args.project_root,
            "scenario": scenario,
            "timeoutMs": args.timeout_ms,
            "pollIntervalMs": args.poll_interval_ms,
        }
    )
    print_json(result.get("structuredContent") or {})
    if result.get("isError"):
        raise SystemExit(1)


def cmd_request_scenario_result(args):
    bridge_args: dict[str, Any] = {}
    if args.run_id:
        bridge_args["runId"] = args.run_id
    if args.scenario_name:
        bridge_args["scenarioName"] = args.scenario_name

    response = invoke_bridge(
        args.project_root,
        "unity.scenario.result",
        bridge_args,
        args.timeout_ms,
    )
    print_json(response)


def cmd_open_editor(args):
    project_root = ensure_project_root(args.project_root)
    unity_app = detect_unity_app_path_for_project(project_root, args.unity_app)
    log_path = resolve_editor_log_path(project_root, args.editor_log_path)
    payload = open_unity_editor(project_root, log_path, unity_app, args.background_open)
    payload["project_root"] = str(project_root)
    print_json(payload)


def cmd_ensure_ready(args):
    project_root = ensure_project_root(args.project_root)
    log_path = resolve_editor_log_path(project_root, args.editor_log_path)

    payload: dict[str, Any] = {
        "project_root": str(project_root),
        "editor_log_path": str(log_path),
        "startup_policy": args.startup_policy,
    }

    if args.open_editor:
        unity_app = detect_unity_app_path_for_project(project_root, args.unity_app)
        payload["launch"] = open_unity_editor(project_root, log_path, unity_app, args.background_open)

    state = wait_for_ready(
        project_root=project_root,
        timeout_ms=args.timeout_ms,
        heartbeat_max_age_seconds=args.heartbeat_max_age_seconds,
        startup_policy=args.startup_policy,
        editor_log_path=log_path,
    )
    payload["bridge_state"] = state
    if payload.get("launch") and not bool(payload["launch"].get("reused_existing_editor")):
        update_host_editor_session_pid(project_root, int(state.get("editor_pid") or 0))
    payload["package_dependency"] = inspect_package_dependency_alignment(project_root)
    print_json(payload)


def cmd_restore_editor_state(args):
    project_root = ensure_project_root(args.project_root)
    payload = restore_host_opened_editor_state(project_root, args.timeout_ms)
    print_json(payload)


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "XUUnity Light Unity MCP server. "
            "Without arguments it serves MCP over stdio. "
            "Subcommands are local diagnostics helpers."
        )
    )
    sub = parser.add_subparsers(dest="command")

    state_cmd = sub.add_parser("bridge-state", help="Read the Unity bridge heartbeat state file.")
    state_cmd.add_argument("--project-root", required=True)
    state_cmd.set_defaults(func=cmd_bridge_state)

    status_cmd = sub.add_parser("request-status", help="Send a direct unity.status request through the active bridge transport.")
    status_cmd.add_argument("--project-root", required=True)
    status_cmd.add_argument("--timeout-ms", type=int, default=5000)
    status_cmd.set_defaults(func=cmd_request_status)

    playmode_state_cmd = sub.add_parser("request-playmode-state", help="Send a direct unity.playmode.state request through the active bridge transport.")
    playmode_state_cmd.add_argument("--project-root", required=True)
    playmode_state_cmd.add_argument("--timeout-ms", type=int, default=5000)
    playmode_state_cmd.set_defaults(func=cmd_request_playmode_state)

    playmode_set_cmd = sub.add_parser("request-playmode-set", help="Send a direct unity.playmode.set request through the active bridge transport.")
    playmode_set_cmd.add_argument("--project-root", required=True)
    playmode_set_cmd.add_argument("--action", required=True, choices=["enter", "exit", "pause", "resume"])
    playmode_set_cmd.add_argument("--timeout-ms", type=int, default=45000)
    playmode_set_cmd.set_defaults(func=cmd_request_playmode_set)

    capabilities_cmd = sub.add_parser("request-capabilities", help="Send a direct unity.capabilities.get request through the active bridge transport.")
    capabilities_cmd.add_argument("--project-root", required=True)
    capabilities_cmd.add_argument("--timeout-ms", type=int, default=5000)
    capabilities_cmd.set_defaults(func=cmd_request_capabilities)

    probe_cmd = sub.add_parser("request-health-probe", help="Send a direct unity.health.probe request through the active bridge transport.")
    probe_cmd.add_argument("--project-root", required=True)
    probe_cmd.add_argument("--timeout-ms", type=int, default=15000)
    probe_cmd.set_defaults(func=cmd_request_health_probe)

    editor_quit_cmd = sub.add_parser("request-editor-quit", help="Send a direct unity.editor.quit request through the active bridge transport.")
    editor_quit_cmd.add_argument("--project-root", required=True)
    editor_quit_cmd.add_argument("--timeout-ms", type=int, default=15000)
    editor_quit_cmd.set_defaults(func=cmd_request_editor_quit)

    project_refresh_cmd = sub.add_parser("request-project-refresh", help="Send a direct unity.project.refresh request through the active bridge transport.")
    project_refresh_cmd.add_argument("--project-root", required=True)
    project_refresh_cmd.add_argument("--force-asset-refresh", dest="force_asset_refresh", action=argparse.BooleanOptionalAction, default=True)
    project_refresh_cmd.add_argument("--resolve-packages", dest="resolve_packages", action=argparse.BooleanOptionalAction, default=True)
    project_refresh_cmd.add_argument("--rerun-health-probe", dest="rerun_health_probe", action=argparse.BooleanOptionalAction, default=True)
    project_refresh_cmd.add_argument("--timeout-ms", type=int, default=15000)
    project_refresh_cmd.set_defaults(func=cmd_request_project_refresh)

    compile_cmd = sub.add_parser("request-compile", help="Send a direct unity.compile.player_scripts request through the active bridge transport.")
    compile_cmd.add_argument("--project-root", required=True)
    compile_cmd.add_argument("--target", required=True)
    compile_cmd.add_argument("--name", default="")
    compile_cmd.add_argument("--option-flag", dest="option_flags", action="append", default=[])
    compile_cmd.add_argument("--extra-define", dest="extra_defines", action="append", default=[])
    compile_cmd.add_argument("--timeout-ms", type=int, default=120000)
    compile_cmd.set_defaults(func=cmd_request_compile)

    compile_matrix_cmd = sub.add_parser("request-compile-matrix", help="Send a direct unity.compile.matrix request using a JSON config file through the active bridge transport.")
    compile_matrix_cmd.add_argument("--project-root", required=True)
    compile_matrix_cmd.add_argument("--config-file", required=True)
    compile_matrix_cmd.add_argument("--timeout-ms", type=int, default=300000)
    compile_matrix_cmd.set_defaults(func=cmd_request_compile_matrix)

    build_config_matrix_cmd = sub.add_parser(
        "request-build-config-compile-matrix",
        help="Resolve build profiles from the project's *BuildConfiguration.asset and run the Android/iOS compile matrix through unity.compile.matrix on the active bridge transport.",
    )
    build_config_matrix_cmd.add_argument("--project-root", required=True)
    build_config_matrix_cmd.add_argument("--build-config-asset")
    build_config_matrix_cmd.add_argument("--profile", action="append", default=[])
    build_config_matrix_cmd.add_argument("--target", action="append", default=[])
    build_config_matrix_cmd.add_argument("--stop-on-first-failure", action="store_true")
    build_config_matrix_cmd.add_argument("--timeout-ms", type=int, default=300000)
    build_config_matrix_cmd.set_defaults(func=cmd_request_build_config_compile_matrix)

    scenario_validate_cmd = sub.add_parser("request-scenario-validate", help="Validate a Unity scenario JSON file through unity.scenario.validate on the active bridge transport.")
    scenario_validate_cmd.add_argument("--project-root", required=True)
    scenario_validate_cmd.add_argument("--scenario-file", required=True)
    scenario_validate_cmd.add_argument("--timeout-ms", type=int, default=5000)
    scenario_validate_cmd.set_defaults(func=cmd_request_scenario_validate)

    scenario_run_cmd = sub.add_parser("request-scenario-run", help="Start a Unity scenario JSON file through unity.scenario.run on the active bridge transport.")
    scenario_run_cmd.add_argument("--project-root", required=True)
    scenario_run_cmd.add_argument("--scenario-file", required=True)
    scenario_run_cmd.add_argument("--timeout-ms", type=int, default=5000)
    scenario_run_cmd.set_defaults(func=cmd_request_scenario_run)

    scenario_run_wait_cmd = sub.add_parser("request-scenario-run-and-wait", help="Start a Unity scenario JSON file and wait until it reaches a terminal state.")
    scenario_run_wait_cmd.add_argument("--project-root", required=True)
    scenario_run_wait_cmd.add_argument("--scenario-file", required=True)
    scenario_run_wait_cmd.add_argument("--timeout-ms", type=int, default=120000)
    scenario_run_wait_cmd.add_argument("--poll-interval-ms", type=int, default=1000)
    scenario_run_wait_cmd.set_defaults(func=cmd_request_scenario_run_and_wait)

    scenario_result_cmd = sub.add_parser("request-scenario-result", help="Read the current or completed result of a Unity scenario run.")
    scenario_result_cmd.add_argument("--project-root", required=True)
    scenario_result_cmd.add_argument("--run-id")
    scenario_result_cmd.add_argument("--scenario-name")
    scenario_result_cmd.add_argument("--timeout-ms", type=int, default=5000)
    scenario_result_cmd.set_defaults(func=cmd_request_scenario_result)

    open_editor_cmd = sub.add_parser("open-editor", help="Open a Unity project with a deterministic log file path for MCP startup diagnostics.")
    open_editor_cmd.add_argument("--project-root", required=True)
    open_editor_cmd.add_argument("--unity-app")
    open_editor_cmd.add_argument("--editor-log-path")
    open_editor_cmd.add_argument("--background-open", action="store_true")
    open_editor_cmd.set_defaults(func=cmd_open_editor)

    ensure_ready_cmd = sub.add_parser(
        "ensure-ready",
        help="Wait for a healthy Unity bridge heartbeat and fail fast on startup blockers visible in Editor.log.",
    )
    ensure_ready_cmd.add_argument("--project-root", required=True)
    ensure_ready_cmd.add_argument("--open-editor", action="store_true")
    ensure_ready_cmd.add_argument("--unity-app")
    ensure_ready_cmd.add_argument("--editor-log-path")
    ensure_ready_cmd.add_argument("--background-open", action="store_true")
    ensure_ready_cmd.add_argument("--timeout-ms", type=int, default=120000)
    ensure_ready_cmd.add_argument("--heartbeat-max-age-seconds", type=int, default=10)
    ensure_ready_cmd.add_argument(
        "--startup-policy",
        default="fail_fast_on_interactive_compile_block",
        choices=sorted(STARTUP_POLICIES),
    )
    ensure_ready_cmd.set_defaults(func=cmd_ensure_ready)

    restore_editor_cmd = sub.add_parser(
        "restore-editor-state",
        help="Close the Unity editor only when it was previously opened by this MCP host for the target project.",
    )
    restore_editor_cmd.add_argument("--project-root", required=True)
    restore_editor_cmd.add_argument("--timeout-ms", type=int, default=15000)
    restore_editor_cmd.set_defaults(func=cmd_restore_editor_state)

    return parser


def main():
    try:
        if len(sys.argv) == 1:
            raise SystemExit(serve_stdio())

        parser = build_parser()
        args = parser.parse_args()
        if not hasattr(args, "func"):
            parser.print_help()
            raise SystemExit(1)
        args.func(args)
    except ToolInvocationError as exc:
        raise SystemExit(f"{exc.code}: {exc.message}")


if __name__ == "__main__":
    main()
