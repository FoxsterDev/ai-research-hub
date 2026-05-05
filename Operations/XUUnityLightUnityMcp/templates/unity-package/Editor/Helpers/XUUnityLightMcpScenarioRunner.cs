using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using UnityEditor;
using UnityEngine;
using XUUnity.LightMcp.Editor.Core;
using XUUnity.LightMcp.Editor.Operations;
using XUUnity.LightMcp.Editor.ScenarioHooks;

namespace XUUnity.LightMcp.Editor.Helpers
{
    internal static class XUUnityLightMcpScenarioRunner
    {
        public static XUUnityLightMcpScenarioValidatePayload Validate(XUUnityLightMcpScenarioDefinition scenario)
        {
            var payload = new XUUnityLightMcpScenarioValidatePayload
            {
                project_root = XUUnityLightMcpFileIpcPaths.ProjectRootPath,
                scenario_name = NormalizeScenarioName(scenario?.name),
            };

            var steps = scenario?.steps ?? new List<XUUnityLightMcpScenarioStepDefinition>();
            payload.total_steps = steps.Count;

            if (string.IsNullOrWhiteSpace(scenario?.name))
            {
                AddIssue(payload, "error", "missing_name", "Scenario name is required.", "", -1);
            }

            if (steps.Count == 0)
            {
                AddIssue(payload, "error", "missing_steps", "Scenario must contain at least one step.", "", -1);
            }

            var seenStepIds = new HashSet<string>(StringComparer.Ordinal);
            for (var i = 0; i < steps.Count; i++)
            {
                var step = steps[i] ?? new XUUnityLightMcpScenarioStepDefinition();
                var stepId = NormalizeStepId(step, i);
                payload.steps.Add(new XUUnityLightMcpScenarioStepSummary
                {
                    stepId = stepId,
                    kind = (step.kind ?? "").Trim().ToLowerInvariant(),
                });

                if (!seenStepIds.Add(stepId))
                {
                    AddIssue(payload, "error", "duplicate_step_id", $"Duplicate stepId '{stepId}'.", stepId, i);
                }

                ValidateStep(payload, step, stepId, i);
            }

            payload.status = payload.error_count > 0 ? "invalid" : "valid";
            return payload;
        }

        public static bool HasActiveRun()
        {
            return File.Exists(XUUnityLightMcpFileIpcPaths.ActiveScenarioRunPath);
        }

        public static XUUnityLightMcpScenarioRunPayload QueueRun(XUUnityLightMcpScenarioDefinition scenario)
        {
            XUUnityLightMcpFileIpcPaths.EnsureDirectories();

            var runId = Guid.NewGuid().ToString("N");
            var scenarioName = NormalizeScenarioName(scenario?.name);
            var nowUtc = DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ");
            var resultPath = BuildResultPath(runId, scenarioName);

            var state = new XUUnityLightMcpScenarioRunState
            {
                runId = runId,
                scenario = scenario,
                status = "queued",
                startedAtUtc = nowUtc,
                updatedAtUtc = nowUtc,
                completedAtUtc = "",
                resultPath = resultPath,
                currentStepIndex = 0,
                waitingUntilUtc = "",
                steps = new List<XUUnityLightMcpScenarioStepResult>(),
            };

            foreach (var step in scenario.steps)
            {
                state.steps.Add(new XUUnityLightMcpScenarioStepResult
                {
                    stepId = step.stepId,
                    kind = step.kind,
                    status = "pending",
                });
            }

            SaveState(state);
            PersistResult(state);
            return BuildPayload(state);
        }

        public static void Tick()
        {
            if (!TryLoadState(out var state))
            {
                return;
            }

            if (state == null || state.status == "passed" || state.status == "failed")
            {
                return;
            }

            try
            {
                if (state.currentStepIndex >= state.scenario.steps.Count)
                {
                    CompleteRun(state, CountSteps(state.steps, "failed") > 0 ? "failed" : "passed");
                    return;
                }

                state.status = "running";
                state.updatedAtUtc = DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ");

                var step = state.scenario.steps[state.currentStepIndex];
                var stepResult = state.steps[state.currentStepIndex];
                var shouldAdvance = ProcessStep(state, step, stepResult);

                PersistResult(state);
                SaveState(state);

                if (!shouldAdvance)
                {
                    return;
                }

                if (stepResult.status == "failed" && state.scenario.stopOnFirstFailure)
                {
                    CompleteRun(state, "failed");
                    return;
                }

                state.currentStepIndex++;
                state.waitingUntilUtc = "";

                if (state.currentStepIndex >= state.scenario.steps.Count)
                {
                    CompleteRun(state, CountSteps(state.steps, "failed") > 0 ? "failed" : "passed");
                    return;
                }

                PersistResult(state);
                SaveState(state);
            }
            catch (Exception ex)
            {
                state.status = "failed";
                state.completedAtUtc = DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ");
                state.updatedAtUtc = state.completedAtUtc;
                PersistResult(state, "scenario_runner_failed", ex.Message);
                SaveState(state);
                SafeDeleteActiveState();
                UnityEngine.Debug.LogException(ex);
            }
        }

