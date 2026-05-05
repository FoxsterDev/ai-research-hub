using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;
using XUUnity.LightMcp.Editor.Core;

namespace XUUnity.LightMcp.Editor.Bridge
{
    internal static class XUUnityLightMcpConsoleBuffer
    {
        const int MaxEntries = 500;
        static readonly object Mutex = new();
        static readonly List<XUUnityLightMcpConsoleItem> Items = new();
        static bool _started;

        public static void EnsureStarted()
        {
            if (_started)
            {
                return;
            }

            _started = true;
            Application.logMessageReceivedThreaded -= OnLog;
            Application.logMessageReceivedThreaded += OnLog;
        }

        static void OnLog(string condition, string stackTrace, LogType type)
        {
            var item = new XUUnityLightMcpConsoleItem
            {
                type = NormalizeType(type),
                message = condition ?? "",
                timestamp = DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ"),
                stack_trace = stackTrace ?? ""
            };

            lock (Mutex)
            {
                if (Items.Count >= MaxEntries)
                {
                    Items.RemoveAt(0);
                }
                Items.Add(item);
            }
        }

        public static List<XUUnityLightMcpConsoleItem> Snapshot()
        {
            lock (Mutex)
            {
                return new List<XUUnityLightMcpConsoleItem>(Items);
            }
        }

        static string NormalizeType(LogType type)
        {
            return type switch
            {
                LogType.Error => "error",
                LogType.Assert => "warning",
                LogType.Warning => "warning",
                LogType.Exception => "exception",
                LogType.Log => "log",
                _ => "unknown"
            };
        }
    }
}
