using System;
using System.IO;
using System.Linq;
using UnityEditor.TestTools.TestRunner.Api;
using XUUnity.LightMcp.Editor.Core;
using XUUnity.LightMcp.Editor.Operations;

namespace XUUnity.LightMcp.Editor.Helpers
{
    internal static class XUUnityLightMcpTestRunState
    {
        static readonly object Gate = new();

        public static XUUnityLightMcpPersistedTestRunState Begin(string requestId, string operation, string testMode, string filterSummary, int requestTimeoutMs)
        {
            lock (Gate)
            {
                XUUnityLightMcpFileIpcPaths.EnsureDirectories();
                var state = new XUUnityLightMcpPersistedTestRunState
                {
                    request_id = requestId ?? "",
                    operation = operation ?? "",
                    project_root = XUUnityLightMcpFileIpcPaths.ProjectRootPath,
                    test_mode = testMode ?? "",
                    started_at_utc = UtcNow(),
                    request_timeout_ms = Math.Max(1000, requestTimeoutMs),
                    completed_at_utc = "",
                    filter_summary = filterSummary ?? "",
                    response_handoff_state = "pending",
                    failures = new System.Collections.Generic.List<XUUnityLightMcpTestFailure>(),
                };

                PersistLocked(state);
                return state;
            }
        }

        public static bool TryLoadPending(out XUUnityLightMcpPersistedTestRunState state)
        {
            lock (Gate)
            {
                if (!TryLoadLocked(out state))
                {
                    return false;
                }

                if (ShouldDiscardStalePendingStateLocked(state))
                {
                    DeleteLocked();
                    state = null;
                    return false;
                }

                return !string.IsNullOrWhiteSpace(state.request_id)
                       && !string.Equals(state.response_handoff_state, "written", StringComparison.Ordinal);
            }
        }

        public static bool TryRestoreActiveForOperation(string operation, out XUUnityLightMcpPersistedTestRunState state)
        {
            lock (Gate)
            {
                if (!TryLoadLocked(out state))
                {
                    return false;
                }

                if (ShouldDiscardStalePendingStateLocked(state))
                {
                    DeleteLocked();
                    state = null;
                    return false;
                }

                return string.Equals(state.operation, operation ?? "", StringComparison.Ordinal)
                       && string.Equals(state.response_handoff_state, "pending", StringComparison.Ordinal)
                       && string.IsNullOrWhiteSpace(state.completed_at_utc)
                       && !string.IsNullOrWhiteSpace(state.request_id);
            }
        }

        public static void RecordRunStarted(int total)
        {
            lock (Gate)
            {
                if (!TryLoadLocked(out var state))
                {
                    return;
                }

                state.total = Math.Max(0, total);
                PersistLocked(state);
            }
        }

        public static void RecordTestFinished(TestStatus testStatus, string testName, string message)
        {
            lock (Gate)
            {
                if (!TryLoadLocked(out var state))
                {
                    return;
                }

                switch (testStatus)
                {
                    case TestStatus.Passed:
                        state.passed++;
                        break;
                    case TestStatus.Failed:
                        state.failed++;
                        state.failures.Add(new XUUnityLightMcpTestFailure
                        {
                            name = testName ?? "",
                            message = message ?? ""
                        });
                        break;
                    case TestStatus.Skipped:
                        state.skipped++;
                        break;
                }

                PersistLocked(state);
            }
        }

        public static XUUnityLightMcpResponse CompleteAndBuildResponse(string completionBasis, string playmodeStateAfterSettle)
        {
            lock (Gate)
            {
                if (!TryLoadLocked(out var state))
                {
                    return XUUnityLightMcpResponseWriter.Error("", "missing_test_run_state", "Test run state was lost before completion.");
                }

                state.completed_at_utc = UtcNow();
                state.completion_basis = completionBasis ?? "";
                state.playmode_state_after_settle = playmodeStateAfterSettle ?? "";
                state.response_handoff_state = "pending_write";
                PersistLocked(state);
                return BuildResponseLocked(state);
            }
        }

        public static bool TryWritePendingCompletedResponse()
        {
            lock (Gate)
            {
                if (!TryLoadLocked(out var state))
                {
                    return false;
                }

                if (!string.Equals(state.response_handoff_state, "pending_write", StringComparison.Ordinal)
                    || string.IsNullOrWhiteSpace(state.completed_at_utc))
                {
                    return false;
                }

                try
                {
                    XUUnityLightMcpResponseWriter.Write(BuildResponseLocked(state));
                    DeleteLocked();
                    return true;
                }
                catch
                {
                    return false;
                }
            }
        }

        public static void Clear()
        {
            lock (Gate)
            {
                DeleteLocked();
            }
        }

