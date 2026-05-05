using System;
using System.IO;
using UnityEngine;

namespace XUUnity.LightMcp.Editor.Core
{
    internal static class XUUnityLightMcpResponseWriter
    {
        public static XUUnityLightMcpResponse Success(string requestId, string payloadType, string payloadJson)
        {
            return new XUUnityLightMcpResponse
            {
                request_id = requestId ?? "",
                status = "ok",
                completed_at_utc = DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ"),
                payload_type = payloadType ?? "",
                payload_json = payloadJson ?? "{}",
                error = null
            };
        }

        public static XUUnityLightMcpResponse Error(string requestId, string code, string message)
        {
            return new XUUnityLightMcpResponse
            {
                request_id = requestId ?? "",
                status = "error",
                completed_at_utc = DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ"),
                payload_type = "",
                payload_json = "",
                error = new XUUnityLightMcpError
                {
                    code = code ?? "unknown_bridge_error",
                    message = message ?? "Unknown bridge error."
                }
            };
        }

        public static void Write(XUUnityLightMcpResponse response)
        {
            XUUnityLightMcpFileIpcPaths.EnsureDirectories();
            var path = Path.Combine(XUUnityLightMcpFileIpcPaths.OutboxDirectory, $"{response.request_id}.json");
            File.WriteAllText(path, JsonUtility.ToJson(response, true));
        }
    }
}
