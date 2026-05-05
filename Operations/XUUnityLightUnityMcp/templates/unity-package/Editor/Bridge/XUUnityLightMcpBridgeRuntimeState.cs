using System;
using System.IO;
using UnityEditor;
using UnityEngine;
using XUUnity.LightMcp.Editor.Core;

namespace XUUnity.LightMcp.Editor.Bridge
{
    internal static class XUUnityLightMcpBridgeRuntimeState
    {
        const double AssetImportActiveWindowSeconds = 2.0d;
        const double PackageOperationQuietWindowSeconds = 2.0d;
        const int RefreshSettleStableTickTarget = 2;
        const int CompileSettleStableTickTarget = 2;
        const int PlayModeTransitionStableTickTarget = 2;
        static readonly object Gate = new();
        static string _bridgeSessionId = "";
        static int _bridgeGeneration;
        static bool _bridgeBootstrapAttached;
        static bool _domainReloadInProgress;
        static string _domainReloadStartedUtc = "";
        static bool _assetImportInProgress;
        static string _assetImportLastActivityUtc = "";
        static double _assetImportActiveUntilRealtime;
        static bool _packageOperationInProgress;
        static string _packageOperationName = "";
        static string _packageOperationPhase = "";
        static string _packageOperationStartedUtc = "";
        static double _packageOperationStartedRealtime;
        static bool _scriptReloadPending;
        static string _scriptReloadStartedUtc = "";
        static bool _refreshSettlePending;
        static string _refreshSettleRequestId = "";
        static string _refreshSettleStartedUtc = "";
        static string _refreshSettleCompletedUtc = "";
        static string _refreshSettlePhase = "";
        static bool _refreshSettlePackageResolveRequested;
        static int _refreshSettleStableTickCount;
        static bool _compileSettlePending;
        static string _compileSettleRequestId = "";
        static string _compileSettleStartedUtc = "";
        static string _compileSettleCompletedUtc = "";
        static string _compileSettlePhase = "";
        static string _compileSettleOperation = "";
        static int _compileSettleStableTickCount;
        static bool _playModeTransitionPending;
        static string _playModeTransitionRequestId = "";
        static string _playModeTransitionAction = "";
        static string _playModeTransitionTargetState = "";
        static string _playModeTransitionStartedUtc = "";
        static string _playModeTransitionCompletedUtc = "";
        static string _playModeTransitionPhase = "";
        static int _playModeTransitionStableTickCount;
        static string _lastPumpUtc = "";
        static string _lastProcessedRequestId = "";
        static int _pendingRequestCount;
        static string _activeRequestId = "";
        static string _activeOperation = "";
        static string _activeOperationStartedUtc = "";
        static string _lastCompletedOperation = "";
        static string _lastCompletedOperationStatus = "";
        static double _lastCompletedOperationDurationSeconds;
        static string _requestJournalHead = "";

        public static string BridgeSessionId
        {
            get
            {
                lock (Gate)
                {
                    return _bridgeSessionId;
                }
            }
        }

        public static int BridgeGeneration
        {
            get
            {
                lock (Gate)
                {
                    return _bridgeGeneration;
                }
            }
        }

        public static bool BridgeBootstrapAttached
        {
            get
            {
                lock (Gate)
                {
                    return _bridgeBootstrapAttached;
                }
            }
        }

        public static bool DomainReloadInProgress
        {
            get
            {
                lock (Gate)
                {
                    return _domainReloadInProgress;
                }
            }
        }

        public static string DomainReloadStartedUtc
        {
            get
            {
                lock (Gate)
                {
                    return _domainReloadStartedUtc;
                }
            }
        }

        public static bool AssetImportInProgress
        {
            get
            {
                lock (Gate)
                {
                    return _assetImportInProgress;
                }
            }
        }

        public static string AssetImportLastActivityUtc
        {
            get
            {
                lock (Gate)
                {
                    return _assetImportLastActivityUtc;
                }
            }
        }

        public static bool PackageOperationInProgress
        {
            get
            {
                lock (Gate)
                {
                    return _packageOperationInProgress;
                }
            }
        }

        public static string PackageOperationName
        {
            get
            {
                lock (Gate)
                {
                    return _packageOperationName;
                }
            }
        }

        public static string PackageOperationPhase
        {
            get
            {
                lock (Gate)
                {
                    return _packageOperationPhase;
                }
            }
        }

        public static string PackageOperationStartedUtc
        {
            get
            {
                lock (Gate)
                {
                    return _packageOperationStartedUtc;
                }
            }
        }

