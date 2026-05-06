using System;
using UnityEditor;
using UnityEngine;
using XUUnity.LightMcp.Editor.Core;

namespace XUUnity.LightMcp.Editor.Operations
{
    internal sealed class XUUnityLightMcpBuildTargetSwitchOperation : IXUUnityLightMcpOperation
    {
        public string OperationName => "unity.build_target.switch";

        public XUUnityLightMcpResponse Execute(XUUnityLightMcpRequest request)
        {
            var args = string.IsNullOrWhiteSpace(request.args_json)
                ? new XUUnityLightMcpBuildTargetSwitchArgs()
                : JsonUtility.FromJson<XUUnityLightMcpBuildTargetSwitchArgs>(request.args_json) ?? new XUUnityLightMcpBuildTargetSwitchArgs();

            var targetText = (args.target ?? "").Trim();
            if (string.IsNullOrWhiteSpace(targetText))
            {
                return XUUnityLightMcpResponseWriter.Error(request.request_id, "missing_target",
                    "unity.build_target.switch requires a target BuildTarget enum name.");
            }

            if (!Enum.TryParse(targetText, true, out BuildTarget target))
            {
                return XUUnityLightMcpResponseWriter.Error(request.request_id, "unknown_build_target",
                    $"Unknown Unity BuildTarget '{targetText}'.");
            }

            var group = BuildPipeline.GetBuildTargetGroup(target);
            if (group == BuildTargetGroup.Unknown)
            {
                return XUUnityLightMcpResponseWriter.Error(request.request_id, "unsupported_build_target",
                    $"Unity BuildTarget '{target}' does not map to a supported BuildTargetGroup.");
            }

            if (!XUUnityLightMcpBuildTargetGetOperation.IsPlatformSupportLoaded(target))
            {
                return XUUnityLightMcpResponseWriter.Error(request.request_id, "build_target_support_missing",
                    $"Platform support is not loaded for Unity BuildTarget '{target}'.");
            }

            var previousTarget = EditorUserBuildSettings.activeBuildTarget;
            var outcome = "target_already_active";
            if (previousTarget != target)
            {
                var switched = EditorUserBuildSettings.SwitchActiveBuildTarget(group, target);
                if (!switched)
                {
                    return XUUnityLightMcpResponseWriter.Error(request.request_id, "target_switch_failed",
                        $"Unity failed to switch the active build target to '{target}'.");
                }

                outcome = "target_switched";
            }

            var currentTarget = EditorUserBuildSettings.activeBuildTarget;
            if (currentTarget != target)
            {
                return XUUnityLightMcpResponseWriter.Error(request.request_id, "target_switch_incomplete",
                    $"Unity reported target switch completion, but the active build target is '{currentTarget}' instead of '{target}'.");
            }

            var payload = new XUUnityLightMcpBuildTargetSwitchPayload
            {
                project_root = XUUnityLightMcpFileIpcPaths.ProjectRootPath,
                requested_build_target = target.ToString(),
                previous_build_target = previousTarget.ToString(),
                active_build_target = currentTarget.ToString(),
                active_build_target_group = group.ToString(),
                selected_build_target_group = EditorUserBuildSettings.selectedBuildTargetGroup.ToString(),
                target_support_loaded = true,
                outcome = outcome,
                request_completed_at_utc = DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ"),
            };

            return XUUnityLightMcpResponseWriter.Success(
                request.request_id,
                OperationName,
                JsonUtility.ToJson(payload)
            );
        }
    }
}
