using System;
using System.IO;
using System.Reflection;
using System.Threading;
using UnityEditor;
using UnityEditorInternal;
using UnityEngine;
using XUUnity.LightMcp.Editor.Core;

namespace XUUnity.LightMcp.Editor.Helpers
{
    internal static class XUUnityLightMcpGameViewUtility
    {
        const int RepaintSettlingDelayMs = 100;
        static readonly BindingFlags AllBindings = BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Static;

        public static XUUnityLightMcpGameViewProbeResult ProbeReflectionSurface()
        {
            try
            {
                var gameViewType = RequireType("UnityEditor.GameView,UnityEditor");
                RequireProperty(gameViewType, "currentGameViewSize");
                RequireProperty(gameViewType, "selectedSizeIndex");
                RequireField(gameViewType, "m_RenderTexture");

                var gameViewSizesType = RequireType("UnityEditor.GameViewSizes,UnityEditor");
                var groupEnumType = RequireType("UnityEditor.GameViewSizeGroupType,UnityEditor");
                var sizeTypeEnum = RequireType("UnityEditor.GameViewSizeType,UnityEditor");
                var sizeType = RequireType("UnityEditor.GameViewSize,UnityEditor");

                RequireMethod(gameViewSizesType, "GetGroup");
                RequireProperty(sizeType, "width");
                RequireProperty(sizeType, "height");
                RequireProperty(sizeType, "baseText");
                RequireConstructor(sizeType, new[] { sizeTypeEnum, typeof(int), typeof(int), typeof(string) });

                var groupEnumValue = Enum.Parse(groupEnumType, "Standalone", true);
                var scriptableSingletonType = RequireType("UnityEditor.ScriptableSingleton`1,UnityEditor").MakeGenericType(gameViewSizesType);
                var instance = scriptableSingletonType.GetProperty("instance", AllBindings)?.GetValue(null, null);
                var groupObject = gameViewSizesType.GetMethod("GetGroup", AllBindings)?.Invoke(instance, new[] { groupEnumValue });
                if (groupObject == null)
                {
                    throw new InvalidOperationException("Unable to resolve Unity Game View size group instance.");
                }

                var groupType = groupObject.GetType();
                RequireMethod(groupType, "GetBuiltinCount");
                RequireMethod(groupType, "GetCustomCount");
                RequireMethod(groupType, "GetGameViewSize");
                RequireMethod(groupType, "AddCustomSize");

                return new XUUnityLightMcpGameViewProbeResult
                {
                    adapter_id = "game_view_reflection_v1",
                    supported = true,
                    reason = ""
                };
            }
            catch (Exception ex)
            {
                return new XUUnityLightMcpGameViewProbeResult
                {
                    adapter_id = "game_view_reflection_v1",
                    supported = false,
                    reason = ex.Message
                };
            }
        }

        public static EditorWindow EnsureGameView()
        {
            try
            {
                if (!EditorApplication.ExecuteMenuItem("Window/General/Game"))
                {
                    EditorApplication.ExecuteMenuItem("Window/General/Game %2");
                }
            }
            catch
            {
            }

            var gameViewType = RequireType("UnityEditor.GameView,UnityEditor");
            var window = EditorWindow.GetWindow(gameViewType, false, null, false);
            if (window == null)
            {
                throw new InvalidOperationException("Unable to open Unity Game View window.");
            }

            try
            {
                window.Focus();
            }
            catch
            {
            }

            window.Repaint();
            try
            {
                SceneView.RepaintAll();
                InternalEditorUtility.RepaintAllViews();
                EditorApplication.QueuePlayerLoopUpdate();
            }
            catch
            {
            }

            Thread.Sleep(RepaintSettlingDelayMs);
            return window;
        }

        public static XUUnityLightMcpGameViewData GetCurrentGameViewData()
        {
            var gameView = EnsureGameView();
            var gameViewType = gameView.GetType();
            var currentSize = gameViewType.GetProperty("currentGameViewSize", AllBindings)?.GetValue(gameView, null);
            if (currentSize == null)
            {
                throw new InvalidOperationException("Unable to resolve current Unity Game View size.");
            }

            return BuildSizeData(currentSize, GetActiveGroupName(), false);
        }

