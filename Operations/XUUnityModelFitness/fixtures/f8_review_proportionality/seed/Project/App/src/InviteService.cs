using System.Threading;
using Cysharp.Threading.Tasks;

namespace Example.App.Invites
{
    public sealed class InviteService
    {
        private readonly object _snapshotGate = new();
        private readonly IInviteApi _api = new InviteApi();
        private InviteSnapshot _latest;
        private int _redemptionRunning;

        public async UniTask<InviteSnapshot> GetSnapshotAsync()
        {
            var snapshot = await _api.GetSnapshotAsync();
            lock (_snapshotGate)
            {
                _latest = snapshot;
                return _latest;
            }
        }

        public async UniTask RedeemAsync(string code)
        {
            if (Interlocked.Exchange(ref _redemptionRunning, 1) != 0)
                return;

            try { await _api.RedeemAsync(code); }
            finally { Interlocked.Exchange(ref _redemptionRunning, 0); }
        }
    }

    public interface IInviteApi
    {
        UniTask<InviteSnapshot> GetSnapshotAsync();
        UniTask RedeemAsync(string code);
    }

    public sealed class InviteApi : IInviteApi
    {
        public UniTask<InviteSnapshot> GetSnapshotAsync() =>
            RequestSender.GetAsync<InviteSnapshot>("invite/snapshot");

        public UniTask RedeemAsync(string code) =>
            RequestSender.PostAsync("invite/redeem", code);
    }
}