        public static bool ScriptReloadPending
        {
            get
            {
                lock (Gate)
                {
                    return _scriptReloadPending;
                }
            }
        }

        public static string ScriptReloadStartedUtc
        {
            get
            {
                lock (Gate)
                {
                    return _scriptReloadStartedUtc;
                }
            }
        }

        public static bool RefreshSettlePending
        {
            get
            {
                lock (Gate)
                {
                    return _refreshSettlePending;
                }
            }
        }

        public static string RefreshSettleRequestId
        {
            get
            {
                lock (Gate)
                {
                    return _refreshSettleRequestId;
                }
            }
        }

        public static string RefreshSettleStartedUtc
        {
            get
            {
                lock (Gate)
                {
                    return _refreshSettleStartedUtc;
                }
            }
        }

        public static string RefreshSettleCompletedUtc
        {
            get
            {
                lock (Gate)
                {
                    return _refreshSettleCompletedUtc;
                }
            }
        }

        public static string RefreshSettlePhase
        {
            get
            {
                lock (Gate)
                {
                    return _refreshSettlePhase;
                }
            }
        }

        public static bool RefreshSettlePackageResolveRequested
        {
            get
            {
                lock (Gate)
                {
                    return _refreshSettlePackageResolveRequested;
                }
            }
        }

        public static bool CompileSettlePending
        {
            get
            {
                lock (Gate)
                {
                    return _compileSettlePending;
                }
            }
        }

        public static string CompileSettleRequestId
        {
            get
            {
                lock (Gate)
                {
                    return _compileSettleRequestId;
                }
            }
        }

        public static string CompileSettleStartedUtc
        {
            get
            {
                lock (Gate)
                {
                    return _compileSettleStartedUtc;
                }
            }
        }

        public static string CompileSettleCompletedUtc
        {
            get
            {
                lock (Gate)
                {
                    return _compileSettleCompletedUtc;
                }
            }
        }

        public static string CompileSettlePhase
        {
            get
            {
                lock (Gate)
                {
                    return _compileSettlePhase;
                }
            }
        }

        public static string CompileSettleOperation
        {
            get
            {
                lock (Gate)
                {
                    return _compileSettleOperation;
                }
            }
        }

        public static bool PlayModeTransitionPending
        {
            get
            {
                lock (Gate)
                {
                    return _playModeTransitionPending;
                }
            }
        }

        public static string PlayModeTransitionRequestId
        {
            get
            {
                lock (Gate)
                {
                    return _playModeTransitionRequestId;
                }
            }
        }

        public static string PlayModeTransitionAction
        {
            get
            {
                lock (Gate)
                {
                    return _playModeTransitionAction;
                }
            }
        }

        public static string PlayModeTransitionTargetState
        {
            get
            {
                lock (Gate)
                {
                    return _playModeTransitionTargetState;
                }
            }
        }

        public static string PlayModeTransitionStartedUtc
        {
            get
            {
                lock (Gate)
                {
                    return _playModeTransitionStartedUtc;
                }
            }
        }

        public static string PlayModeTransitionCompletedUtc
        {
            get
            {
                lock (Gate)
                {
                    return _playModeTransitionCompletedUtc;
                }
            }
        }

        public static string PlayModeTransitionPhase
        {
            get
            {
                lock (Gate)
                {
                    return _playModeTransitionPhase;
                }
            }
        }

        public static string LastPumpUtc
        {
            get
            {
                lock (Gate)
                {
                    return _lastPumpUtc;
                }
            }
        }

        public static string LastProcessedRequestId
        {
            get
            {
                lock (Gate)
                {
                    return _lastProcessedRequestId;
                }
            }
        }

        public static int PendingRequestCount
        {
            get
            {
                lock (Gate)
                {
                    return _pendingRequestCount;
                }
            }
        }

        public static string ActiveRequestId
        {
            get
            {
                lock (Gate)
                {
                    return _activeRequestId;
                }
            }
        }

        public static string ActiveOperation
        {
            get
            {
                lock (Gate)
                {
                    return _activeOperation;
                }
            }
        }

        public static string ActiveOperationStartedUtc
        {
            get
            {
                lock (Gate)
                {
                    return _activeOperationStartedUtc;
                }
            }
        }

        public static string LastCompletedOperation
        {
            get
            {
                lock (Gate)
                {
                    return _lastCompletedOperation;
                }
            }
        }

