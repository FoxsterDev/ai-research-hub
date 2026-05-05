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
                transport_requested = XUUnityLightMcpBridgeTransportRuntime.RequestedTransport,
                transport = XUUnityLightMcpBridgeTransportRuntime.ActiveTransport,
                transport_listener_state = XUUnityLightMcpBridgeTransportRuntime.ListenerState,
                transport_host = XUUnityLightMcpBridgeTransportRuntime.TransportHost,
                transport_port = XUUnityLightMcpBridgeTransportRuntime.TransportPort,
                bridge_session_id = XUUnityLightMcpBridgeRuntimeState.BridgeSessionId,
                bridge_generation = XUUnityLightMcpBridgeRuntimeState.BridgeGeneration,
                bridge_bootstrap_attached = XUUnityLightMcpBridgeRuntimeState.BridgeBootstrapAttached,
                domain_reload_in_progress = XUUnityLightMcpBridgeRuntimeState.DomainReloadInProgress,
                domain_reload_started_utc = XUUnityLightMcpBridgeRuntimeState.DomainReloadStartedUtc,
                asset_import_in_progress = XUUnityLightMcpBridgeRuntimeState.AssetImportInProgress,
                asset_import_last_activity_utc = XUUnityLightMcpBridgeRuntimeState.AssetImportLastActivityUtc,
                package_operation_in_progress = XUUnityLightMcpBridgeRuntimeState.PackageOperationInProgress,
                package_operation_name = XUUnityLightMcpBridgeRuntimeState.PackageOperationName,
                package_operation_phase = XUUnityLightMcpBridgeRuntimeState.PackageOperationPhase,
                package_operation_started_utc = XUUnityLightMcpBridgeRuntimeState.PackageOperationStartedUtc,
                script_reload_pending = XUUnityLightMcpBridgeRuntimeState.ScriptReloadPending,
                script_reload_started_utc = XUUnityLightMcpBridgeRuntimeState.ScriptReloadStartedUtc,
                refresh_settle_pending = XUUnityLightMcpBridgeRuntimeState.RefreshSettlePending,
                refresh_settle_request_id = XUUnityLightMcpBridgeRuntimeState.RefreshSettleRequestId,
                refresh_settle_started_utc = XUUnityLightMcpBridgeRuntimeState.RefreshSettleStartedUtc,
                refresh_settle_completed_utc = XUUnityLightMcpBridgeRuntimeState.RefreshSettleCompletedUtc,
                refresh_settle_phase = XUUnityLightMcpBridgeRuntimeState.RefreshSettlePhase,
                refresh_settle_package_resolve_requested = XUUnityLightMcpBridgeRuntimeState.RefreshSettlePackageResolveRequested,
                compile_settle_pending = XUUnityLightMcpBridgeRuntimeState.CompileSettlePending,
                compile_settle_request_id = XUUnityLightMcpBridgeRuntimeState.CompileSettleRequestId,
                compile_settle_started_utc = XUUnityLightMcpBridgeRuntimeState.CompileSettleStartedUtc,
                compile_settle_completed_utc = XUUnityLightMcpBridgeRuntimeState.CompileSettleCompletedUtc,
                compile_settle_phase = XUUnityLightMcpBridgeRuntimeState.CompileSettlePhase,
                compile_settle_operation = XUUnityLightMcpBridgeRuntimeState.CompileSettleOperation,
                playmode_transition_pending = XUUnityLightMcpBridgeRuntimeState.PlayModeTransitionPending,
                playmode_transition_request_id = XUUnityLightMcpBridgeRuntimeState.PlayModeTransitionRequestId,
                playmode_transition_action = XUUnityLightMcpBridgeRuntimeState.PlayModeTransitionAction,
                playmode_transition_target_state = XUUnityLightMcpBridgeRuntimeState.PlayModeTransitionTargetState,
                playmode_transition_started_utc = XUUnityLightMcpBridgeRuntimeState.PlayModeTransitionStartedUtc,
                playmode_transition_completed_utc = XUUnityLightMcpBridgeRuntimeState.PlayModeTransitionCompletedUtc,
                playmode_transition_phase = XUUnityLightMcpBridgeRuntimeState.PlayModeTransitionPhase,
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
                request_journal_directory = XUUnityLightMcpFileIpcPaths.RequestJournalDirectory,
                request_journal_head = XUUnityLightMcpBridgeRuntimeState.RequestJournalHead,
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
            if (XUUnityLightMcpBridgeRuntimeState.DomainReloadInProgress)
            {
                return "domain_reload";
            }

            if (XUUnityLightMcpBridgeRuntimeState.PackageOperationInProgress)
            {
                return "package_operation";
            }

            if (XUUnityLightMcpBridgeRuntimeState.RefreshSettlePending)
            {
                return "refresh_settle";
            }

            if (XUUnityLightMcpBridgeRuntimeState.CompileSettlePending)
            {
                return "compile_settle";
            }

            if (XUUnityLightMcpBridgeRuntimeState.PlayModeTransitionPending)
            {
                return "playmode_settle";
            }

            if (EditorApplication.isCompiling)
            {
                return "compiling";
            }

            if (XUUnityLightMcpBridgeRuntimeState.ScriptReloadPending)
            {
                return "script_reload_pending";
            }

            if (XUUnityLightMcpBridgeRuntimeState.AssetImportInProgress)
            {
                return "asset_import";
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
            if (XUUnityLightMcpBridgeRuntimeState.DomainReloadInProgress)
            {
                return "AssemblyReloadEvents.beforeAssemblyReload";
            }

            if (XUUnityLightMcpBridgeRuntimeState.PackageOperationInProgress)
            {
                return $"{XUUnityLightMcpBridgeRuntimeState.PackageOperationName}:{XUUnityLightMcpBridgeRuntimeState.PackageOperationPhase}";
            }

            if (XUUnityLightMcpBridgeRuntimeState.RefreshSettlePending)
            {
                return XUUnityLightMcpBridgeRuntimeState.RefreshSettlePhase;
            }

            if (XUUnityLightMcpBridgeRuntimeState.CompileSettlePending)
            {
                return $"{XUUnityLightMcpBridgeRuntimeState.CompileSettleOperation}:{XUUnityLightMcpBridgeRuntimeState.CompileSettlePhase}";
            }

            if (XUUnityLightMcpBridgeRuntimeState.PlayModeTransitionPending)
            {
                return $"{XUUnityLightMcpBridgeRuntimeState.PlayModeTransitionAction}:{XUUnityLightMcpBridgeRuntimeState.PlayModeTransitionPhase}";
            }

            if (EditorApplication.isCompiling)
            {
                return "EditorApplication.isCompiling";
            }

            if (XUUnityLightMcpBridgeRuntimeState.ScriptReloadPending)
            {
                return "CompilationPipeline.compilationStarted";
            }

            if (XUUnityLightMcpBridgeRuntimeState.AssetImportInProgress)
            {
                return "AssetPostprocessor activity";
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
