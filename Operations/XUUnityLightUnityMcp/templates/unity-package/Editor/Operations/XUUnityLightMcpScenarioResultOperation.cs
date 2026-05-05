using System;
using UnityEngine;
using XUUnity.LightMcp.Editor.Core;
using XUUnity.LightMcp.Editor.Helpers;

namespace XUUnity.LightMcp.Editor.Operations
{
    internal sealed class XUUnityLightMcpScenarioResultOperation : IXUUnityLightMcpOperation
    {
        public string OperationName => "unity.scenario.result";

        public XUUnityLightMcpResponse Execute(XUUnityLightMcpRequest request)
        {
            var args = string.IsNullOrWhiteSpace(request.args_json)
                ? new XUUnityLightMcpScenarioResultArgs()
                : JsonUtility.FromJson<XUUnityLightMcpScenarioResultArgs>(request.args_json) ?? new XUUnityLightMcpScenarioResultArgs();

            try
            {
                if (!XUUnityLightMcpScenarioRunner.TryReadResult(args.runId, args.scenarioName, out var payload, out var errorCode, out var errorMessage))
                {
                    return XUUnityLightMcpResponseWriter.Error(request.request_id, errorCode, errorMessage);
                }

                return XUUnityLightMcpResponseWriter.Success(
                    request.request_id,
                    OperationName,
                    JsonUtility.ToJson(payload)
                );
            }
            catch (Exception ex)
            {
                return XUUnityLightMcpResponseWriter.Error(request.request_id, "scenario_result_failed", ex.Message);
            }
        }
    }
}