        public static string LastCompletedOperationStatus
        {
            get
            {
                lock (Gate)
                {
                    return _lastCompletedOperationStatus;
                }
            }
        }

        public static double LastCompletedOperationDurationSeconds
        {
            get
            {
                lock (Gate)
                {
                    return _lastCompletedOperationDurationSeconds;
                }
            }
        }

        public static string RequestJournalHead
        {
            get
            {
                lock (Gate)
                {
                    return _requestJournalHead;
                }
            }
        }

        public static bool TryGetActiveRequestSnapshot(out XUUnityLightMcpActiveRequestSnapshot snapshot)
        {
            lock (Gate)
            {
                if (string.IsNullOrWhiteSpace(_activeRequestId))
                {
                    snapshot = null;
                    return false;
                }

                snapshot = new XUUnityLightMcpActiveRequestSnapshot
                {
                    request_id = _activeRequestId,
                    operation = _activeOperation,
                    started_at_utc = _activeOperationStartedUtc,
                };
                return true;
            }
        }

        public static void InitializeBridgeSession()
        {
            lock (Gate)
            {
                XUUnityLightMcpFileIpcPaths.EnsureDirectories();

                var nextGeneration = 1;
                try
                {
                    if (File.Exists(XUUnityLightMcpFileIpcPaths.BridgeGenerationStatePath))
                    {
                        var json = File.ReadAllText(XUUnityLightMcpFileIpcPaths.BridgeGenerationStatePath);
                        var payload = JsonUtility.FromJson<XUUnityLightMcpBridgeGenerationState>(json);
                        if (payload != null)
                        {
                            nextGeneration = Math.Max(1, payload.bridge_generation + 1);
                        }
                    }
                }
                catch
                {
                }

                _bridgeGeneration = nextGeneration;
                _bridgeSessionId = Guid.NewGuid().ToString("N");
                _bridgeBootstrapAttached = true;
                _domainReloadInProgress = false;
                _domainReloadStartedUtc = "";
                _assetImportInProgress = false;
                _assetImportLastActivityUtc = "";
                _assetImportActiveUntilRealtime = 0.0d;
                _packageOperationInProgress = false;
                _packageOperationName = "";
                _packageOperationPhase = "";
                _packageOperationStartedUtc = "";
                _packageOperationStartedRealtime = 0.0d;
                _scriptReloadPending = false;
                _scriptReloadStartedUtc = "";
                _refreshSettlePending = false;
                _refreshSettleRequestId = "";
                _refreshSettleStartedUtc = "";
                _refreshSettleCompletedUtc = "";
                _refreshSettlePhase = "";
                _refreshSettlePackageResolveRequested = false;
                _refreshSettleStableTickCount = 0;
                _compileSettlePending = false;
                _compileSettleRequestId = "";
                _compileSettleStartedUtc = "";
                _compileSettleCompletedUtc = "";
                _compileSettlePhase = "";
                _compileSettleOperation = "";
                _compileSettleStableTickCount = 0;
                _playModeTransitionPending = false;
                _playModeTransitionRequestId = "";
                _playModeTransitionAction = "";
                _playModeTransitionTargetState = "";
                _playModeTransitionStartedUtc = "";
                _playModeTransitionCompletedUtc = "";
                _playModeTransitionPhase = "";
                _playModeTransitionStableTickCount = 0;
                _requestJournalHead = "";
                _activeRequestId = "";
                _activeOperation = "";
                _activeOperationStartedUtc = "";

                RestorePersistedPlayModeTransitionState();
                PersistGenerationState();
            }
        }

        public static void MarkJournalEvent(string eventId)
        {
            lock (Gate)
            {
                _requestJournalHead = eventId ?? "";
            }
        }

        public static void MarkDomainReloadStarting()
        {
            lock (Gate)
            {
                _domainReloadInProgress = true;
                _domainReloadStartedUtc = UtcNow();
                if (string.IsNullOrWhiteSpace(_scriptReloadStartedUtc))
                {
                    _scriptReloadStartedUtc = _domainReloadStartedUtc;
                }

                _scriptReloadPending = true;
            }
        }

        public static void MarkDomainReloadCompleted()
        {
            lock (Gate)
            {
                _domainReloadInProgress = false;
                _domainReloadStartedUtc = "";
                _scriptReloadPending = false;
                _scriptReloadStartedUtc = "";
            }
        }

