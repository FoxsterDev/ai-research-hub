using Cysharp.Threading.Tasks;

namespace App.Async
{
    public sealed class AsyncPump
    {
        public async UniTask DrainAsync()
        {
            await UniTask.SwitchToThreadPool();
        }
    }
}
