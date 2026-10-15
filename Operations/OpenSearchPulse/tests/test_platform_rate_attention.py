import importlib.util
import pathlib
import sys
import unittest


MODULE = pathlib.Path(__file__).parents[1] / "opensearch_pulse.py"
spec = importlib.util.spec_from_file_location("opensearch_pulse_platform_attention", MODULE)
pulse = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = pulse
spec.loader.exec_module(pulse)


def funnel_cfg(min_den=50):
    return {"funnels": [{
        "key": "provider", "label": "Provider off",
        "stages": [{"key": "off", "label": "Provider skipped", "phrase": "provider skipped"}],
        "rates": [{"label": "provider off", "num": "off", "den": "dau", "good": "low",
                   "good_at": 1, "bad_at": 5, "attention": "platform", "min_den": min_den}],
    }]}


def today(android_dau, android_off, version_dau, ios_dau=1000):
    return {
        "funnels_raw": {"provider::off": {"users": android_off, "total": android_off * 2}},
        "funnels_platform_raw": {"provider::off": {
            "Android": {"users": android_off, "total": android_off * 2}}},
        "funnels_version_raw": {"provider::off": {"Android": {
            "2.0.0": {"users": android_off, "total": android_off * 2}}}},
        "platform_users": {"iOS": ios_dau, "Android": android_dau},
        "versions_detail": [
            {"ver": "2.0.0", "plat": "Android", "dau": version_dau},
            {"ver": "1.9.0", "plat": "Android", "dau": android_dau - version_dau},
            {"ver": "1.9.0", "plat": "IPhonePlayer", "dau": ios_dau},
        ],
    }


def attention(cfg, day):
    funnels = pulse.assemble_funnels(cfg, day, sum(day["platform_users"].values()), "APP2")
    project = {"name": "Second App", "status": "healthy", "funnels": funnels}
    return pulse.build_attention({"projects": [project], "errors": [], "incidents": []})


class PlatformRateAttentionTests(unittest.TestCase):
    def test_platform_breach_is_an_alert_even_when_the_project_rate_is_diluted(self):
        att = attention(funnel_cfg(), today(141, 16, 22))
        self.assertEqual(len(att), 1, att)
        self.assertEqual(att[0]["sev"], "degraded")
        self.assertEqual(att[0]["proj"], "Second App")
        self.assertEqual(att[0]["text"],
                         "Provider off · Android: provider off 11.3% (16/141 users) — ≥ alert 5%; "
                         "v2.0.0 73% (16/22)")

    def test_watch_zone_between_the_two_bars(self):
        att = attention(funnel_cfg(), today(141, 3, 3))
        self.assertEqual([a["sev"] for a in att], ["watch"])
        self.assertIn("provider off 2.1% (3/141 users) — > watch 1%", att[0]["text"])

    def test_inside_the_good_zone_raises_nothing(self):
        self.assertEqual(attention(funnel_cfg(), today(1000, 10, 10)), [])

    def test_platform_below_min_den_is_not_judged(self):
        self.assertEqual(attention(funnel_cfg(min_den=50), today(40, 20, 20)), [])

    def test_rate_without_platform_scope_keeps_the_project_level_rule(self):
        cfg = funnel_cfg()
        rate = cfg["funnels"][0]["rates"][0]
        del rate["attention"], rate["min_den"]
        att = attention(cfg, today(141, 80, 80))
        self.assertEqual([a["sev"] for a in att], ["watch"])
        self.assertEqual(att[0]["text"], "Provider off: provider off 7% (limit ≤5%)")


if __name__ == "__main__":
    unittest.main()
