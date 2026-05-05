using System;
using UnityEditor;
using UnityEngine;
using XUUnity.LightMcp.Editor.Core;
using XUUnity.LightMcp.Editor.Helpers;

namespace XUUnity.LightMcp.Editor.Operations
{
    internal sealed class XUUnityLightMcpPlayModeSetOperation : IXUUnityLightMcpOperation
    {
        public string OperationName => "unity.playmode.set";

        public XUUnityLightMcpResponse Execute(XUUnityLightMcpRequest request)
        {
            var args = string.IsNullOrWhiteSpace(request.args_json)
                ? new XUUnityLightMcpPlayModeSetArgs()
                : JsonUtility.FromJson<XUUnityLightMcpPlayModeSetArgs>(request.args_json) ?? new XUUnityLightMcpPlayModeSetArgs();

            var action = (args.action ?? "").Trim().ToLowerInvariant();
            if (string.IsNullOrWhiteSpace(action))
            {
                return XUUnityLightMcpResponseWriter.Error(request.request_id, "missing_action",
                    "unity.playmode.set requires action: enter, exit, pause, or resume.");
            }

            string outcome;
            try
            {
                outcome = action switch
                {
                    "enter" => EnterPlayMode(),
                    "exit" => ExitPlayMode(),
                    "pause" => PausePlayMode(),
                    "resume" => ResumePlayMode(),
                    _ => throw new InvalidOperationException(
                        $"Unsupported play mode action '{action}'. Valid actions: enter, exit, pause, resume.")
                };
            }
            catch (Exception ex)
            {
                return XUUnityLightMcpResponseWriter.Error(request.request_id, "playmode_action_failed", ex.Message);
            }

            var state = XUUnityLightMcpPlayModeStateOperation.BuildPayload();
            var payload = new XUUnityLightMcpPlayModeSetPayload
            {
                project_root = XUUnityLightMcpFileIpcPaths.ProjectRootPath,
                requested_action = action,
                outcome = outcome,
                is_playing = state.is_playing,
                is_paused = state.is_paused,
                is_playing_or_will_change_playmode = state.is_playing_or_will_change_playmode,
                playmode_state = state.playmode_state
            };

            return XUUnityLightMcpResponseWriter.Success(
                request.request_id,
                OperationName,
                JsonUtility.ToJson(payload)
            );
        }

        static string EnterPlayMode()
        {
            if (EditorApplication.isPlaying)
            {
                return "already_playing";
            }

            if (EditorApplication.isPlayingOrWillChangePlaymode)
            {
                return "already_transitioning";
            }

            try
            {
                XUUnityLightMcpGameViewUtility.EnsureGameView();
            }
            catch
            {
            }

            EditorApplication.isPlaying = true;
            return "enter_requested";
        }

        static string ExitPlayMode()
        {
            if (!EditorApplication.isPlaying && !EditorApplication.isPlayingOrWillChangePlaymode)
            {
                return "already_in_edit_mode";
            }

            EditorApplication.isPlaying = false;
            return "exit_requested";
        }

        static string PausePlayMode()
        {
            if (!EditorApplication.isPlaying)
            {
                throw new InvalidOperationException("Cannot pause because Unity is not currently in play mode.");
            }

            if (EditorApplication.isPaused)
            {
                return "already_paused";
            }

            EditorApplication.isPaused = true;
            return "pause_requested";
        }

        static string ResumePlayMode()
        {
            if (!EditorApplication.isPlaying)
            {
                throw new InvalidOperationException("Cannot resume because Unity is not currently in play mode.");
            }

            if (!EditorApplication.isPaused)
            {
                return "already_running";
            }

            EditorApplication.isPaused = false;
            return "resume_requested";
        }
    }
}
