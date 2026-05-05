using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEditor.TestTools.TestRunner.Api;
using UnityEngine;
using UnityEngine.SceneManagement;
using XUUnity.LightMcp.Editor.Bridge;
using XUUnity.LightMcp.Editor.Core;

namespace XUUnity.LightMcp.Editor.Operations
{
    internal sealed class XUUnityLightMcpEditModeTestsOperation : IXUUnityLightMcpOperation
    {
        public string OperationName => "unity.tests.run_editmode";

        public XUUnityLightMcpResponse Execute(XUUnityLightMcpRequest request)
        {
            if (EditorApplication.isCompiling)
            {
                return XUUnityLightMcpResponseWriter.Error(request.request_id, "compile_broken", "Unity is currently compiling scripts.");
            }

            if (EditorUtility.scriptCompilationFailed)
            {
                return XUUnityLightMcpResponseWriter.Error(request.request_id, "compile_broken", "Unity has compilation errors. Resolve them before running EditMode tests.");
            }

            var dirtyScenes = GetDirtyOpenScenes();
            if (dirtyScenes.Count > 0)
            {
                var sceneList = string.Join(", ", dirtyScenes.Select(FormatSceneForMessage));
                return XUUnityLightMcpResponseWriter.Error(
                    request.request_id,
                    "dirty_scene",
                    $"Cannot run EditMode tests while open scenes have unsaved changes: {sceneList}"
                );
            }

            return XUUnityLightMcpEditModeTestRunner.Start(request);
        }

        static List<Scene> GetDirtyOpenScenes()
        {
            var result = new List<Scene>(EditorSceneManager.sceneCount);
            for (var i = 0; i < EditorSceneManager.sceneCount; i++)
            {
                var scene = EditorSceneManager.GetSceneAt(i);
                if (scene.isDirty)
                {
                    result.Add(scene);
                }
            }
            return result;
        }

        static string FormatSceneForMessage(Scene scene)
        {
            var name = string.IsNullOrEmpty(scene.name) ? "(untitled)" : scene.name;
            var path = string.IsNullOrEmpty(scene.path) ? "(unsaved)" : scene.path;
            return $"'{name}' ({path})";
        }
    }

    [InitializeOnLoad]
    internal static class XUUnityLightMcpEditModeTestRunner
    {
        static readonly object Mutex = new();
        static volatile TestRunnerApi Api;
        static volatile XUUnityLightMcpEditModeCallbacks Callbacks;
        static volatile bool CallbacksRegistered;
        static volatile string ActiveRequestId;

        static XUUnityLightMcpEditModeTestRunner()
        {
            EnsureApi();
        }

        public static XUUnityLightMcpResponse Start(XUUnityLightMcpRequest request)
        {
            lock (Mutex)
            {
                if (!string.IsNullOrWhiteSpace(ActiveRequestId))
                {
                    return XUUnityLightMcpResponseWriter.Error(
                        request.request_id,
                        "tests_busy",
                        $"Another EditMode test run is already active: {ActiveRequestId}"
                    );
                }

                EnsureApi();
                Callbacks.Begin(request.request_id, XUUnityLightMcpFileIpcPaths.ProjectRootPath);

                try
                {
                    ActiveRequestId = request.request_id;
                    Api.Execute(new ExecutionSettings(new Filter
                    {
                        testMode = TestMode.EditMode
                    }));
                }
                catch (Exception ex)
                {
                    ActiveRequestId = null;
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
                Callbacks ??= new XUUnityLightMcpEditModeCallbacks(OnRunCompleted);

                if (!CallbacksRegistered)
                {
                    Api.RegisterCallbacks(Callbacks);
                    CallbacksRegistered = true;
                }
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
                    "unity.tests.run_editmode",
                    response?.status ?? "ok",
                    Callbacks.StartedAtUtc,
                    0);
                try
                {
                    XUUnityLightMcpRequestJournal.WriteRequestCompleted(
                        ActiveRequestId,
                        "unity.tests.run_editmode",
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
                XUUnityLightMcpResponseWriter.Write(response);
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

    internal sealed class XUUnityLightMcpEditModeCallbacks : ICallbacks
    {
        readonly Action<XUUnityLightMcpResponse> _onCompleted;
        readonly List<XUUnityLightMcpTestFailure> _failures = new();

        string _requestId = "";
        string _projectRoot = "";
        DateTime _startedAtUtc;
        bool _active;
        int _total;
        int _passed;
        int _failed;
        int _skipped;

        public bool IsActive => _active;
        public string StartedAtUtc => _active ? _startedAtUtc.ToString("yyyy-MM-ddTHH:mm:ssZ") : "";

        public XUUnityLightMcpEditModeCallbacks(Action<XUUnityLightMcpResponse> onCompleted)
        {
            _onCompleted = onCompleted ?? throw new ArgumentNullException(nameof(onCompleted));
        }

        public void Begin(string requestId, string projectRoot)
        {
            _requestId = requestId ?? "";
            _projectRoot = projectRoot ?? "";
            _startedAtUtc = DateTime.UtcNow;
            _active = true;
            _total = 0;
            _passed = 0;
            _failed = 0;
            _skipped = 0;
            _failures.Clear();
        }

        public void Clear()
        {
            _active = false;
            _requestId = "";
            _projectRoot = "";
            _startedAtUtc = default;
            _total = 0;
            _passed = 0;
            _failed = 0;
            _skipped = 0;
            _failures.Clear();
        }

        public void RunStarted(ITestAdaptor testsToRun)
        {
            _total = CountLeafTests(testsToRun);
        }

        public void RunFinished(ITestResultAdaptor result)
        {
            var payload = new XUUnityLightMcpTestsPayload
            {
                project_root = _projectRoot,
                total = _total,
                passed = _passed,
                failed = _failed,
                skipped = _skipped,
                duration_seconds = Math.Round((DateTime.UtcNow - _startedAtUtc).TotalSeconds, 6),
                failures = new List<XUUnityLightMcpTestFailure>(_failures)
            };

            payload.status = payload.total == 0
                ? "no_tests"
                : payload.failed > 0
                    ? "failed"
                    : "passed";

            _onCompleted(
                XUUnityLightMcpResponseWriter.Success(
                    _requestId,
                    "unity.tests.run_editmode",
                    JsonUtility.ToJson(payload)
                )
            );
        }

        public void TestStarted(ITestAdaptor test)
        {
        }

        public void TestFinished(ITestResultAdaptor result)
        {
            if (result?.Test == null || result.Test.IsSuite)
            {
                return;
            }

            switch (result.TestStatus)
            {
                case TestStatus.Passed:
                    _passed++;
                    break;
                case TestStatus.Failed:
                    _failed++;
                    _failures.Add(new XUUnityLightMcpTestFailure
                    {
                        name = result.Test.FullName ?? result.Test.Name ?? "",
                        message = result.Message ?? ""
                    });
                    break;
                case TestStatus.Skipped:
                    _skipped++;
                    break;
            }
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
