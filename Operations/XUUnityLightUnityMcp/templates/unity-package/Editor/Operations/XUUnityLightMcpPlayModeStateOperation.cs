using UnityEditor;
using UnityEngine;
using XUUnity.LightMcp.Editor.Core;

namespace XUUnity.LightMcp.Editor.Operations
{
    internal sealed class XUUnityLightMcpPlayModeStateOperation : IXUUnityLightMcpOperation
    {
        public string OperationName => "unity.playmode.state";

        public XUUnityLightMcpResponse Execute(XUUnityLightMcpRequest request)
        {
            var payload = BuildPayload();
            return XUUnityLightMcpResponseWriter.Success(
                request.request_id,
                OperationName,
                JsonUtility.ToJson(payload)
            );
        }

        internal static XUUnityLightMcpPlayModeStatePayload BuildPayload()
        {
            return new XUUnityLightMcpPlayModeStatePayload
            {
                project_root = XUUnityLightMcpFileIpcPaths.ProjectRootPath,
                is_playing = EditorApplication.isPlaying,
                is_paused = EditorApplication.isPaused,
                is_playing_or_will_change_playmode = EditorApplication.isPlayingOrWillChangePlaymode,
                playmode_state = ResolvePlayModeState()
            };
        }

        internal static string ResolvePlayModeState()
        {
            if (EditorApplication.isPlaying)
            {
                return EditorApplication.isPaused ? "paused" : "playing";
            }

            return EditorApplication.isPlayingOrWillChangePlaymode ? "transitioning" : "edit";
        }
    }
}
