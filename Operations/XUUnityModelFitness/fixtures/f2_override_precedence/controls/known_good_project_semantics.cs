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
            RetryPolicy.ProjectJittered(5, 250).Execute(() => _client.Post(batch));
        }
    }
}
