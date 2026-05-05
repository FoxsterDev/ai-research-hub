using System;
using System.IO;
using UnityEngine;
using XUUnity.LightMcp.Editor.Core;
using XUUnity.LightMcp.Editor.Helpers;

namespace XUUnity.LightMcp.Editor.Bridge
{
    internal static class XUUnityLightMcpBridgeRequestPump
    {
        public static void PumpOnce()
        {
            XUUnityLightMcpFileIpcPaths.EnsureDirectories();

            var inbox = new DirectoryInfo(XUUnityLightMcpFileIpcPaths.InboxDirectory);
            foreach (var file in inbox.GetFiles("*.json"))
            {
                ProcessRequest(file);
            }
        }

        static void ProcessRequest(FileInfo file)
        {
            XUUnityLightMcpRequest request = null;

            try
            {
                var json = File.ReadAllText(file.FullName);
                request = JsonUtility.FromJson<XUUnityLightMcpRequest>(json);
                if (request == null || string.IsNullOrWhiteSpace(request.request_id))
                {
                    throw new InvalidOperationException("Request payload is empty or missing request_id.");
                }

                if (!XUUnityLightMcpOperationRegistry.TryGet(request.operation, out var operation))
                {
                    XUUnityLightMcpResponseWriter.Write(
                        XUUnityLightMcpResponseWriter.Error(
                            request.request_id,
                            "tool_unsupported",
                            $"Unsupported operation: {request.operation}"
                        )
                    );
                }
                else
                {
                    if (!XUUnityLightMcpHealthProbe.IsOperationSupported(request.operation, out var unsupportedReason))
                    {
                        XUUnityLightMcpResponseWriter.Write(
                            XUUnityLightMcpResponseWriter.Error(
                                request.request_id,
                                "operation_unavailable",
                                unsupportedReason
                            )
                        );
                        return;
                    }

                    var response = operation.Execute(request);
                    if (response != null)
                    {
                        XUUnityLightMcpResponseWriter.Write(response);
                    }
                }
            }
            catch (Exception ex)
            {
                var requestId = request?.request_id;
                if (string.IsNullOrWhiteSpace(requestId))
                {
                    requestId = Path.GetFileNameWithoutExtension(file.Name);
                }
                XUUnityLightMcpResponseWriter.Write(
                    XUUnityLightMcpResponseWriter.Error(requestId, "bridge_request_failed", ex.Message)
                );
                Debug.LogException(ex);
            }
            finally
            {
                try
                {
                    file.Delete();
                }
                catch
                {
                }
            }
        }
    }
}
