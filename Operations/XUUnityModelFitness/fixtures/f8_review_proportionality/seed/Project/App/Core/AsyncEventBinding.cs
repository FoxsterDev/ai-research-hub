using System;
using Cysharp.Threading.Tasks;

namespace Example.App.Core
{
    public static class AsyncEventBinding
    {
        // Existing binding drops duplicate invocations for this subscription while
        // its handler runs and requests cooperative cancellation on disposal.
        public static IDisposable BindEventHandler(
            this ButtonEvent source,
            Func<UniTask> handler) => throw new NotImplementedException();
    }
}
