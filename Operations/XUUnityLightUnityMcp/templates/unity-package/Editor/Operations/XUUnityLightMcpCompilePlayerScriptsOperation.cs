using System;
using UnityEngine;
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
                var payload = new XUUnityLightMcpCompilePlayerScriptsPayload
                {
                    project_root = XUUnityLightMcpFileIpcPaths.ProjectRootPath,
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
