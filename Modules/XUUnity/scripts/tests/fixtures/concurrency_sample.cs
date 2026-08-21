using System.Threading;

internal sealed class ConcurrencySample
{
    private int _isRunning;

    public bool TryStart()
    {
        return Interlocked.Exchange(ref _isRunning, 1) == 0;
    }
}
