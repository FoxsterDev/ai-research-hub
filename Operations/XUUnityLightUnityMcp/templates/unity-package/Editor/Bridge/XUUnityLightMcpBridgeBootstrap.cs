using System;
using UnityEditor;
using XUUnity.LightMcp.Editor.Helpers;

namespace XUUnity.LightMcp.Editor.Bridge
{
    [InitializeOnLoad]
    internal static class XUUnityLightMcpBridgeBootstrap
    {
        static double _heartbeatIntervalSeconds = 2.0d;
        static double _pumpIntervalSeconds = 0.5d;
        static double _lastHeartbeatAt;
        static double _lastPumpAt;

        static XUUnityLightMcpBridgeBootstrap()
        {
            if (!XUUnityLightMcpBridgeActivation.IsEnabled())
            {
                return;
            }

            var config = XUUnityLightMcpBridgeActivation.LoadConfig();
            _heartbeatIntervalSeconds = config.heartbeat_interval_ms / 1000.0d;
            _pumpIntervalSeconds = config.pump_interval_ms / 1000.0d;

            XUUnityLightMcpConsoleBuffer.EnsureStarted();
            if (config.auto_probe_on_startup)
            {
                try
                {
                    XUUnityLightMcpHealthProbe.EnsureCurrentReport();
                }
                catch
                {
                }
            }
            EditorApplication.update -= OnUpdate;
            EditorApplication.update += OnUpdate;
        }

        static void OnUpdate()
        {
            var now = EditorApplication.timeSinceStartup;

            if (now - _lastHeartbeatAt >= _heartbeatIntervalSeconds)
            {
                try
                {
                    XUUnityLightMcpBridgeStateWriter.WriteHeartbeat();
                }
                catch (Exception ex)
                {
                    XUUnityLightMcpBridgeStateWriter.WriteHeartbeat(ex.Message);
                }
                _lastHeartbeatAt = now;
            }

            if (now - _lastPumpAt >= _pumpIntervalSeconds)
            {
                XUUnityLightMcpBridgeRequestPump.PumpOnce();
                XUUnityLightMcpScenarioRunner.Tick();
                _lastPumpAt = now;
            }
        }
    }
}
