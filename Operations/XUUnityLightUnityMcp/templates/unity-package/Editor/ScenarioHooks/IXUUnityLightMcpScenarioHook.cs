using System;

namespace XUUnity.LightMcp.Editor.ScenarioHooks
{
    public interface IXUUnityLightMcpScenarioHook
    {
        string HookName { get; }

        XUUnityLightMcpScenarioHookResult Execute(string payloadJson);
    }

    [Serializable]
    public sealed class XUUnityLightMcpScenarioHookResult
    {
        public bool success = true;
        public string outcome = "hook_succeeded";
        public string payload_json = "";
        public string error_code = "";
        public string error_message = "";
    }
}
