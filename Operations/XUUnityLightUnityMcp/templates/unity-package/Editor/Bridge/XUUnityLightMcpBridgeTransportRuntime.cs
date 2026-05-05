using System;
using System.Collections.Generic;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Threading;
using UnityEngine;
using XUUnity.LightMcp.Editor.Core;

namespace XUUnity.LightMcp.Editor.Bridge
{
    internal static class XUUnityLightMcpBridgeTransportRuntime
    {
        public const string FileIpcTransport = "file_ipc";
        public const string TcpLoopbackTransport = "tcp_loopback";

        static readonly object Gate = new();
        static readonly Queue<PendingLoopbackRequest> PendingLoopbackRequests = new();
        static readonly Dictionary<string, PendingLoopbackRequest> ActiveLoopbackRequests = new();

        static string _requestedTransport = FileIpcTransport;
        static string _activeTransport = FileIpcTransport;
        static string _listenerState = "inactive";
        static string _transportHost = "";
        static int _transportPort;
        static TcpListener _listener;
        static Thread _acceptThread;
        static volatile bool _acceptLoopRunning;

        public static string RequestedTransport
        {
            get
            {
                lock (Gate)
                {
                    return _requestedTransport;
                }
            }
        }

        public static string ActiveTransport
        {
            get
            {
                lock (Gate)
                {
                    return _activeTransport;
                }
            }
        }

        public static string ListenerState
        {
            get
            {
                lock (Gate)
                {
                    return _listenerState;
                }
            }
        }

        public static string TransportHost
        {
            get
            {
                lock (Gate)
                {
                    return _transportHost;
                }
            }
        }

        public static int TransportPort
        {
            get
            {
                lock (Gate)
                {
                    return _transportPort;
                }
            }
        }

        public static void Initialize(XUUnityLightMcpBridgeConfig config)
        {
            Shutdown();

            var requestedTransport = NormalizeTransportName(config?.transport);
            var host = string.IsNullOrWhiteSpace(config?.loopback_host) ? "127.0.0.1" : config.loopback_host.Trim();
            var port = Math.Max(0, config?.loopback_port ?? 0);

            lock (Gate)
            {
                _requestedTransport = requestedTransport;
                _activeTransport = FileIpcTransport;
                _listenerState = "inactive";
                _transportHost = "";
                _transportPort = 0;
            }

            if (string.Equals(requestedTransport, FileIpcTransport, StringComparison.Ordinal))
            {
                return;
            }

            if (!string.Equals(requestedTransport, TcpLoopbackTransport, StringComparison.Ordinal))
            {
                lock (Gate)
                {
                    _listenerState = $"unsupported:{requestedTransport}";
                }
                return;
            }

            try
            {
                StartLoopbackListener(host, port);
            }
            catch (Exception ex)
            {
                lock (Gate)
                {
                    _activeTransport = FileIpcTransport;
                    _listenerState = $"failed:{SanitizeStateToken(ex.Message)}";
                    _transportHost = host;
                    _transportPort = 0;
                }
                Debug.LogWarning($"XUUnityLightMcp loopback transport start failed, falling back to file_ipc: {ex.Message}");
            }
        }

        public static void Shutdown()
        {
            TcpListener listenerToStop = null;
            Thread acceptThreadToJoin = null;
            List<PendingLoopbackRequest> requestsToClose = null;

            lock (Gate)
            {
                _acceptLoopRunning = false;
                listenerToStop = _listener;
                _listener = null;
                acceptThreadToJoin = _acceptThread;
                _acceptThread = null;

                requestsToClose = new List<PendingLoopbackRequest>(PendingLoopbackRequests.Count + ActiveLoopbackRequests.Count);
                while (PendingLoopbackRequests.Count > 0)
                {
                    requestsToClose.Add(PendingLoopbackRequests.Dequeue());
                }

                foreach (var pair in ActiveLoopbackRequests)
                {
                    requestsToClose.Add(pair.Value);
                }

                ActiveLoopbackRequests.Clear();

                if (!string.Equals(_listenerState, "inactive", StringComparison.Ordinal))
                {
                    _listenerState = "stopped";
                }

                _activeTransport = FileIpcTransport;
                _transportHost = "";
                _transportPort = 0;
            }

            try
            {
                listenerToStop?.Stop();
            }
            catch
            {
            }

            if (acceptThreadToJoin != null && acceptThreadToJoin.IsAlive)
            {
                try
                {
                    acceptThreadToJoin.Join(250);
                }
                catch
                {
                }
            }

            if (requestsToClose != null)
            {
                foreach (var request in requestsToClose)
                {
                    TryWriteTransportRestarting(request);
                    ClosePendingRequest(request);
                }
            }
        }

        public static int GetPendingRequestCount()
        {
            lock (Gate)
            {
                return PendingLoopbackRequests.Count;
            }
        }

        public static bool TryDequeueRequest(out XUUnityLightMcpRequest request, out int remainingQueuedRequests)
        {
            lock (Gate)
            {
                if (PendingLoopbackRequests.Count <= 0)
                {
                    request = null;
                    remainingQueuedRequests = 0;
                    return false;
                }

                var pending = PendingLoopbackRequests.Dequeue();
                request = pending.Request;
                remainingQueuedRequests = PendingLoopbackRequests.Count;
                return true;
            }
        }

