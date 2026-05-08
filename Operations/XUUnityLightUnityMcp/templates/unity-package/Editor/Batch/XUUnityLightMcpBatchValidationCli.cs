using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEditor.TestTools.TestRunner.Api;
using UnityEngine;
using UnityEngine.SceneManagement;
using XUUnity.LightMcp.Editor.Core;
using XUUnity.LightMcp.Editor.Helpers;

namespace XUUnity.LightMcp.Editor.Batch
{
    public static class XUUnityLightMcpBatchValidationCli
    {
        const string ActionArg = "--xuunity-batch-action";
        const string ResultFileArg = "--xuunity-result-file";
        const string CompileNameArg = "--xuunity-compile-name";
        const string BuildTargetArg = "--xuunity-build-target";
        const string OptionFlagArg = "--xuunity-option-flag";
        const string ExtraDefineArg = "--xuunity-extra-define";
        const string ConfigFileArg = "--xuunity-config-file";
        const string StopOnFirstFailureArg = "--xuunity-stop-on-first-failure";
        const string TestNameArg = "--xuunity-test-name";
        const string GroupNameArg = "--xuunity-group-name";
        const string CategoryNameArg = "--xuunity-category-name";
        const string AssemblyNameArg = "--xuunity-assembly-name";

        [Serializable]
        sealed class BatchValidationArgs
        {
            public string action = "";
            public string resultFile = "";
            public string compileName = "";
            public string buildTarget = "";
            public string configFile = "";
            public bool stopOnFirstFailure;
            public string[] optionFlags = Array.Empty<string>();
            public string[] extraDefines = Array.Empty<string>();
            public string[] testNames = Array.Empty<string>();
            public string[] groupNames = Array.Empty<string>();
            public string[] categoryNames = Array.Empty<string>();
            public string[] assemblyNames = Array.Empty<string>();
        }

        [Serializable]
        sealed class BatchValidationResult
        {
            public string action = "batch_validation";
            public string operation = "";
            public string project_root = "";
            public string validation_evidence = "unity_batchmode";
            public string outcome = "batch_validation_failed";
            public bool succeeded;
            public string top_actionable_error = "";
            public string exception_message = "";
            public string started_at_utc = "";
            public string completed_at_utc = "";
            public double duration_seconds;
            public string compile_name = "";
            public string requested_build_target = "";
            public string config_file = "";
            public XUUnityLightMcpCompilePlayerScriptsPayload compile;
            public XUUnityLightMcpCompileMatrixPayload matrix;
            public XUUnityLightMcpTestsPayload tests;
        }

        static BatchValidationArgs _activeArgs;
        static BatchValidationResult _activeResult;
        static DateTime _startedAtUtc;

        public static void ExecuteFromCommandLine()
        {
            _startedAtUtc = DateTime.UtcNow;
            var args = new BatchValidationArgs();
            var result = new BatchValidationResult
            {
                project_root = XUUnityLightMcpFileIpcPaths.ProjectRootPath,
                started_at_utc = _startedAtUtc.ToString("yyyy-MM-ddTHH:mm:ssZ"),
            };

            var awaitAsyncCompletion = false;
            var exitCode = 1;

            try
            {
                args = ParseArgs(Environment.GetCommandLineArgs());
                result.operation = args.action ?? "";
                result.compile_name = args.compileName ?? "";
                result.requested_build_target = args.buildTarget ?? "";
                result.config_file = args.configFile ?? "";

                switch ((args.action ?? "").Trim())
                {
                    case "compile-player-scripts":
                        exitCode = ExecuteCompilePlayerScripts(args, result) ? 0 : 1;
                        break;

                    case "compile-matrix":
                        exitCode = ExecuteCompileMatrix(args, result) ? 0 : 1;
                        break;

                    case "editmode-tests":
                        _activeArgs = args;
                        _activeResult = result;
                        StartEditModeTests(args, result);
                        awaitAsyncCompletion = true;
                        break;

                    default:
                        throw new InvalidOperationException($"Unknown batch validation action '{args.action}'.");
                }
            }
            catch (Exception ex)
            {
                result.exception_message = string.IsNullOrWhiteSpace(ex.Message) ? "Batch validation failed." : ex.Message;
                result.top_actionable_error = string.IsNullOrWhiteSpace(ex.Message) ? "Batch validation failed." : ex.Message;
                result.succeeded = false;
                result.outcome = "batch_validation_failed";
            }
            finally
            {
                if (!awaitAsyncCompletion)
                {
                    FinalizeAndExit(args, result, exitCode);
                }
            }
        }

