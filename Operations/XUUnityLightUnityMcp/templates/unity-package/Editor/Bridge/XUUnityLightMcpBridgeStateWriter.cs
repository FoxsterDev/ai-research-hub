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
                request_journal_directory = XUUnityLightMcpFileIpcPaths.RequestJournalDirectory,
                request_journal_head = XUUnityLightMcpBridgeRuntimeState.RequestJournalHead,
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
