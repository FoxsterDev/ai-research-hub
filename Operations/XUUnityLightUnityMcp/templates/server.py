#!/usr/bin/env python3
import argparse
import json
import sys
import time
import uuid
from pathlib import Path
from typing import Any

PROTOCOL_VERSION = "2025-06-18"
SERVER_INFO = {
    "name": "xuunity-light-unity-mcp",
    "version": "0.1.0",
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


def call_tool(name: str, arguments: dict[str, Any] | None) -> dict[str, Any]:
    if name not in TOOLS:
        raise JsonRpcError(-32601, f"Unknown tool: {name}")

    args = arguments or {}
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