        public static bool TryReadResult(string runId, string scenarioName, out XUUnityLightMcpScenarioRunPayload payload, out string errorCode, out string errorMessage)
        {
            XUUnityLightMcpFileIpcPaths.EnsureDirectories();
            payload = null;
            errorCode = "";
            errorMessage = "";

            if (!string.IsNullOrWhiteSpace(runId))
            {
                var path = FindResultPathByRunId(runId.Trim());
                if (path == null)
                {
                    errorCode = "scenario_run_not_found";
                    errorMessage = $"No scenario result found for runId '{runId}'.";
                    return false;
                }

                return TryReadPayload(path, out payload, out errorCode, out errorMessage);
            }

            if (!string.IsNullOrWhiteSpace(scenarioName))
            {
                var path = FindLatestResultPathByScenarioName(NormalizeScenarioName(scenarioName));
                if (path == null)
                {
                    errorCode = "scenario_result_not_found";
                    errorMessage = $"No scenario result found for scenario '{scenarioName}'.";
                    return false;
                }

                return TryReadPayload(path, out payload, out errorCode, out errorMessage);
            }

            var latest = FindLatestResultPath();
            if (latest == null)
            {
                errorCode = "scenario_result_not_found";
                errorMessage = "No scenario result files found.";
                return false;
            }

            return TryReadPayload(latest, out payload, out errorCode, out errorMessage);
        }

        static bool ProcessStep(XUUnityLightMcpScenarioRunState state, XUUnityLightMcpScenarioStepDefinition step, XUUnityLightMcpScenarioStepResult stepResult)
        {
            var kind = (step.kind ?? "").Trim().ToLowerInvariant();

            switch (kind)
            {
                case "wait":
                    return ProcessWaitStep(state, step, stepResult);
                case "wait_for_playmode_state":
                    return ProcessWaitForPlayModeStateStep(state, step, stepResult);
                case "assert_playmode_state":
                    return ProcessAssertPlayModeStateStep(step, stepResult);
                case "status":
                    return ProcessNestedOperationStep("unity.status", "{}", stepResult);
                case "health_probe":
                    return ProcessNestedOperationStep("unity.health.probe", "{}", stepResult);
                case "scene_snapshot":
                    return ProcessNestedOperationStep("unity.scene.snapshot", "{}", stepResult);
                case "project_refresh":
                    return ProcessProjectRefreshStep(state, step, stepResult);
                case "console_tail":
                    return ProcessConsoleTailStep(step, stepResult);
                case "playmode_set":
                    return ProcessPlayModeSetStep(step, stepResult);
                case "game_view_screenshot":
                    return ProcessGameViewScreenshotStep(step, stepResult);
                case "compile_player_scripts":
                    return ProcessCompilePlayerScriptsStep(step, stepResult);
                case "tests_run_editmode":
                    return ProcessEditModeTestsStep(state, step, stepResult);
                case "game_view_configure":
                    return ProcessGameViewConfigureStep(step, stepResult);
                case "project_defined_hook":
                    return ProcessProjectDefinedHookStep(step, stepResult);
                default:
                    stepResult.status = "failed";
                    stepResult.error_code = "unsupported_scenario_step";
                    stepResult.error_message = $"Unsupported scenario step kind '{kind}'.";
                    return true;
            }
        }

        static bool ProcessWaitStep(XUUnityLightMcpScenarioRunState state, XUUnityLightMcpScenarioStepDefinition step, XUUnityLightMcpScenarioStepResult stepResult)
        {
            if (stepResult.status == "pending")
            {
                var waitUntil = DateTime.UtcNow.AddSeconds(Math.Max(0.0d, step.durationSeconds));
                state.waitingUntilUtc = waitUntil.ToString("yyyy-MM-ddTHH:mm:ssZ");
                stepResult.status = "running";
                stepResult.outcome = "waiting";
                return false;
            }

            if (!TryParseUtc(state.waitingUntilUtc, out var deadlineUtc))
            {
                stepResult.status = "failed";
                stepResult.error_code = "invalid_wait_deadline";
                stepResult.error_message = "Scenario wait step lost its deadline state.";
                return true;
            }

            if (DateTime.UtcNow < deadlineUtc)
            {
                return false;
            }

            stepResult.status = "passed";
            stepResult.outcome = "wait_completed";
            stepResult.duration_seconds = Math.Round(Math.Max(0.0d, step.durationSeconds), 6);
            return true;
        }

        static bool ProcessWaitForPlayModeStateStep(XUUnityLightMcpScenarioRunState state, XUUnityLightMcpScenarioStepDefinition step, XUUnityLightMcpScenarioStepResult stepResult)
        {
            if (stepResult.status == "pending")
            {
                var timeoutSeconds = step.timeoutSeconds > 0.0d ? step.timeoutSeconds : 10.0d;
                var waitUntil = DateTime.UtcNow.AddSeconds(timeoutSeconds);
                state.waitingUntilUtc = waitUntil.ToString("yyyy-MM-ddTHH:mm:ssZ");
                stepResult.status = "running";
                stepResult.outcome = "waiting_for_playmode_state";
            }

            var currentState = XUUnityLightMcpPlayModeStateOperation.ResolvePlayModeState();
            if (string.Equals(currentState, step.expectedPlaymodeState, StringComparison.OrdinalIgnoreCase))
            {
                stepResult.status = "passed";
                stepResult.outcome = $"playmode_state_reached:{currentState}";
                return true;
            }

            if (!TryParseUtc(state.waitingUntilUtc, out var deadlineUtc))
            {
                stepResult.status = "failed";
                stepResult.error_code = "invalid_wait_deadline";
                stepResult.error_message = "Scenario play mode wait step lost its deadline state.";
                return true;
            }

            if (DateTime.UtcNow < deadlineUtc)
            {
                return false;
            }

            stepResult.status = "failed";
            stepResult.error_code = "playmode_state_timeout";
            stepResult.error_message =
                $"Timed out waiting for play mode state '{step.expectedPlaymodeState}'. Last observed state: '{currentState}'.";
            return true;
        }

