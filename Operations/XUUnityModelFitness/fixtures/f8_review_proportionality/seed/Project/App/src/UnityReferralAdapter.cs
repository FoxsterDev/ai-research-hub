using System;

namespace Example.App.Invites
{
    public sealed class UnityReferralAdapter
    {
        // The vendor invokes this method through UnitySendMessage. It therefore
        // enters managed code on the Unity player loop.
        public event Action<string> ReferralReceived;

        public void OnReferralReceived(string referralCode)
        {
            ReferralReceived?.Invoke(referralCode);
        }
    }
}
