#!/usr/bin/env python3
import argparse
import calendar
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any

PROTOCOL_VERSION = "2025-06-18"
SERVER_INFO = {
    "name": "xuunity-light-unity-mcp",
    "version": "0.3.0",
}

STARTUP_POLICIES = {
    "auto_enter_safe_mode_preferred",
    "batch_compile_lane",
    "fail_fast_on_interactive_compile_block",
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
                "timeoutMs": {"type": "integer", "default": 5000, "minimum": 1000}
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
                "timeoutMs": {"type": "integer", "default": 5000, "minimum": 1000}
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
    }
}


def ensure_project_root(project_root: str) -> Path:
    root = Path(project_root).expanduser().resolve()
    if not (root / "Assets").is_dir() or not (root / "ProjectSettings" / "ProjectVersion.txt").is_file():
        raise ToolInvocationError("project_not_found", f"Not a Unity project root: {root}")
    return root


def bridge_root(project_root: Path) -> Path:
    return project_root / "Library" / "XUUnityLightMcp"


def bridge_state_path(project_root: Path) -> Path:
    return bridge_root(project_root) / "state" / "bridge_state.json"


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
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=True)
        handle.write("\n")


def print_json(data: Any) -> None:
    json.dump(data, sys.stdout, indent=2, ensure_ascii=True)
    sys.stdout.write("\n")


class ToolInvocationError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def bridge_enabled(project_root: Path) -> bool:
    config_path = bridge_config_path(project_root)
    if not config_path.is_file():
        return False

    try:
        data = read_json(config_path)
    except Exception:
        return False

    return bool(data.get("enabled"))


def invoke_bridge(project_root_value: str, operation: str, args: dict[str, Any], timeout_ms: int) -> dict[str, Any]:
    project_root = ensure_project_root(project_root_value)
    if not bridge_enabled(project_root):
        raise ToolInvocationError(
            "bridge_disabled",
            (
                "Unity bridge is disabled for this project. "
                "Enable it with init_xuunity_light_unity_mcp.sh --project-root <path> --enable-project "
                "and reopen Unity."
            ),
        )

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
            return response
        time.sleep(0.2)

    raise ToolInvocationError("operation_timeout", f"Timed out waiting for {response_path}")


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


def heartbeat_age_seconds(state: dict[str, Any]) -> float | None:
    heartbeat_utc = state.get("heartbeat_utc")
    if not isinstance(heartbeat_utc, str) or not heartbeat_utc:
        return None

    try:
        heartbeat_unix = calendar.timegm(time.strptime(heartbeat_utc, "%Y-%m-%dT%H:%M:%SZ"))
    except ValueError:
        return None

    return max(0.0, time.time() - heartbeat_unix)


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


def open_unity_editor(project_root: Path, log_path: Path, unity_app: Path, background_open: bool) -> dict[str, Any]:
    log_path.parent.mkdir(parents=True, exist_ok=True)

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
    return {
        "unity_app": str(unity_app),
        "editor_log_path": str(log_path),
        "background_open": background_open,
    }


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
        try:
            payload = json.loads(payload_json)
        except json.JSONDecodeError:
            payload = {"raw_payload_json": payload_json}

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


def call_tool(name: str, arguments: dict[str, Any] | None) -> dict[str, Any]:
    if name not in TOOLS:
        raise JsonRpcError(-32601, f"Unknown tool: {name}")

    args = arguments or {}
    if name == "unity_compile_build_config_matrix":
        return call_unity_compile_build_config_matrix_tool(args)

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
    print_json(read_json(state_path))


def cmd_request_status(args):
    response = invoke_bridge(args.project_root, "unity.status", {}, args.timeout_ms)
    print_json(response)


def cmd_request_capabilities(args):
    response = invoke_bridge(args.project_root, "unity.capabilities.get", {}, args.timeout_ms)
    print_json(response)


