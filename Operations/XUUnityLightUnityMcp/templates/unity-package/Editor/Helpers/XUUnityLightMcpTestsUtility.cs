using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEditor.TestTools.TestRunner.Api;
using UnityEngine;
using UnityEngine.SceneManagement;
using XUUnity.LightMcp.Editor.Core;
using XUUnity.LightMcp.Editor.Operations;

namespace XUUnity.LightMcp.Editor.Helpers
{
    internal static class XUUnityLightMcpTestsUtility
    {
        public static bool TryPrepareTestRun(
            XUUnityLightMcpRequest request,
            TestMode testMode,
            string modeLabel,
            bool requireEditModeState,
            out Filter filter,
            out string filterSummary,
            out XUUnityLightMcpResponse errorResponse)
        {
            filter = null;
            filterSummary = "";
            errorResponse = null;

            if (EditorApplication.isCompiling)
            {
                errorResponse = XUUnityLightMcpResponseWriter.Error(request.request_id, "compile_broken", "Unity is currently compiling scripts.");
                return false;
            }

            if (EditorUtility.scriptCompilationFailed)
            {
                errorResponse = XUUnityLightMcpResponseWriter.Error(
                    request.request_id,
                    "compile_broken",
                    $"Unity has compilation errors. Resolve them before running {modeLabel} tests.");
                return false;
            }

            var dirtyScenes = GetDirtyOpenScenes();
            if (dirtyScenes.Count > 0)
            {
                var sceneList = string.Join(", ", dirtyScenes.Select(FormatSceneForMessage));
                errorResponse = XUUnityLightMcpResponseWriter.Error(
                    request.request_id,
                    "dirty_scene",
                    $"Cannot run {modeLabel} tests while open scenes have unsaved changes: {sceneList}");
                return false;
            }

            if (requireEditModeState)
            {
                var playModeState = XUUnityLightMcpPlayModeStateOperation.ResolvePlayModeState();
                if (!string.Equals(playModeState, "edit", StringComparison.Ordinal))
                {
                    errorResponse = XUUnityLightMcpResponseWriter.Error(
                        request.request_id,
                        "playmode_state_invalid",
                        $"Cannot run {modeLabel} tests unless Unity is in edit mode. Current state: {playModeState}.");
                    return false;
                }
            }

            if (XUUnityLightMcpTestRunState.TryLoadPending(out var activeState))
            {
                errorResponse = XUUnityLightMcpResponseWriter.Error(
                    request.request_id,
                    "tests_busy",
                    $"Another test run is already active: {activeState.request_id}");
                return false;
            }

            if (!TryBuildFilter(request.args_json, testMode, modeLabel, out filter, out filterSummary, out var errorMessage))
            {
                errorResponse = XUUnityLightMcpResponseWriter.Error(request.request_id, "invalid_args", errorMessage);
                return false;
            }

            return true;
        }

        public static bool TryBuildFilter(
            string argsJson,
            TestMode testMode,
            string modeLabel,
            out Filter filter,
            out string filterSummary,
            out string errorMessage)
        {
            filter = new Filter
            {
                testMode = testMode
            };
            filterSummary = "all";
            errorMessage = "";

            XUUnityLightMcpTestsArgs args;
            try
            {
                args = string.IsNullOrWhiteSpace(argsJson)
                    ? new XUUnityLightMcpTestsArgs()
                    : JsonUtility.FromJson<XUUnityLightMcpTestsArgs>(argsJson) ?? new XUUnityLightMcpTestsArgs();
            }
            catch (Exception ex)
            {
                errorMessage = $"Invalid {modeLabel} test filter JSON: {ex.Message}";
                return false;
            }

            filter.testNames = NormalizeOptionalStringArray(args.testNames);
            filter.groupNames = NormalizeOptionalStringArray(args.groupNames);
            filter.categoryNames = NormalizeOptionalStringArray(args.categoryNames);
            filter.assemblyNames = NormalizeOptionalStringArray(args.assemblyNames);
            XUUnityLightMcpEditModeFilterResolver.ResolveTestNames(filter);
            filterSummary = BuildFilterSummary(filter);
            return true;
        }

        public static string BuildTestsArgsJson(XUUnityLightMcpScenarioStepDefinition step)
        {
            var args = new XUUnityLightMcpTestsArgs
            {
                testNames = NormalizeOptionalStringArray(step.testNames),
                groupNames = NormalizeOptionalStringArray(step.groupNames),
                categoryNames = NormalizeOptionalStringArray(step.categoryNames),
                assemblyNames = NormalizeOptionalStringArray(step.assemblyNames),
            };

            return args.testNames == null
                   && args.groupNames == null
                   && args.categoryNames == null
                   && args.assemblyNames == null
                ? "{}"
                : JsonUtility.ToJson(args);
        }

        public static string[] NormalizeOptionalStringArray(string[] values)
        {
            if (values == null || values.Length == 0)
            {
                return null;
            }

            var normalized = values
                .Where(value => !string.IsNullOrWhiteSpace(value))
                .Select(value => value.Trim())
                .Distinct(StringComparer.Ordinal)
                .ToArray();

            return normalized.Length == 0 ? null : normalized;
        }

        static string BuildFilterSummary(Filter filter)
        {
            return string.Join(
                "; ",
                new[]
                {
                    $"tests={JoinOrAll(filter.testNames)}",
                    $"groups={JoinOrAll(filter.groupNames)}",
                    $"categories={JoinOrAll(filter.categoryNames)}",
                    $"assemblies={JoinOrAll(filter.assemblyNames)}",
                });
        }

        static string JoinOrAll(string[] values)
        {
            return values == null || values.Length == 0 ? "all" : string.Join(",", values);
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
}
