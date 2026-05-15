using System;
using UnityEditor;
using UnityEditor.TestTools.TestRunner.Api;
using UnityEngine;
using XUUnity.LightMcp.Editor.Bridge;
using XUUnity.LightMcp.Editor.Core;
using XUUnity.LightMcp.Editor.Helpers;

namespace XUUnity.LightMcp.Editor.Operations
{
    internal sealed class XUUnityLightMcpEditModeTestsOperation : IXUUnityLightMcpOperation
    {
        public string OperationName => XUUnityLightMcpEditModeTestRunner.OperationName;

        public XUUnityLightMcpResponse Execute(XUUnityLightMcpRequest request)
        {
            if (!XUUnityLightMcpTestsUtility.TryPrepareTestRun(
                    request,
                    TestMode.EditMode,
                    "EditMode",
                    requireEditModeState: false,
                    out var filter,
                    out var filterSummary,
                    out var errorResponse))
            {
                return errorResponse;
            }

            return XUUnityLightMcpEditModeTestRunner.Start(request, filter, filterSummary);
        }
    }

    [InitializeOnLoad]
    internal static class XUUnityLightMcpEditModeTestRunner
    {
        internal const string OperationName = "unity.tests.run_editmode";

        static readonly object Mutex = new();
        static volatile TestRunnerApi Api;
        static volatile XUUnityLightMcpPersistedTestCallbacks Callbacks;
        static volatile bool CallbacksRegistered;
        static volatile string ActiveRequestId;

        static XUUnityLightMcpEditModeTestRunner()
        {
            XUUnityLightMcpTestRunState.TryWritePendingCompletedResponse();
            EnsureApi();
            RestoreActiveRunIfNeeded();
        }

        public static XUUnityLightMcpResponse Start(XUUnityLightMcpRequest request, Filter filter, string filterSummary)
        {
            lock (Mutex)
            {
                if (!string.IsNullOrWhiteSpace(ActiveRequestId))
                {
                    if (!XUUnityLightMcpTestRunState.TryRestoreActiveForOperation(OperationName, out var activeState)
                        || activeState == null
                        || !string.Equals(activeState.request_id, ActiveRequestId, StringComparison.Ordinal))
                    {
                        ActiveRequestId = null;
                        Callbacks?.Clear();
                    }
                }

                if (!string.IsNullOrWhiteSpace(ActiveRequestId))
                {
                    return XUUnityLightMcpResponseWriter.Error(
                        request.request_id,
                        "tests_busy",
                        $"Another test run is already active: {ActiveRequestId}. Wait for it to finish or recover it with request-latest-status --operation {OperationName} before retrying."
                    );
                }

                EnsureApi();
                Callbacks.Begin(request.request_id, filterSummary, request.timeout_ms);

                try
                {
                    ActiveRequestId = request.request_id;
                    Api.Execute(new ExecutionSettings(filter));
                }
                catch (Exception ex)
                {
                    ActiveRequestId = null;
                    Callbacks.Clear();
                    XUUnityLightMcpTestRunState.MarkAbandonedAndRelease("timeout_before_test_start");
                    return XUUnityLightMcpResponseWriter.Error(
                        request.request_id,
                        "test_execution_failed",
                        ex.Message
                    );
                }

                return null;
            }
        }

        static void EnsureApi()
        {
            lock (Mutex)
            {
                Api ??= ScriptableObject.CreateInstance<TestRunnerApi>();
                Callbacks ??= new XUUnityLightMcpPersistedTestCallbacks(OperationName, "editmode", OnRunCompleted);

                if (!CallbacksRegistered)
                {
                    Api.RegisterCallbacks(Callbacks);
                    CallbacksRegistered = true;
                }
            }
        }

        static void RestoreActiveRunIfNeeded()
        {
            lock (Mutex)
            {
                if (!XUUnityLightMcpTestRunState.TryRestoreActiveForOperation(OperationName, out var state))
                {
                    return;
                }

                EnsureApi();
                ActiveRequestId = state.request_id;
                Callbacks.Restore(state);
            }
        }

        static void OnRunCompleted(XUUnityLightMcpResponse response)
        {
            lock (Mutex)
            {
                if (string.IsNullOrWhiteSpace(ActiveRequestId) || !Callbacks.IsActive)
                {
                    return;
                }

                var completedAtUtc = response?.completed_at_utc ?? DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ");
                XUUnityLightMcpBridgeRuntimeState.MarkRequestProcessed(
                    ActiveRequestId,
                    OperationName,
                    response?.status ?? "ok",
                    Callbacks.StartedAtUtc,
                    0);
                try
                {
                    XUUnityLightMcpRequestJournal.WriteRequestCompleted(
                        ActiveRequestId,
                        OperationName,
                        response?.status ?? "ok",
                        Callbacks.StartedAtUtc,
                        completedAtUtc,
                        0);
                }
                catch
                {
                }

                ActiveRequestId = null;
                Callbacks.Clear();

                try
                {
                    XUUnityLightMcpResponseWriter.Write(response);
                    XUUnityLightMcpTestRunState.MarkResponseWrittenAndRelease();
                }
                catch
                {
                }

                try
                {
                    XUUnityLightMcpBridgeStateWriter.WriteHeartbeat();
                }
                catch
                {
                }
            }
        }
    }
}
