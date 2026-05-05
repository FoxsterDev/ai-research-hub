using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using UnityEditor;
using UnityEditor.Build.Player;
using UnityEditor.TestTools.TestRunner.Api;
using UnityEngine;
using XUUnity.LightMcp.Editor.Core;

namespace XUUnity.LightMcp.Editor.Helpers
{
    internal static class XUUnityLightMcpHealthProbe
    {
        const int ProbeVersion = 1;
        static readonly BindingFlags StaticBindings = BindingFlags.NonPublic | BindingFlags.Public | BindingFlags.Static;
        static XUUnityLightMcpCapabilitiesReport _cachedReport;

        public static XUUnityLightMcpCapabilitiesReport EnsureCurrentReport()
        {
            if (_cachedReport != null && IsCurrent(_cachedReport))
            {
                return _cachedReport;
            }

            var loaded = LoadReportFromDisk();
            if (loaded != null && IsCurrent(loaded))
            {
                _cachedReport = loaded;
                return loaded;
            }

            return RunProbeAndPersist();
        }

        public static XUUnityLightMcpCapabilitiesReport RunProbeAndPersist()
        {
            XUUnityLightMcpFileIpcPaths.EnsureDirectories();

            var capabilities = new List<XUUnityLightMcpCapabilityRecord>
            {
                BuildCoreCapability(),
                BuildEditModeTestsCapability(),
                BuildCompileCapability(),
                BuildPlayModeCapability(),
                BuildGameViewCapability()
            };

            var supportedOperations = new List<string>();
            var disabledOperations = new List<string>();

            foreach (var capability in capabilities)
            {
                if (capability.operations == null)
                {
                    continue;
                }

                if (capability.supported)
                {
                    supportedOperations.AddRange(capability.operations);
                }
                else
                {
                    disabledOperations.AddRange(capability.operations);
                }
            }

            supportedOperations.Sort(StringComparer.Ordinal);
            disabledOperations.Sort(StringComparer.Ordinal);

            var report = new XUUnityLightMcpCapabilitiesReport
            {
                probe_version = ProbeVersion,
                project_root = XUUnityLightMcpFileIpcPaths.ProjectRootPath,
                unity_version = Application.unityVersion,
                checked_at_utc = DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ"),
                status = disabledOperations.Count == 0 ? "healthy" : "degraded",
                supported_operations = supportedOperations,
                disabled_operations = disabledOperations,
                capabilities = capabilities
            };

            File.WriteAllText(XUUnityLightMcpFileIpcPaths.CapabilitiesReportPath, JsonUtility.ToJson(report, true));
            _cachedReport = report;
            return report;
        }

        public static bool IsOperationSupported(string operationName, out string reason)
        {
            reason = "";

            if (XUUnityLightMcpCapabilityRegistry.IsUngated(operationName))
            {
                return true;
            }

            if (!XUUnityLightMcpCapabilityRegistry.TryGetRequiredCapability(operationName, out var capabilityId))
            {
                return true;
            }

            var report = EnsureCurrentReport();
            foreach (var capability in report.capabilities)
            {
                if (!string.Equals(capability.capability_id, capabilityId, StringComparison.Ordinal))
                {
                    continue;
                }

                if (capability.supported)
                {
                    return true;
                }

                reason = string.IsNullOrWhiteSpace(capability.reason)
                    ? $"Capability '{capabilityId}' is not supported in Unity {Application.unityVersion}."
                    : capability.reason;
                return false;
            }

            reason = $"Capability '{capabilityId}' is not registered.";
            return false;
        }

        static XUUnityLightMcpCapabilitiesReport LoadReportFromDisk()
        {
            try
            {
                if (!File.Exists(XUUnityLightMcpFileIpcPaths.CapabilitiesReportPath))
                {
                    return null;
                }

                var json = File.ReadAllText(XUUnityLightMcpFileIpcPaths.CapabilitiesReportPath);
                return JsonUtility.FromJson<XUUnityLightMcpCapabilitiesReport>(json);
            }
            catch
            {
                return null;
            }
        }

        static bool IsCurrent(XUUnityLightMcpCapabilitiesReport report)
        {
            return report != null &&
                   report.probe_version == ProbeVersion &&
                   string.Equals(report.unity_version, Application.unityVersion, StringComparison.Ordinal) &&
                   string.Equals(report.project_root, XUUnityLightMcpFileIpcPaths.ProjectRootPath, StringComparison.Ordinal);
        }

        static XUUnityLightMcpCapabilityRecord BuildCoreCapability()
        {
            return new XUUnityLightMcpCapabilityRecord
            {
                capability_id = XUUnityLightMcpCapabilityRegistry.CoreCapability,
                adapter_id = "unity_editor_builtin_v1",
                supported = true,
                reason = "",
                operations = new List<string>
                {
                    "unity.status",
                    "unity.console.tail",
                    "unity.scene.snapshot"
                }
            };
        }

        static XUUnityLightMcpCapabilityRecord BuildEditModeTestsCapability()
        {
            var supported = typeof(TestRunnerApi) != null;
            return new XUUnityLightMcpCapabilityRecord
            {
                capability_id = XUUnityLightMcpCapabilityRegistry.EditModeTestsCapability,
                adapter_id = "unity_test_framework_v1",
                supported = supported,
                reason = supported
                    ? ""
                    : "Unity Test Framework API is unavailable; EditMode test operations are disabled.",
                operations = new List<string> { "unity.tests.run_editmode" }
            };
        }

        static XUUnityLightMcpCapabilityRecord BuildCompileCapability()
        {
            var method = typeof(PlayerBuildInterface).GetMethod(
                "CompilePlayerScripts",
                StaticBindings,
                null,
                new[] { typeof(ScriptCompilationSettings), typeof(string) },
                null);

            var supported = method != null;
            return new XUUnityLightMcpCapabilityRecord
            {
                capability_id = XUUnityLightMcpCapabilityRegistry.CompileCapability,
                adapter_id = "compile_player_scripts_v1",
                supported = supported,
                reason = supported
                    ? ""
                    : "Unity PlayerBuildInterface.CompilePlayerScripts API is unavailable; compile validation operations are disabled.",
                operations = new List<string>
                {
                    "unity.compile.player_scripts",
                    "unity.compile.matrix"
                }
            };
        }

        static XUUnityLightMcpCapabilityRecord BuildPlayModeCapability()
        {
            return new XUUnityLightMcpCapabilityRecord
            {
                capability_id = XUUnityLightMcpCapabilityRegistry.PlayModeCapability,
                adapter_id = "editor_playmode_builtin_v1",
                supported = true,
                reason = "",
                operations = new List<string>
                {
                    "unity.playmode.state",
                    "unity.playmode.set"
                }
            };
        }

        static XUUnityLightMcpCapabilityRecord BuildGameViewCapability()
        {
            var probe = XUUnityLightMcpGameViewUtility.ProbeReflectionSurface();
            return new XUUnityLightMcpCapabilityRecord
            {
                capability_id = XUUnityLightMcpCapabilityRegistry.GameViewCapability,
                adapter_id = probe.adapter_id,
                supported = probe.supported,
                reason = probe.reason,
                operations = new List<string>
                {
                    "unity.game_view.configure",
                    "unity.game_view.screenshot"
                }
            };
        }
    }
}
