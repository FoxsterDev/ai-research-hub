using UnityEngine;
using UnityEngine.SceneManagement;
using XUUnity.LightMcp.Editor.Core;

namespace XUUnity.LightMcp.Editor.Operations
{
    internal sealed class XUUnityLightMcpSceneSnapshotOperation : IXUUnityLightMcpOperation
    {
        public string OperationName => "unity.scene.snapshot";

        public XUUnityLightMcpResponse Execute(XUUnityLightMcpRequest request)
        {
            var scene = SceneManager.GetActiveScene();
            var roots = scene.IsValid() ? scene.GetRootGameObjects() : new GameObject[0];

            var payload = new XUUnityLightMcpSceneSnapshotPayload
            {
                project_root = XUUnityLightMcpFileIpcPaths.ProjectRootPath,
                active_scene = new XUUnityLightMcpSceneData
                {
                    name = scene.name ?? "",
                    path = scene.path ?? "",
                    is_dirty = scene.isDirty,
                    root_count = roots.Length
                }
            };

            foreach (var root in roots)
            {
                payload.root_objects.Add(new XUUnityLightMcpRootObject
                {
                    name = root != null ? root.name ?? "" : ""
                });
            }

            return XUUnityLightMcpResponseWriter.Success(
                request.request_id,
                OperationName,
                JsonUtility.ToJson(payload)
            );
        }
    }
}
