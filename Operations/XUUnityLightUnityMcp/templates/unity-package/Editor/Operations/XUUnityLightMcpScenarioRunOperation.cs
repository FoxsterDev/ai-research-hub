using System;
using UnityEngine;
using XUUnity.LightMcp.Editor.Core;
using XUUnity.LightMcp.Editor.Helpers;

namespace XUUnity.LightMcp.Editor.Operations
{
    internal sealed class XUUnityLightMcpScenarioRunOperation : IXUUnityLightMcpOperation
    {
        public string OperationName => "unity.scenario.run";

        public XUUnityLightMcpResponse Execute(XUUnityLightMcpRequest request)
        {
            var args = string.IsNullOrWhiteSpace(request.args_json)
                ? new XUUnityLightMcpScenarioRunArgs()
                : JsonUtility.FromJson<XUUnityLightMcpScenarioRunArgs>(request.args_json) ?? new XUUnityLightMcpScenarioRunArgs();

            try
            {
                var validation = XUUnityLightMcpScenarioRunner.Validate(args.scenario);
                if (validation.status != "valid")
                {
                    return XUUnityLightMcpResponseWriter.Error(
                        request.request_id,
                        "scenario_invalid",
                        "Scenario validation failed. Run unity.scenario.validate for detailed issues.");
                }

                if (XUUnityLightMcpScenarioRunner.HasActiveRun())
                {
                    return XUUnityLightMcpResponseWriter.Error(
                        request.request_id,
                        "scenario_already_running",
                        "Another Unity scenario is already running. Read it with unity.scenario.result before starting a new one.");
                }

                var payload = XUUnityLightMcpScenarioRunner.QueueRun(args.scenario);
                return XUUnityLightMcpResponseWriter.Success(
                    request.request_id,
                    OperationName,
                    JsonUtility.ToJson(payload)
                );
            }
            catch (Exception ex)
            {
                return XUUnityLightMcpResponseWriter.Error(request.request_id, "scenario_run_failed", ex.Message);
            }
        }
    }
}