        static bool ExecuteCompilePlayerScripts(BatchValidationArgs args, BatchValidationResult result)
        {
            var compileArgs = new XUUnityLightMcpCompilePlayerScriptsArgs
            {
                name = args.compileName ?? "",
                target = args.buildTarget ?? "",
                optionFlags = NormalizeFilterValues(args.optionFlags),
                extraDefines = NormalizeFilterValues(args.extraDefines)
            };

            var compilePayload = XUUnityLightMcpCompileUtility.Compile(compileArgs);
            result.compile = new XUUnityLightMcpCompilePlayerScriptsPayload
            {
                project_root = XUUnityLightMcpFileIpcPaths.ProjectRootPath,
                request_completed_at_utc = DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ"),
                settled_at_utc = DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ"),
                completion_basis = "batchmode",
                settle_phase = "batchmode",
                playmode_state_after_settle = "edit",
                result = compilePayload,
                validation_evidence = "unity_batchmode"
            };

            result.succeeded = compilePayload.status == "passed";
            result.outcome = result.succeeded ? "batch_validation_completed" : "batch_validation_failed";
            result.top_actionable_error = FirstCompileError(compilePayload);
            return result.succeeded;
        }

        static bool ExecuteCompileMatrix(BatchValidationArgs args, BatchValidationResult result)
        {
            var configFile = (args.configFile ?? "").Trim();
            if (string.IsNullOrWhiteSpace(configFile))
            {
                throw new InvalidOperationException($"{ConfigFileArg} is required for compile-matrix.");
            }

            if (!File.Exists(configFile))
            {
                throw new FileNotFoundException($"Compile matrix config file was not found: {configFile}");
            }

            var rawJson = File.ReadAllText(configFile);
            var matrixArgs = JsonUtility.FromJson<XUUnityLightMcpCompileMatrixArgs>(rawJson) ?? new XUUnityLightMcpCompileMatrixArgs();
            if (matrixArgs.configurations == null || matrixArgs.configurations.Count == 0)
            {
                throw new InvalidOperationException("Compile matrix config did not contain any configurations.");
            }

            var startedAtUtc = DateTime.UtcNow;
            var matrixPayload = new XUUnityLightMcpCompileMatrixPayload
            {
                project_root = XUUnityLightMcpFileIpcPaths.ProjectRootPath,
                stop_on_first_failure = matrixArgs.stopOnFirstFailure,
                total = matrixArgs.configurations.Count,
                validation_evidence = "unity_batchmode"
            };

            var results = new List<XUUnityLightMcpCompileConfigPayload>(matrixArgs.configurations.Count);
            var passed = 0;
            var failed = 0;
            var skipped = 0;

            foreach (var configuration in matrixArgs.configurations)
            {
                XUUnityLightMcpCompileConfigPayload compilePayload;
                try
                {
                    compilePayload = XUUnityLightMcpCompileUtility.Compile(configuration);
                }
                catch (Exception ex)
                {
                    compilePayload = new XUUnityLightMcpCompileConfigPayload
                    {
                        name = string.IsNullOrWhiteSpace(configuration?.name) ? configuration?.target ?? "" : configuration.name,
                        target = configuration?.target ?? "",
                        status = "infrastructure_error",
                        errors = new List<XUUnityLightMcpCompileErrorItem>
                        {
                            new XUUnityLightMcpCompileErrorItem
                            {
                                message = ex.Message ?? "Compile matrix configuration failed."
                            }
                        },
                        error_count = 1
                    };
                }

                results.Add(compilePayload);
                switch (compilePayload.status)
                {
                    case "passed":
                        passed++;
                        break;
                    case "target_support_missing":
                        skipped++;
                        break;
                    default:
                        failed++;
                        break;
                }

                if (matrixArgs.stopOnFirstFailure && compilePayload.status != "passed")
                {
                    break;
                }
            }

            matrixPayload.results = results;
            matrixPayload.total = results.Count;
            matrixPayload.passed = passed;
            matrixPayload.failed = failed;
            matrixPayload.skipped = skipped;
            matrixPayload.status = failed > 0 ? "failed" : "passed";
            matrixPayload.request_completed_at_utc = DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ");
            matrixPayload.settled_at_utc = DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ");
            matrixPayload.completion_basis = "batchmode";
            matrixPayload.settle_phase = "batchmode";
            matrixPayload.playmode_state_after_settle = "edit";
            matrixPayload.duration_seconds = Math.Round((DateTime.UtcNow - startedAtUtc).TotalSeconds, 6);

            result.matrix = matrixPayload;
            result.succeeded = matrixPayload.status == "passed";
            result.outcome = result.succeeded ? "batch_validation_completed" : "batch_validation_failed";
            result.top_actionable_error = FirstCompileError(matrixPayload.results.FirstOrDefault(item => item.status != "passed"));
            return result.succeeded;
        }

