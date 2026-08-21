using System;
using Cysharp.Threading.Tasks;

namespace Example.App.Core
{
    // Existing capability for callers that must join one underlying operation.
    public sealed class SharedExecution<T>
    {
        public SharedExecution(Func<UniTask<T>> factory) { }
        public UniTask<T> ExecuteAsync() => throw new NotImplementedException();
    }
}