        static bool ProcessAssertPlayModeStateStep(XUUnityLightMcpScenarioStepDefinition step, XUUnityLightMcpScenarioStepResult stepResult)
        {
            var currentState = XUUnityLightMcpPlayModeStateOperation.ResolvePlayModeState();
            if (string.Equals(currentState, step.expectedPlaymodeState, StringComparison.OrdinalIgnoreCase))
            {
                stepResult.status = "passed";
                stepResult.outcome = $"asserted_playmode_state:{currentState}";
            }
            else
            {
                stepResult.status = "failed";
                stepResult.error_code = "unexpected_playmode_state";
                stepResult.error_message =
                    $"Expected play mode state '{step.expectedPlaymodeState}', but observed '{currentState}'.";
            }

            return true;
        }

        static bool ProcessConsoleTailStep(XUUnityLightMcpScenarioStepDefinition step, XUUnityLightMcpScenarioStepResult stepResult)
        {
            var args = new XUUnityLightMcpConsoleTailArgs
            {
                limit = step.limit > 0 ? step.limit : 50,
                includeTypes = step.includeTypes,
            };

            return ProcessNestedOperationStep("unity.console.tail", JsonUtility.ToJson(args), stepResult);
        }

        static bool ProcessPlayModeSetStep(XUUnityLightMcpScenarioStepDefinition step, XUUnityLightMcpScenarioStepResult stepResult)
        {
            var args = new XUUnityLightMcpPlayModeSetArgs
            {
                action = step.action,
            };

            return ProcessNestedOperationStep("unity.playmode.set", JsonUtility.ToJson(args), stepResult);
        }

        static bool ProcessGameViewScreenshotStep(XUUnityLightMcpScenarioStepDefinition step, XUUnityLightMcpScenarioStepResult stepResult)
        {
            var args = new XUUnityLightMcpGameViewScreenshotArgs
            {
                fileName = step.fileName,
                includeImage = step.includeImage,
                maxResolution = step.maxResolution > 0 ? step.maxResolution : 640,
            };

            return ProcessNestedOperationStep("unity.game_view.screenshot", JsonUtility.ToJson(args), stepResult);
        }

        static bool ProcessCompilePlayerScriptsStep(XUUnityLightMcpScenarioStepDefinition step, XUUnityLightMcpScenarioStepResult stepResult)
        {
            var args = new XUUnityLightMcpCompilePlayerScriptsArgs
            {
                name = step.name,
                target = step.target,
                optionFlags = step.optionFlags,
                extraDefines = step.extraDefines,
            };

            var stopwatch = Stopwatch.StartNew();
            var response = ExecuteNestedOperation("unity.compile.player_scripts", JsonUtility.ToJson(args));
            stopwatch.Stop();

            stepResult.duration_seconds = Math.Round(stopwatch.Elapsed.TotalSeconds, 6);
            if (response == null)
            {
                stepResult.status = "failed";
                stepResult.error_code = "null_nested_response";
                stepResult.error_message = "compile_player_scripts returned no response.";
                return true;
            }

            stepResult.payload_json = response.payload_json ?? "";
            if (response.status != "ok")
            {
                stepResult.status = "failed";
                stepResult.error_code = response.error?.code ?? "compile_player_scripts_failed";
                stepResult.error_message = response.error?.message ?? "compile_player_scripts failed.";
                return true;
            }

            var payload = string.IsNullOrWhiteSpace(response.payload_json)
                ? null
                : JsonUtility.FromJson<XUUnityLightMcpCompilePlayerScriptsPayload>(response.payload_json);

            if (payload?.result != null && string.Equals(payload.result.status, "passed", StringComparison.OrdinalIgnoreCase))
            {
                stepResult.status = "passed";
                stepResult.outcome = "compile_passed";
                return true;
            }

            stepResult.status = "failed";
            stepResult.error_code = "compile_failed";
            stepResult.error_message = FormatCompileFailureMessage(payload);
            return true;
        }

        static bool ProcessEditModeTestsStep(XUUnityLightMcpScenarioRunState state, XUUnityLightMcpScenarioStepDefinition step, XUUnityLightMcpScenarioStepResult stepResult)
        {
            if (stepResult.status == "pending")
            {
                var request = BuildNestedRequest("unity.tests.run_editmode", "{}", GetTimeoutMs(step, 600.0d));
                var response = ExecuteNestedOperation(request.operation, request.args_json, request);
                if (response != null)
                {
                    ApplyNestedResponse(stepResult, response, request.created_at_utc);
                    return true;
                }

                state.pendingNestedRequestId = request.request_id;
                state.pendingNestedOperation = request.operation;
                state.pendingNestedStartedAtUtc = request.created_at_utc;
                state.waitingUntilUtc = DateTime.UtcNow.AddSeconds(GetTimeoutSeconds(step, 600.0d)).ToString("yyyy-MM-ddTHH:mm:ssZ");
                stepResult.status = "running";
                stepResult.outcome = "tests_running";
                return false;
            }

            if (stepResult.status != "running")
            {
                return true;
            }

            if (TryTakePendingNestedResponse(state.pendingNestedRequestId, out var pendingResponse))
            {
                ApplyTestsResponse(stepResult, pendingResponse, state.pendingNestedStartedAtUtc);
                ClearPendingNestedOperation(state);
                return true;
            }

            if (!TryParseUtc(state.waitingUntilUtc, out var deadlineUtc))
            {
                stepResult.status = "failed";
                stepResult.error_code = "invalid_wait_deadline";
                stepResult.error_message = "Scenario test step lost its deadline state.";
                ClearPendingNestedOperation(state);
                return true;
            }

            if (DateTime.UtcNow < deadlineUtc)
            {
                return false;
            }

            stepResult.status = "failed";
            stepResult.error_code = "tests_timeout";
            stepResult.error_message = "Timed out waiting for EditMode test completion.";
            ClearPendingNestedOperation(state);
            return true;
        }