        static void StartEditModeTests(BatchValidationArgs args, BatchValidationResult result)
        {
            if (EditorApplication.isCompiling)
            {
                throw new InvalidOperationException("Unity is currently compiling scripts.");
            }

            if (EditorUtility.scriptCompilationFailed)
            {
                throw new InvalidOperationException("Unity has compilation errors. Resolve them before running EditMode tests.");
            }

            var dirtyScenes = GetDirtyOpenScenes();
            if (dirtyScenes.Count > 0)
            {
                var sceneList = string.Join(", ", dirtyScenes.Select(FormatSceneForMessage));
                throw new InvalidOperationException($"Cannot run EditMode tests while open scenes have unsaved changes: {sceneList}");
            }

            if (!TryBuildFilter(args, out var filter, out var errorMessage))
            {
                throw new InvalidOperationException(errorMessage);
            }

            var api = ScriptableObject.CreateInstance<TestRunnerApi>();
            var callbacks = new BatchEditModeCallbacks(OnEditModeTestsCompleted);
            callbacks.Begin(result.project_root);
            api.RegisterCallbacks(callbacks);
            api.Execute(new ExecutionSettings(filter));
        }

        static void OnEditModeTestsCompleted(XUUnityLightMcpTestsPayload payload)
        {
            _activeResult.tests = payload;
            _activeResult.succeeded = payload.status == "passed";
            _activeResult.outcome = _activeResult.succeeded ? "batch_validation_completed" : "batch_validation_failed";
            _activeResult.top_actionable_error = FirstTestFailure(payload);
            FinalizeAndExit(_activeArgs, _activeResult, _activeResult.succeeded ? 0 : 1);
        }

        static BatchValidationArgs ParseArgs(string[] rawArgs)
        {
            var args = new BatchValidationArgs();
            var optionFlags = new List<string>();
            var extraDefines = new List<string>();
            var testNames = new List<string>();
            var groupNames = new List<string>();
            var categoryNames = new List<string>();
            var assemblyNames = new List<string>();

            for (var i = 0; i < rawArgs.Length; i++)
            {
                var current = rawArgs[i] ?? "";
                switch (current)
                {
                    case ActionArg:
                        args.action = RequireValue(rawArgs, ref i, ActionArg);
                        break;
                    case ResultFileArg:
                        args.resultFile = RequireValue(rawArgs, ref i, ResultFileArg);
                        break;
                    case CompileNameArg:
                        args.compileName = RequireValue(rawArgs, ref i, CompileNameArg);
                        break;
                    case BuildTargetArg:
                        args.buildTarget = RequireValue(rawArgs, ref i, BuildTargetArg);
                        break;
                    case ConfigFileArg:
                        args.configFile = RequireValue(rawArgs, ref i, ConfigFileArg);
                        break;
                    case OptionFlagArg:
                        optionFlags.Add(RequireValue(rawArgs, ref i, OptionFlagArg));
                        break;
                    case ExtraDefineArg:
                        extraDefines.Add(RequireValue(rawArgs, ref i, ExtraDefineArg));
                        break;
                    case TestNameArg:
                        testNames.Add(RequireValue(rawArgs, ref i, TestNameArg));
                        break;
                    case GroupNameArg:
                        groupNames.Add(RequireValue(rawArgs, ref i, GroupNameArg));
                        break;
                    case CategoryNameArg:
                        categoryNames.Add(RequireValue(rawArgs, ref i, CategoryNameArg));
                        break;
                    case AssemblyNameArg:
                        assemblyNames.Add(RequireValue(rawArgs, ref i, AssemblyNameArg));
                        break;
                    case StopOnFirstFailureArg:
                        args.stopOnFirstFailure = true;
                        break;
                }
            }

            args.optionFlags = optionFlags.ToArray();
            args.extraDefines = extraDefines.ToArray();
            args.testNames = testNames.ToArray();
            args.groupNames = groupNames.ToArray();
            args.categoryNames = categoryNames.ToArray();
            args.assemblyNames = assemblyNames.ToArray();
            return args;
        }

