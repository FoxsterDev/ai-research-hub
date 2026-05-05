using UnityEngine;
using XUUnity.LightMcp.Editor.Core;
using XUUnity.LightMcp.Editor.Helpers;

namespace XUUnity.LightMcp.Editor.Operations
{
    internal sealed class XUUnityLightMcpCapabilitiesGetOperation : IXUUnityLightMcpOperation
    {
        public string OperationName => "unity.capabilities.get";

        public XUUnityLightMcpResponse Execute(XUUnityLightMcpRequest request)
        {
            var payload = new XUUnityLightMcpCapabilitiesPayload
            {
                project_root = XUUnityLightMcpFileIpcPaths.ProjectRootPath,
                report = XUUnityLightMcpHealthProbe.EnsureCurrentReport()
            };

            return XUUnityLightMcpResponseWriter.Success(
                request.request_id,
                OperationName,
                JsonUtility.ToJson(payload)
            );
        }
    }
}