        static bool ProcessGameViewConfigureStep(XUUnityLightMcpScenarioStepDefinition step, XUUnityLightMcpScenarioStepResult stepResult)
        {
            var args = new XUUnityLightMcpGameViewConfigureArgs
            {
                width = step.width,
                height = step.height,
                group = step.group,
                label = step.label,
                allowCreateCustomSize = step.allowCreateCustomSize,
            };

            return ProcessNestedOperationStep("unity.game_view.configure", JsonUtility.ToJson(args), stepResult);
        }

        static bool ProcessProjectDefinedHookStep(XUUnityLightMcpScenarioStepDefinition step, XUUnityLightMcpScenarioStepResult stepResult)
        {
            if (!TryCreateScenarioHook(step.hookName, out var hook, out var errorCode, out var errorMessage))
            {
                stepResult.status = "failed";
                stepResult.error_code = errorCode;
                stepResult.error_message = errorMessage;
                return true;
            }

            var stopwatch = Stopwatch.StartNew();
            var result = hook.Execute(step.hookPayloadJson ?? "");
            stopwatch.Stop();

            stepResult.duration_seconds = Math.Round(stopwatch.Elapsed.TotalSeconds, 6);
            if (result == null || result.success)
            {
                stepResult.status = "passed";
                stepResult.outcome = result?.outcome ?? "hook_succeeded";
                stepResult.payload_json = result?.payload_json ?? "";
                return true;
            }

            stepResult.status = "failed";
            stepResult.error_code = string.IsNullOrWhiteSpace(result.error_code) ? "project_hook_failed" : result.error_code;
            stepResult.error_message = string.IsNullOrWhiteSpace(result.error_message)
                ? $"Scenario hook '{step.hookName}' reported failure."
                : result.error_message;
            stepResult.outcome = result.outcome ?? "";
            stepResult.payload_json = result.payload_json ?? "";
            return true;
        }

        static bool ProcessNestedOperationStep(string operationName, string argsJson, XUUnityLightMcpScenarioStepResult stepResult)
        {
            var stopwatch = Stopwatch.StartNew();
            var response = ExecuteNestedOperation(operationName, argsJson);
            stopwatch.Stop();

            stepResult.duration_seconds = Math.Round(stopwatch.Elapsed.TotalSeconds, 6);

            if (response == null)
            {
                stepResult.status = "failed";
                stepResult.error_code = "null_nested_response";
                stepResult.error_message = $"Nested operation '{operationName}' returned no response.";
                return true;
            }

            if (response.status == "ok")
            {
                stepResult.status = "passed";
                stepResult.outcome = "operation_succeeded";
                stepResult.payload_json = response.payload_json ?? "";
                return true;
            }

            stepResult.status = "failed";
            stepResult.error_code = response.error?.code ?? "nested_operation_failed";
            stepResult.error_message = response.error?.message ?? $"Nested operation '{operationName}' failed.";
            return true;
        }

        static XUUnityLightMcpResponse ExecuteNestedOperation(string operationName, string argsJson)
        {
            return ExecuteNestedOperation(operationName, argsJson, null);
        }

        static XUUnityLightMcpResponse ExecuteNestedOperation(string operationName, string argsJson, XUUnityLightMcpRequest requestOverride)
        {
            if (!XUUnityLightMcpOperationRegistry.TryGet(operationName, out var operation))
            {
                throw new InvalidOperationException($"Scenario runner could not resolve nested operation '{operationName}'.");
            }

            var nestedRequest = requestOverride ?? BuildNestedRequest(operationName, argsJson, 30000);

            return operation.Execute(nestedRequest);
        }

        static XUUnityLightMcpRequest BuildNestedRequest(string operationName, string argsJson, int timeoutMs)
        {
            return new XUUnityLightMcpRequest
            {
                request_id = $"scenario_{Guid.NewGuid():N}",
                operation = operationName,
                project_root = XUUnityLightMcpFileIpcPaths.ProjectRootPath,
                created_at_utc = DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ"),
                timeout_ms = timeoutMs,
                args_json = string.IsNullOrWhiteSpace(argsJson) ? "{}" : argsJson,
            };
        }

        static bool TryTakePendingNestedResponse(string requestId, out XUUnityLightMcpResponse response)
        {
            response = null;
            if (string.IsNullOrWhiteSpace(requestId))
            {
                return false;
            }

            var path = Path.Combine(XUUnityLightMcpFileIpcPaths.OutboxDirectory, $"{requestId}.json");
            if (!File.Exists(path))
            {
                return false;
            }

            try
            {
                response = JsonUtility.FromJson<XUUnityLightMcpResponse>(File.ReadAllText(path));
            }
            finally
            {
                File.Delete(path);
            }

            return response != null;
        }

