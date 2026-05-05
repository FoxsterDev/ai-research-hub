using System;
using System.Collections.Generic;
using XUUnity.LightMcp.Editor.Operations;

namespace XUUnity.LightMcp.Editor.Core
{
    internal interface IXUUnityLightMcpOperation
    {
        string OperationName { get; }
        XUUnityLightMcpResponse Execute(XUUnityLightMcpRequest request);
    }

    internal static class XUUnityLightMcpOperationRegistry
    {
        static readonly Dictionary<string, IXUUnityLightMcpOperation> Operations = new(StringComparer.Ordinal)
        {
            { "unity.status", new XUUnityLightMcpStatusOperation() },
            { "unity.capabilities.get", new XUUnityLightMcpCapabilitiesGetOperation() },
            { "unity.health.probe", new XUUnityLightMcpHealthProbeOperation() },
            { "unity.console.tail", new XUUnityLightMcpConsoleTailOperation() },
            { "unity.scene.snapshot", new XUUnityLightMcpSceneSnapshotOperation() },
            { "unity.tests.run_editmode", new XUUnityLightMcpEditModeTestsOperation() },
            { "unity.playmode.state", new XUUnityLightMcpPlayModeStateOperation() },
            { "unity.playmode.set", new XUUnityLightMcpPlayModeSetOperation() },
            { "unity.game_view.configure", new XUUnityLightMcpGameViewConfigureOperation() },
            { "unity.game_view.screenshot", new XUUnityLightMcpGameViewScreenshotOperation() },
            { "unity.compile.player_scripts", new XUUnityLightMcpCompilePlayerScriptsOperation() },
            { "unity.compile.matrix", new XUUnityLightMcpCompileMatrixOperation() },
            { "unity.scenario.validate", new XUUnityLightMcpScenarioValidateOperation() },
            { "unity.scenario.run", new XUUnityLightMcpScenarioRunOperation() },
            { "unity.scenario.result", new XUUnityLightMcpScenarioResultOperation() }
        };

        public static bool TryGet(string operationName, out IXUUnityLightMcpOperation operation)
        {
            return Operations.TryGetValue(operationName, out operation);
        }
    }
}
