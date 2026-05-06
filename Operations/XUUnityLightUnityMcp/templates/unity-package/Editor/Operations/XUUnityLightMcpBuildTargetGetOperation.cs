using System;
using System.Reflection;
using UnityEditor;
using UnityEngine;
using XUUnity.LightMcp.Editor.Core;

namespace XUUnity.LightMcp.Editor.Operations
{
    internal sealed class XUUnityLightMcpBuildTargetGetOperation : IXUUnityLightMcpOperation
    {
        const BindingFlags StaticBindings = BindingFlags.NonPublic | BindingFlags.Public | BindingFlags.Static;

        public string OperationName => "unity.build_target.get";

        public XUUnityLightMcpResponse Execute(XUUnityLightMcpRequest request)
        {
            var payload = BuildPayload();
            return XUUnityLightMcpResponseWriter.Success(
                request.request_id,
                OperationName,
                JsonUtility.ToJson(payload)
            );
        }

        internal static XUUnityLightMcpBuildTargetGetPayload BuildPayload()
        {
            var activeBuildTarget = EditorUserBuildSettings.activeBuildTarget;
            var activeBuildTargetGroup = BuildPipeline.GetBuildTargetGroup(activeBuildTarget);
            return new XUUnityLightMcpBuildTargetGetPayload
            {
                project_root = XUUnityLightMcpFileIpcPaths.ProjectRootPath,
                active_build_target = activeBuildTarget.ToString(),
                active_build_target_group = activeBuildTargetGroup.ToString(),
                selected_build_target_group = EditorUserBuildSettings.selectedBuildTargetGroup.ToString(),
                target_support_loaded = IsPlatformSupportLoaded(activeBuildTarget),
            };
        }

        internal static bool IsPlatformSupportLoaded(BuildTarget target)
        {
            try
            {
                var moduleManagerType = Type.GetType("UnityEditor.Modules.ModuleManager,UnityEditor.CoreModule");
                var method = moduleManagerType?.GetMethod(
                    "IsPlatformSupportLoadedByBuildTarget",
                    StaticBindings);
                if (method == null)
                {
                    return false;
                }

                return (bool)method.Invoke(null, new object[] { target });
            }
            catch
            {
                return false;
            }
        }
    }
}
