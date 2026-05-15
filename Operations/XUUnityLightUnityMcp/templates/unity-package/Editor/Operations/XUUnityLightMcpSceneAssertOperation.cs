using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.SceneManagement;
using XUUnity.LightMcp.Editor.Core;

namespace XUUnity.LightMcp.Editor.Operations
{
    internal sealed class XUUnityLightMcpSceneAssertOperation : IXUUnityLightMcpOperation
    {
        public string OperationName => "unity.scene.assert";

        public XUUnityLightMcpResponse Execute(XUUnityLightMcpRequest request)
        {
            var args = string.IsNullOrWhiteSpace(request.args_json)
                ? new XUUnityLightMcpSceneAssertArgs()
                : JsonUtility.FromJson<XUUnityLightMcpSceneAssertArgs>(request.args_json) ?? new XUUnityLightMcpSceneAssertArgs();

            var scene = SceneManager.GetActiveScene();
            var roots = scene.IsValid() ? scene.GetRootGameObjects() : Array.Empty<GameObject>();
            var rootNames = roots
                .Where(root => root != null)
                .Select(root => root.name ?? "")
                .ToList();

            var payload = new XUUnityLightMcpSceneAssertPayload
            {
                project_root = XUUnityLightMcpFileIpcPaths.ProjectRootPath,
                expected_name = args.expectedName ?? "",
                expected_path = args.expectedPath ?? "",
                allow_dirty = args.allowDirty,
                active_scene = new XUUnityLightMcpSceneData
                {
                    name = scene.name ?? "",
                    path = scene.path ?? "",
                    is_dirty = scene.isDirty,
                    root_count = rootNames.Count
                }
            };

            foreach (var rootName in rootNames)
            {
                payload.root_objects.Add(new XUUnityLightMcpRootObject { name = rootName });
            }

            var requiredRoots = NormalizeRequiredRoots(args.requiredRootNames);
            payload.required_root_names.AddRange(requiredRoots);

            var failures = new List<string>();
            if (string.IsNullOrWhiteSpace(args.expectedName)
                && string.IsNullOrWhiteSpace(args.expectedPath)
                && requiredRoots.Count == 0
                && args.allowDirty)
            {
                failures.Add("no scene assertion expectations were provided");
            }

            if (!string.IsNullOrWhiteSpace(args.expectedName)
                && !string.Equals(scene.name ?? "", args.expectedName.Trim(), StringComparison.Ordinal))
            {
                failures.Add($"expected scene name '{args.expectedName.Trim()}', observed '{scene.name ?? ""}'");
            }

            if (!string.IsNullOrWhiteSpace(args.expectedPath)
                && !string.Equals(scene.path ?? "", args.expectedPath.Trim(), StringComparison.Ordinal))
            {
                failures.Add($"expected scene path '{args.expectedPath.Trim()}', observed '{scene.path ?? ""}'");
            }

            if (!args.allowDirty && scene.isDirty)
            {
                failures.Add("active scene is dirty");
            }

            foreach (var requiredRoot in requiredRoots)
            {
                if (rootNames.Contains(requiredRoot, StringComparer.Ordinal))
                {
                    continue;
                }

                payload.missing_root_names.Add(requiredRoot);
                failures.Add($"required root '{requiredRoot}' was not found");
            }

            payload.passed = failures.Count == 0;
            payload.status = payload.passed ? "passed" : "failed";
            payload.failure_reason = string.Join("; ", failures);

            return XUUnityLightMcpResponseWriter.Success(
                request.request_id,
                OperationName,
                JsonUtility.ToJson(payload)
            );
        }

        static List<string> NormalizeRequiredRoots(string[] requiredRootNames)
        {
            if (requiredRootNames == null || requiredRootNames.Length == 0)
            {
                return new List<string>();
            }

            return requiredRootNames
                .Where(value => !string.IsNullOrWhiteSpace(value))
                .Select(value => value.Trim())
                .Distinct(StringComparer.Ordinal)
                .ToList();
        }
    }
}
