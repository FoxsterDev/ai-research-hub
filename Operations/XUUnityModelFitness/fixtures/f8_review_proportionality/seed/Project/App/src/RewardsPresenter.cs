using System;
using Cysharp.Threading.Tasks;

namespace Example.App.Rewards
{
    public sealed class RewardsPresenter : Presenter
    {
        private readonly InviteBannerPresenter _inviteBanner;

        public RewardsPresenter(Func<UniTask> navigateAfterCollect)
        {
            _inviteBanner = new InviteBannerPresenter(navigateAfterCollect);
        }
    }
}
