using System;
using System.Diagnostics;
using System.IO;
using UnityEditor;
using UnityEngine;
using XUUnity.LightMcp.Editor.Core;
using XUUnity.LightMcp.Editor.Helpers;

namespace XUUnity.LightMcp.Editor.Bridge
{
    internal static class XUUnityLightMcpBridgeStateWriter
    {
        public static void WriteHeartbeat(string lastError = "")
        {
            XUUnityLightMcpFileIpcPaths.EnsureDirectories();
            var report = XUUnityLightMcpHealthProbe.EnsureCurrentReport();

            var state = new XUUnityLightMcpBridgeState
            {
                project_root = XUUnityLightMcpFileIpcPaths.ProjectRootPath,
                editor_pid = Process.GetCurrentProcess().Id,
                unity_version = Application.unityVersion,
                is_compiling = EditorApplication.isCompiling,
                is_playing = EditorApplication.isPlaying,
                heartbeat_utc = DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ"),
                last_error = lastError ?? "",
                health_status = report.status,
                supported_operation_count = report.supported_operations?.Count ?? 0,
                disabled_operation_count = report.disabled_operations?.Count ?? 0,
                capabilities_report_path = XUUnityLightMcpFileIpcPaths.CapabilitiesReportPath
            };

            File.WriteAllText(XUUnityLightMcpFileIpcPaths.BridgeStatePath, JsonUtility.ToJson(state, true));
        }
    }
}
