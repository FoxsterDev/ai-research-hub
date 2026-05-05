using System.Collections.Generic;
using UnityEditor;
using UnityEditor.Compilation;
using UnityEditor.PackageManager;
using UnityEngine;

namespace XUUnity.LightMcp.Editor.Bridge
{
    [InitializeOnLoad]
    internal static class XUUnityLightMcpLifecycleMonitor
    {
        static bool _initialized;

        static XUUnityLightMcpLifecycleMonitor()
        {
            InitializeIfNeeded();
        }

        public static void InitializeIfNeeded()
        {
            if (_initialized || !XUUnityLightMcpBridgeActivation.IsEnabled())
            {
                return;
            }

            AssemblyReloadEvents.beforeAssemblyReload -= OnBeforeAssemblyReload;
            AssemblyReloadEvents.beforeAssemblyReload += OnBeforeAssemblyReload;
            AssemblyReloadEvents.afterAssemblyReload -= OnAfterAssemblyReload;
            AssemblyReloadEvents.afterAssemblyReload += OnAfterAssemblyReload;

            CompilationPipeline.compilationStarted -= OnCompilationStarted;
            CompilationPipeline.compilationStarted += OnCompilationStarted;
            CompilationPipeline.compilationFinished -= OnCompilationFinished;
            CompilationPipeline.compilationFinished += OnCompilationFinished;

            EditorApplication.playModeStateChanged -= OnPlayModeStateChanged;
            EditorApplication.playModeStateChanged += OnPlayModeStateChanged;

            Events.registeringPackages -= OnRegisteringPackages;
            Events.registeringPackages += OnRegisteringPackages;
            Events.registeredPackages -= OnRegisteredPackages;
            Events.registeredPackages += OnRegisteredPackages;

            _initialized = true;
            XUUnityLightMcpBridgeRuntimeState.PollTransientLifecycleState();
        }

        public static void Tick()
        {
            if (!_initialized)
            {
                return;
            }

            XUUnityLightMcpBridgeRuntimeState.PollTransientLifecycleState();
        }

        public static void MarkAssetRefreshRequested()
        {
            XUUnityLightMcpBridgeRuntimeState.MarkAssetImportActivity();
        }

        public static void MarkAssetPostprocessActivity()
        {
            XUUnityLightMcpBridgeRuntimeState.MarkAssetImportActivity();
        }

        public static void MarkPackageResolveRequested()
        {
            XUUnityLightMcpBridgeRuntimeState.MarkPackageOperationStarted("Client.Resolve", "resolve_requested");
        }

        static void OnBeforeAssemblyReload()
        {
            if (XUUnityLightMcpBridgeRuntimeState.TryGetActiveRequestSnapshot(out var snapshot))
            {
                XUUnityLightMcpRequestJournal.WriteRequestAbandoned(
                    snapshot,
                    "domain_reload_before_request_completion",
                    true);
            }

            XUUnityLightMcpBridgeTransportRuntime.Shutdown();
            XUUnityLightMcpBridgeRuntimeState.MarkDomainReloadStarting();
            TryWriteHeartbeat();
        }

        static void OnAfterAssemblyReload()
        {
            XUUnityLightMcpBridgeRuntimeState.MarkDomainReloadCompleted();
            TryWriteHeartbeat();
        }

        static void OnCompilationStarted(object context)
        {
            XUUnityLightMcpBridgeRuntimeState.MarkScriptReloadPending();
        }

        static void OnCompilationFinished(object context)
        {
            XUUnityLightMcpBridgeRuntimeState.MarkScriptReloadCompleted();
        }

        static void OnRegisteringPackages(PackageRegistrationEventArgs eventArgs)
        {
            XUUnityLightMcpBridgeRuntimeState.MarkPackageOperationStarted(BuildPackageOperationName(eventArgs), "registering_packages");
            TryWriteHeartbeat();
        }

        static void OnRegisteredPackages(PackageRegistrationEventArgs eventArgs)
        {
            XUUnityLightMcpBridgeRuntimeState.MarkPackageOperationCompleted();
            XUUnityLightMcpBridgeRuntimeState.MarkAssetImportActivity();
            TryWriteHeartbeat();
        }

        static void OnPlayModeStateChanged(PlayModeStateChange stateChange)
        {
            XUUnityLightMcpBridgeRuntimeState.MarkPlayModeStateChanged(ResolvePlayModeStateLabel(stateChange));
            TryWriteHeartbeat();
        }

        static string BuildPackageOperationName(PackageRegistrationEventArgs eventArgs)
        {
            if (eventArgs == null)
            {
                return "package_registration";
            }

            var addedCount = CountItems(eventArgs.added);
            var removedCount = CountItems(eventArgs.removed);
            var changedCount = CountItems(eventArgs.changedTo);
            return $"package_registration(add={addedCount},change={changedCount},remove={removedCount})";
        }

        static int CountItems<T>(IEnumerable<T> items)
        {
            if (items == null)
            {
                return 0;
            }

            var count = 0;
            foreach (var _ in items)
            {
                count++;
            }

            return count;
        }

        static void TryWriteHeartbeat()
        {
            try
            {
                XUUnityLightMcpBridgeStateWriter.WriteHeartbeat();
            }
            catch
            {
            }
        }

        static string ResolvePlayModeStateLabel(PlayModeStateChange stateChange)
        {
            return stateChange switch
            {
                PlayModeStateChange.EnteredEditMode => "edit",
                PlayModeStateChange.ExitingEditMode => "transitioning",
                PlayModeStateChange.EnteredPlayMode => EditorApplication.isPaused ? "paused" : "playing",
                PlayModeStateChange.ExitingPlayMode => "transitioning",
                _ => "transitioning",
            };
        }
    }

    internal sealed class XUUnityLightMcpLifecycleAssetPostprocessor : AssetPostprocessor
    {
        static void OnPostprocessAllAssets(
            string[] importedAssets,
            string[] deletedAssets,
            string[] movedAssets,
            string[] movedFromAssetPaths)
        {
            if ((importedAssets?.Length ?? 0) <= 0
                && (deletedAssets?.Length ?? 0) <= 0
                && (movedAssets?.Length ?? 0) <= 0
                && (movedFromAssetPaths?.Length ?? 0) <= 0)
            {
                return;
            }

            XUUnityLightMcpLifecycleMonitor.MarkAssetPostprocessActivity();
        }
    }
}
