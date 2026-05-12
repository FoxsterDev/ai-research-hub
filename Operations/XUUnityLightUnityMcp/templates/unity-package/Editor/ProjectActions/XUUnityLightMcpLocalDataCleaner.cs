using System;
using System.Collections.Generic;
using System.IO;
using UnityEngine;

namespace XUUnity.LightMcp.Editor.ProjectActions
{
    [Serializable]
    public sealed class XUUnityLightMcpLocalDataClearRequest
    {
        public bool clearPlayerPrefs;
        public bool clearPersistentDataPath;
    }

    [Serializable]
    public sealed class XUUnityLightMcpLocalDataClearResult
    {
        public bool playerPrefsRequested;
        public bool playerPrefsCleared;
        public bool persistentDataPathRequested;
        public bool persistentDataPathExisted;
        public bool persistentDataPathCleared;
        public string persistentDataPath = "";
        public string[] errors = Array.Empty<string>();

        public bool Succeeded => errors == null || errors.Length == 0;
    }

    public static class XUUnityLightMcpLocalDataCleaner
    {
        public static XUUnityLightMcpLocalDataClearResult Clear(XUUnityLightMcpLocalDataClearRequest request)
        {
            if (request == null)
            {
                request = new XUUnityLightMcpLocalDataClearRequest();
            }

            var result = new XUUnityLightMcpLocalDataClearResult
            {
                playerPrefsRequested = request.clearPlayerPrefs,
                persistentDataPathRequested = request.clearPersistentDataPath,
                persistentDataPath = Application.persistentDataPath ?? "",
            };
            var errors = new List<string>();

            if (request.clearPlayerPrefs)
            {
                try
                {
                    PlayerPrefs.DeleteAll();
                    PlayerPrefs.Save();
                    result.playerPrefsCleared = true;
                }
                catch (Exception exception)
                {
                    errors.Add($"player_prefs: {exception.GetType().Name}: {exception.Message}");
                }
            }

            if (request.clearPersistentDataPath)
            {
                try
                {
                    var path = result.persistentDataPath;
                    result.persistentDataPathExisted = !string.IsNullOrWhiteSpace(path) && Directory.Exists(path);
                    if (result.persistentDataPathExisted)
                    {
                        Directory.Delete(path, true);
                    }

                    result.persistentDataPathCleared = true;
                }
                catch (Exception exception)
                {
                    errors.Add($"persistent_data_path: {exception.GetType().Name}: {exception.Message}");
                }
            }

            result.errors = errors.ToArray();
            return result;
        }
    }
}
