using System;

namespace App.Telemetry
{
    public sealed class TelemetryUploader
    {
        private readonly IIngestClient _client;

        public TelemetryUploader(IIngestClient client)
        {
            _client = client;
        }

        public void Send(TelemetryBatch batch)
        {
            RetryPolicy.PublicFixed(3).Execute(() => _client.Post(batch));
        }
    }
}