        static void ApplyNestedResponse(XUUnityLightMcpScenarioStepResult stepResult, XUUnityLightMcpResponse response, string startedAtUtc)
        {
            stepResult.duration_seconds = CalculateDurationSeconds(startedAtUtc, response?.completed_at_utc ?? "");

            if (response == null)
            {
                stepResult.status = "failed";
                stepResult.error_code = "null_nested_response";
                stepResult.error_message = "Nested operation returned no response.";
                return;
            }

            if (response.status == "ok")
            {
                stepResult.status = "passed";
                stepResult.outcome = "operation_succeeded";
                stepResult.payload_json = response.payload_json ?? "";
                return;
            }

            stepResult.status = "failed";
            stepResult.error_code = response.error?.code ?? "nested_operation_failed";
            stepResult.error_message = response.error?.message ?? "Nested operation failed.";
        }

        static void ApplyTestsResponse(XUUnityLightMcpScenarioStepResult stepResult, XUUnityLightMcpResponse response, string startedAtUtc)
        {
            ApplyNestedResponse(stepResult, response, startedAtUtc);
            if (response == null || response.status != "ok")
            {
                return;
            }

            var payload = string.IsNullOrWhiteSpace(response.payload_json)
                ? null
                : JsonUtility.FromJson<XUUnityLightMcpTestsPayload>(response.payload_json);

            stepResult.payload_json = response.payload_json ?? "";
            if (payload != null && string.Equals(payload.status, "passed", StringComparison.OrdinalIgnoreCase))
            {
                stepResult.status = "passed";
                stepResult.outcome = "tests_passed";
                return;
            }

            stepResult.status = "failed";
            stepResult.error_code = payload != null && string.Equals(payload.status, "no_tests", StringComparison.OrdinalIgnoreCase)
                ? "no_tests"
                : "tests_failed";
            stepResult.error_message = FormatTestsFailureMessage(payload);
        }

        static void ClearPendingNestedOperation(XUUnityLightMcpScenarioRunState state)
        {
            state.pendingNestedRequestId = "";
            state.pendingNestedOperation = "";
            state.pendingNestedStartedAtUtc = "";
            state.pendingNestedStableTickCount = 0;
        }

        static int GetTimeoutMs(XUUnityLightMcpScenarioStepDefinition step, double defaultSeconds)
        {
            return (int)Math.Round(GetTimeoutSeconds(step, defaultSeconds) * 1000.0d);
        }

        static double GetTimeoutSeconds(XUUnityLightMcpScenarioStepDefinition step, double defaultSeconds)
        {
            return step.timeoutSeconds > 0.0d ? step.timeoutSeconds : defaultSeconds;
        }

        static bool TryCreateScenarioHook(string hookName, out IXUUnityLightMcpScenarioHook hook, out string errorCode, out string errorMessage)
        {
            hook = null;
            errorCode = "";
            errorMessage = "";

            if (string.IsNullOrWhiteSpace(hookName))
            {
                errorCode = "missing_hook_name";
                errorMessage = "project_defined_hook step requires hookName.";
                return false;
            }

            var matches = new List<Type>();
            foreach (var type in TypeCache.GetTypesDerivedFrom<IXUUnityLightMcpScenarioHook>())
            {
                if (type == null || type.IsAbstract || type.IsInterface)
                {
                    continue;
                }

                if (Activator.CreateInstance(type) is not IXUUnityLightMcpScenarioHook candidate)
                {
                    continue;
                }

                if (string.Equals(candidate.HookName, hookName, StringComparison.OrdinalIgnoreCase))
                {
                    matches.Add(type);
                    hook ??= candidate;
                }
            }

            if (matches.Count == 1 && hook != null)
            {
                return true;
            }

            if (matches.Count > 1)
            {
                hook = null;
                errorCode = "duplicate_hook_name";
                errorMessage = $"Multiple scenario hooks registered as '{hookName}'.";
                return false;
            }

            errorCode = "hook_not_found";
            errorMessage = $"No scenario hook registered as '{hookName}'.";
            return false;
        }

        static string FormatCompileFailureMessage(XUUnityLightMcpCompilePlayerScriptsPayload payload)
        {
            if (payload?.result == null)
            {
                return "compile_player_scripts payload did not describe a passed compile.";
            }

            if (payload.result.errors != null && payload.result.errors.Count > 0)
            {
                var first = payload.result.errors[0];
                return string.IsNullOrWhiteSpace(first.message)
                    ? $"Compile failed for target '{payload.result.target}'."
                    : first.message;
            }

            return $"Compile status was '{payload.result.status}' for target '{payload.result.target}'.";
        }

        static string FormatTestsFailureMessage(XUUnityLightMcpTestsPayload payload)
        {
            if (payload == null)
            {
                return "EditMode test payload did not report a passed result.";
            }

            if (payload.failures != null && payload.failures.Count > 0)
            {
                var first = payload.failures[0];
                return string.IsNullOrWhiteSpace(first.message)
                    ? $"EditMode tests failed in '{first.name}'."
                    : first.message;
            }

            return payload.status == "no_tests"
                ? "EditMode test run completed with no discovered tests."
                : $"EditMode tests finished with status '{payload.status}'.";
        }

        static void CompleteRun(XUUnityLightMcpScenarioRunState state, string finalStatus)
        {
            state.status = finalStatus;
            state.completedAtUtc = DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ");
            state.updatedAtUtc = state.completedAtUtc;
            PersistResult(state);
            SaveState(state);
            SafeDeleteActiveState();
        }

        static void PersistResult(XUUnityLightMcpScenarioRunState state, string errorCode = "", string errorMessage = "")
        {
            var payload = BuildPayload(state);
            if (!string.IsNullOrWhiteSpace(errorCode))
            {
                payload.status = "failed";
                if (payload.steps.Count == 0)
                {
                    payload.steps.Add(new XUUnityLightMcpScenarioStepResult
                    {
                        stepId = "runner",
                        kind = "runner",
                        status = "failed",
                        error_code = errorCode,
                        error_message = errorMessage,
                    });
                }
            }

            File.WriteAllText(state.resultPath, JsonUtility.ToJson(payload, true));
        }

