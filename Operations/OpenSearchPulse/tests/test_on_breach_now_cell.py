import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest


MODULE = pathlib.Path(__file__).parents[1] / "opensearch_pulse.py"
spec = importlib.util.spec_from_file_location("opensearch_pulse_on_breach", MODULE)
pulse = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = pulse
spec.loader.exec_module(pulse)


def provider_funnel(**extra):
    return {"key": "provider", "label": "Provider off",
            "stages": [{"key": "off", "label": "Provider skipped", "phrase": "provider skipped"}],
            "rates": [{"label": "provider off", "num": "off", "den": "dau", "good": "low",
                       "good_at": 1, "bad_at": 5, "attention": "platform", "min_den": 50}],
            **extra}


ON_BREACH = {"key": "provider_off", "label": "Provider off", "display_label": "provider off",
             "kind": "funnel_rate", "funnel": "provider", "rate": "provider off",
             "now_cell": "on_breach"}


def day(platform_users, off_by_platform):
    total = sum(off_by_platform.values())
    return {
        "funnels_raw": {"provider::off": {"users": total, "total": total}} if total else {},
        "funnels_platform_raw": {"provider::off": {
            p: {"users": n, "total": n} for p, n in off_by_platform.items() if n}},
        "funnels_version_raw": {},
        "platform_users": platform_users,
        "versions_detail": [],
    }


def project(key, name, platform_users, off_by_platform, fn):
    cfg = {"funnels": [fn]}
    dau = sum(platform_users.values())
    return {"key": key, "name": name, "status": "healthy", "dau": dau,
            "platform_users": platform_users, "err_per_user": 0.5,
            "err_per_user_delta_pct": 0.0, "operations": [], "impact": [],
            "funnels": pulse.assemble_funnels(cfg, day(platform_users, off_by_platform), dau, key),
            "funnel_applicability": {fn["key"]: pulse.funnel_applies(fn, key)}}


def report(projects):
    r = {"projects": projects, "errors": [], "incidents": [],
         "brand": {"org": "Example Org", "product": "Production Pulse"},
         "overview": {"portfolio_name": "Example", "default_family": "Example",
                      "family_by_app": {}, "secondary_metrics": [ON_BREACH]},
         "report_day": "2026-10-14", "baseline_days": 3, "generated_utc": "2026-10-15 05:30 UTC"}
    r["health"] = pulse.build_health(r, None)
    return r


def row(r, key):
    return next(x for x in r["health"]["rows"] if x["key"] == key)


def card(text, name):
    return text.split(f"*{name}*", 1)[1].split("────", 1)[0]


def now_line(text, platform):
    lines = text.splitlines()
    head = next(i for i, line in enumerate(lines) if line.startswith(f"  *{platform}*"))
    return lines[head + 1]


class ZeroWhenAbsentTests(unittest.TestCase):
    def test_an_absent_signal_is_dropped_by_default(self):
        funnels = pulse.assemble_funnels({"funnels": [provider_funnel()]},
                                         day({"iOS": 600, "Android": 400}, {}), 1000, "APP1")
        self.assertEqual(funnels, [])

    def test_an_absent_signal_reads_as_a_measured_zero_when_declared(self):
        funnels = pulse.assemble_funnels({"funnels": [provider_funnel(zero_when_absent=True)]},
                                         day({"iOS": 600, "Android": 400}, {}), 1000, "APP1")
        self.assertTrue(funnels[0]["zero_filled"])
        android = funnels[0]["platforms"]["Android"]["rates"][0]
        self.assertEqual((android["num"], android["den"], android["pct"]), (0, 400, 0.0))

    def test_an_excluded_app_is_not_applicable_rather_than_zero(self):
        fn = provider_funnel(zero_when_absent=True, exclude_apps=["OTHER"])
        self.assertEqual(pulse.assemble_funnels({"funnels": [fn]},
                                                day({"iOS": 600}, {}), 600, "OTHER"), [])
        self.assertFalse(pulse.funnel_applies(fn, "OTHER"))
        self.assertTrue(pulse.funnel_applies(fn, "APP1"))

    def test_zero_filled_funnels_stay_out_of_the_technical_funnel_sections(self):
        p = project("APP1", "First App", {"iOS": 600, "Android": 400}, {},
                    provider_funnel(zero_when_absent=True))
        self.assertEqual(pulse.funnels_section(p), "")
        self.assertEqual(pulse.funnels_summary({"projects": [p]}), "")


