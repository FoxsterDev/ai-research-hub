using System;
using UnityEditor;
using UnityEngine;
using XUUnity.LightMcp.Editor.Bridge;
using XUUnity.LightMcp.Editor.Core;
using XUUnity.LightMcp.Editor.Helpers;

namespace XUUnity.LightMcp.Editor.Operations
{
    internal sealed class XUUnityLightMcpStatusOperation : IXUUnityLightMcpOperation
    {
        public string OperationName => "unity.status";

        public XUUnityLightMcpResponse Execute(XUUnityLightMcpRequest request)
        {
            var report = XUUnityLightMcpHealthProbe.EnsureCurrentReport();
            var visiblePendingRequestCount = GetVisiblePendingRequestCount(request);
            var activeOperation = GetVisibleActiveOperation(request);
            var activeRequestId = GetVisibleActiveRequestId(request);
            var activeStartedUtc = GetVisibleActiveOperationStartedUtc(request);
            var payload = new XUUnityLightMcpStatusPayload
            {
                project_root = XUUnityLightMcpFileIpcPaths.ProjectRootPath,
                is_compiling = EditorApplication.isCompiling,
                is_playing = EditorApplication.isPlaying,
                is_paused = EditorApplication.isPaused,
                is_updating = EditorApplication.isUpdating,
                is_playing_or_will_change_playmode = EditorApplication.isPlayingOrWillChangePlaymode,
                playmode_state = XUUnityLightMcpPlayModeStateOperation.ResolvePlayModeState(),
                last_pump_utc = XUUnityLightMcpBridgeRuntimeState.LastPumpUtc,
                last_processed_request_id = XUUnityLightMcpBridgeRuntimeState.LastProcessedRequestId,
                pending_request_count = visiblePendingRequestCount,
                busy_reason = ResolveBusyReason(activeOperation, visiblePendingRequestCount),
                busy_reason_detail = ResolveBusyReasonDetail(activeOperation, visiblePendingRequestCount),
                active_request_id = activeRequestId,
                active_operation = activeOperation,
                active_operation_started_utc = activeStartedUtc,
                last_completed_operation = XUUnityLightMcpBridgeRuntimeState.LastCompletedOperation,
                last_completed_operation_status = XUUnityLightMcpBridgeRuntimeState.LastCompletedOperationStatus,
                last_completed_operation_duration_seconds = XUUnityLightMcpBridgeRuntimeState.LastCompletedOperationDurationSeconds,
                health_status = report.status,
                supported_operations = report.supported_operations ?? new System.Collections.Generic.List<string>(),
                disabled_operations = report.disabled_operations ?? new System.Collections.Generic.List<string>()
            };

            return new XUUnityLightMcpResponse
            {
                request_id = request.request_id,
                status = "ok",
                completed_at_utc = DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ"),
                payload_type = "unity.status",
                payload_json = JsonUtility.ToJson(payload),
                error = null
            };
        }

        static string ResolveBusyReason(string activeOperation, int pendingRequestCount)
        {
            if (EditorApplication.isCompiling)
            {
                return "compiling";
            }

            if (EditorApplication.isUpdating)
            {
                return "updating";
            }

            if (!string.IsNullOrWhiteSpace(activeOperation))
            {
                return "processing_request";
            }

            if (!EditorApplication.isPlaying && EditorApplication.isPlayingOrWillChangePlaymode)
            {
                return "playmode_transition";
            }

            if (pendingRequestCount > 0)
            {
                return "request_queue_pending";
            }

            return "";
        }

        static string ResolveBusyReasonDetail(string activeOperation, int pendingRequestCount)
        {
            if (EditorApplication.isCompiling)
            {
                return "EditorApplication.isCompiling";
            }

            if (EditorApplication.isUpdating)
            {
                return "EditorApplication.isUpdating";
            }

            if (!string.IsNullOrWhiteSpace(activeOperation))
            {
                return activeOperation;
            }

            if (!EditorApplication.isPlaying && EditorApplication.isPlayingOrWillChangePlaymode)
            {
                return "EditorApplication.isPlayingOrWillChangePlaymode";
            }

            if (pendingRequestCount > 0)
            {
                return $"{pendingRequestCount} request(s) queued";
            }

            return "";
        }

        static string GetVisibleActiveOperation(XUUnityLightMcpRequest request)
        {
            if (IsSelfStatusRequest(request))
            {
                return "";
            }

            return XUUnityLightMcpBridgeRuntimeState.ActiveOperation;
        }

        static string GetVisibleActiveRequestId(XUUnityLightMcpRequest request)
        {
            if (IsSelfStatusRequest(request))
            {
                return "";
            }

            return XUUnityLightMcpBridgeRuntimeState.ActiveRequestId;
        }

        static string GetVisibleActiveOperationStartedUtc(XUUnityLightMcpRequest request)
        {
            if (IsSelfStatusRequest(request))
            {
                return "";
            }

            return XUUnityLightMcpBridgeRuntimeState.ActiveOperationStartedUtc;
        }

        static int GetVisiblePendingRequestCount(XUUnityLightMcpRequest request)
        {
            var count = XUUnityLightMcpBridgeRuntimeState.PendingRequestCount;
            if (request != null && string.Equals(request.operation, "unity.status", StringComparison.Ordinal))
            {
                count = Math.Max(0, count - 1);
            }

            return count;
        }

        static bool IsSelfStatusRequest(XUUnityLightMcpRequest request)
        {
            return request != null
                && string.Equals(request.operation, "unity.status", StringComparison.Ordinal)
                && string.Equals(XUUnityLightMcpBridgeRuntimeState.ActiveRequestId, request.request_id, StringComparison.Ordinal);
        }
    }
}
