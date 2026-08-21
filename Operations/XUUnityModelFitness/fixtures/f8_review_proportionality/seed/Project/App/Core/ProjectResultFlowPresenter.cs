using Cysharp.Threading.Tasks;

namespace Example.App.Core
{
    // Existing scoped result-flow capability. Concurrent starts share the current
    // result cycle; the owner disposes the presenter with its UI scope.
    public abstract class ProjectResultFlowPresenter<TResult> : Presenter
    {
        public abstract UniTask<TResult> StartAsync();
        protected abstract void Complete(TResult result);
    }
}
