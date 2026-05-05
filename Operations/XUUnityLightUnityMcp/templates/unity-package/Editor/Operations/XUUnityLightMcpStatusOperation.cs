using System;
using UnityEditor;
using UnityEngine;
using XUUnity.LightMcp.Editor.Core;
using XUUnity.LightMcp.Editor.Helpers;

namespace XUUnity.LightMcp.Editor.Operations
{
    internal sealed class XUUnityLightMcpStatusOperation : IXUUnityLightMcpOperation
    {
        public string OperationName => "unity.status";

        public XUUnityLightMcpResponse Execute(XUUnityLightMcpRequest request)
        {
            var report = XUUnityLightMcpHealthProbe.EnsureCurrentReport();
            var payload = new XUUnityLightMcpStatusPayload
            {
                project_root = XUUnityLightMcpFileIpcPaths.ProjectRootPath,
                is_compiling = EditorApplication.isCompiling,
                is_playing = EditorApplication.isPlaying,
                is_paused = EditorApplication.isPaused,
                is_playing_or_will_change_playmode = EditorApplication.isPlayingOrWillChangePlaymode,
                playmode_state = XUUnityLightMcpPlayModeStateOperation.ResolvePlayModeState(),
                health_status = report.status,
                supported_operations = report.supported_operations ?? new System.Collections.Generic.List<string>(),
                disabled_operations = report.disabled_operations ?? new System.Collections.Generic.List<string>()
            };

            return new XUUnityLightMcpResponse
            {
                request_id = request.request_id,
                status = "ok",
                completed_at_utc = DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ"),
                payload_type = "unity.status",
                payload_json = JsonUtility.ToJson(payload),
                error = null
            };
        }
    }
}
