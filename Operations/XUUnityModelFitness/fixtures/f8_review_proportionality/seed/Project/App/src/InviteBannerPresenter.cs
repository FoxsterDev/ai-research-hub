using System.Threading;
using Cysharp.Threading.Tasks;

namespace Example.App.Invites
{
    public sealed class InviteBannerPresenter : Presenter
    {
        private readonly SemaphoreSlim _bankOperationGate = new(1, 1);
        private int _refreshRunning;

        // A late GET must not overwrite the balance returned by CollectAsync.
        public async UniTask RefreshAsync()
        {
            if (Interlocked.Exchange(ref _refreshRunning, 1) != 0)
                return;

            await _bankOperationGate.WaitAsync();
            try { View.SetSnapshot(await Service.GetSnapshotAsync()); }
            finally
            {
                _bankOperationGate.Release();
                Interlocked.Exchange(ref _refreshRunning, 0);
            }
        }

        public async UniTask CollectAsync()
        {
            await _bankOperationGate.WaitAsync();
            try { View.SetSnapshot(await Service.CollectAsync()); }
            finally { _bankOperationGate.Release(); }
        }
    }
}
