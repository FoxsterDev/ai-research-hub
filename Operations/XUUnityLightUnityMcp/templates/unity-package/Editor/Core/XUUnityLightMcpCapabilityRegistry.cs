using System;
using System.Collections.Generic;
using System.Linq;

namespace XUUnity.LightMcp.Editor.Core
{
    internal static class XUUnityLightMcpCapabilityRegistry
    {
        public const string CoreCapability = "core";
        public const string EditModeTestsCapability = "editmode_tests";
        public const string CompileCapability = "compile_player_scripts";
        public const string PlayModeCapability = "playmode_control";
        public const string GameViewCapability = "game_view_reflection";

        static readonly HashSet<string> UngatedOperations = new(StringComparer.Ordinal)
        {
            "unity.status",
            "unity.capabilities.get",
            "unity.health.probe",
            "unity.project.refresh",
            "unity.editor.quit"
        };

        static readonly Dictionary<string, string> OperationCapabilities = new(StringComparer.Ordinal)
        {
            { "unity.status", CoreCapability },
            { "unity.project.refresh", CoreCapability },
            { "unity.editor.quit", CoreCapability },
            { "unity.console.tail", CoreCapability },
            { "unity.scene.snapshot", CoreCapability },
            { "unity.scenario.validate", CoreCapability },
            { "unity.scenario.run", CoreCapability },
            { "unity.scenario.result", CoreCapability },
            { "unity.tests.run_editmode", EditModeTestsCapability },
            { "unity.compile.player_scripts", CompileCapability },
            { "unity.compile.matrix", CompileCapability },
            { "unity.playmode.state", PlayModeCapability },
            { "unity.playmode.set", PlayModeCapability },
            { "unity.game_view.configure", GameViewCapability },
            { "unity.game_view.screenshot", GameViewCapability }
        };

        public static bool IsUngated(string operationName)
        {
            return UngatedOperations.Contains(operationName ?? "");
        }

        public static bool TryGetRequiredCapability(string operationName, out string capabilityId)
        {
            return OperationCapabilities.TryGetValue(operationName ?? "", out capabilityId);
        }

        public static List<string> AllKnownOperations()
        {
            return OperationCapabilities.Keys.OrderBy(value => value, StringComparer.Ordinal).ToList();
        }
    }
}
