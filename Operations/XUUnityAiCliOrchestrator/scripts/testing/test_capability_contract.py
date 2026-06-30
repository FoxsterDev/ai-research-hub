import unittest

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "templates"))

import runner


class CapabilityContractTests(unittest.TestCase):
    def test_default_config_is_subscription_first(self):
        config = runner.DEFAULT_CONFIG
        self.assertEqual(config["defaultPolicy"]["priority"], "subscription_quota_first")
        self.assertEqual(config["defaultPolicy"]["authPolicy"], "official_login_only")
        self.assertFalse(config["defaultPolicy"]["allowApiBilling"])

    def test_subscription_providers_disallow_api_keys(self):
        for provider in runner.DEFAULT_CONFIG["providers"]:
            if provider["kind"] == "subscription_cli":
                self.assertFalse(provider["apiKeyAuthAllowed"])
                self.assertIn(provider["costMode"], {"subscription_quota", "subscription_or_account_quota"})

    def test_metered_api_stub_is_disabled(self):
        provider = next(item for item in runner.DEFAULT_CONFIG["providers"] if item["id"] == "metered_api_stub")
        self.assertFalse(provider["enabled"])
        self.assertEqual(provider["kind"], "metered_api")


if __name__ == "__main__":
    unittest.main()