        public static void MarkScriptReloadPending()
        {
            lock (Gate)
            {
                _scriptReloadPending = true;
                if (string.IsNullOrWhiteSpace(_scriptReloadStartedUtc))
                {
                    _scriptReloadStartedUtc = UtcNow();
                }
            }
        }

        public static void MarkScriptReloadCompleted()
        {
            lock (Gate)
            {
                _scriptReloadPending = false;
                _scriptReloadStartedUtc = "";
            }
        }

        public static void MarkAssetImportActivity()
        {
            lock (Gate)
            {
                _assetImportInProgress = true;
                _assetImportLastActivityUtc = UtcNow();
                _assetImportActiveUntilRealtime = EditorApplication.timeSinceStartup + AssetImportActiveWindowSeconds;
            }
        }

        public static void MarkPackageOperationStarted(string operationName, string phase = "started")
        {
            lock (Gate)
            {
                _packageOperationInProgress = true;
                _packageOperationName = operationName ?? "";
                _packageOperationPhase = phase ?? "";
                _packageOperationStartedUtc = UtcNow();
                _packageOperationStartedRealtime = EditorApplication.timeSinceStartup;
            }
        }

        public static void MarkPackageOperationCompleted()
        {
            lock (Gate)
            {
                if (!_packageOperationInProgress)
                {
                    return;
                }

                _packageOperationPhase = "settling";
                _packageOperationStartedRealtime = EditorApplication.timeSinceStartup;
            }
        }

        public static void BeginRefreshSettleTracking(string requestId, bool packageResolveRequested)
        {
            lock (Gate)
            {
                _refreshSettlePending = true;
                _refreshSettleRequestId = requestId ?? "";
                _refreshSettleStartedUtc = UtcNow();
                _refreshSettleCompletedUtc = "";
                _refreshSettlePhase = packageResolveRequested ? "waiting_for_package_settle" : "waiting_for_editor_idle";
                _refreshSettlePackageResolveRequested = packageResolveRequested;
                _refreshSettleStableTickCount = 0;
            }
        }

        public static void BeginCompileSettleTracking(string requestId, string operationName)
        {
            lock (Gate)
            {
                _compileSettlePending = true;
                _compileSettleRequestId = requestId ?? "";
                _compileSettleStartedUtc = UtcNow();
                _compileSettleCompletedUtc = "";
                _compileSettlePhase = "waiting_for_editor_idle";
                _compileSettleOperation = operationName ?? "";
                _compileSettleStableTickCount = 0;
            }
        }

        public static void BeginPlayModeTransitionTracking(string requestId, string action, string targetState)
        {
            lock (Gate)
            {
                _playModeTransitionPending = true;
                _playModeTransitionRequestId = requestId ?? "";
                _playModeTransitionAction = action ?? "";
                _playModeTransitionTargetState = targetState ?? "";
                _playModeTransitionStartedUtc = UtcNow();
                _playModeTransitionCompletedUtc = "";
                _playModeTransitionPhase = "waiting_for_target_state";
                _playModeTransitionStableTickCount = 0;
                PersistPlayModeTransitionState();
            }
        }

        public static void CancelPlayModeTransitionTracking()
        {
            lock (Gate)
            {
                _playModeTransitionPending = false;
                _playModeTransitionRequestId = "";
                _playModeTransitionAction = "";
                _playModeTransitionTargetState = "";
                _playModeTransitionStartedUtc = "";
                _playModeTransitionCompletedUtc = "";
                _playModeTransitionPhase = "";
                _playModeTransitionStableTickCount = 0;
                DeletePersistedPlayModeTransitionState();
            }
        }

        public static void MarkPlayModeStateChanged(string currentState)
        {
            lock (Gate)
            {
                if (_playModeTransitionPending)
                {
                    _playModeTransitionPhase = $"state_changed:{currentState ?? ""}";
                }
            }
        }

