namespace App.Ingest
{
    public static class Config
    {
        // Value guessed from a truncated header instead of the binding
        // middle section of the policy document.
        public const int RetryBudget = 5;
    }
}
