using System;
using System.Collections.Generic;

namespace Example.App.Invites
{
    public sealed class UnityReferralAdapter
    {
        private readonly object _pendingReferralGate = new object();
        private readonly Queue<string> _pendingReferralCodes = new Queue<string>();

        public event Action<string> ReferralReceived;

        /// <summary>
        /// The vendor contract invokes this callback on a worker thread.
        /// </summary>
        public void OnReferralReceivedFromWorkerThread(string referralCode)
        {
            lock (_pendingReferralGate)
            {
                _pendingReferralCodes.Enqueue(referralCode);
            }
        }

        /// <summary>
        /// The Unity player loop calls this method once per update.
        /// </summary>
        public bool TryDrainOnUnityPlayerLoop()
        {
            string referralCode;
            lock (_pendingReferralGate)
            {
                if (_pendingReferralCodes.Count == 0)
                {
                    return false;
                }

                referralCode = _pendingReferralCodes.Dequeue();
            }

            ReferralReceived?.Invoke(referralCode);
            return true;
        }
    }
}