        public static XUUnityLightMcpGameViewData SetFixedResolution(
            int width,
            int height,
            string requestedGroup,
            string requestedLabel,
            bool allowCreateCustomSize)
        {
            if (width < 1 || height < 1)
            {
                throw new InvalidOperationException("Game View width and height must both be greater than zero.");
            }

            var activeGroupName = GetActiveGroupName();
            if (!string.IsNullOrWhiteSpace(requestedGroup) &&
                !string.Equals(requestedGroup, activeGroupName, StringComparison.OrdinalIgnoreCase))
            {
                throw new InvalidOperationException(
                    $"Requested Game View group '{requestedGroup}' does not match the active build group '{activeGroupName}'.");
            }

            var label = string.IsNullOrWhiteSpace(requestedLabel)
                ? $"XUUnity {width}x{height}"
                : requestedLabel.Trim();

            var groupObject = GetGameViewGroup(activeGroupName);
            var matchIndex = FindSizeIndex(groupObject, width, height);
            var createdCustom = false;
            if (matchIndex < 0)
            {
                if (!allowCreateCustomSize)
                {
                    throw new InvalidOperationException(
                        $"Game View size {width}x{height} is not available in the active group '{activeGroupName}'. " +
                        "Re-run with allowCreateCustomSize=true if persistent editor user-state changes are acceptable.");
                }

                AddCustomSize(groupObject, width, height, label);
                matchIndex = FindSizeIndex(groupObject, width, height);
                createdCustom = true;
            }

            if (matchIndex < 0)
            {
                throw new InvalidOperationException($"Unable to add or select Game View size {width}x{height}.");
            }

            var gameView = EnsureGameView();
            var selectedSizeIndex = gameView.GetType().GetProperty("selectedSizeIndex", AllBindings);
            if (selectedSizeIndex == null)
            {
                throw new InvalidOperationException("Unity Game View does not expose selectedSizeIndex in this editor version.");
            }

            selectedSizeIndex.SetValue(gameView, matchIndex, null);
            gameView.Repaint();
            InternalEditorUtility.RepaintAllViews();
            EditorApplication.QueuePlayerLoopUpdate();
            Thread.Sleep(RepaintSettlingDelayMs);

            var current = GetCurrentGameViewData();
            current.is_custom = createdCustom;
            if (string.IsNullOrWhiteSpace(current.label))
            {
                current.label = label;
            }
            return current;
        }

        public static XUUnityLightMcpGameViewScreenshotPayload CaptureScreenshot(
            string requestId,
            string fileName,
            bool includeImage,
            int maxResolution)
        {
            var gameView = EnsureGameView();
            var gameViewType = gameView.GetType();
            var rtField = gameViewType.GetField("m_RenderTexture", AllBindings);
            var sourceRt = rtField?.GetValue(gameView) as RenderTexture;
            if (sourceRt == null || !sourceRt.IsCreated())
            {
                throw new InvalidOperationException(
                    "Game View render texture is not available. Ensure the Game View window is open and visible.");
            }

            var safeFileName = SanitizeFileName(fileName);
            var fullPath = BuildCapturePath(requestId, safeFileName);

            var width = sourceRt.width;
            var height = sourceRt.height;
            var previousActive = RenderTexture.active;
            Texture2D captured = null;
            Texture2D inlineTexture = null;
            try
            {
                RenderTexture.active = sourceRt;
                captured = new Texture2D(width, height, TextureFormat.RGB24, false);
                captured.ReadPixels(new Rect(0, 0, width, height), 0, 0);

                if (SystemInfo.graphicsUVStartsAtTop)
                {
                    FlipTextureVertically(captured);
                }

                captured.Apply();
                File.WriteAllBytes(fullPath, captured.EncodeToPNG());

                string imageBase64 = "";
                if (includeImage)
                {
                    inlineTexture = DownscaleIfNeeded(captured, maxResolution);
                    imageBase64 = Convert.ToBase64String(inlineTexture.EncodeToPNG());
                }

                return new XUUnityLightMcpGameViewScreenshotPayload
                {
                    project_root = XUUnityLightMcpFileIpcPaths.ProjectRootPath,
                    file_path = fullPath,
                    width = width,
                    height = height,
                    image_base64 = imageBase64,
                    image_included = includeImage
                };
            }
            finally
            {
                RenderTexture.active = previousActive;
                if (inlineTexture != null && !ReferenceEquals(inlineTexture, captured))
                {
                    UnityEngine.Object.DestroyImmediate(inlineTexture);
                }
                if (captured != null)
                {
                    UnityEngine.Object.DestroyImmediate(captured);
                }
            }
        }

