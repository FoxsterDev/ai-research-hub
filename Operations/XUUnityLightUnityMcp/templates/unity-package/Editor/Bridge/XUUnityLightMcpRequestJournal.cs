using System;
using System.IO;
using UnityEngine;
using XUUnity.LightMcp.Editor.Core;

namespace XUUnity.LightMcp.Editor.Bridge
{
    internal static class XUUnityLightMcpRequestJournal
    {
        public static void WriteBootstrapAttached()
        {
            WriteEvent(new XUUnityLightMcpRequestJournalEvent
            {
                event_type = "bridge_bootstrap_attached",
                event_at_utc = UtcNow(),
            });
        }

        public static void WriteRequestStarted(string requestId, string operation, string startedAtUtc, int pendingRequestCount)
        {
            WriteEvent(new XUUnityLightMcpRequestJournalEvent
            {
                event_type = "request_started",
                event_at_utc = UtcNow(),
                request_id = requestId ?? "",
                operation = operation ?? "",
                pending_request_count = Math.Max(0, pendingRequestCount),
                started_at_utc = startedAtUtc ?? "",
            });
        }

        public static void WriteRequestCompleted(
            string requestId,
            string operation,
            string operationStatus,
            string startedAtUtc,
            string completedAtUtc,
            int pendingRequestCount)
        {
            WriteEvent(new XUUnityLightMcpRequestJournalEvent
            {
                event_type = "request_completed",
                event_at_utc = UtcNow(),
                request_id = requestId ?? "",
                operation = operation ?? "",
                operation_status = operationStatus ?? "",
                pending_request_count = Math.Max(0, pendingRequestCount),
                started_at_utc = startedAtUtc ?? "",
                completed_at_utc = completedAtUtc ?? "",
            });
        }

        public static void WriteRequestAbandoned(
            XUUnityLightMcpActiveRequestSnapshot snapshot,
            string reason,
            bool retryable)
        {
            if (snapshot == null || string.IsNullOrWhiteSpace(snapshot.request_id))
            {
                return;
            }

            WriteEvent(new XUUnityLightMcpRequestJournalEvent
            {
                event_type = "request_abandoned",
                event_at_utc = UtcNow(),
                request_id = snapshot.request_id ?? "",
                operation = snapshot.operation ?? "",
                started_at_utc = snapshot.started_at_utc ?? "",
                reason = reason ?? "",
                retryable = retryable,
                reclassified_status = retryable ? "retryable_after_lifecycle_reset" : "abandoned_after_lifecycle_reset",
            });
        }

        public static void WriteRequestReclassified(
            string requestId,
            string operation,
            string reason,
            bool retryable,
            string reclassifiedStatus,
            int previousBridgeGeneration,
            string previousBridgeSessionId)
        {
            WriteEvent(new XUUnityLightMcpRequestJournalEvent
            {
                event_type = "request_reclassified",
                event_at_utc = UtcNow(),
                request_id = requestId ?? "",
                operation = operation ?? "",
                reason = reason ?? "",
                retryable = retryable,
                reclassified_status = reclassifiedStatus ?? "",
                previous_bridge_generation = previousBridgeGeneration,
                previous_bridge_session_id = previousBridgeSessionId ?? "",
            });
        }

        static void WriteEvent(XUUnityLightMcpRequestJournalEvent payload)
        {
            XUUnityLightMcpFileIpcPaths.EnsureDirectories();

            payload.project_root = XUUnityLightMcpFileIpcPaths.ProjectRootPath;
            payload.bridge_session_id = XUUnityLightMcpBridgeRuntimeState.BridgeSessionId;
            payload.bridge_generation = XUUnityLightMcpBridgeRuntimeState.BridgeGeneration;
            payload.event_id = BuildEventId(payload.event_type);

            var path = Path.Combine(XUUnityLightMcpFileIpcPaths.RequestJournalDirectory, $"{payload.event_id}.json");
            File.WriteAllText(path, JsonUtility.ToJson(payload, true));
            XUUnityLightMcpBridgeRuntimeState.MarkJournalEvent(path);
        }

        static string BuildEventId(string eventType)
        {
            var compactUtc = DateTime.UtcNow.ToString("yyyyMMddTHHmmssfffZ");
            return $"{compactUtc}_{Guid.NewGuid():N}_{Sanitize(eventType)}";
        }

        static string Sanitize(string value)
        {
            var trimmed = string.IsNullOrWhiteSpace(value) ? "event" : value.Trim();
            foreach (var invalid in Path.GetInvalidFileNameChars())
            {
                trimmed = trimmed.Replace(invalid, '_');
            }

            return trimmed.Replace(' ', '_');
        }

        static string UtcNow()
        {
            return DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ");
        }
    }
}