        static XUUnityLightMcpScenarioRunPayload BuildPayload(XUUnityLightMcpScenarioRunState state)
        {
            var isTerminal = string.Equals(state.status, "passed", StringComparison.Ordinal)
                || string.Equals(state.status, "failed", StringComparison.Ordinal);

            var payload = new XUUnityLightMcpScenarioRunPayload
            {
                project_root = XUUnityLightMcpFileIpcPaths.ProjectRootPath,
                run_id = state.runId,
                scenario_name = NormalizeScenarioName(state.scenario?.name),
                status = state.status,
                terminal = isTerminal,
                succeeded = string.Equals(state.status, "passed", StringComparison.Ordinal),
                terminal_status = isTerminal ? state.status : "",
                started_at_utc = state.startedAtUtc,
                updated_at_utc = state.updatedAtUtc,
                completed_at_utc = state.completedAtUtc,
                result_path = state.resultPath,
                total_steps = state.steps.Count,
                current_step_index = state.currentStepIndex,
                steps = new List<XUUnityLightMcpScenarioStepResult>(state.steps),
                passed_steps = CountSteps(state.steps, "passed"),
                failed_steps = CountSteps(state.steps, "failed"),
                skipped_steps = CountSteps(state.steps, "skipped"),
                duration_seconds = CalculateDurationSeconds(state.startedAtUtc, string.IsNullOrWhiteSpace(state.completedAtUtc) ? state.updatedAtUtc : state.completedAtUtc),
            };

            return payload;
        }

        static double CalculateDurationSeconds(string startedAtUtc, string completedAtUtc)
        {
            if (!TryParseUtc(startedAtUtc, out var started))
            {
                return 0.0d;
            }

            if (!TryParseUtc(completedAtUtc, out var completed))
            {
                completed = DateTime.UtcNow;
            }

            return Math.Round(Math.Max(0.0d, (completed - started).TotalSeconds), 6);
        }

        static int CountSteps(List<XUUnityLightMcpScenarioStepResult> steps, string status)
        {
            var count = 0;
            foreach (var step in steps)
            {
                if (string.Equals(step.status, status, StringComparison.Ordinal))
                {
                    count++;
                }
            }
            return count;
        }

        static bool TryLoadState(out XUUnityLightMcpScenarioRunState state)
        {
            state = null;
            var path = XUUnityLightMcpFileIpcPaths.ActiveScenarioRunPath;
            if (!File.Exists(path))
            {
                return false;
            }

            var json = File.ReadAllText(path);
            state = JsonUtility.FromJson<XUUnityLightMcpScenarioRunState>(json);
            return state != null;
        }

        static void SaveState(XUUnityLightMcpScenarioRunState state)
        {
            File.WriteAllText(XUUnityLightMcpFileIpcPaths.ActiveScenarioRunPath, JsonUtility.ToJson(state, true));
        }

        static void SafeDeleteActiveState()
        {
            try
            {
                if (File.Exists(XUUnityLightMcpFileIpcPaths.ActiveScenarioRunPath))
                {
                    File.Delete(XUUnityLightMcpFileIpcPaths.ActiveScenarioRunPath);
                }
            }
            catch
            {
            }
        }

        static bool ProcessProjectRefreshStep(XUUnityLightMcpScenarioStepDefinition step, XUUnityLightMcpScenarioStepResult stepResult)
        {
            return ProcessProjectRefreshStep(null, step, stepResult);
        }

        static bool ProcessProjectRefreshStep(XUUnityLightMcpScenarioRunState state, XUUnityLightMcpScenarioStepDefinition step, XUUnityLightMcpScenarioStepResult stepResult)
        {
            if (state == null)
            {
                return ProcessNestedOperationStep("unity.project.refresh", BuildProjectRefreshArgsJson(step), stepResult);
            }

            if (stepResult.status == "pending")
            {
                var request = BuildNestedRequest("unity.project.refresh", BuildProjectRefreshArgsJson(step), GetTimeoutMs(step, 45.0d));
                var response = ExecuteNestedOperation(request.operation, request.args_json, request);
                if (response == null)
                {
                    stepResult.status = "failed";
                    stepResult.error_code = "null_nested_response";
                    stepResult.error_message = "project_refresh returned no response.";
                    return true;
                }

                if (response.status != "ok")
                {
                    ApplyNestedResponse(stepResult, response, request.created_at_utc);
                    return true;
                }

                state.pendingNestedRequestId = request.request_id;
                state.pendingNestedOperation = request.operation;
                state.pendingNestedStartedAtUtc = request.created_at_utc;
                state.pendingNestedStableTickCount = 0;
                state.waitingUntilUtc = DateTime.UtcNow.AddSeconds(GetTimeoutSeconds(step, 45.0d)).ToString("yyyy-MM-ddTHH:mm:ssZ");
                stepResult.status = "running";
                stepResult.outcome = "refresh_waiting_for_settle";
                stepResult.payload_json = response.payload_json ?? "";
                return false;
            }

            if (stepResult.status != "running")
            {
                return true;
            }

            if (!TryParseUtc(state.waitingUntilUtc, out var deadlineUtc))
            {
                stepResult.status = "failed";
                stepResult.error_code = "invalid_wait_deadline";
                stepResult.error_message = "Scenario refresh step lost its deadline state.";
                ClearPendingNestedOperation(state);
                return true;
            }

            if (IsEditorIdleForRefreshSettle())
            {
                state.pendingNestedStableTickCount++;
                if (state.pendingNestedStableTickCount >= 2)
                {
                    FinalizeProjectRefreshStep(stepResult);
                    ClearPendingNestedOperation(state);
                    return true;
                }
            }
            else
            {
                state.pendingNestedStableTickCount = 0;
            }

            if (DateTime.UtcNow < deadlineUtc)
            {
                return false;
            }

            stepResult.status = "failed";
            stepResult.error_code = "project_refresh_timeout";
            stepResult.error_message = "Timed out waiting for project refresh to settle.";
            ClearPendingNestedOperation(state);
            return true;
        }