        public static bool TryWriteResponse(XUUnityLightMcpResponse response)
        {
            if (response == null || string.IsNullOrWhiteSpace(response.request_id))
            {
                return false;
            }

            PendingLoopbackRequest pending;
            lock (Gate)
            {
                if (!ActiveLoopbackRequests.TryGetValue(response.request_id, out pending))
                {
                    return false;
                }

                ActiveLoopbackRequests.Remove(response.request_id);
            }

            try
            {
                using var writer = new StreamWriter(pending.Client.GetStream(), new System.Text.UTF8Encoding(false), 4096, true);
                writer.NewLine = "\n";
                writer.Write(JsonUtility.ToJson(response, true));
                writer.Flush();
                return true;
            }
            catch
            {
                return false;
            }
            finally
            {
                ClosePendingRequest(pending);
            }
        }

        static void StartLoopbackListener(string host, int port)
        {
            if (!IPAddress.TryParse(host, out var ipAddress))
            {
                ipAddress = IPAddress.Loopback;
                host = "127.0.0.1";
            }

            var listener = new TcpListener(ipAddress, port);
            listener.Server.SetSocketOption(SocketOptionLevel.Socket, SocketOptionName.ReuseAddress, true);
            listener.Start();

            lock (Gate)
            {
                _listener = listener;
                _acceptLoopRunning = true;
                _activeTransport = TcpLoopbackTransport;
                _listenerState = "listening";
                _transportHost = host;
                _transportPort = ((IPEndPoint)listener.LocalEndpoint).Port;
                _acceptThread = new Thread(AcceptLoop)
                {
                    IsBackground = true,
                    Name = "XUUnityLightMcpTcpLoopback"
                };
                _acceptThread.Start();
            }
        }

        static void AcceptLoop()
        {
            while (_acceptLoopRunning)
            {
                TcpClient client = null;
                try
                {
                    client = _listener?.AcceptTcpClient();
                    if (client == null)
                    {
                        continue;
                    }

                    ThreadPool.QueueUserWorkItem(_ => ReadClientRequest(client));
                }
                catch (SocketException)
                {
                    if (!_acceptLoopRunning)
                    {
                        return;
                    }

                    lock (Gate)
                    {
                        if (string.Equals(_activeTransport, TcpLoopbackTransport, StringComparison.Ordinal))
                        {
                            _listenerState = "accept_failed";
                        }
                    }
                }
                catch (ObjectDisposedException)
                {
                    return;
                }
                catch (Exception ex)
                {
                    if (!_acceptLoopRunning)
                    {
                        return;
                    }

                    lock (Gate)
                    {
                        if (string.Equals(_activeTransport, TcpLoopbackTransport, StringComparison.Ordinal))
                        {
                            _listenerState = $"accept_failed:{SanitizeStateToken(ex.Message)}";
                        }
                    }
                }
            }
        }

        static void ReadClientRequest(TcpClient client)
        {
            PendingLoopbackRequest pending = null;

            try
            {
                client.NoDelay = true;
                using var reader = new StreamReader(client.GetStream(), System.Text.Encoding.UTF8, false, 4096, true);
                var rawRequest = reader.ReadToEnd();
                var request = JsonUtility.FromJson<XUUnityLightMcpRequest>(rawRequest);
                if (request == null || string.IsNullOrWhiteSpace(request.request_id))
                {
                    WriteDirectError(client, "", "invalid_transport_request", "TCP loopback request payload is empty or missing request_id.");
                    ClosePendingRequest(new PendingLoopbackRequest(client, null));
                    return;
                }

                pending = new PendingLoopbackRequest(client, request);
                lock (Gate)
                {
                    ActiveLoopbackRequests[request.request_id] = pending;
                    PendingLoopbackRequests.Enqueue(pending);
                }
            }
            catch (Exception ex)
            {
                try
                {
                    WriteDirectError(client, "", "invalid_transport_request", ex.Message);
                }
                catch
                {
                }

                ClosePendingRequest(pending ?? new PendingLoopbackRequest(client, null));
            }
        }

        static void WriteDirectError(TcpClient client, string requestId, string code, string message)
        {
            if (client == null)
            {
                return;
            }

            var response = XUUnityLightMcpResponseWriter.Error(requestId, code, message);
            using var writer = new StreamWriter(client.GetStream(), new System.Text.UTF8Encoding(false), 4096, true);
            writer.NewLine = "\n";
            writer.Write(JsonUtility.ToJson(response, true));
            writer.Flush();
        }

        static void ClosePendingRequest(PendingLoopbackRequest pending)
        {
            try
            {
                pending?.Client?.Close();
            }
            catch
            {
            }
        }

        static void TryWriteTransportRestarting(PendingLoopbackRequest pending)
        {
            if (pending?.Client == null)
            {
                return;
            }

            try
            {
                var requestId = pending.Request?.request_id ?? "";
                WriteDirectError(
                    pending.Client,
                    requestId,
                    "transport_restarting",
                    "TCP loopback transport is restarting during Unity bridge lifecycle reset. Retry the request after the next healthy bridge heartbeat."
                );
            }
            catch
            {
            }
        }

        static string NormalizeTransportName(string transport)
        {
            var normalized = string.IsNullOrWhiteSpace(transport)
                ? FileIpcTransport
                : transport.Trim().ToLowerInvariant();
            return normalized;
        }

        static string SanitizeStateToken(string value)
        {
            if (string.IsNullOrWhiteSpace(value))
            {
                return "";
            }

            return value.Replace("\r", " ").Replace("\n", " ").Trim();
        }

        sealed class PendingLoopbackRequest
        {
            public PendingLoopbackRequest(TcpClient client, XUUnityLightMcpRequest request)
            {
                Client = client;
                Request = request;
            }

            public TcpClient Client { get; }
            public XUUnityLightMcpRequest Request { get; }
        }
    }
}
