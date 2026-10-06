import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest


MODULE = pathlib.Path(__file__).parents[1] / "opensearch_pulse.py"
spec = importlib.util.spec_from_file_location("opensearch_pulse_sampling", MODULE)
pulse = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = pulse
spec.loader.exec_module(pulse)

FIELDS = {"message_text": "Message", "category": "Category.keyword", "level": "LogLevel.keyword",
          "user": "UUID.keyword", "platform": "Platform.keyword", "debug_mode": "DebugMode",
          "app_id": "AppId.keyword", "version": "GameVersion.keyword",
          "message_keyword": "Message.keyword", "time": "TimeUTC"}


def sampled_funnel():
    return {"key": "ads", "label": "Ads", "stages": [
        {"key": "fill", "label": "Filled", "phrase": "FILLED", "debug_sampled": True},
        {"key": "nofill", "label": "No fill", "phrase": "load failed", "debug_sampled": True},
        {"key": "shown", "label": "Shown", "phrase": "Showing Rewarded"},
    ], "rates": [
        {"label": "no-fill rate", "num": "nofill", "den": ["fill", "nofill"], "good": "low"},
        {"label": "fill reach", "num": "fill", "den": "dau"},
        {"label": "shown reach", "num": "shown", "den": "dau"},
    ]}


def write_config(directory, funnels):
    path = pathlib.Path(directory) / "config.json"
    path.write_text(json.dumps({"sources": [{"index_prefix": "logs-", "key": "A", "name": "A"}],
                                "funnels": funnels}))
    return path


class DebugSamplingTests(unittest.TestCase):
    def test_sampled_stage_filter_requires_the_debug_mode_flag(self):
        sampled = pulse.stage_filter(FIELDS, {"key": "fill", "phrase": "FILLED", "debug_sampled": True})
        plain = pulse.stage_filter(FIELDS, {"key": "fill", "phrase": "FILLED"})
        self.assertIn({"term": {"DebugMode": True}}, sampled["bool"]["must"])
        self.assertNotIn({"term": {"DebugMode": True}}, plain["bool"]["must"])

    def test_day_query_counts_debug_sessions_only_when_a_stage_is_sampled(self):
        with tempfile.TemporaryDirectory() as directory:
            cfg = pulse.load_config(write_config(directory, [sampled_funnel()]))
            body = pulse.day_query(cfg, "A", "2026-10-05")
            self.assertEqual({"term": {"DebugMode": True}}, body["aggs"]["debug_users"]["filter"])
            self.assertIn("by_platform", body["aggs"]["debug_users"]["aggs"])
            plain = sampled_funnel()
            for stage in plain["stages"]:
                stage.pop("debug_sampled", None)
            plain["rates"] = plain["rates"][:1]
            cfg = pulse.load_config(write_config(directory, [plain]))
            self.assertNotIn("debug_users", pulse.day_query(cfg, "A", "2026-10-05")["aggs"])

    def test_sampled_stages_and_rates_use_the_debug_session_denominator(self):
        today = {"funnels_raw": {"ads::fill": {"users": 15, "total": 40},
                                 "ads::nofill": {"users": 5, "total": 10},
                                 "ads::shown": {"users": 600, "total": 900}},
                 "funnels_platform_raw": {"ads::fill": {"iOS": {"users": 9, "total": 20}},
                                          "ads::shown": {"iOS": {"users": 300, "total": 400}}},
                 "platform_users": {"iOS": 500, "Android": 500},
                 "debug_users": 20, "debug_platform_users": {"iOS": 10, "Android": 10}}
        funnel = pulse.assemble_funnels({"funnels": [sampled_funnel()]}, today, 1000, "A")[0]
        stages = {s["key"]: s for s in funnel["stages"]}
        self.assertEqual(75.0, stages["fill"]["pct"])
        self.assertTrue(stages["fill"]["sampled"])
        self.assertEqual("Filled · debug-sampled", stages["fill"]["label"])
        self.assertEqual(60.0, stages["shown"]["pct"])
        self.assertFalse(stages["shown"]["sampled"])
        rates = {r["num_stage"]: r for r in funnel["rates"]}
        self.assertEqual(25.0, rates["nofill"]["pct"])
        self.assertEqual("no-fill rate (debug-sampled)", rates["nofill"]["label"])
        self.assertEqual(20, rates["fill"]["den"])
        self.assertEqual(75.0, rates["fill"]["pct"])
        self.assertEqual(1000, rates["shown"]["den"])
        self.assertFalse(rates["shown"]["sampled"])
        ios = funnel["platforms"]["iOS"]
        self.assertEqual(90.0, {s["key"]: s for s in ios["stages"]}["fill"]["pct"])
        self.assertEqual(10, {r["num_stage"]: r for r in ios["rates"]}["fill"]["den"])

    def test_a_rate_mixing_sampled_and_unsampled_stages_is_rejected(self):
        funnel = sampled_funnel()
        funnel["rates"].append({"label": "ad-gate start", "num": "fill", "den": "shown"})
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                pulse.load_config(write_config(directory, [funnel]))
        rate = pulse._funnel_rates({"rates": [{"label": "x", "num": "fill", "den": "shown"}]},
                                   {"fill": 15, "shown": 600}, 1000, None, 20, {"fill"})[0]
        self.assertIsNone(rate["pct"])
        self.assertEqual("mixed_sampling", rate["data_quality"])

    def test_sampled_stages_cannot_be_split_by_launch_tag(self):
        funnel = sampled_funnel()
        funnel["split_by_tag"] = True
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                pulse.load_config(write_config(directory, [funnel]))


if __name__ == "__main__":
    unittest.main()