        static string GetActiveGroupName()
        {
            return EditorUserBuildSettings.activeBuildTarget switch
            {
                BuildTarget.Android => "Android",
                BuildTarget.iOS => "iPhone",
                _ => "Standalone"
            };
        }

        static object GetGameViewGroup(string groupName)
        {
            var gameViewSizesType = RequireType("UnityEditor.GameViewSizes,UnityEditor");
            var scriptableSingletonType = RequireType("UnityEditor.ScriptableSingleton`1,UnityEditor").MakeGenericType(gameViewSizesType);
            var instance = scriptableSingletonType.GetProperty("instance", AllBindings)?.GetValue(null, null);
            if (instance == null)
            {
                throw new InvalidOperationException("Unable to access Unity GameViewSizes singleton.");
            }

            var groupEnumType = RequireType("UnityEditor.GameViewSizeGroupType,UnityEditor");
            var groupEnum = Enum.Parse(groupEnumType, groupName, true);
            var getGroup = gameViewSizesType.GetMethod("GetGroup", AllBindings);
            var groupObject = getGroup?.Invoke(instance, new[] { groupEnum });
            if (groupObject == null)
            {
                throw new InvalidOperationException($"Unable to access Unity Game View size group '{groupName}'.");
            }

            return groupObject;
        }

        static int FindSizeIndex(object groupObject, int width, int height)
        {
            var groupType = groupObject.GetType();
            var getBuiltinCount = groupType.GetMethod("GetBuiltinCount", AllBindings);
            var getCustomCount = groupType.GetMethod("GetCustomCount", AllBindings);
            var getGameViewSize = groupType.GetMethod("GetGameViewSize", AllBindings);

            if (getBuiltinCount == null || getCustomCount == null || getGameViewSize == null)
            {
                throw new InvalidOperationException("Unity Game View size group reflection surface changed.");
            }

            var total = (int)getBuiltinCount.Invoke(groupObject, null) + (int)getCustomCount.Invoke(groupObject, null);
            for (var index = 0; index < total; index++)
            {
                var sizeObject = getGameViewSize.Invoke(groupObject, new object[] { index });
                if (sizeObject == null)
                {
                    continue;
                }

                var currentWidth = ReadIntProperty(sizeObject, "width");
                var currentHeight = ReadIntProperty(sizeObject, "height");
                if (currentWidth == width && currentHeight == height)
                {
                    return index;
                }
            }

            return -1;
        }

        static void AddCustomSize(object groupObject, int width, int height, string label)
        {
            var gameViewSizeType = RequireType("UnityEditor.GameViewSize,UnityEditor");
            var sizeTypeEnum = RequireType("UnityEditor.GameViewSizeType,UnityEditor");
            var fixedResolution = Enum.Parse(sizeTypeEnum, "FixedResolution");
            var constructor = gameViewSizeType.GetConstructor(AllBindings, null,
                new[] { sizeTypeEnum, typeof(int), typeof(int), typeof(string) }, null);
            if (constructor == null)
            {
                throw new InvalidOperationException("Unity GameViewSize constructor signature changed.");
            }

            var newSize = constructor.Invoke(new object[] { fixedResolution, width, height, label });
            var addCustomSize = groupObject.GetType().GetMethod("AddCustomSize", AllBindings);
            if (addCustomSize == null)
            {
                throw new InvalidOperationException("Unity Game View size group no longer exposes AddCustomSize.");
            }

            addCustomSize.Invoke(groupObject, new[] { newSize });
        }

        static XUUnityLightMcpGameViewData BuildSizeData(object sizeObject, string groupName, bool isCustom)
        {
            return new XUUnityLightMcpGameViewData
            {
                group = groupName,
                label = ReadStringProperty(sizeObject, "baseText"),
                width = ReadIntProperty(sizeObject, "width"),
                height = ReadIntProperty(sizeObject, "height"),
                is_custom = isCustom
            };
        }

        static int ReadIntProperty(object instance, string propertyName)
        {
            var value = instance.GetType().GetProperty(propertyName, AllBindings)?.GetValue(instance, null);
            return value is int intValue ? intValue : 0;
        }

        static string ReadStringProperty(object instance, string propertyName)
        {
            var value = instance.GetType().GetProperty(propertyName, AllBindings)?.GetValue(instance, null);
            return value as string ?? "";
        }

