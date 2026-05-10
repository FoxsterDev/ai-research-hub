from pathlib import Path
from typing import Any

STARTUP_POLICIES = {
    "auto_enter_safe_mode_preferred",
    "batch_compile_lane",
    "fail_fast_on_interactive_compile_block",
}

SCENARIO_TERMINAL_STATUSES = {"passed", "failed"}

OPERATION_LIFECYCLE_POLICIES: dict[str, dict[str, Any]] = {
    "unity.status": {
        "retry_on_lifecycle_reset": True,
        "retry_on_transport_response_missing": True,
        "retry_on_transport_connect_failed": True,
    },
    "unity.capabilities.get": {
        "retry_on_lifecycle_reset": True,
        "retry_on_transport_response_missing": True,
        "retry_on_transport_connect_failed": True,
    },
    "unity.health.probe": {
        "retry_on_lifecycle_reset": True,
        "retry_on_transport_response_missing": True,
        "retry_on_transport_connect_failed": True,
    },
    "unity.build_target.get": {
        "retry_on_lifecycle_reset": True,
        "retry_on_transport_response_missing": True,
        "retry_on_transport_connect_failed": True,
    },
    "unity.build_target.switch": {
        "activate_unity": True,
        "wait_for_idle_before": True,
        "wait_for_idle_after": True,
        "idle_stable_cycles_after": 2,
        "retry_on_lifecycle_reset": True,
    },
    "unity.project.refresh": {
        "activate_unity": True,
        "wait_for_idle_before": True,
        "wait_for_idle_after": True,
        "idle_stable_cycles_after": 2,
        "retry_on_lifecycle_reset": True,
        "retry_on_transport_response_missing": True,
        "retry_on_transport_connect_failed": True,
        "post_reset_recovery_cap_ms": 180000,
    },
    "unity.scene.snapshot": {
        "retry_on_lifecycle_reset": True,
        "retry_on_transport_response_missing": True,
        "retry_on_transport_connect_failed": True,
    },
    "unity.scenario.validate": {
        "retry_on_lifecycle_reset": True,
        "retry_on_transport_response_missing": True,
        "retry_on_transport_connect_failed": True,
    },
    "unity.compile.player_scripts": {
        "activate_unity": True,
        "wait_for_idle_before": True,
        "wait_for_idle_after": True,
        "idle_stable_cycles_after": 2,
        "post_reset_recovery_cap_ms": 180000,
    },
    "unity.compile.matrix": {
        "activate_unity": True,
        "wait_for_idle_before": True,
        "wait_for_idle_after": True,
        "idle_stable_cycles_after": 2,
        "post_reset_recovery_cap_ms": 300000,
    },
    "unity.tests.run_editmode": {
        "activate_unity": True,
        "wait_for_idle_before": True,
        "wait_for_idle_after": True,
        "idle_stable_cycles_after": 2,
        "post_reset_recovery_cap_ms": 300000,
    },
    "unity.tests.run_playmode": {
        "activate_unity": True,
        "wait_for_idle_before": True,
        "wait_for_idle_after": True,
        "idle_stable_cycles_after": 2,
        "post_reset_recovery_cap_ms": 300000,
    },
    "unity.playmode.set": {
        "activate_unity": True,
        "wait_for_idle_before": True,
        "wait_for_idle_after": True,
        "idle_stable_cycles_after": 2,
        "post_reset_recovery_cap_ms": 180000,
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
        "post_reset_recovery_cap_ms": 600000,
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
                "tests_run_playmode",
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
    "unity_build_target_get": {
        "bridgeOperation": "unity.build_target.get",
        "description": "Return the current active Unity build target and target-group state for one project.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "projectRoot": {"type": "string"},
                "timeoutMs": {"type": "integer", "default": 5000, "minimum": 1000}
            },
            "required": ["projectRoot"]
        }
    },
    "unity_build_target_switch": {
        "bridgeOperation": "unity.build_target.switch",
        "description": "Switch the active Unity build target and wait until the editor returns to an idle state.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "projectRoot": {"type": "string"},
                "target": {
                    "type": "string",
                    "description": "Unity BuildTarget enum name, for example Android, iOS, StandaloneOSX, or StandaloneWindows64."
                },
                "timeoutMs": {"type": "integer", "default": 120000, "minimum": 1000}
            },
            "required": ["projectRoot", "target"]
        }
    },
    "unity_status_summary": {
        "description": "Return a compact Unity status summary suitable for polling and low-token diagnostics.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "projectRoot": {"type": "string"},
                "timeoutMs": {"type": "integer", "default": 5000, "minimum": 1000}
            },
            "required": ["projectRoot"]
        }
    },
    "unity_request_final_status": {
        "description": "Resolve final disposition for one request id from the request journal and current bridge state.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "projectRoot": {"type": "string"},
                "requestId": {"type": "string"},
                "operation": {"type": "string"},
                "timeoutMs": {"type": "integer", "default": 2000, "minimum": 0}
            },
            "required": ["projectRoot", "requestId"]
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
                "timeoutMs": {"type": "integer", "default": 180000, "minimum": 1000}
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
                "testNames": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "groupNames": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "categoryNames": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "assemblyNames": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "timeoutMs": {"type": "integer", "default": 300000, "minimum": 1000}
            },
            "required": ["projectRoot"]
        }
    },
    "unity_tests_run_playmode": {
        "bridgeOperation": "unity.tests.run_playmode",
        "description": "Run Unity PlayMode tests and return normalized result accounting.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "projectRoot": {"type": "string"},
                "testNames": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "groupNames": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "categoryNames": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "assemblyNames": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "timeoutMs": {"type": "integer", "default": 300000, "minimum": 1000}
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
                "timeoutMs": {"type": "integer", "default": 180000, "minimum": 1000}
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
                "timeoutMs": {"type": "integer", "default": 180000, "minimum": 1000}
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
    "unity_scenario_result_summary": {
        "description": "Return a compact summary of the current or completed Unity automation scenario result.",
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
    "unity_scenario_results_list": {
        "description": "List persisted Unity automation scenario results with compact summaries from Library/XUUnityLightMcp/scenarios/results.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "projectRoot": {"type": "string"},
                "scenarioName": {"type": "string"},
                "limit": {"type": "integer", "default": 20, "minimum": 1},
            },
            "required": ["projectRoot"],
        },
    },
    "unity_scenario_result_latest": {
        "description": "Return the latest persisted Unity automation scenario result summary, optionally filtered by scenario name.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "projectRoot": {"type": "string"},
                "scenarioName": {"type": "string"},
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
                "timeoutMs": {"type": "integer", "default": 600000, "minimum": 1000},
                "pollIntervalMs": {"type": "integer", "default": 1000, "minimum": 100},
            },
            "required": ["projectRoot", "scenario"],
        },
    },
    "unity_maintenance_prune": {
        "description": "Prune stale request-journal, scenario-result, capture, and optional log artifacts under Library/XUUnityLightMcp.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "projectRoot": {"type": "string"},
                "dryRun": {"type": "boolean", "default": False},
                "requestJournalMaxAgeHours": {"type": "integer", "default": 72, "minimum": 1},
                "requestJournalKeepLatest": {"type": "integer", "default": 200, "minimum": 0},
                "scenarioSuccessMaxAgeHours": {"type": "integer", "default": 168, "minimum": 1},
                "scenarioFailureMaxAgeHours": {"type": "integer", "default": 336, "minimum": 1},
                "scenarioRunningMaxAgeHours": {"type": "integer", "default": 168, "minimum": 1},
                "scenarioKeepLatestSuccess": {"type": "integer", "default": 20, "minimum": 0},
                "scenarioKeepLatestFailure": {"type": "integer", "default": 50, "minimum": 0},
                "scenarioKeepLatestRunning": {"type": "integer", "default": 20, "minimum": 0},
                "capturesMaxAgeHours": {"type": "integer", "default": 168, "minimum": 1},
                "capturesKeepLatest": {"type": "integer", "default": 20, "minimum": 0},
                "pruneLogs": {"type": "boolean", "default": False},
                "logsMaxAgeHours": {"type": "integer", "default": 168, "minimum": 1},
                "logsKeepLatest": {"type": "integer", "default": 10, "minimum": 0}
            },
            "required": ["projectRoot"]
        }
    },
}
