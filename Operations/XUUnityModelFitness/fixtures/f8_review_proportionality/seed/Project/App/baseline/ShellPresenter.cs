namespace Example.App
{
    public sealed class ShellPresenter : Presenter
    {
        public override void Initialize()
        {
            base.Initialize();
            PresentStartupPopupsAsync().Forget();
        }
    }
}