def cmd_request_health_probe(args):
    response = invoke_bridge(args.project_root, "unity.health.probe", {}, args.timeout_ms)
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
    unity_app = detect_unity_app_path(args.unity_app)
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
        unity_app = detect_unity_app_path(args.unity_app)
        payload["launch"] = open_unity_editor(project_root, log_path, unity_app, args.background_open)

    state = wait_for_ready(
        project_root=project_root,
        timeout_ms=args.timeout_ms,
        heartbeat_max_age_seconds=args.heartbeat_max_age_seconds,
        startup_policy=args.startup_policy,
        editor_log_path=log_path,
    )
    payload["bridge_state"] = state
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

    status_cmd = sub.add_parser("request-status", help="Send a direct file-IPC unity.status request.")
    status_cmd.add_argument("--project-root", required=True)
    status_cmd.add_argument("--timeout-ms", type=int, default=5000)
    status_cmd.set_defaults(func=cmd_request_status)

    capabilities_cmd = sub.add_parser("request-capabilities", help="Send a direct file-IPC unity.capabilities.get request.")
    capabilities_cmd.add_argument("--project-root", required=True)
    capabilities_cmd.add_argument("--timeout-ms", type=int, default=5000)
    capabilities_cmd.set_defaults(func=cmd_request_capabilities)

    probe_cmd = sub.add_parser("request-health-probe", help="Send a direct file-IPC unity.health.probe request.")
    probe_cmd.add_argument("--project-root", required=True)
    probe_cmd.add_argument("--timeout-ms", type=int, default=15000)
    probe_cmd.set_defaults(func=cmd_request_health_probe)

    compile_cmd = sub.add_parser("request-compile", help="Send a direct file-IPC unity.compile.player_scripts request.")
    compile_cmd.add_argument("--project-root", required=True)
    compile_cmd.add_argument("--target", required=True)
    compile_cmd.add_argument("--name", default="")
    compile_cmd.add_argument("--option-flag", dest="option_flags", action="append", default=[])
    compile_cmd.add_argument("--extra-define", dest="extra_defines", action="append", default=[])
    compile_cmd.add_argument("--timeout-ms", type=int, default=120000)
    compile_cmd.set_defaults(func=cmd_request_compile)

    compile_matrix_cmd = sub.add_parser("request-compile-matrix", help="Send a direct file-IPC unity.compile.matrix request using a JSON config file.")
    compile_matrix_cmd.add_argument("--project-root", required=True)
    compile_matrix_cmd.add_argument("--config-file", required=True)
    compile_matrix_cmd.add_argument("--timeout-ms", type=int, default=300000)
    compile_matrix_cmd.set_defaults(func=cmd_request_compile_matrix)

    build_config_matrix_cmd = sub.add_parser(
        "request-build-config-compile-matrix",
        help="Resolve build profiles from the project's *BuildConfiguration.asset and run the Android/iOS compile matrix through unity.compile.matrix.",
    )
    build_config_matrix_cmd.add_argument("--project-root", required=True)
    build_config_matrix_cmd.add_argument("--build-config-asset")
    build_config_matrix_cmd.add_argument("--profile", action="append", default=[])
    build_config_matrix_cmd.add_argument("--target", action="append", default=[])
    build_config_matrix_cmd.add_argument("--stop-on-first-failure", action="store_true")
    build_config_matrix_cmd.add_argument("--timeout-ms", type=int, default=300000)
    build_config_matrix_cmd.set_defaults(func=cmd_request_build_config_compile_matrix)

    scenario_validate_cmd = sub.add_parser("request-scenario-validate", help="Validate a Unity scenario JSON file through unity.scenario.validate.")
    scenario_validate_cmd.add_argument("--project-root", required=True)
    scenario_validate_cmd.add_argument("--scenario-file", required=True)
    scenario_validate_cmd.add_argument("--timeout-ms", type=int, default=5000)
    scenario_validate_cmd.set_defaults(func=cmd_request_scenario_validate)

    scenario_run_cmd = sub.add_parser("request-scenario-run", help="Start a Unity scenario JSON file through unity.scenario.run.")
    scenario_run_cmd.add_argument("--project-root", required=True)
    scenario_run_cmd.add_argument("--scenario-file", required=True)
    scenario_run_cmd.add_argument("--timeout-ms", type=int, default=5000)
    scenario_run_cmd.set_defaults(func=cmd_request_scenario_run)

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
