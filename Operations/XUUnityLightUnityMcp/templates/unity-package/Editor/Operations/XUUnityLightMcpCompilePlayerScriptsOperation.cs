using System;
using UnityEditor;
using UnityEngine;
using XUUnity.LightMcp.Editor.Bridge;
using XUUnity.LightMcp.Editor.Core;
using XUUnity.LightMcp.Editor.Helpers;

namespace XUUnity.LightMcp.Editor.Operations
{
    internal sealed class XUUnityLightMcpCompilePlayerScriptsOperation : IXUUnityLightMcpOperation
    {
        public string OperationName => "unity.compile.player_scripts";

        public XUUnityLightMcpResponse Execute(XUUnityLightMcpRequest request)
        {
            var args = string.IsNullOrWhiteSpace(request.args_json)
                ? new XUUnityLightMcpCompilePlayerScriptsArgs()
                : JsonUtility.FromJson<XUUnityLightMcpCompilePlayerScriptsArgs>(request.args_json) ?? new XUUnityLightMcpCompilePlayerScriptsArgs();

            try
            {
                var result = XUUnityLightMcpCompileUtility.Compile(args);
                var requestCompletedAtUtc = DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ");
                XUUnityLightMcpBridgeRuntimeState.BeginCompileSettleTracking(request.request_id, OperationName);
                var payload = new XUUnityLightMcpCompilePlayerScriptsPayload
                {
                    project_root = XUUnityLightMcpFileIpcPaths.ProjectRootPath,
                    request_completed_at_utc = requestCompletedAtUtc,
                    editor_is_compiling_after_request = EditorApplication.isCompiling,
                    editor_is_updating_after_request = EditorApplication.isUpdating,
                    settle_request_id = request.request_id,
                    settle_phase = XUUnityLightMcpBridgeRuntimeState.CompileSettlePhase,
                    result = result
                };

                return XUUnityLightMcpResponseWriter.Success(
                    request.request_id,
                    OperationName,
                    JsonUtility.ToJson(payload)
                );
            }
            catch (Exception ex)
            {
                return XUUnityLightMcpResponseWriter.Error(request.request_id, "compile_player_scripts_failed", ex.Message);
            }
        }
    }
}
