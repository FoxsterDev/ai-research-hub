using UnityEditor;
using UnityEngine;
using XUUnity.LightMcp.Editor.Bridge;
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
                playmode_transition_pending = XUUnityLightMcpBridgeRuntimeState.PlayModeTransitionPending,
                playmode_transition_request_id = XUUnityLightMcpBridgeRuntimeState.PlayModeTransitionRequestId,
                playmode_transition_action = XUUnityLightMcpBridgeRuntimeState.PlayModeTransitionAction,
                playmode_transition_target_state = XUUnityLightMcpBridgeRuntimeState.PlayModeTransitionTargetState,
                playmode_transition_started_utc = XUUnityLightMcpBridgeRuntimeState.PlayModeTransitionStartedUtc,
                playmode_transition_completed_utc = XUUnityLightMcpBridgeRuntimeState.PlayModeTransitionCompletedUtc,
                playmode_transition_phase = XUUnityLightMcpBridgeRuntimeState.PlayModeTransitionPhase,
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