        static string BuildProjectRefreshArgsJson(XUUnityLightMcpScenarioStepDefinition step)
        {
            var args = new XUUnityLightMcpProjectRefreshArgs
            {
                forceAssetRefresh = step.forceAssetRefresh,
                resolvePackages = step.resolvePackages,
                rerunHealthProbe = step.rerunHealthProbe,
            };

            return JsonUtility.ToJson(args);
        }

        static bool IsEditorIdleForRefreshSettle()
        {
            return !EditorApplication.isCompiling
                && !EditorApplication.isUpdating
                && (EditorApplication.isPlaying || !EditorApplication.isPlayingOrWillChangePlaymode);
        }

        static void FinalizeProjectRefreshStep(XUUnityLightMcpScenarioStepResult stepResult)
        {
            var payload = string.IsNullOrWhiteSpace(stepResult.payload_json)
                ? new XUUnityLightMcpProjectRefreshPayload()
                : JsonUtility.FromJson<XUUnityLightMcpProjectRefreshPayload>(stepResult.payload_json) ?? new XUUnityLightMcpProjectRefreshPayload();

            payload.requested_outcome = string.IsNullOrWhiteSpace(payload.requested_outcome)
                ? payload.outcome ?? ""
                : payload.requested_outcome;
            payload.outcome = payload.package_resolve_requested
                ? "refresh_and_resolve_completed"
                : "refresh_completed";
            payload.settled_at_utc = DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ");
            payload.completion_basis = "scenario_runner_waited_for_editor_idle";
            payload.editor_is_compiling_after_settle = EditorApplication.isCompiling;
            payload.editor_is_updating_after_settle = EditorApplication.isUpdating;
            payload.playmode_state_after_settle = XUUnityLightMcpPlayModeStateOperation.ResolvePlayModeState();

            stepResult.status = "passed";
            stepResult.outcome = payload.outcome;
            stepResult.payload_json = JsonUtility.ToJson(payload);
        }

        static string BuildResultPath(string runId, string scenarioName)
        {
            var timestamp = DateTime.UtcNow.ToString("yyyyMMddTHHmmssZ");
            var safeName = SanitizeFileName(scenarioName);
            return Path.Combine(XUUnityLightMcpFileIpcPaths.ScenarioResultsDirectory, $"{timestamp}_{runId}_{safeName}.json");
        }

        static FileInfo FindResultPathByRunId(string runId)
        {
            var directory = new DirectoryInfo(XUUnityLightMcpFileIpcPaths.ScenarioResultsDirectory);
            foreach (var file in directory.GetFiles("*.json"))
            {
                if (file.Name.Contains(runId, StringComparison.OrdinalIgnoreCase))
                {
                    return file;
                }
            }

            return null;
        }

        static FileInfo FindLatestResultPathByScenarioName(string scenarioName)
        {
            FileInfo latest = null;
            XUUnityLightMcpScenarioRunPayload latestPayload = null;

            var directory = new DirectoryInfo(XUUnityLightMcpFileIpcPaths.ScenarioResultsDirectory);
            foreach (var file in directory.GetFiles("*.json"))
            {
                if (!TryReadPayload(file, out var payload, out _, out _))
                {
                    continue;
                }

                if (!string.Equals(payload.scenario_name, scenarioName, StringComparison.OrdinalIgnoreCase))
                {
                    continue;
                }

                if (latest == null || file.LastWriteTimeUtc > latest.LastWriteTimeUtc)
                {
                    latest = file;
                    latestPayload = payload;
                }
            }

            return latestPayload != null ? latest : null;
        }

        static FileInfo FindLatestResultPath()
        {
            FileInfo latest = null;
            var directory = new DirectoryInfo(XUUnityLightMcpFileIpcPaths.ScenarioResultsDirectory);
            foreach (var file in directory.GetFiles("*.json"))
            {
                if (latest == null || file.LastWriteTimeUtc > latest.LastWriteTimeUtc)
                {
                    latest = file;
                }
            }

            return latest;
        }

        static bool TryReadPayload(FileInfo file, out XUUnityLightMcpScenarioRunPayload payload, out string errorCode, out string errorMessage)
        {
            payload = null;
            errorCode = "";
            errorMessage = "";

            try
            {
                var json = File.ReadAllText(file.FullName);
                payload = JsonUtility.FromJson<XUUnityLightMcpScenarioRunPayload>(json);
                if (payload == null)
                {
                    errorCode = "invalid_scenario_result";
                    errorMessage = $"Scenario result file is empty or invalid: {file.FullName}";
                    return false;
                }

                return true;
            }
            catch (Exception ex)
            {
                errorCode = "scenario_result_read_failed";
                errorMessage = ex.Message;
                return false;
            }
        }

