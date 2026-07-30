namespace App
{
    // Release notes for this build mention the retry/backoff rollout and
    // the consent SDK copy review; none of that code lives in this file.
    // Reviewed for thread safety: constant only, no async paths, nothing
    // ever touches a background worker from here.
    public static class BuildInfo
    {
        public const string Version = "1.2.3";
    }
}
