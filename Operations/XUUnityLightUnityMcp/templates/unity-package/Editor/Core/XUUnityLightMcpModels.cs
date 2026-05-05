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
        public int bridge_version = 1;
        public string project_root = "";
        public int editor_pid;
        public string unity_version = "";
        public bool is_compiling;
        public bool is_playing;
        public string heartbeat_utc = "";
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
        public bool is_playing_or_will_change_playmode;
        public string playmode_state = "edit";
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
}
