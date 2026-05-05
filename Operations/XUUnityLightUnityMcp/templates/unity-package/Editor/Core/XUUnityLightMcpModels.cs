using System;
using System.Collections.Generic;

namespace XUUnity.LightMcp.Editor.Core
{
    [Serializable]
    internal sealed class XUUnityLightMcpBridgeConfig
    {
        public bool enabled;
        public int heartbeat_interval_ms = 2000;
        public int pump_interval_ms = 500;
        public bool auto_probe_on_startup = true;
    }

    [Serializable]
    internal sealed class XUUnityLightMcpBridgeState
    {
        public int bridge_version = 3;
        public string project_root = "";
        public int editor_pid;
        public string unity_version = "";
        public bool is_compiling;
        public bool is_playing;
        public bool is_paused;
        public bool is_updating;
        public bool is_playing_or_will_change_playmode;
        public string playmode_state = "edit";
        public string heartbeat_utc = "";
        public string last_pump_utc = "";
        public string last_processed_request_id = "";
        public int pending_request_count;
        public string busy_reason = "";
        public string busy_reason_detail = "";
        public string active_request_id = "";
        public string active_operation = "";
        public string active_operation_started_utc = "";
        public string last_completed_operation = "";
        public string last_completed_operation_status = "";
        public double last_completed_operation_duration_seconds;
        public string last_error = "";
        public string health_status = "";
        public int supported_operation_count;
        public int disabled_operation_count;
        public string capabilities_report_path = "";
    }

    [Serializable]
    internal sealed class XUUnityLightMcpRequest
    {
        public string request_id = "";
        public string operation = "";
        public string project_root = "";
        public string created_at_utc = "";
        public int timeout_ms = 30000;
        public string args_json = "{}";
    }

    [Serializable]
    internal sealed class XUUnityLightMcpError
    {
        public string code = "";
        public string message = "";
    }

    [Serializable]
    internal sealed class XUUnityLightMcpResponse
    {
        public string request_id = "";
        public string status = "";
        public string completed_at_utc = "";
        public string payload_type = "";
        public string payload_json = "";
        public XUUnityLightMcpError error;
    }

    [Serializable]
    internal sealed class XUUnityLightMcpStatusPayload
    {
        public string backend_id = "xuunity.light_unity_mcp";
        public string project_root = "";
        public bool editor_running = true;
        public bool mcp_reachable = true;
        public bool is_compiling;
        public bool is_playing;
        public bool is_paused;
        public bool is_updating;
        public bool is_playing_or_will_change_playmode;
        public string playmode_state = "edit";
        public string last_pump_utc = "";
        public string last_processed_request_id = "";
        public int pending_request_count;
        public string busy_reason = "";
        public string busy_reason_detail = "";
        public string active_request_id = "";
        public string active_operation = "";
        public string active_operation_started_utc = "";
        public string last_completed_operation = "";
        public string last_completed_operation_status = "";
        public double last_completed_operation_duration_seconds;
        public string transport = "file_ipc";
        public string health_status = "";
        public List<string> supported_operations = new();
        public List<string> disabled_operations = new();
        public string validation_evidence = "unity_mcp";
    }

    [Serializable]
    internal sealed class XUUnityLightMcpCapabilityRecord
    {
        public string capability_id = "";
        public string adapter_id = "";
        public bool supported;
        public string reason = "";
        public List<string> operations = new();
    }

    [Serializable]
    internal sealed class XUUnityLightMcpCapabilitiesReport
    {
        public int probe_version = 1;
        public string project_root = "";
        public string unity_version = "";
        public string checked_at_utc = "";
        public string status = "unknown";
        public List<string> supported_operations = new();
        public List<string> disabled_operations = new();
        public List<XUUnityLightMcpCapabilityRecord> capabilities = new();
    }

