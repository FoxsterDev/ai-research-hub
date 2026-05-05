using System;
using UnityEngine;
using XUUnity.LightMcp.Editor.Core;
using XUUnity.LightMcp.Editor.Helpers;

namespace XUUnity.LightMcp.Editor.Operations
{
    internal sealed class XUUnityLightMcpGameViewScreenshotOperation : IXUUnityLightMcpOperation
    {
        public string OperationName => "unity.game_view.screenshot";

        public XUUnityLightMcpResponse Execute(XUUnityLightMcpRequest request)
        {
            var args = string.IsNullOrWhiteSpace(request.args_json)
                ? new XUUnityLightMcpGameViewScreenshotArgs()
                : JsonUtility.FromJson<XUUnityLightMcpGameViewScreenshotArgs>(request.args_json) ?? new XUUnityLightMcpGameViewScreenshotArgs();

            try
            {
                var payload = XUUnityLightMcpGameViewUtility.CaptureScreenshot(
                    request.request_id,
                    args.fileName,
                    args.includeImage,
                    args.maxResolution);

                return XUUnityLightMcpResponseWriter.Success(
                    request.request_id,
                    OperationName,
                    JsonUtility.ToJson(payload)
                );
            }
            catch (Exception ex)
            {
                return XUUnityLightMcpResponseWriter.Error(request.request_id, "game_view_screenshot_failed", ex.Message);
            }
        }
    }
}
