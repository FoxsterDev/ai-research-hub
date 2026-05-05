using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using XUUnity.LightMcp.Editor.Bridge;
using XUUnity.LightMcp.Editor.Core;

namespace XUUnity.LightMcp.Editor.Operations
{
    internal sealed class XUUnityLightMcpConsoleTailOperation : IXUUnityLightMcpOperation
    {
        public string OperationName => "unity.console.tail";

        public XUUnityLightMcpResponse Execute(XUUnityLightMcpRequest request)
        {
            var args = string.IsNullOrWhiteSpace(request.args_json)
                ? new XUUnityLightMcpConsoleTailArgs()
                : JsonUtility.FromJson<XUUnityLightMcpConsoleTailArgs>(request.args_json) ?? new XUUnityLightMcpConsoleTailArgs();

            var limit = Math.Max(1, args.limit);
            var includeTypes = NormalizeIncludeTypes(args.includeTypes);

            var allItems = XUUnityLightMcpConsoleBuffer.Snapshot();
            var filtered = allItems.Where(item => includeTypes.Contains(item.type)).ToList();

            var truncated = filtered.Count > limit;
            if (filtered.Count > limit)
            {
                filtered = filtered.Skip(filtered.Count - limit).ToList();
            }

            var payload = new XUUnityLightMcpConsolePayload
            {
                project_root = XUUnityLightMcpFileIpcPaths.ProjectRootPath,
                items = filtered,
                truncated = truncated
            };

            return XUUnityLightMcpResponseWriter.Success(
                request.request_id,
                OperationName,
                JsonUtility.ToJson(payload)
            );
        }

        static HashSet<string> NormalizeIncludeTypes(string[] includeTypes)
        {
            if (includeTypes == null || includeTypes.Length == 0)
            {
                return new HashSet<string>(new[] { "error", "warning", "log", "exception" }, StringComparer.OrdinalIgnoreCase);
            }

            return new HashSet<string>(includeTypes.Where(value => !string.IsNullOrWhiteSpace(value)), StringComparer.OrdinalIgnoreCase);
        }
    }
}
