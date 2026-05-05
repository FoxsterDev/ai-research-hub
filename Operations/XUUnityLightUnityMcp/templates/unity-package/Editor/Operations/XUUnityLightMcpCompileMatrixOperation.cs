using System;
using System.Collections.Generic;
using System.Diagnostics;
using UnityEditor;
using UnityEngine;
using XUUnity.LightMcp.Editor.Bridge;
using XUUnity.LightMcp.Editor.Core;
using XUUnity.LightMcp.Editor.Helpers;

namespace XUUnity.LightMcp.Editor.Operations
{
    internal sealed class XUUnityLightMcpCompileMatrixOperation : IXUUnityLightMcpOperation
    {
        public string OperationName => "unity.compile.matrix";

        public XUUnityLightMcpResponse Execute(XUUnityLightMcpRequest request)
        {
            var args = string.IsNullOrWhiteSpace(request.args_json)
                ? new XUUnityLightMcpCompileMatrixArgs()
                : JsonUtility.FromJson<XUUnityLightMcpCompileMatrixArgs>(request.args_json) ?? new XUUnityLightMcpCompileMatrixArgs();

            if (args.configurations == null || args.configurations.Count == 0)
            {
                return XUUnityLightMcpResponseWriter.Error(
                    request.request_id,
                    "missing_configurations",
                    "unity.compile.matrix requires at least one configuration.");
            }

            try
            {
                var stopwatch = Stopwatch.StartNew();
                var results = new List<XUUnityLightMcpCompileConfigPayload>(args.configurations.Count);
                var passed = 0;
                var failed = 0;
                var skipped = 0;

                foreach (var configuration in args.configurations)
                {
                    var result = XUUnityLightMcpCompileUtility.Compile(configuration);
                    results.Add(result);

                    switch (result.status)
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

                    if (args.stopOnFirstFailure && result.status != "passed")
                    {
                        break;
                    }
                }

                stopwatch.Stop();
                var requestCompletedAtUtc = DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ");
                XUUnityLightMcpBridgeRuntimeState.BeginCompileSettleTracking(request.request_id, OperationName);

                var payload = new XUUnityLightMcpCompileMatrixPayload
                {
                    project_root = XUUnityLightMcpFileIpcPaths.ProjectRootPath,
                    status = failed > 0 ? "failed" : "passed",
                    request_completed_at_utc = requestCompletedAtUtc,
                    editor_is_compiling_after_request = EditorApplication.isCompiling,
                    editor_is_updating_after_request = EditorApplication.isUpdating,
                    settle_request_id = request.request_id,
                    settle_phase = XUUnityLightMcpBridgeRuntimeState.CompileSettlePhase,
                    stop_on_first_failure = args.stopOnFirstFailure,
                    total = results.Count,
                    passed = passed,
                    failed = failed,
                    skipped = skipped,
                    duration_seconds = Math.Round(stopwatch.Elapsed.TotalSeconds, 6),
                    results = results
                };

                return XUUnityLightMcpResponseWriter.Success(
                    request.request_id,
                    OperationName,
                    JsonUtility.ToJson(payload)
                );
            }
            catch (Exception ex)
            {
                return XUUnityLightMcpResponseWriter.Error(request.request_id, "compile_matrix_failed", ex.Message);
            }
        }
    }
}