        public static void PollTransientLifecycleState()
        {
            lock (Gate)
            {
                if (_assetImportInProgress
                    && EditorApplication.timeSinceStartup >= _assetImportActiveUntilRealtime
                    && !EditorApplication.isUpdating)
                {
                    _assetImportInProgress = false;
                }

                if (_packageOperationInProgress
                    && !EditorApplication.isUpdating
                    && !EditorApplication.isCompiling
                    && !_domainReloadInProgress
                    && EditorApplication.timeSinceStartup >= _packageOperationStartedRealtime + PackageOperationQuietWindowSeconds)
                {
                    _packageOperationInProgress = false;
                    _packageOperationName = "";
                    _packageOperationPhase = "";
                    _packageOperationStartedUtc = "";
                    _packageOperationStartedRealtime = 0.0d;
                }

                if (_scriptReloadPending
                    && !_domainReloadInProgress
                    && !EditorApplication.isCompiling
                    && !EditorApplication.isUpdating)
                {
                    _scriptReloadPending = false;
                    _scriptReloadStartedUtc = "";
                }

                if (_refreshSettlePending)
                {
                    var editorIsIdle = !_domainReloadInProgress
                        && !_packageOperationInProgress
                        && !_scriptReloadPending
                        && !_assetImportInProgress
                        && !EditorApplication.isCompiling
                        && !EditorApplication.isUpdating
                        && (EditorApplication.isPlaying || !EditorApplication.isPlayingOrWillChangePlaymode);

                    _refreshSettlePhase = editorIsIdle
                        ? "waiting_for_stable_idle_ticks"
                        : (_refreshSettlePackageResolveRequested ? "waiting_for_package_settle" : "waiting_for_editor_idle");

                    if (editorIsIdle)
                    {
                        _refreshSettleStableTickCount++;
                        if (_refreshSettleStableTickCount >= RefreshSettleStableTickTarget)
                        {
                            _refreshSettlePending = false;
                            _refreshSettleCompletedUtc = UtcNow();
                            _refreshSettlePhase = "settled";
                        }
                    }
                    else
                    {
                        _refreshSettleStableTickCount = 0;
                    }
                }

                if (_compileSettlePending)
                {
                    var editorIsIdle = !_domainReloadInProgress
                        && !_packageOperationInProgress
                        && !_scriptReloadPending
                        && !_assetImportInProgress
                        && !EditorApplication.isCompiling
                        && !EditorApplication.isUpdating
                        && (EditorApplication.isPlaying || !EditorApplication.isPlayingOrWillChangePlaymode);

                    _compileSettlePhase = editorIsIdle
                        ? "waiting_for_stable_idle_ticks"
                        : "waiting_for_editor_idle";

                    if (editorIsIdle)
                    {
                        _compileSettleStableTickCount++;
                        if (_compileSettleStableTickCount >= CompileSettleStableTickTarget)
                        {
                            _compileSettlePending = false;
                            _compileSettleCompletedUtc = UtcNow();
                            _compileSettlePhase = "settled";
                        }
                    }
                    else
                    {
                        _compileSettleStableTickCount = 0;
                    }
                }

                if (_playModeTransitionPending)
                {
                    var currentState = ResolveCurrentPlayModeState();
                    var targetReached = string.Equals(currentState, _playModeTransitionTargetState, StringComparison.Ordinal);
                    var stableState = !EditorApplication.isUpdating
                        && !EditorApplication.isCompiling
                        && !_domainReloadInProgress
                        && !_scriptReloadPending
                        && !_assetImportInProgress
                        && !_packageOperationInProgress;

                    _playModeTransitionPhase = targetReached
                        ? "waiting_for_stable_target_state"
                        : $"waiting_for_target_state:{currentState}";

                    if (targetReached && stableState)
                    {
                        _playModeTransitionStableTickCount++;
                        if (_playModeTransitionStableTickCount >= PlayModeTransitionStableTickTarget)
                        {
                            _playModeTransitionPending = false;
                            _playModeTransitionCompletedUtc = UtcNow();
                            _playModeTransitionPhase = "settled";
                            DeletePersistedPlayModeTransitionState();
                        }
                    }
                    else
                    {
                        _playModeTransitionStableTickCount = 0;
                    }
                }
            }
        }

        public static void MarkPumpTick(int pendingRequestCount)
        {
            lock (Gate)
            {
                _lastPumpUtc = UtcNow();
                _pendingRequestCount = Math.Max(0, pendingRequestCount);
            }
        }

        public static void MarkRequestStarted(string requestId, string operation, int pendingRequestCount)
        {
            lock (Gate)
            {
                _lastPumpUtc = UtcNow();
                _activeRequestId = requestId ?? "";
                _activeOperation = operation ?? "";
                _activeOperationStartedUtc = _lastPumpUtc;
                _pendingRequestCount = Math.Max(0, pendingRequestCount);
            }
        }

        public static void MarkAsyncRequestPending(int remainingPendingRequests)
        {
            lock (Gate)
            {
                _lastPumpUtc = UtcNow();
                _pendingRequestCount = Math.Max(0, remainingPendingRequests);
            }
        }

