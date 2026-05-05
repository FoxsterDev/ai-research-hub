using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using UnityEditor;
using UnityEditor.Build.Player;
using UnityEditor.Compilation;
using XUUnity.LightMcp.Editor.Core;

namespace XUUnity.LightMcp.Editor.Helpers
{
    internal static class XUUnityLightMcpCompileUtility
    {
        const BindingFlags StaticBindings = BindingFlags.NonPublic | BindingFlags.Public | BindingFlags.Static;

        public static XUUnityLightMcpCompileConfigPayload Compile(XUUnityLightMcpCompilePlayerScriptsArgs args)
        {
            if (args == null)
            {
                throw new InvalidOperationException("Compile arguments are required.");
            }

            if (EditorApplication.isCompiling || EditorApplication.isPlayingOrWillChangePlaymode || EditorApplication.isUpdating)
            {
                throw new InvalidOperationException(
                    $"Unity editor is busy. isCompiling={EditorApplication.isCompiling}, " +
                    $"isPlayingOrWillChangePlaymode={EditorApplication.isPlayingOrWillChangePlaymode}, " +
                    $"isUpdating={EditorApplication.isUpdating}");
            }

            if (EditorUtility.scriptCompilationFailed)
            {
                throw new InvalidOperationException("Unity has compilation errors. Resolve them before running compile validation.");
            }

            if (string.IsNullOrWhiteSpace(args.target))
            {
                throw new InvalidOperationException("Compile target is required.");
            }

            if (!Enum.TryParse(args.target.Trim(), true, out BuildTarget target))
            {
                throw new InvalidOperationException($"Unknown Unity BuildTarget '{args.target}'.");
            }

            var payload = new XUUnityLightMcpCompileConfigPayload
            {
                name = string.IsNullOrWhiteSpace(args.name) ? target.ToString() : args.name.Trim(),
                target = target.ToString(),
                target_group = ConvertToBuildTargetGroup(target).ToString(),
                target_supported = IsBuildTargetSupported(target),
                option_flags = NormalizeStrings(args.optionFlags),
                extra_defines = NormalizeStrings(args.extraDefines)
            };

            if (!payload.target_supported)
            {
                payload.status = "target_support_missing";
                return payload;
            }

            var outputDirectory = BuildOutputDirectory(payload.name, target);
            payload.output_directory = outputDirectory;

            var compilationSettings = new ScriptCompilationSettings
            {
                target = target,
                group = ConvertToBuildTargetGroup(target),
                options = ParseOptions(payload.option_flags),
                extraScriptingDefines = payload.extra_defines.ToArray()
            };

            var stopwatch = Stopwatch.StartNew();
            var errors = new List<XUUnityLightMcpCompileErrorItem>();

            void HandleAssemblyCompilationFinished(string assemblyName, CompilerMessage[] compilerMessages)
            {
                if (compilerMessages == null)
                {
                    return;
                }

                foreach (var message in compilerMessages)
                {
                    if (message.type != CompilerMessageType.Error)
                    {
                        continue;
                    }

                    errors.Add(new XUUnityLightMcpCompileErrorItem
                    {
                        assembly_name = assemblyName ?? "",
                        message = message.message ?? "",
                        file = message.file ?? "",
                        line = message.line,
                        column = message.column
                    });
                }
            }

            try
            {
                CompilationPipeline.assemblyCompilationFinished -= HandleAssemblyCompilationFinished;
                CompilationPipeline.assemblyCompilationFinished += HandleAssemblyCompilationFinished;
                var result = PlayerBuildInterface.CompilePlayerScripts(compilationSettings, outputDirectory);
                payload.compiled_assembly_count = result.assemblies?.Count ?? 0;
            }
            finally
            {
                CompilationPipeline.assemblyCompilationFinished -= HandleAssemblyCompilationFinished;
                stopwatch.Stop();
            }

            payload.duration_seconds = Math.Round(stopwatch.Elapsed.TotalSeconds, 6);
            payload.errors = errors;
            payload.error_count = errors.Count;
            payload.status = errors.Count > 0 ? "failed" : "passed";
            return payload;
        }

        static List<string> NormalizeStrings(string[] values)
        {
            var result = new List<string>();
            if (values == null)
            {
                return result;
            }

            foreach (var value in values)
            {
                if (string.IsNullOrWhiteSpace(value))
                {
                    continue;
                }

                result.Add(value.Trim());
            }

            return result;
        }

        static ScriptCompilationOptions ParseOptions(List<string> optionFlags)
        {
            var options = ScriptCompilationOptions.None;
            if (optionFlags == null)
            {
                return options;
            }

            foreach (var optionFlag in optionFlags)
            {
                if (!Enum.TryParse(optionFlag, true, out ScriptCompilationOptions parsed))
                {
                    throw new InvalidOperationException($"Unknown ScriptCompilationOptions flag '{optionFlag}'.");
                }

                options |= parsed;
            }

            return options;
        }

        static string BuildOutputDirectory(string compileName, BuildTarget target)
        {
            var safeName = string.IsNullOrWhiteSpace(compileName) ? target.ToString() : compileName;
            foreach (var invalid in Path.GetInvalidFileNameChars())
            {
                safeName = safeName.Replace(invalid, '_');
            }

            var path = Path.Combine(
                XUUnityLightMcpFileIpcPaths.RootPath,
                "compile",
                $"{safeName}-{target}");

            if (Directory.Exists(path))
            {
                Directory.Delete(path, true);
            }

            Directory.CreateDirectory(path);
            return path;
        }

        static bool IsBuildTargetSupported(BuildTarget target)
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

        static BuildTargetGroup ConvertToBuildTargetGroup(BuildTarget target)
        {
            switch (target)
            {
                case BuildTarget.Android:
                    return BuildTargetGroup.Android;
                case BuildTarget.iOS:
                    return BuildTargetGroup.iOS;
                case BuildTarget.WebGL:
                    return BuildTargetGroup.WebGL;
                case BuildTarget.StandaloneWindows:
                case BuildTarget.StandaloneWindows64:
                case BuildTarget.StandaloneLinux64:
                case BuildTarget.StandaloneOSX:
                    return BuildTargetGroup.Standalone;
                case BuildTarget.tvOS:
                    return BuildTargetGroup.tvOS;
                case BuildTarget.WSAPlayer:
                    return BuildTargetGroup.WSA;
                default:
                    return BuildTargetGroup.Unknown;
            }
        }
    }
}
