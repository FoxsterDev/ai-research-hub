using System;

namespace XUUnity.LightMcp.Editor.Bridge
{
    internal static class XUUnityLightMcpBridgeRuntimeState
    {
        static readonly object Gate = new();
        static string _lastPumpUtc = "";
        static string _lastProcessedRequestId = "";
        static int _pendingRequestCount;
        static string _activeRequestId = "";
        static string _activeOperation = "";
        static string _activeOperationStartedUtc = "";
        static string _lastCompletedOperation = "";
        static string _lastCompletedOperationStatus = "";
        static double _lastCompletedOperationDurationSeconds;

        public static string LastPumpUtc
        {
            get
            {
                lock (Gate)
                {
                    return _lastPumpUtc;
                }
            }
        }

        public static string LastProcessedRequestId
        {
            get
            {
                lock (Gate)
                {
                    return _lastProcessedRequestId;
                }
            }
        }

        public static int PendingRequestCount
        {
            get
            {
                lock (Gate)
                {
                    return _pendingRequestCount;
                }
            }
        }

        public static string ActiveRequestId
        {
            get
            {
                lock (Gate)
                {
                    return _activeRequestId;
                }
            }
        }

        public static string ActiveOperation
        {
            get
            {
                lock (Gate)
                {
                    return _activeOperation;
                }
            }
        }

        public static string ActiveOperationStartedUtc
        {
            get
            {
                lock (Gate)
                {
                    return _activeOperationStartedUtc;
                }
            }
        }

        public static string LastCompletedOperation
        {
            get
            {
                lock (Gate)
                {
                    return _lastCompletedOperation;
                }
            }
        }

        public static string LastCompletedOperationStatus
        {
            get
            {
                lock (Gate)
                {
                    return _lastCompletedOperationStatus;
                }
            }
        }

        public static double LastCompletedOperationDurationSeconds
        {
            get
            {
                lock (Gate)
                {
                    return _lastCompletedOperationDurationSeconds;
                }
            }
        }

        public static void MarkPumpTick(int pendingRequestCount)
        {
            lock (Gate)
            {
                _lastPumpUtc = UtcNow();
                _pendingRequestCount = Math.Max(0, pendingRequestCount);
            }
        }

        public static void MarkRequestStarted(string requestId, string operation, int pendingRequestCount)
        {
            lock (Gate)
            {
                _lastPumpUtc = UtcNow();
                _activeRequestId = requestId ?? "";
                _activeOperation = operation ?? "";
                _activeOperationStartedUtc = _lastPumpUtc;
                _pendingRequestCount = Math.Max(0, pendingRequestCount);
            }
        }

        public static void MarkRequestProcessed(
            string requestId,
            string operation,
            string operationStatus,
            string startedAtUtc,
            int remainingPendingRequests)
        {
            lock (Gate)
            {
                _lastPumpUtc = UtcNow();
                if (!string.IsNullOrWhiteSpace(requestId))
                {
                    _lastProcessedRequestId = requestId;
                }

                _lastCompletedOperation = operation ?? "";
                _lastCompletedOperationStatus = operationStatus ?? "";
                _lastCompletedOperationDurationSeconds = CalculateDurationSeconds(startedAtUtc, _lastPumpUtc);
                _activeRequestId = "";
                _activeOperation = "";
                _activeOperationStartedUtc = "";
                _pendingRequestCount = Math.Max(0, remainingPendingRequests);
            }
        }

        static double CalculateDurationSeconds(string startedAtUtc, string completedAtUtc)
        {
            if (string.IsNullOrWhiteSpace(startedAtUtc))
            {
                return 0.0d;
            }

            if (!DateTime.TryParse(startedAtUtc, null, System.Globalization.DateTimeStyles.AdjustToUniversal | System.Globalization.DateTimeStyles.AssumeUniversal, out var started))
            {
                return 0.0d;
            }

            if (!DateTime.TryParse(completedAtUtc, null, System.Globalization.DateTimeStyles.AdjustToUniversal | System.Globalization.DateTimeStyles.AssumeUniversal, out var completed))
            {
                completed = DateTime.UtcNow;
            }

            return Math.Round(Math.Max(0.0d, (completed - started).TotalSeconds), 6);
        }

        static string UtcNow()
        {
            return DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ");
        }
    }
}