        static string RequireValue(string[] rawArgs, ref int index, string argumentName)
        {
            var valueIndex = index + 1;
            if (valueIndex >= rawArgs.Length || string.IsNullOrWhiteSpace(rawArgs[valueIndex]))
            {
                throw new InvalidOperationException($"{argumentName} requires a value.");
            }

            index = valueIndex;
            return rawArgs[valueIndex];
        }

        static void FinalizeAndExit(BatchValidationArgs args, BatchValidationResult result, int exitCode)
        {
            result.completed_at_utc = DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ");
            result.duration_seconds = Math.Round((DateTime.UtcNow - _startedAtUtc).TotalSeconds, 6);
            PersistResult(args.resultFile, result);
            if (Application.isBatchMode)
            {
                EditorApplication.Exit(exitCode);
            }
        }

        static void PersistResult(string resultFile, BatchValidationResult result)
        {
            if (string.IsNullOrWhiteSpace(resultFile))
            {
                return;
            }

            var fullPath = Path.GetFullPath(resultFile);
            var directory = Path.GetDirectoryName(fullPath);
            if (!string.IsNullOrWhiteSpace(directory))
            {
                Directory.CreateDirectory(directory);
            }

            File.WriteAllText(fullPath, JsonUtility.ToJson(result, true));
        }

        static bool TryBuildFilter(BatchValidationArgs args, out Filter filter, out string errorMessage)
        {
            filter = new Filter
            {
                testMode = TestMode.EditMode
            };
            errorMessage = "";

            filter.testNames = NormalizeFilterValues(args.testNames);
            filter.groupNames = NormalizeFilterValues(args.groupNames);
            filter.categoryNames = NormalizeFilterValues(args.categoryNames);
            filter.assemblyNames = NormalizeFilterValues(args.assemblyNames);
            return true;
        }

        static string[] NormalizeFilterValues(string[] values)
        {
            if (values == null || values.Length == 0)
            {
                return null;
            }

            var normalized = values
                .Where(value => !string.IsNullOrWhiteSpace(value))
                .Select(value => value.Trim())
                .Distinct()
                .ToArray();

            return normalized.Length == 0 ? null : normalized;
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

        static string FirstCompileError(XUUnityLightMcpCompileConfigPayload payload)
        {
            if (payload == null)
            {
                return "";
            }

            var firstError = payload.errors == null ? null : payload.errors.FirstOrDefault();
            if (firstError != null && !string.IsNullOrWhiteSpace(firstError.message))
            {
                return firstError.message;
            }

            return payload.status == "passed"
                ? ""
                : $"Compile validation finished with status '{payload.status}'.";
        }

        static string FirstTestFailure(XUUnityLightMcpTestsPayload payload)
        {
            if (payload == null)
            {
                return "";
            }

            var firstFailure = payload.failures == null ? null : payload.failures.FirstOrDefault();
            if (firstFailure != null && !string.IsNullOrWhiteSpace(firstFailure.message))
            {
                return firstFailure.message;
            }

            return payload.status == "passed"
                ? ""
                : $"EditMode tests finished with status '{payload.status}'.";
        }

        sealed class BatchEditModeCallbacks : ICallbacks
        {
            readonly Action<XUUnityLightMcpTestsPayload> _onCompleted;
            readonly List<XUUnityLightMcpTestFailure> _failures = new();

            string _projectRoot = "";
            DateTime _startedAtUtc;
            int _total;
            int _passed;
            int _failed;
            int _skipped;

            public BatchEditModeCallbacks(Action<XUUnityLightMcpTestsPayload> onCompleted)
            {
                _onCompleted = onCompleted ?? throw new ArgumentNullException(nameof(onCompleted));
            }

            public void Begin(string projectRoot)
            {
                _projectRoot = projectRoot ?? "";
                _startedAtUtc = DateTime.UtcNow;
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
                    failures = new List<XUUnityLightMcpTestFailure>(_failures),
                    validation_evidence = "unity_batchmode"
                };

                payload.status = payload.total == 0
                    ? "no_tests"
                    : payload.failed > 0
                        ? "failed"
                        : "passed";

                _onCompleted(payload);
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
}
