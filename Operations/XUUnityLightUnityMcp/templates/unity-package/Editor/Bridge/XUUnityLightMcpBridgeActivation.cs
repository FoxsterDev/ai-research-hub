using System;
using System.IO;
using UnityEngine;
using XUUnity.LightMcp.Editor.Core;

namespace XUUnity.LightMcp.Editor.Bridge
{
    internal static class XUUnityLightMcpBridgeActivation
    {
        static XUUnityLightMcpBridgeConfig _cachedConfig;
        static bool _loaded;

        public static bool IsEnabled()
        {
            return LoadConfig().enabled;
        }

        public static XUUnityLightMcpBridgeConfig LoadConfig()
        {
            if (_loaded)
            {
                return _cachedConfig;
            }

            _loaded = true;
            _cachedConfig = new XUUnityLightMcpBridgeConfig();

            try
            {
                var path = XUUnityLightMcpFileIpcPaths.BridgeConfigPath;
                if (!File.Exists(path))
                {
                    return _cachedConfig;
                }

                var json = File.ReadAllText(path);
                var config = JsonUtility.FromJson<XUUnityLightMcpBridgeConfig>(json);
                if (config != null)
                {
                    config.heartbeat_interval_ms = Math.Max(1000, config.heartbeat_interval_ms);
                    config.pump_interval_ms = Math.Max(250, config.pump_interval_ms);
                    config.transport = string.IsNullOrWhiteSpace(config.transport) ? "file_ipc" : config.transport.Trim().ToLowerInvariant();
                    config.loopback_host = string.IsNullOrWhiteSpace(config.loopback_host) ? "127.0.0.1" : config.loopback_host.Trim();
                    config.loopback_port = Math.Max(0, config.loopback_port);
                    _cachedConfig = config;
                }
            }
            catch
            {
                _cachedConfig = new XUUnityLightMcpBridgeConfig();
            }

            return _cachedConfig;
        }
    }
}
