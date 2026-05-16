using System;
using UnityEditor;
using UnityEngine;

namespace XUUnity.LightMcp.Editor.Helpers
{
    internal static class XUUnityLightMcpTestPreflight
    {
        const string AndroidLogcatConsoleWindowTypeName = "Unity.Android.Logcat.AndroidLogcatConsoleWindow";

        public static void RunBeforeTestExecution()
        {
            CloseEditorWindowsByTypeName(AndroidLogcatConsoleWindowTypeName);
        }

        static void CloseEditorWindowsByTypeName(string fullTypeName)
        {
            if (string.IsNullOrWhiteSpace(fullTypeName))
            {
                return;
            }

            EditorWindow[] windows;
            try
            {
                windows = Resources.FindObjectsOfTypeAll<EditorWindow>();
            }
            catch
            {
                return;
            }

            foreach (var window in windows)
            {
                if (window == null)
                {
                    continue;
                }

                var windowType = window.GetType();
                if (!string.Equals(windowType.FullName, fullTypeName, StringComparison.Ordinal))
                {
                    continue;
                }

                try
                {
                    window.Close();
                }
                catch
                {
                }
            }
        }
    }
}
