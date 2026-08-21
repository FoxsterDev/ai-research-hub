using System.Threading;
using Cysharp.Threading.Tasks;

namespace Example.App
{
    public sealed class ShellPresenter : Presenter
    {
        private readonly SemaphoreSlim _postStartupPopupGate = new(1, 1);
        private readonly Invites.UnityReferralAdapter _adapter = new();
        private readonly Invites.InviteService _inviteService = new();

        public override void Initialize()
        {
            base.Initialize();
            _adapter.ReferralReceived += OnReferralReceived;
            PresentStartupPopupsAsync().Forget();
        }

        private void OnReferralReceived(string code)
        {
            PresentReferralAsync(code).Forget();
        }

        private async UniTask PresentStartupPopupsAsync()
        {
            await _postStartupPopupGate.WaitAsync();
            try
            {
                await CollectPersonalGiftAsync();
                await PresentReferralIfPendingAsync();
                await PresentRemotePopupAsync();
            }
            finally { _postStartupPopupGate.Release(); }
        }

        private async UniTask PresentReferralAsync(string code)
        {
            await _postStartupPopupGate.WaitAsync();
            try
            {
                await _inviteService.RedeemAsync(code);
                await PresentRewardAndReconcileBalanceAsync();
            }
            finally { _postStartupPopupGate.Release(); }
        }

        public UniTask NavigateToCollectedInviteCashAsync() =>
            NavigateToRewardsAndHighlightInviteBannerAsync();
    }
}