class OnBreachNowCellTests(unittest.TestCase):
    def setUp(self):
        fn = provider_funnel(zero_when_absent=True, exclude_apps=["OTHER"])
        self.report = report([
            project("APP2", "Second App", {"iOS": 755, "Android": 141}, {"Android": 16}, fn),
            project("APP1", "First App", {"iOS": 600, "Android": 400}, {}, fn),
            project("OTHER", "Other Client", {"iOS": 500, "Android": 300}, {}, fn),
        ])
        self.slack = pulse.render_status_slack(self.report)
        self.md = pulse.render_status_md(self.report)

    def test_an_alert_prints_its_cell_and_paints_the_project_red(self):
        self.assertIn("🔴 *Second App*", self.slack)
        second = card(self.slack, "Second App")
        self.assertTrue(now_line(second, "Android").endswith(" · provider off *11.3% 🔴*"), second)
        self.assertNotIn("provider off", now_line(second, "iOS"))
        triggers = row(self.report, "APP2")["overview_triggers"]
        self.assertEqual([(t["scope"], t["metric"], t["status"]) for t in triggers],
                         [("Android", "provider_off", "degraded")])

    def test_the_overview_md_names_the_numerator_and_denominator(self):
        self.assertIn("- Android Provider off: **16 users** of 141 (11.3%) · degraded", self.md)
        self.assertNotIn("- iOS Provider off:", self.md)

    def test_a_healthy_platform_prints_no_cell_and_no_coverage_gap(self):
        self.assertNotIn("provider off", card(self.slack, "First App"))
        self.assertIn("• *First App*", self.slack)
        self.assertEqual(row(self.report, "APP1")["overview_status"], "healthy")
        section = self.md.split("### First App")[1].split("###")[0]
        self.assertIn("Provider off 0%", section)
        self.assertNotIn("Provider off", section.split("Coverage gaps:")[1])

    def test_an_excluded_client_is_not_measured(self):
        metric = row(self.report, "OTHER")["secondary_metrics"][0]
        self.assertEqual((metric["available"], metric["availability"]), (False, "not_applicable"))
        self.assertNotIn("provider off", card(self.slack, "Other Client"))

    def test_the_diluted_project_level_rate_never_sets_a_status(self):
        metric = row(self.report, "APP2")["secondary_metrics"][0]
        self.assertEqual(metric["value"], 1.8)
        self.assertEqual(metric["status"], "nodata")

    def test_the_watch_zone_is_bold_without_a_colour_marker(self):
        r = report([project("APP2", "Second App", {"iOS": 755, "Android": 141}, {"Android": 3},
                            provider_funnel(zero_when_absent=True))])
        text = pulse.render_status_slack(r)
        self.assertTrue(now_line(card(text, "Second App"), "Android")
                        .endswith(" · provider off *2.1%*"), text)
        self.assertNotIn("🔴", text.split("*Projects*")[1])
        self.assertEqual(row(r, "APP2")["overview_status"], "watch")

    def test_a_platform_below_min_den_prints_nothing(self):
        r = report([project("APP2", "Second App", {"iOS": 755, "Android": 40}, {"Android": 20},
                            provider_funnel(zero_when_absent=True))])
        self.assertNotIn("provider off", pulse.render_status_slack(r))
        self.assertEqual(row(r, "APP2")["platform_overview"]["Android"]["flows"][0]["status"],
                         "nodata")


class NowCellConfigTests(unittest.TestCase):
    def test_an_unknown_now_cell_mode_is_rejected(self):
        cfg = {"sources": [{"index_prefix": "x-"}],
               "overview": {"secondary_metrics": [dict(ON_BREACH, now_cell="always")]}}
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(cfg, f)
        with self.assertRaisesRegex(ValueError, "now_cell"):
            pulse.load_config(f.name)
        pathlib.Path(f.name).unlink()


if __name__ == "__main__":
    unittest.main()