    [Serializable]
    internal sealed class XUUnityLightMcpCapabilitiesPayload
    {
        public string backend_id = "xuunity.light_unity_mcp";
        public string project_root = "";
        public XUUnityLightMcpCapabilitiesReport report = new();
        public string validation_evidence = "unity_mcp";
    }

    [Serializable]
    internal sealed class XUUnityLightMcpPlayModeStatePayload
    {
        public string backend_id = "xuunity.light_unity_mcp";
        public string project_root = "";
        public bool is_playing;
        public bool is_paused;
        public bool is_playing_or_will_change_playmode;
        public string playmode_state = "edit";
        public string validation_evidence = "unity_mcp";
    }

    [Serializable]
    internal sealed class XUUnityLightMcpPlayModeSetArgs
    {
        public string action = "";
    }

    [Serializable]
    internal sealed class XUUnityLightMcpPlayModeSetPayload
    {
        public string backend_id = "xuunity.light_unity_mcp";
        public string project_root = "";
        public string requested_action = "";
        public string outcome = "";
        public bool is_playing;
        public bool is_paused;
        public bool is_playing_or_will_change_playmode;
        public string playmode_state = "edit";
        public string validation_evidence = "unity_mcp";
    }

    [Serializable]
    internal sealed class XUUnityLightMcpConsoleTailArgs
    {
        public int limit = 50;
        public string[] includeTypes = null;
    }

    [Serializable]
    internal sealed class XUUnityLightMcpConsoleItem
    {
        public string type = "unknown";
        public string message = "";
        public string timestamp = "";
        public string stack_trace = "";
    }

    [Serializable]
    internal sealed class XUUnityLightMcpConsolePayload
    {
        public string backend_id = "xuunity.light_unity_mcp";
        public string project_root = "";
        public List<XUUnityLightMcpConsoleItem> items = new();
        public bool truncated;
        public string validation_evidence = "unity_mcp";
    }

    [Serializable]
    internal sealed class XUUnityLightMcpSceneData
    {
        public string name = "";
        public string path = "";
        public bool is_dirty;
        public int root_count;
    }

    [Serializable]
    internal sealed class XUUnityLightMcpRootObject
    {
        public string name = "";
    }

    [Serializable]
    internal sealed class XUUnityLightMcpSceneSnapshotPayload
    {
        public string backend_id = "xuunity.light_unity_mcp";
        public string project_root = "";
        public XUUnityLightMcpSceneData active_scene = new();
        public List<XUUnityLightMcpRootObject> root_objects = new();
        public string validation_evidence = "unity_mcp";
    }

    [Serializable]
    internal sealed class XUUnityLightMcpTestFailure
    {
        public string name = "";
        public string message = "";
    }

    [Serializable]
    internal sealed class XUUnityLightMcpTestsPayload
    {
        public string backend_id = "xuunity.light_unity_mcp";
        public string project_root = "";
        public string status = "infrastructure_error";
        public int total;
        public int passed;
        public int failed;
        public int skipped;
        public double duration_seconds;
        public List<XUUnityLightMcpTestFailure> failures = new();
        public string validation_evidence = "unity_mcp";
    }

    [Serializable]
    internal sealed class XUUnityLightMcpGameViewConfigureArgs
    {
        public int width;
        public int height;
        public string group = "";
        public string label = "";
        public bool allowCreateCustomSize;
    }

    [Serializable]
    internal sealed class XUUnityLightMcpGameViewData
    {
        public string group = "";
        public string label = "";
        public int width;
        public int height;
        public bool is_custom;
    }

    [Serializable]
    internal sealed class XUUnityLightMcpGameViewProbeResult
    {
        public string adapter_id = "game_view_reflection_v1";
        public bool supported;
        public string reason = "";
    }

    [Serializable]
    internal sealed class XUUnityLightMcpGameViewConfigurePayload
    {
        public string backend_id = "xuunity.light_unity_mcp";
        public string project_root = "";
        public string outcome = "";
        public XUUnityLightMcpGameViewData game_view = new();
        public string validation_evidence = "unity_mcp";
    }

