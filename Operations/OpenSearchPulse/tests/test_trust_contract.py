import importlib.util
import pathlib
import sys
import tempfile
import unittest
import json
from unittest import mock


MODULE = pathlib.Path(__file__).parents[1] / "opensearch_pulse.py"
spec = importlib.util.spec_from_file_location("opensearch_pulse_trust", MODULE)
pulse = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = pulse
spec.loader.exec_module(pulse)
import report_safety


class StaticClient(pulse.Client):
    def __init__(self, result):
        super().__init__("https://example.invalid", {})
        self.result = result

    def _req(self, path, body=None):
        return self.result


class TrustContractTests(unittest.TestCase):
    def test_http_200_timeout_is_not_a_successful_search(self):
        client = StaticClient({"timed_out": True, "_shards": {"failed": 0},
                               "aggregations": {}})
        with self.assertRaises(pulse.PartialSearchError):
            client.search("logs-2026-08-26", {"size": 0})

    def test_http_200_failed_shards_are_not_a_successful_search(self):
        client = StaticClient({"timed_out": False,
                               "_shards": {"failed": 2, "failures": [{"reason": "token=secret"}]},
                               "aggregations": {}})
        with self.assertRaisesRegex(pulse.PartialSearchError, r"failed_shards=2"):
            client.search("logs-2026-08-26", {"size": 0})

    def test_missing_aggregations_fail_only_when_the_query_requested_them(self):
        response = {"timed_out": False, "_shards": {"failed": 0},
                    "hits": {"hits": [], "total": {"value": 0}}}
        client = StaticClient(response)
        with self.assertRaisesRegex(pulse.PartialSearchError, "no aggregations"):
            client.search("logs-2026-08-26", {"size": 0, "aggs": {"dau": {}}})
        self.assertIs(client.search("logs-2026-08-26", {"size": 100})["hits"],
                      response["hits"])

    def test_reason_severity_controls_joined_health(self):
        project = {"key": "A", "name": "Example", "status": "healthy", "dau": 1000,
                   "platform_users": {"iOS": 500}, "funnels": [], "operations": [{
                       "label": "Payments", "flows": [{"label": "Checkout", "status": "alert",
                       "terminal_failure_rate_pct": 80.0, "retry_reach_pct_dau": 2.0}]}]}
        report = {"projects": [project], "errors": []}
        row = pulse.build_health(report, None)["rows"][0]
        self.assertEqual(row["status"], "degraded")
        self.assertTrue(any("Checkout" in reason["text"] for reason in row["reasons"]))

    def test_status_message_keeps_every_tracked_app_at_scale(self):
        rows = [{"key": f"a{i}", "name": f"Example {i:02d}", "status": "watch",
                 "reasons": [{"sev": "watch", "text": "needs review", "side": "logs"}],
                 "dau": 100 + i} for i in range(50)]
        report = {"brand": {"org": "Example", "product": "Pulse"},
                  "report_day": "2026-08-26", "generated_utc": "now", "projects": [],
                  "health": {"rows": rows, "counts": {"watch": 50},
                             "store_unavailable": "test"}}
        parts = pulse.render_status_slack_parts(report)
        self.assertGreater(len(parts), 1)
        self.assertTrue(all(pulse.slack_len(part) <= pulse.SLACK_ONE_MESSAGE_BUDGET
                            for part in parts))
        text = "\n".join(parts)
        for row in rows:
            self.assertIn(f"*{row['name']}*", text)

    def test_redaction_covers_signed_urls_bearer_and_pem(self):
        raw = ("Bearer abcdefghijklmnop https://host/path?X-Amz-Signature=sensitive "
               "-----BEGIN PRIVATE KEY-----privatebytes")
        clean = pulse.redact(raw)
        for secret in ("abcdefghijklmnop", "sensitive", "privatebytes"):
            self.assertNotIn(secret, clean)

    def test_funnel_breakdown_is_redacted_at_ingestion(self):
        cfg = {"funnels": [{"key": "startup", "label": "Startup", "stages": [{
            "key": "failed", "label": "Failed", "breakdown": {"top": 5}}]}]}
        today = {"funnels_raw": {"startup::failed": {"users": 1, "total": 1}},
                 "funnel_breakdowns": {"startup::failed": [{
                     "msg": "failed https://host/path?token=sensitive", "users": 1,
                     "total": 1}]}}
        result = pulse.assemble_funnels(cfg, today, 10, "A")
        reason = result[0]["breakdowns"][0]["reasons"][0]["reason"]
        self.assertNotIn("sensitive", reason)

    def test_corrupt_baseline_candidate_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            pathlib.Path(directory, "pulse_2026-08-25.json").write_text("{truncated")
            history, dates, meta = pulse.load_prior_reports(
                directory, "pulse", "2026-08-26", return_meta=True)
        self.assertEqual(history, {})
        self.assertEqual(dates, [])
        self.assertEqual(meta["corrupt_candidates"][0]["file"], "pulse_2026-08-25.json")

    def test_atomic_json_redacts_values_and_remains_valid_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory, "report.json")
            report_safety.atomic_write_json(path, {"reason": 'token=secret"quoted'})
            loaded = json.loads(path.read_text())
            self.assertNotIn("secret", loaded["reason"])
            self.assertEqual(list(path.parent.glob(".report.json.*")), [])

    def test_missing_required_index_preserves_expected_project_and_blocks_green(self):
        cfg = {"baseline_days": 3, "operation_baseline_days": 0, "operations": [],
               "sources": [{"index_prefix": "logs-", "split_by_app_id": True,
                            "app_names": {"A": "Example A", "B": "Example B"}}],
               "max_workers": 2, "funnel_top_dau": None, "funnels": [],
               "brand": {"org": "Example", "product": "Pulse"},
               "funnels_summary_note": "", "md_observations": [], "signals": {},
               "fresh_launch_tag": ""}
        client = StaticClient({})
        with tempfile.TemporaryDirectory() as directory, \
             mock.patch.object(pulse, "discover_indices", return_value={}):
            report = pulse.build_report(client, cfg, "2026-08-26", directory, "pulse")
        self.assertEqual(report["overall_status"], "degraded")
        self.assertEqual(report["trust"]["expected_projects"], 2)
        self.assertEqual(report["trust"]["failed_projects"], 2)
        self.assertFalse(report["trust"]["complete"])

    def test_zero_dau_after_a_measured_baseline_is_degraded_not_removed(self):
        today = {"dau": 0, "err_total": 0, "err_users": 0, "warn_total": 0,
                 "warn_users": 0, "top_errors": [], "top_warns": [],
                 "errors_by_cat": [], "warns_by_cat": [], "versions": [],
                 "versions_detail": [], "platforms": [], "signals": {}, "funnels_raw": {}}
        previous = {"err_per_user": 1.0, "warn_per_user": 1.0, "dau": 1000,
                    "status": "healthy", "top_errors": [], "top_warns": [], "versions": []}
        cfg = {"thresholds": {"degraded_pct": 40, "watch_pct": 15,
                              "new_release_min_share": 0.02},
               "min_dau": 10, "hygiene": {"default": {"verdict": "review"}},
               "funnels": [], "operations": []}
        with mock.patch.object(pulse, "collect_day", return_value=today):
            project = pulse.build_project(None, cfg, "A", "Example", "logs-", None,
                                          "2026-08-26", [], [],
                                          {"2026-08-25": {"A": previous}},
                                          ["2026-08-25"], 3)
        self.assertIsNotNone(project)
        self.assertEqual(project["dau"], 0)
        self.assertEqual(project["status"], "degraded")
        self.assertEqual(project["dau_drop_pct"], 100.0)


if __name__ == "__main__":
    unittest.main()
