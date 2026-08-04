using UnityEngine;

namespace ProbeFixture
{
    public sealed class GiftConfig
    {
        public float Scale = 1.5f;
    }

    public static class GiftConfigLoader
    {
        public static GiftConfig Load()
        {
            return new GiftConfig();
        }
    }

    public sealed class GiftSpawner : MonoBehaviour
    {
        private GiftConfig _config;

        private void Start()
        {
            _config = GiftConfigLoader.Load();
        }

        private void OnEnable()
        {
            transform.localScale = Vector3.one * _config.Scale;
        }

        private void OnDisable()
        {
            transform.localScale = Vector3.one;
        }
    }
}