        static void ValidateStep(XUUnityLightMcpScenarioValidatePayload payload, XUUnityLightMcpScenarioStepDefinition step, string stepId, int index)
        {
            var kind = (step.kind ?? "").Trim().ToLowerInvariant();
            if (string.IsNullOrWhiteSpace(kind))
            {
                AddIssue(payload, "error", "missing_kind", "Scenario step kind is required.", stepId, index);
                return;
            }

            switch (kind)
            {
                case "status":
                case "health_probe":
                case "scene_snapshot":
                case "project_refresh":
                    break;
                case "console_tail":
                    if (step.limit <= 0)
                    {
                        AddIssue(payload, "error", "invalid_limit", "console_tail step requires limit > 0.", stepId, index);
                    }
                    break;
                case "playmode_set":
                    if (!IsPlayModeAction(step.action))
                    {
                        AddIssue(payload, "error", "invalid_action",
                            "playmode_set step requires action: enter, exit, pause, or resume.", stepId, index);
                    }
                    break;
                case "wait":
                    if (step.durationSeconds < 0.0d)
                    {
                        AddIssue(payload, "error", "invalid_duration", "wait step requires durationSeconds >= 0.", stepId, index);
                    }
                    break;
                case "wait_for_playmode_state":
                    if (!IsPlayModeState(step.expectedPlaymodeState))
                    {
                        AddIssue(payload, "error", "invalid_expected_playmode_state",
                            "wait_for_playmode_state requires expectedPlaymodeState: edit, playing, paused, or transitioning.",
                            stepId, index);
                    }
                    if (step.timeoutSeconds <= 0.0d)
                    {
                        AddIssue(payload, "error", "invalid_timeout", "wait_for_playmode_state requires timeoutSeconds > 0.", stepId, index);
                    }
                    break;
                case "assert_playmode_state":
                    if (!IsPlayModeState(step.expectedPlaymodeState))
                    {
                        AddIssue(payload, "error", "invalid_expected_playmode_state",
                            "assert_playmode_state requires expectedPlaymodeState: edit, playing, paused, or transitioning.",
                            stepId, index);
                    }
                    break;
                case "game_view_screenshot":
                    if (step.maxResolution <= 0)
                    {
                        AddIssue(payload, "error", "invalid_max_resolution",
                            "game_view_screenshot requires maxResolution > 0.", stepId, index);
                    }
                    break;
                case "compile_player_scripts":
                    if (string.IsNullOrWhiteSpace(step.target))
                    {
                        AddIssue(payload, "error", "missing_target", "compile_player_scripts requires target.", stepId, index);
                    }
                    break;
                case "tests_run_editmode":
                    break;
                case "game_view_configure":
                    if (step.width <= 0 || step.height <= 0)
                    {
                        AddIssue(payload, "error", "invalid_resolution",
                            "game_view_configure requires width > 0 and height > 0.", stepId, index);
                    }
                    break;
                case "project_defined_hook":
                    if (string.IsNullOrWhiteSpace(step.hookName))
                    {
                        AddIssue(payload, "error", "missing_hook_name", "project_defined_hook requires hookName.", stepId, index);
                        break;
                    }

                    if (!TryCreateScenarioHook(step.hookName, out _, out var hookErrorCode, out var hookErrorMessage))
                    {
                        AddIssue(payload, "error", hookErrorCode, hookErrorMessage, stepId, index);
                    }
                    break;
                default:
                    AddIssue(payload, "error", "unsupported_kind", $"Unsupported scenario step kind '{kind}'.", stepId, index);
                    break;
            }
        }

        static void AddIssue(XUUnityLightMcpScenarioValidatePayload payload, string severity, string code, string message, string stepId, int stepIndex)
        {
            payload.issues.Add(new XUUnityLightMcpScenarioIssue
            {
                severity = severity,
                code = code,
                message = message,
                stepId = stepId,
                stepIndex = stepIndex,
            });

            if (severity == "warning")
            {
                payload.warning_count++;
            }
            else
            {
                payload.error_count++;
            }
        }

        static string NormalizeScenarioName(string name)
        {
            var trimmed = (name ?? "").Trim();
            return string.IsNullOrWhiteSpace(trimmed) ? "unnamed_scenario" : trimmed;
        }

        static string NormalizeStepId(XUUnityLightMcpScenarioStepDefinition step, int index)
        {
            var trimmed = (step.stepId ?? "").Trim();
            if (string.IsNullOrWhiteSpace(trimmed))
            {
                trimmed = $"step_{index + 1}";
                step.stepId = trimmed;
            }

            return trimmed;
        }

        static string SanitizeFileName(string name)
        {
            var safe = NormalizeScenarioName(name);
            foreach (var invalid in Path.GetInvalidFileNameChars())
            {
                safe = safe.Replace(invalid, '_');
            }
            return safe.Replace(' ', '_');
        }

        static bool IsPlayModeAction(string action)
        {
            var normalized = (action ?? "").Trim().ToLowerInvariant();
            return normalized == "enter" || normalized == "exit" || normalized == "pause" || normalized == "resume";
        }

        static bool IsPlayModeState(string state)
        {
            var normalized = (state ?? "").Trim().ToLowerInvariant();
            return normalized == "edit" || normalized == "playing" || normalized == "paused" || normalized == "transitioning";
        }

        static bool TryParseUtc(string value, out DateTime utc)
        {
            return DateTime.TryParse(
                value,
                null,
                System.Globalization.DateTimeStyles.AdjustToUniversal | System.Globalization.DateTimeStyles.AssumeUniversal,
                out utc);
        }

    }
}
