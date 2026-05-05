using System;
using System.Diagnostics;
using System.IO;
using UnityEditor;
using UnityEngine;
using XUUnity.LightMcp.Editor.Core;
using XUUnity.LightMcp.Editor.Helpers;
using XUUnity.LightMcp.Editor.Operations;

namespace XUUnity.LightMcp.Editor.Bridge
{
    internal static class XUUnityLightMcpBridgeStateWriter
    {
        public static void WriteHeartbeat(string lastError = "")
        {
            XUUnityLightMcpFileIpcPaths.EnsureDirectories();
            var report = XUUnityLightMcpHealthProbe.EnsureCurrentReport();
            var playmodeState = XUUnityLightMcpPlayModeStateOperation.ResolvePlayModeState();

            var state = new XUUnityLightMcpBridgeState
            {
                project_root = XUUnityLightMcpFileIpcPaths.ProjectRootPath,
                editor_pid = Process.GetCurrentProcess().Id,
                unity_version = Application.unityVersion,
                is_compiling = EditorApplication.isCompiling,
                is_playing = EditorApplication.isPlaying,
                is_paused = EditorApplication.isPaused,
                is_updating = EditorApplication.isUpdating,
                is_playing_or_will_change_playmode = EditorApplication.isPlayingOrWillChangePlaymode,
                playmode_state = playmodeState,
                heartbeat_utc = DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ"),
                last_pump_utc = XUUnityLightMcpBridgeRuntimeState.LastPumpUtc,
                last_processed_request_id = XUUnityLightMcpBridgeRuntimeState.LastProcessedRequestId,
                pending_request_count = XUUnityLightMcpBridgeRuntimeState.PendingRequestCount,
                busy_reason = ResolveBusyReason(),
                busy_reason_detail = ResolveBusyReasonDetail(),
                active_request_id = XUUnityLightMcpBridgeRuntimeState.ActiveRequestId,
                active_operation = XUUnityLightMcpBridgeRuntimeState.ActiveOperation,
                active_operation_started_utc = XUUnityLightMcpBridgeRuntimeState.ActiveOperationStartedUtc,
                last_completed_operation = XUUnityLightMcpBridgeRuntimeState.LastCompletedOperation,
                last_completed_operation_status = XUUnityLightMcpBridgeRuntimeState.LastCompletedOperationStatus,
                last_completed_operation_duration_seconds = XUUnityLightMcpBridgeRuntimeState.LastCompletedOperationDurationSeconds,
                last_error = lastError ?? "",
                health_status = report.status,
                supported_operation_count = report.supported_operations?.Count ?? 0,
                disabled_operation_count = report.disabled_operations?.Count ?? 0,
                capabilities_report_path = XUUnityLightMcpFileIpcPaths.CapabilitiesReportPath
            };

            File.WriteAllText(XUUnityLightMcpFileIpcPaths.BridgeStatePath, JsonUtility.ToJson(state, true));
        }

        static string ResolveBusyReason()
        {
            if (EditorApplication.isCompiling)
            {
                return "compiling";
            }

            if (EditorApplication.isUpdating)
            {
                return "updating";
            }

            if (!string.IsNullOrWhiteSpace(XUUnityLightMcpBridgeRuntimeState.ActiveOperation))
            {
                return "processing_request";
            }

            if (!EditorApplication.isPlaying && EditorApplication.isPlayingOrWillChangePlaymode)
            {
                return "playmode_transition";
            }

            if (XUUnityLightMcpBridgeRuntimeState.PendingRequestCount > 0)
            {
                return "request_queue_pending";
            }

            return "";
        }

        static string ResolveBusyReasonDetail()
        {
            if (EditorApplication.isCompiling)
            {
                return "EditorApplication.isCompiling";
            }

            if (EditorApplication.isUpdating)
            {
                return "EditorApplication.isUpdating";
            }

            var activeOperation = XUUnityLightMcpBridgeRuntimeState.ActiveOperation;
            if (!string.IsNullOrWhiteSpace(activeOperation))
            {
                return activeOperation;
            }

            if (!EditorApplication.isPlaying && EditorApplication.isPlayingOrWillChangePlaymode)
            {
                return "EditorApplication.isPlayingOrWillChangePlaymode";
            }

            if (XUUnityLightMcpBridgeRuntimeState.PendingRequestCount > 0)
            {
                return $"{XUUnityLightMcpBridgeRuntimeState.PendingRequestCount} request(s) queued";
            }

            return "";
        }
    }
}
