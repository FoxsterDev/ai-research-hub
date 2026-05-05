using System;
using UnityEngine;
using XUUnity.LightMcp.Editor.Core;
using XUUnity.LightMcp.Editor.Helpers;

namespace XUUnity.LightMcp.Editor.Operations
{
    internal sealed class XUUnityLightMcpGameViewConfigureOperation : IXUUnityLightMcpOperation
    {
        public string OperationName => "unity.game_view.configure";

        public XUUnityLightMcpResponse Execute(XUUnityLightMcpRequest request)
        {
            var args = string.IsNullOrWhiteSpace(request.args_json)
                ? new XUUnityLightMcpGameViewConfigureArgs()
                : JsonUtility.FromJson<XUUnityLightMcpGameViewConfigureArgs>(request.args_json) ?? new XUUnityLightMcpGameViewConfigureArgs();

            if (args.width < 1 || args.height < 1)
            {
                return XUUnityLightMcpResponseWriter.Error(
                    request.request_id,
                    "invalid_resolution",
                    "unity.game_view.configure requires width and height greater than zero.");
            }

            try
            {
                var gameView = XUUnityLightMcpGameViewUtility.SetFixedResolution(
                    args.width,
                    args.height,
                    args.group,
                    args.label,
                    args.allowCreateCustomSize);

                var payload = new XUUnityLightMcpGameViewConfigurePayload
                {
                    project_root = XUUnityLightMcpFileIpcPaths.ProjectRootPath,
                    outcome = "resolution_applied",
                    game_view = gameView
                };

                return XUUnityLightMcpResponseWriter.Success(
                    request.request_id,
                    OperationName,
                    JsonUtility.ToJson(payload)
                );
            }
            catch (Exception ex)
            {
                return XUUnityLightMcpResponseWriter.Error(request.request_id, "game_view_configure_failed", ex.Message);
            }
        }
    }
}