        public static void MarkRequestProcessed(
            string requestId,
            string operation,
            string operationStatus,
            string startedAtUtc,
            int remainingPendingRequests)
        {
            lock (Gate)
            {
                _lastPumpUtc = UtcNow();
                if (!string.IsNullOrWhiteSpace(requestId))
                {
                    _lastProcessedRequestId = requestId;
                }

                _lastCompletedOperation = operation ?? "";
                _lastCompletedOperationStatus = operationStatus ?? "";
                _lastCompletedOperationDurationSeconds = CalculateDurationSeconds(startedAtUtc, _lastPumpUtc);
                _activeRequestId = "";
                _activeOperation = "";
                _activeOperationStartedUtc = "";
                _pendingRequestCount = Math.Max(0, remainingPendingRequests);
            }
        }

        static double CalculateDurationSeconds(string startedAtUtc, string completedAtUtc)
        {
            if (string.IsNullOrWhiteSpace(startedAtUtc))
            {
                return 0.0d;
            }

            if (!DateTime.TryParse(startedAtUtc, null, System.Globalization.DateTimeStyles.AdjustToUniversal | System.Globalization.DateTimeStyles.AssumeUniversal, out var started))
            {
                return 0.0d;
            }

            if (!DateTime.TryParse(completedAtUtc, null, System.Globalization.DateTimeStyles.AdjustToUniversal | System.Globalization.DateTimeStyles.AssumeUniversal, out var completed))
            {
                completed = DateTime.UtcNow;
            }

            return Math.Round(Math.Max(0.0d, (completed - started).TotalSeconds), 6);
        }

        static string UtcNow()
        {
            return DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ");
        }

        static void PersistPlayModeTransitionState()
        {
            var payload = new XUUnityLightMcpPersistedPlayModeTransitionState
            {
                request_id = _playModeTransitionRequestId,
                action = _playModeTransitionAction,
                target_state = _playModeTransitionTargetState,
                started_at_utc = _playModeTransitionStartedUtc,
                phase = _playModeTransitionPhase,
            };

            File.WriteAllText(XUUnityLightMcpFileIpcPaths.PlayModeTransitionStatePath, JsonUtility.ToJson(payload, true));
        }

        static void DeletePersistedPlayModeTransitionState()
        {
            try
            {
                if (File.Exists(XUUnityLightMcpFileIpcPaths.PlayModeTransitionStatePath))
                {
                    File.Delete(XUUnityLightMcpFileIpcPaths.PlayModeTransitionStatePath);
                }
            }
            catch
            {
            }
        }

        static void RestorePersistedPlayModeTransitionState()
        {
            try
            {
                if (!File.Exists(XUUnityLightMcpFileIpcPaths.PlayModeTransitionStatePath))
                {
                    return;
                }

                var json = File.ReadAllText(XUUnityLightMcpFileIpcPaths.PlayModeTransitionStatePath);
                var payload = JsonUtility.FromJson<XUUnityLightMcpPersistedPlayModeTransitionState>(json);
                if (payload == null || string.IsNullOrWhiteSpace(payload.request_id))
                {
                    DeletePersistedPlayModeTransitionState();
                    return;
                }

                _playModeTransitionPending = true;
                _playModeTransitionRequestId = payload.request_id ?? "";
                _playModeTransitionAction = payload.action ?? "";
                _playModeTransitionTargetState = payload.target_state ?? "";
                _playModeTransitionStartedUtc = payload.started_at_utc ?? UtcNow();
                _playModeTransitionCompletedUtc = "";
                _playModeTransitionPhase = string.IsNullOrWhiteSpace(payload.phase) ? "waiting_for_target_state" : payload.phase;
                _playModeTransitionStableTickCount = 0;
            }
            catch
            {
                DeletePersistedPlayModeTransitionState();
            }
        }

        static string ResolveCurrentPlayModeState()
        {
            if (EditorApplication.isPlaying)
            {
                return EditorApplication.isPaused ? "paused" : "playing";
            }

            return EditorApplication.isPlayingOrWillChangePlaymode ? "transitioning" : "edit";
        }

        static void PersistGenerationState()
        {
            var payload = new XUUnityLightMcpBridgeGenerationState
            {
                bridge_generation = _bridgeGeneration,
                bridge_session_id = _bridgeSessionId,
                bootstrap_attached_at_utc = UtcNow(),
            };

            File.WriteAllText(XUUnityLightMcpFileIpcPaths.BridgeGenerationStatePath, JsonUtility.ToJson(payload, true));
        }
    }
}
