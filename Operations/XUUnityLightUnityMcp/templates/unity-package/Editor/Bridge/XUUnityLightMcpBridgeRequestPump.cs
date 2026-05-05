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
            var files = inbox.GetFiles("*.json");
            XUUnityLightMcpBridgeRuntimeState.MarkPumpTick(files.Length);

            for (var index = 0; index < files.Length; index++)
            {
                ProcessRequest(files[index], Math.Max(0, files.Length - index - 1));
            }
        }

        static void ProcessRequest(FileInfo file, int remainingPendingRequests)
        {
            XUUnityLightMcpRequest request = null;
            string requestId = "";
            string operationName = "";
            string operationStatus = "error";
            string startedAtUtc = "";

            try
            {
                var json = File.ReadAllText(file.FullName);
                request = JsonUtility.FromJson<XUUnityLightMcpRequest>(json);
                if (request == null || string.IsNullOrWhiteSpace(request.request_id))
                {
                    throw new InvalidOperationException("Request payload is empty or missing request_id.");
                }

                requestId = request.request_id;
                operationName = request.operation ?? "";
                startedAtUtc = DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ");
                XUUnityLightMcpBridgeRuntimeState.MarkRequestStarted(requestId, operationName, remainingPendingRequests + 1);

                if (!XUUnityLightMcpOperationRegistry.TryGet(request.operation, out var operation))
                {
                    XUUnityLightMcpResponseWriter.Write(
                        XUUnityLightMcpResponseWriter.Error(
                            request.request_id,
                            "tool_unsupported",
                            $"Unsupported operation: {request.operation}"
                        )
                    );
                    operationStatus = "tool_unsupported";
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
                        operationStatus = "operation_unavailable";
                        return;
                    }

                    var response = operation.Execute(request);
                    if (response != null)
                    {
                        XUUnityLightMcpResponseWriter.Write(response);
                        operationStatus = response.status ?? "ok";
                    }
                }
            }
            catch (Exception ex)
            {
                requestId = request?.request_id;
                if (string.IsNullOrWhiteSpace(requestId))
                {
                    requestId = Path.GetFileNameWithoutExtension(file.Name);
                }
                XUUnityLightMcpResponseWriter.Write(
                    XUUnityLightMcpResponseWriter.Error(requestId, "bridge_request_failed", ex.Message)
                );
                operationStatus = "bridge_request_failed";
                Debug.LogException(ex);
            }
            finally
            {
                XUUnityLightMcpBridgeRuntimeState.MarkRequestProcessed(
                    requestId,
                    operationName,
                    operationStatus,
                    startedAtUtc,
                    remainingPendingRequests);
                try
                {
                    XUUnityLightMcpBridgeStateWriter.WriteHeartbeat();
                }
                catch
                {
                }

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
