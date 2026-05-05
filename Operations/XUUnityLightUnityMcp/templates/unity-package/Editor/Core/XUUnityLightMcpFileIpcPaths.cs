using System.IO;
using UnityEngine;

namespace XUUnity.LightMcp.Editor.Core
{
    internal static class XUUnityLightMcpFileIpcPaths
    {
        public static string ProjectRootPath =>
            Directory.GetParent(Application.dataPath)?.FullName
            ?? throw new DirectoryNotFoundException("Unable to resolve Unity project root from Application.dataPath.");

        public static string RootPath => Path.Combine(ProjectRootPath, "Library", "XUUnityLightMcp");
        public static string ConfigDirectory => Path.Combine(RootPath, "config");
        public static string StateDirectory => Path.Combine(RootPath, "state");
        public static string InboxDirectory => Path.Combine(RootPath, "inbox");
        public static string OutboxDirectory => Path.Combine(RootPath, "outbox");
        public static string JournalDirectory => Path.Combine(RootPath, "journal");
        public static string RequestJournalDirectory => Path.Combine(JournalDirectory, "requests");
        public static string LogsDirectory => Path.Combine(RootPath, "logs");
        public static string CapturesDirectory => Path.Combine(RootPath, "captures");
        public static string ScenariosDirectory => Path.Combine(RootPath, "scenarios");
        public static string ScenarioResultsDirectory => Path.Combine(ScenariosDirectory, "results");
        public static string ActiveScenarioRunPath => Path.Combine(ScenariosDirectory, "active_run.json");
        public static string BridgeConfigPath => Path.Combine(ConfigDirectory, "bridge_config.json");
        public static string BridgeStatePath => Path.Combine(StateDirectory, "bridge_state.json");
        public static string BridgeGenerationStatePath => Path.Combine(StateDirectory, "bridge_generation_state.json");
        public static string PlayModeTransitionStatePath => Path.Combine(StateDirectory, "playmode_transition_state.json");
        public static string CapabilitiesReportPath => Path.Combine(StateDirectory, "capabilities_report.json");

        public static void EnsureDirectories()
        {
            Directory.CreateDirectory(ConfigDirectory);
            Directory.CreateDirectory(StateDirectory);
            Directory.CreateDirectory(InboxDirectory);
            Directory.CreateDirectory(OutboxDirectory);
            Directory.CreateDirectory(JournalDirectory);
            Directory.CreateDirectory(RequestJournalDirectory);
            Directory.CreateDirectory(LogsDirectory);
            Directory.CreateDirectory(CapturesDirectory);
            Directory.CreateDirectory(ScenariosDirectory);
            Directory.CreateDirectory(ScenarioResultsDirectory);
        }
    }
}
