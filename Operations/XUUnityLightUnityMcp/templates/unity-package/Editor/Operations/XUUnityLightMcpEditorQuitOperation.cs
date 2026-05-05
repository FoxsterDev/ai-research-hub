using System;
using UnityEditor;
using UnityEngine;
using XUUnity.LightMcp.Editor.Core;

namespace XUUnity.LightMcp.Editor.Operations
{
    internal sealed class XUUnityLightMcpEditorQuitOperation : IXUUnityLightMcpOperation
    {
        public string OperationName => "unity.editor.quit";

        public XUUnityLightMcpResponse Execute(XUUnityLightMcpRequest request)
        {
            var payload = new XUUnityLightMcpEditorQuitPayload
            {
                project_root = XUUnityLightMcpFileIpcPaths.ProjectRootPath,
                outcome = "quit_requested",
                requested_at_utc = DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ"),
            };

            EditorApplication.delayCall += RequestQuit;

            return XUUnityLightMcpResponseWriter.Success(
                request.request_id,
                OperationName,
                JsonUtility.ToJson(payload)
            );
        }

        static void RequestQuit()
        {
            try
            {
                EditorApplication.Exit(0);
            }
            catch (Exception ex)
            {
                Debug.LogException(ex);
            }
        }
    }
}