        static XUUnityLightMcpResponse BuildResponseLocked(XUUnityLightMcpPersistedTestRunState state)
        {
            return new XUUnityLightMcpResponse
            {
                request_id = state.request_id ?? "",
                status = "ok",
                completed_at_utc = string.IsNullOrWhiteSpace(state.completed_at_utc) ? UtcNow() : state.completed_at_utc,
                payload_type = state.operation ?? "",
                payload_json = UnityEngine.JsonUtility.ToJson(BuildPayloadLocked(state)),
                error = null
            };
        }

        static XUUnityLightMcpTestsPayload BuildPayloadLocked(XUUnityLightMcpPersistedTestRunState state)
        {
            return new XUUnityLightMcpTestsPayload
            {
                project_root = state.project_root ?? XUUnityLightMcpFileIpcPaths.ProjectRootPath,
                status = ResolveStatus(state),
                total = Math.Max(0, state.total),
                passed = Math.Max(0, state.passed),
                failed = Math.Max(0, state.failed),
                skipped = Math.Max(0, state.skipped),
                duration_seconds = CalculateDurationSeconds(state.started_at_utc, state.completed_at_utc),
                failures = state.failures == null
                    ? new System.Collections.Generic.List<XUUnityLightMcpTestFailure>()
                    : new System.Collections.Generic.List<XUUnityLightMcpTestFailure>(state.failures),
                started_at_utc = state.started_at_utc ?? "",
                completed_at_utc = state.completed_at_utc ?? "",
                completion_basis = state.completion_basis ?? "",
                playmode_state_after_settle = state.playmode_state_after_settle ?? "",
                validation_evidence = "unity_mcp"
            };
        }

        static string ResolveStatus(XUUnityLightMcpPersistedTestRunState state)
        {
            if (state == null)
            {
                return "infrastructure_error";
            }

            return state.total <= 0
                ? "no_tests"
                : state.failed > 0
                    ? "failed"
                    : "passed";
        }

        static bool TryLoadLocked(out XUUnityLightMcpPersistedTestRunState state)
        {
            state = null;
            try
            {
                if (!File.Exists(XUUnityLightMcpFileIpcPaths.ActiveTestRunStatePath))
                {
                    return false;
                }

                state = UnityEngine.JsonUtility.FromJson<XUUnityLightMcpPersistedTestRunState>(
                    File.ReadAllText(XUUnityLightMcpFileIpcPaths.ActiveTestRunStatePath));
                return state != null;
            }
            catch
            {
                state = null;
                return false;
            }
        }

        static bool ShouldDiscardStalePendingStateLocked(XUUnityLightMcpPersistedTestRunState state)
        {
            if (state == null
                || string.IsNullOrWhiteSpace(state.request_id)
                || !string.Equals(state.response_handoff_state, "pending", StringComparison.Ordinal)
                || !string.IsNullOrWhiteSpace(state.completed_at_utc))
            {
                return false;
            }

            try
            {
                if (!Directory.Exists(XUUnityLightMcpFileIpcPaths.RequestJournalDirectory))
                {
                    return false;
                }

                foreach (var path in Directory.EnumerateFiles(XUUnityLightMcpFileIpcPaths.RequestJournalDirectory, "*.json").OrderByDescending(value => value))
                {
                    var payload = UnityEngine.JsonUtility.FromJson<XUUnityLightMcpRequestJournalEvent>(File.ReadAllText(path));
                    if (payload == null || !string.Equals(payload.request_id, state.request_id, StringComparison.Ordinal))
                    {
                        continue;
                    }

                    if (string.Equals(payload.event_type, "request_completed", StringComparison.Ordinal))
                    {
                        return true;
                    }

                    if (string.Equals(payload.event_type, "request_abandoned", StringComparison.Ordinal)
                        && !string.Equals(state.operation, XUUnityLightMcpPlayModeTestRunner.OperationName, StringComparison.Ordinal))
                    {
                        return true;
                    }

                    if (string.Equals(payload.event_type, "request_abandoned", StringComparison.Ordinal)
                        && string.Equals(state.operation, XUUnityLightMcpPlayModeTestRunner.OperationName, StringComparison.Ordinal))
                    {
                        return IsRecoveryDeadlineExpiredLocked(state);
                    }
                }
            }
            catch
            {
            }

            return IsRecoveryDeadlineExpiredLocked(state);
        }