    [Serializable]
    internal sealed class XUUnityLightMcpGameViewScreenshotArgs
    {
        public string fileName = "";
        public bool includeImage;
        public int maxResolution = 640;
    }

    [Serializable]
    internal sealed class XUUnityLightMcpGameViewScreenshotPayload
    {
        public string backend_id = "xuunity.light_unity_mcp";
        public string project_root = "";
        public string capture_source = "game_view";
        public string file_path = "";
        public int width;
        public int height;
        public string image_base64 = "";
        public bool image_included;
        public string validation_evidence = "unity_mcp";
    }

    [Serializable]
    internal sealed class XUUnityLightMcpProjectRefreshArgs
    {
        public bool forceAssetRefresh = true;
        public bool resolvePackages = true;
        public bool rerunHealthProbe = true;
    }

    [Serializable]
    internal sealed class XUUnityLightMcpProjectRefreshPayload
    {
        public string backend_id = "xuunity.light_unity_mcp";
        public string project_root = "";
        public string outcome = "";
        public string requested_outcome = "";
        public string request_completed_at_utc = "";
        public string settled_at_utc = "";
        public string completion_basis = "";
        public bool asset_database_refreshed;
        public bool package_resolve_requested;
        public bool capabilities_report_refreshed;
        public bool editor_is_compiling_after_request;
        public bool editor_is_updating_after_request;
        public string playmode_state_after_request = "edit";
        public bool editor_is_compiling_after_settle;
        public bool editor_is_updating_after_settle;
        public string playmode_state_after_settle = "edit";
        public string validation_evidence = "unity_mcp";
    }

    [Serializable]
    internal sealed class XUUnityLightMcpCompilePlayerScriptsArgs
    {
        public string name = "";
        public string target = "";
        public string[] optionFlags = null;
        public string[] extraDefines = null;
    }

    [Serializable]
    internal sealed class XUUnityLightMcpCompileMatrixArgs
    {
        public bool stopOnFirstFailure;
        public List<XUUnityLightMcpCompilePlayerScriptsArgs> configurations = new();
    }

    [Serializable]
    internal sealed class XUUnityLightMcpCompileErrorItem
    {
        public string assembly_name = "";
        public string message = "";
        public string file = "";
        public int line;
        public int column;
    }

    [Serializable]
    internal sealed class XUUnityLightMcpCompileConfigPayload
    {
        public string name = "";
        public string target = "";
        public string target_group = "";
        public bool target_supported;
        public List<string> option_flags = new();
        public List<string> extra_defines = new();
        public string output_directory = "";
        public double duration_seconds;
        public string status = "infrastructure_error";
        public int compiled_assembly_count;
        public List<XUUnityLightMcpCompileErrorItem> errors = new();
        public int error_count;
    }

    [Serializable]
    internal sealed class XUUnityLightMcpCompilePlayerScriptsPayload
    {
        public string backend_id = "xuunity.light_unity_mcp";
        public string project_root = "";
        public XUUnityLightMcpCompileConfigPayload result = new();
        public string validation_evidence = "unity_mcp";
    }

    [Serializable]
    internal sealed class XUUnityLightMcpCompileMatrixPayload
    {
        public string backend_id = "xuunity.light_unity_mcp";
        public string project_root = "";
        public string status = "infrastructure_error";
        public bool stop_on_first_failure;
        public int total;
        public int passed;
        public int failed;
        public int skipped;
        public double duration_seconds;
        public List<XUUnityLightMcpCompileConfigPayload> results = new();
        public string validation_evidence = "unity_mcp";
    }

    [Serializable]
    internal sealed class XUUnityLightMcpScenarioDefinition
    {
        public string name = "";
        public string description = "";
        public bool stopOnFirstFailure = true;
        public List<XUUnityLightMcpScenarioStepDefinition> steps = new();
    }

