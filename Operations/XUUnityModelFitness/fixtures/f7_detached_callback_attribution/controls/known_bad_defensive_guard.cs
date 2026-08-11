using System;

namespace App.Media
{
    public sealed class IconCache
    {
        private readonly IDownloader _downloader;
        private readonly IFrameScheduler _scheduler;

        public IconCache(IDownloader downloader, IFrameScheduler scheduler)
        {
            _downloader = downloader;
            _scheduler = scheduler;
        }

        public byte[] Download(string url, CancellationScope parent)
        {
            using var deadline = CancellationScope.LinkedTo(parent);
            try
            {
                _scheduler.CancelAfter(deadline, TimeSpan.FromSeconds(15));
                return _downloader.Fetch(url, deadline.Token);
            }
            catch (ObjectDisposedException)
            {
                return Array.Empty<byte>();
            }
        }
    }
}