        static string BuildCapturePath(string requestId, string fileName)
        {
            XUUnityLightMcpFileIpcPaths.EnsureDirectories();
            var timestamp = DateTime.UtcNow.ToString("yyyyMMdd-HHmmss");
            var finalFileName = string.IsNullOrWhiteSpace(fileName)
                ? $"game-view-{timestamp}.png"
                : fileName;

            if (!finalFileName.EndsWith(".png", StringComparison.OrdinalIgnoreCase))
            {
                finalFileName += ".png";
            }

            var fullPath = Path.Combine(XUUnityLightMcpFileIpcPaths.CapturesDirectory, finalFileName);
            if (!File.Exists(fullPath))
            {
                return fullPath;
            }

            var suffix = string.IsNullOrWhiteSpace(requestId) ? Guid.NewGuid().ToString("N")[..8] : requestId[..Math.Min(8, requestId.Length)];
            var baseName = Path.GetFileNameWithoutExtension(finalFileName);
            return Path.Combine(XUUnityLightMcpFileIpcPaths.CapturesDirectory, $"{baseName}-{suffix}.png");
        }

        static string SanitizeFileName(string fileName)
        {
            if (string.IsNullOrWhiteSpace(fileName))
            {
                return "";
            }

            var sanitized = fileName.Trim();
            foreach (var invalid in Path.GetInvalidFileNameChars())
            {
                sanitized = sanitized.Replace(invalid, '_');
            }
            return sanitized;
        }

        static Texture2D DownscaleIfNeeded(Texture2D source, int maxResolution)
        {
            var limit = maxResolution > 0 ? maxResolution : 640;
            if (source.width <= limit && source.height <= limit)
            {
                return source;
            }

            var scale = Mathf.Min(limit / (float)source.width, limit / (float)source.height);
            var targetWidth = Mathf.Max(1, Mathf.RoundToInt(source.width * scale));
            var targetHeight = Mathf.Max(1, Mathf.RoundToInt(source.height * scale));

            var rt = RenderTexture.GetTemporary(targetWidth, targetHeight, 0, RenderTextureFormat.ARGB32);
            var previousActive = RenderTexture.active;
            try
            {
                Graphics.Blit(source, rt);
                RenderTexture.active = rt;
                var resized = new Texture2D(targetWidth, targetHeight, TextureFormat.RGBA32, false);
                resized.ReadPixels(new Rect(0, 0, targetWidth, targetHeight), 0, 0);
                resized.Apply();
                return resized;
            }
            finally
            {
                RenderTexture.active = previousActive;
                RenderTexture.ReleaseTemporary(rt);
            }
        }

        static void FlipTextureVertically(Texture2D texture)
        {
            var width = texture.width;
            var height = texture.height;
            var pixels = texture.GetPixels32();
            var flipped = new Color32[pixels.Length];
            for (var y = 0; y < height; y++)
            {
                var srcRow = y * width;
                var dstRow = (height - 1 - y) * width;
                Array.Copy(pixels, srcRow, flipped, dstRow, width);
            }
            texture.SetPixels32(flipped);
        }

        static Type RequireType(string typeName)
        {
            var type = Type.GetType(typeName);
            if (type == null)
            {
                throw new InvalidOperationException($"Required Unity editor type not found: {typeName}");
            }
            return type;
        }

        static PropertyInfo RequireProperty(Type type, string propertyName)
        {
            var property = type.GetProperty(propertyName, AllBindings);
            if (property == null)
            {
                throw new InvalidOperationException($"Required property '{propertyName}' not found on {type.FullName}.");
            }

            return property;
        }

        static FieldInfo RequireField(Type type, string fieldName)
        {
            var field = type.GetField(fieldName, AllBindings);
            if (field == null)
            {
                throw new InvalidOperationException($"Required field '{fieldName}' not found on {type.FullName}.");
            }

            return field;
        }

        static MethodInfo RequireMethod(Type type, string methodName)
        {
            var method = type.GetMethod(methodName, AllBindings);
            if (method == null)
            {
                throw new InvalidOperationException($"Required method '{methodName}' not found on {type.FullName}.");
            }

            return method;
        }

        static ConstructorInfo RequireConstructor(Type type, Type[] argumentTypes)
        {
            var constructor = type.GetConstructor(AllBindings, null, argumentTypes, null);
            if (constructor == null)
            {
                throw new InvalidOperationException($"Required constructor not found on {type.FullName}.");
            }

            return constructor;
        }
    }
}