        static bool IsRecoveryDeadlineExpiredLocked(XUUnityLightMcpPersistedTestRunState state)
        {
            if (state == null)
            {
                return false;
            }

            if (!DateTime.TryParse(
                    state.started_at_utc,
                    null,
                    System.Globalization.DateTimeStyles.AdjustToUniversal | System.Globalization.DateTimeStyles.AssumeUniversal,
                    out var started))
            {
                return false;
            }

            var timeoutMs = Math.Max(1000, state.request_timeout_ms);
            var deadlineUtc = started.ToUniversalTime().AddMilliseconds(timeoutMs);
            return DateTime.UtcNow >= deadlineUtc;
        }

        static void PersistLocked(XUUnityLightMcpPersistedTestRunState state)
        {
            XUUnityLightMcpFileIpcPaths.EnsureDirectories();
            File.WriteAllText(
                XUUnityLightMcpFileIpcPaths.ActiveTestRunStatePath,
                UnityEngine.JsonUtility.ToJson(state, true));
        }

        static void DeleteLocked()
        {
            try
            {
                if (File.Exists(XUUnityLightMcpFileIpcPaths.ActiveTestRunStatePath))
                {
                    File.Delete(XUUnityLightMcpFileIpcPaths.ActiveTestRunStatePath);
                }
            }
            catch
            {
            }
        }

        static double CalculateDurationSeconds(string startedAtUtc, string completedAtUtc)
        {
            if (!DateTime.TryParse(
                    startedAtUtc,
                    null,
                    System.Globalization.DateTimeStyles.AdjustToUniversal | System.Globalization.DateTimeStyles.AssumeUniversal,
                    out var started))
            {
                return 0.0d;
            }

            if (!DateTime.TryParse(
                    completedAtUtc,
                    null,
                    System.Globalization.DateTimeStyles.AdjustToUniversal | System.Globalization.DateTimeStyles.AssumeUniversal,
                    out var completed))
            {
                completed = DateTime.UtcNow;
            }

            return Math.Round(Math.Max(0.0d, (completed - started).TotalSeconds), 6);
        }

        static string UtcNow()
        {
            return DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ");
        }
    }

    internal sealed class XUUnityLightMcpPersistedTestCallbacks : ICallbacks
    {
        readonly string _operationName;
        readonly string _testMode;
        readonly Action<XUUnityLightMcpResponse> _onCompleted;

        bool _active;
        string _startedAtUtc = "";

        public bool IsActive => _active;
        public string StartedAtUtc => _startedAtUtc ?? "";

        public XUUnityLightMcpPersistedTestCallbacks(string operationName, string testMode, Action<XUUnityLightMcpResponse> onCompleted)
        {
            _operationName = operationName ?? throw new ArgumentNullException(nameof(operationName));
            _testMode = testMode ?? throw new ArgumentNullException(nameof(testMode));
            _onCompleted = onCompleted ?? throw new ArgumentNullException(nameof(onCompleted));
        }

        public void Begin(string requestId, string filterSummary, int requestTimeoutMs)
        {
            var state = XUUnityLightMcpTestRunState.Begin(requestId, _operationName, _testMode, filterSummary, requestTimeoutMs);
            Restore(state);
        }

        public void Restore(XUUnityLightMcpPersistedTestRunState state)
        {
            _active = state != null
                      && string.Equals(state.operation, _operationName, StringComparison.Ordinal)
                      && string.Equals(state.response_handoff_state, "pending", StringComparison.Ordinal)
                      && string.IsNullOrWhiteSpace(state.completed_at_utc);
            _startedAtUtc = _active ? state.started_at_utc ?? "" : "";
        }

        public void Clear()
        {
            _active = false;
            _startedAtUtc = "";
        }

        public void RunStarted(ITestAdaptor testsToRun)
        {
            if (!_active)
            {
                return;
            }

            XUUnityLightMcpTestRunState.RecordRunStarted(CountLeafTests(testsToRun));
        }

        public void RunFinished(ITestResultAdaptor result)
        {
            if (!_active)
            {
                return;
            }

            var response = XUUnityLightMcpTestRunState.CompleteAndBuildResponse(
                "unity_test_runner_callbacks",
                XUUnityLightMcpPlayModeStateOperation.ResolvePlayModeState());
            _onCompleted(response);
        }

        public void TestStarted(ITestAdaptor test)
        {
        }

        public void TestFinished(ITestResultAdaptor result)
        {
            if (!_active || result?.Test == null || result.Test.IsSuite)
            {
                return;
            }

            XUUnityLightMcpTestRunState.RecordTestFinished(
                result.TestStatus,
                result.Test.FullName ?? result.Test.Name ?? "",
                result.Message ?? "");
        }

        static int CountLeafTests(ITestAdaptor test)
        {
            if (test == null)
            {
                return 0;
            }

            if (test.HasChildren && test.Children != null)
            {
                return test.Children.Sum(CountLeafTests);
            }

            return test.IsSuite ? 0 : 1;
        }
    }
}
