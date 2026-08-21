using System.Threading;
using Cysharp.Threading.Tasks;

namespace Example.App.Invites
{
    public sealed class InvitePopupPresenter : Presenter
    {
        private UniTaskCompletionSource<bool> _completion;
        private int _started;
        private int _actionRunning;

        public UniTask<bool> StartAsync()
        {
            if (Interlocked.Exchange(ref _started, 1) != 0)
                return _completion.Task;

            _completion = new UniTaskCompletionSource<bool>();
            SetActiveAsync(true).Forget();
            return _completion.Task;
        }

        private async UniTask ShareAsync()
        {
            if (Interlocked.Exchange(ref _actionRunning, 1) != 0)
                return;

            try { await NativeShare.OpenAsync(); }
            finally { Interlocked.Exchange(ref _actionRunning, 0); }
        }
    }
}