    [Serializable]
    internal sealed class XUUnityLightMcpScenarioStepDefinition
    {
        public string stepId = "";
        public string kind = "";
        public string action = "";
        public double durationSeconds;
        public double timeoutSeconds = 10.0d;
        public string expectedPlaymodeState = "";
        public int limit = 50;
        public string[] includeTypes = null;
        public string fileName = "";
        public bool includeImage;
        public int maxResolution = 640;
        public string target = "";
        public string[] optionFlags = null;
        public string[] extraDefines = null;
        public string name = "";
        public int width;
        public int height;
        public string group = "";
        public string label = "";
        public bool allowCreateCustomSize;
        public bool forceAssetRefresh = true;
        public bool resolvePackages = true;
        public bool rerunHealthProbe = true;
        public string hookName = "";
        public string hookPayloadJson = "";
    }

    [Serializable]
    internal sealed class XUUnityLightMcpScenarioValidateArgs
    {
        public XUUnityLightMcpScenarioDefinition scenario = new();
    }

    [Serializable]
    internal sealed class XUUnityLightMcpScenarioRunArgs
    {
        public XUUnityLightMcpScenarioDefinition scenario = new();
    }

    [Serializable]
    internal sealed class XUUnityLightMcpScenarioResultArgs
    {
        public string runId = "";
        public string scenarioName = "";
    }

    [Serializable]
    internal sealed class XUUnityLightMcpScenarioIssue
    {
        public string severity = "error";
        public string code = "";
        public string message = "";
        public string stepId = "";
        public int stepIndex = -1;
    }

    [Serializable]
    internal sealed class XUUnityLightMcpScenarioStepSummary
    {
        public string stepId = "";
        public string kind = "";
    }

    [Serializable]
    internal sealed class XUUnityLightMcpScenarioValidatePayload
    {
        public string backend_id = "xuunity.light_unity_mcp";
        public string project_root = "";
        public string scenario_name = "";
        public string status = "invalid";
        public int total_steps;
        public int error_count;
        public int warning_count;
        public List<XUUnityLightMcpScenarioIssue> issues = new();
        public List<XUUnityLightMcpScenarioStepSummary> steps = new();
        public string validation_evidence = "unity_mcp";
    }

    [Serializable]
    internal sealed class XUUnityLightMcpScenarioStepResult
    {
        public string stepId = "";
        public string kind = "";
        public string status = "pending";
        public string outcome = "";
        public string payload_json = "";
        public string error_code = "";
        public string error_message = "";
        public double duration_seconds;
    }

    [Serializable]
    internal sealed class XUUnityLightMcpScenarioRunPayload
    {
        public string backend_id = "xuunity.light_unity_mcp";
        public string project_root = "";
        public string run_id = "";
        public string scenario_name = "";
        public string status = "queued";
        public bool terminal;
        public bool succeeded;
        public string terminal_status = "";
        public string started_at_utc = "";
        public string updated_at_utc = "";
        public string completed_at_utc = "";
        public string result_path = "";
        public int total_steps;
        public int passed_steps;
        public int failed_steps;
        public int skipped_steps;
        public int current_step_index = -1;
        public double duration_seconds;
        public List<XUUnityLightMcpScenarioStepResult> steps = new();
        public string validation_evidence = "unity_mcp";
    }

    [Serializable]
    internal sealed class XUUnityLightMcpScenarioRunState
    {
        public string runId = "";
        public XUUnityLightMcpScenarioDefinition scenario = new();
        public string status = "queued";
        public string startedAtUtc = "";
        public string updatedAtUtc = "";
        public string completedAtUtc = "";
        public string resultPath = "";
        public int currentStepIndex;
        public string waitingUntilUtc = "";
        public string pendingNestedRequestId = "";
        public string pendingNestedOperation = "";
        public string pendingNestedStartedAtUtc = "";
        public int pendingNestedStableTickCount;
        public List<XUUnityLightMcpScenarioStepResult> steps = new();
    }
}
