import io
import pathlib
import sys
import unittest
import urllib.error
from unittest import mock


ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
import store_auth
import store_pulse as pulse
import store_sources as sources


def app(name, metrics, as_of="2026-08-26"):
    return {"name": name, "slices": {"ios_analytics": {
        "as_of": as_of, "metrics": metrics, "derived": {}}}, "crash_delta": {}}


class IntegrityContractTests(unittest.TestCase):
    def test_portfolio_rate_uses_only_matched_app_date_population(self):
        apps = [
            app("Numerator only", {"crashes": {"value": 1200, "as_of": "2026-08-26"}}),
            app("Matched", {"crashes": {"value": 50, "as_of": "2026-08-26"},
                            "sessions": {"value": 2_000_000, "as_of": "2026-08-26"}}),
        ]
        core = pulse.build_core_metrics(apps)["core"]
        self.assertAlmostEqual(core["crashes_per_1k"], 0.025)
        self.assertEqual(core["crash_rate_population"]["apps"], 1)
        self.assertEqual(core["crash_rate_population"]["expected_apps"], 2)

    def test_cross_date_components_do_not_form_a_rate(self):
        core = pulse.build_core_metrics([app("Mismatch", {
            "crashes": {"value": 10, "as_of": "2026-08-26"},
            "sessions": {"value": 1000, "as_of": "2026-08-25"}})])["core"]
        self.assertIsNone(core["crashes_per_1k"])
        self.assertEqual(core["crash_rate_population"]["apps"], 0)

    def test_portfolio_rate_uses_one_common_processing_date(self):
        older = app("Older", {"crashes": {"value": 100, "as_of": "2026-08-25"},
                              "sessions": {"value": 1000, "as_of": "2026-08-25"}})
        newer = app("Newer", {"crashes": {"value": 1, "as_of": "2026-08-26"},
                              "sessions": {"value": 1000, "as_of": "2026-08-26"}})
        core = pulse.build_core_metrics([older, newer])["core"]
        self.assertAlmostEqual(core["crashes_per_1k"], 1.0)
        self.assertEqual(core["crash_rate_population"]["as_of"], "2026-08-26")
        self.assertEqual(core["crash_rate_population"]["excluded_other_dates"], 1)

    def test_between_release_comparison_requires_authoritative_order(self):
        block = app("Example", {"crashes": {"value": 5}, "sessions": {"value": 1000}})
        block["slices"]["ios_analytics"]["metrics"]["crashes"]["breakdown"] = {
            "App Version": [{"key": "2.0", "value": 5}]}
        block["slices"]["ios_analytics"]["metrics"]["sessions"]["breakdown"] = {
            "App Version": [{"key": "2.0", "value": 1000}]}
        self.assertEqual(pulse._version_rates(block, [], 100), [])

    def test_non_idempotent_post_is_not_retried(self):
        transport = store_auth.Transport(retries=3, backoff=0)
        error = urllib.error.HTTPError("https://example.invalid", 503, "busy", {}, io.BytesIO())
        with mock.patch("urllib.request.urlopen", side_effect=error) as opened:
            with self.assertRaises(store_auth.HttpError):
                transport.raw("https://example.invalid", method="POST", body=b"{}")
        self.assertEqual(opened.call_count, 1)

    def test_explicitly_safe_post_can_retry(self):
        transport = store_auth.Transport(retries=3, backoff=0)
        error = urllib.error.HTTPError("https://example.invalid", 503, "busy", {}, io.BytesIO())
        with mock.patch("urllib.request.urlopen", side_effect=error) as opened:
            with self.assertRaises(store_auth.HttpError):
                transport.raw("https://example.invalid", method="POST", body=b"{}",
                              retry_safe=True)
        self.assertEqual(opened.call_count, 3)

    def test_asc_segments_follow_all_next_links(self):
        class Fake:
            def __init__(self):
                self.calls = 0

            def json(self, url, headers=None):
                self.calls += 1
                if self.calls == 1:
                    return {"data": [{"attributes": {"url": "one"}}],
                            "links": {"next": "https://next"}}
                return {"data": [{"attributes": {"url": "two"}}], "links": {}}

        rows = sources.asc_instance_segments(Fake(), {}, "instance")
        self.assertEqual([row["url"] for row in rows], ["one", "two"])

    def test_analytics_safety_cap_is_explicitly_incomplete(self):
        ctx = {"cfg": {"ios_analytics_max_rows": 100,
                       "ios_analytics_max_segments": 1},
               "transport": object(), "creds": mock.Mock()}
        with mock.patch.object(pulse.src, "asc_instance_segments",
                               return_value=[{"url": "one"}, {"url": "two"}]), \
             mock.patch.object(pulse.src, "asc_segment_rows",
                               return_value=(["Count"], [{"Count": "1"}])):
            _, rows, coverage = pulse._analytics_rows(ctx, "instance")
        self.assertEqual(len(rows), 1)
        self.assertFalse(coverage["complete"])
        self.assertEqual(coverage["segments"], 2)
        self.assertEqual(coverage["segments_read"], 1)

    def test_experience_message_leads_with_incomplete_source_banner(self):
        summary = {"apps_rated": 0, "apps_total": 2, "ratings_total": 0,
                   "reviews_new": 0, "reviews_neg": 0, "rating_median": None,
                   "rating_min": None, "rating_max": None, "worst_app": None,
                   "backlog": 0, "backlog_by_app": [], "topics": {}, "movers": [],
                   "release_states": {}, "conversion_median": None, "installs": None,
                   "uninstalls": None}
        report = {"brand": {"org": "Example"}, "report_day": "2026-08-26",
                  "generated_utc": "now", "overall_by_nature": {"experience": "degraded"},
                  "store_summaries": {"ios": dict(summary), "play": dict(summary)},
                  "credential_state": {}, "attention": [], "apps": [], "coverage_gaps": [],
                  "slice_state": {"ios_reviews": {"ok": 0, "expected": 2, "failed": 2,
                                                   "skipped_count": 0, "complete": False}}}
        text = pulse.render_experience_slack(report)
        self.assertIn("Source completeness: PARTIAL", text)
        self.assertIn("failed 2", text)
        self.assertNotIn("Nothing over threshold", text)


if __name__ == "__main__":
    unittest.main()
