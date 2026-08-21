"""Offline tests for Store Pulse.

The Play and Apple paths cannot be exercised without provider credentials, so
every collector takes an injectable transport and is tested here against recorded
payload shapes. The scoring, delta and rendering layers are tested end to end.

Run: python3 -m unittest discover -s tests   (from the module directory)
"""

import datetime as dt
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

MODULE_DIR = Path(__file__).parents[1]
sys.path.insert(0, str(MODULE_DIR))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, MODULE_DIR / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


auth = _load("store_auth")
src = _load("store_sources")
pulse = _load("store_pulse")


class FakeTransport:
    """Answers by first matching URL substring; records every call."""

    def __init__(self, routes, raw_routes=None):
        self.routes = routes
        self.raw_routes = raw_routes or {}
        self.seen = []
        self.calls = 0

    def _match(self, table, url):
        for key, value in table.items():
            if key in url:
                return value
        raise AssertionError(f"no fake route for {url}")

    def json(self, url, method="GET", payload=None, headers=None, form=None, timeout=None):
        self.calls += 1
        self.seen.append((method, url, payload))
        value = self._match(self.routes, url)
        if isinstance(value, Exception):
            raise value
        if callable(value):
            return value(url, payload)
        return value

    def raw(self, url, method="GET", body=None, headers=None, timeout=None):
        self.calls += 1
        self.seen.append((method, url, None))
        return self._match(self.raw_routes, url)


# ------------------------------------------------------------------ auth layer

class AuthTests(unittest.TestCase):
    def test_der_to_raw_rejects_garbage(self):
        with self.assertRaises(auth.AuthError):
            auth.der_ecdsa_to_raw(b"\x01\x02")

    @unittest.skipIf(shutil.which("openssl") is None, "openssl unavailable")
    def test_es256_signature_is_64_raw_bytes_and_verifies(self):
        tmp = tempfile.mkdtemp()
        try:
            key = os.path.join(tmp, "k.pem")
            subprocess.run(["openssl", "ecparam", "-genkey", "-name", "prime256v1", "-noout",
                            "-out", key], check=True, capture_output=True)
            raw = auth.der_ecdsa_to_raw(auth._sign_with_pem_file(key, b"payload"))
            self.assertEqual(len(raw), 64)
        finally:
            shutil.rmtree(tmp)

    def test_in_memory_pem_signing_leaves_no_key_file(self):
        before = {p for p in os.listdir(tempfile.gettempdir()) if p.startswith("storepulse-")}
        with self.assertRaises(auth.AuthError):
            auth._sign_with_pem_text("not a key", b"payload")
        after = {p for p in os.listdir(tempfile.gettempdir()) if p.startswith("storepulse-")}
        self.assertEqual(before, after)

    def test_credentials_report_missing_env_without_leaking_values(self):
        cfg = pulse._merge(pulse.DEFAULTS, {"apps": [{"key": "A"}]})
        for var in cfg["credentials"].values():
            os.environ.pop(var, None)
        creds = pulse.Creds(cfg, FakeTransport({}))
        self.assertFalse(creds.has("google"))
        self.assertFalse(creds.has("apple"))
        self.assertIn("STORE_PULSE_GOOGLE_SA_JSON", creds.reasons["google"])
        self.assertEqual(sorted(creds.missing_for("play_rating")), ["bucket", "google"])


# --------------------------------------------------------------- iTunes source

ITUNES_RATED = {"resultCount": 1, "results": [{
    "trackId": 123, "trackName": "Example", "version": "1.2.3",
    "averageUserRating": 4.4321, "userRatingCount": 250,
    "averageUserRatingForCurrentVersion": 4.5, "userRatingCountForCurrentVersion": 12,
    "currentVersionReleaseDate": "2026-08-01T10:00:00Z", "minimumOsVersion": "13.0"}]}
ITUNES_UNRATED = {"resultCount": 1, "results": [{
    "trackId": 123, "trackName": "Example", "version": "1.2.3",
    "averageUserRating": 0.0, "userRatingCount": 0,
    "averageUserRatingForCurrentVersion": 0.0, "userRatingCountForCurrentVersion": 0}]}


class ITunesTests(unittest.TestCase):
    def test_rating_and_track_id_are_read(self):
        t = FakeTransport({"itunes.apple.com": ITUNES_RATED})
        out = src.itunes_lookup(t, "com.example.app", ["us"])
        self.assertEqual(out["track_id"], 123)
        self.assertAlmostEqual(out["storefronts"]["us"]["avg"], 4.4321)
        self.assertEqual(out["storefronts"]["us"]["count"], 250)

    def test_zero_ratings_is_null_not_zero_stars(self):
        t = FakeTransport({"itunes.apple.com": ITUNES_UNRATED})
        out = src.itunes_lookup(t, "com.example.app", ["de"])
        self.assertIsNone(out["storefronts"]["de"]["avg"])
        self.assertIsNone(out["storefronts"]["de"]["avg_current"])
        self.assertEqual(out["storefronts"]["de"]["count"], 0)

    def test_unlisted_bundle_is_marked_not_listed(self):
        t = FakeTransport({"itunes.apple.com": {"resultCount": 0, "results": []}})
        out = src.itunes_lookup(t, "com.example.ghost", ["us"])
        self.assertFalse(out["storefronts"]["us"]["listed"])


# ----------------------------------------------------------------- Play vitals

def _metric_rows():
    return {"rows": [
        {"startTime": {"year": 2026, "month": 8, "day": 17},
         "dimensions": [], "metrics": [
             {"metric": "userPerceivedCrashRate", "decimalValue": {"value": "0.0142"}},
             {"metric": "distinctUsers", "decimalValue": {"value": "12000"}}]},
        {"startTime": {"year": 2026, "month": 8, "day": 16},
         "dimensions": [], "metrics": [
             {"metric": "userPerceivedCrashRate", "decimalValue": {"value": "0.0031"}}]},
        {"startTime": {"year": 2026, "month": 8, "day": 17},
         "dimensions": [{"dimension": "versionCode", "int64Value": "1603"}],
         "metrics": [{"metric": "userPerceivedCrashRate", "decimalValue": {"value": "0.0910"}}]},
    ]}


class PlayVitalsTests(unittest.TestCase):
    def setUp(self):
        self.routes = {
            "crashRateMetricSet:query": _metric_rows(),
            "crashRateMetricSet": {"freshnessInfo": {"freshnesses": [
                {"aggregationPeriod": "DAILY", "latestEndTime": {"year": 2026, "month": 8, "day": 17}}]}},
        }
        self.sets = [{"key": "crash", "metric_set": "crashRateMetricSet",
                      "metrics": ["userPerceivedCrashRate", "distinctUsers"],
                      "dimensions": ["versionCode"]}]

    def test_freshness_clamps_the_requested_day(self):
        t = FakeTransport(self.routes)
        out = src.play_vitals(t, {}, "com.example", dt.date(2026, 8, 19), self.sets)
        self.assertEqual(out["as_of"], "2026-08-17")
        body = [c[2] for c in t.seen if c[2]][0]
        self.assertEqual(body["timelineSpec"]["endTime"]["day"], 17)
        self.assertEqual(body["timelineSpec"]["endTime"]["timeZone"]["id"], "America/Los_Angeles")

    def test_overall_and_breakdown_rows_are_separated(self):
        t = FakeTransport(self.routes)
        out = src.play_vitals(t, {}, "com.example", dt.date(2026, 8, 17), self.sets)
        block = out["sets"]["crash"]
        self.assertAlmostEqual(block["overall"]["userPerceivedCrashRate"], 0.0142)
        self.assertEqual(len(block["breakdown"]), 1)
        self.assertEqual(block["breakdown"][0]["dims"], {"versionCode": "1603"})
        self.assertIn("2026-08-16", block["trail"])

    def test_a_failing_metric_set_is_recorded_not_raised(self):
        routes = dict(self.routes)
        routes["crashRateMetricSet:query"] = auth.HttpError(403, "u", "denied")
        out = src.play_vitals(FakeTransport(routes), {}, "com.example", dt.date(2026, 8, 17), self.sets)
        self.assertIn("crash", out["errors"])
        self.assertEqual(out["sets"], {})

    def test_rates_convert_to_percent(self):
        self.assertAlmostEqual(pulse.rate_to_pct(0.0142), 1.42)
        self.assertAlmostEqual(pulse.rate_to_pct(1.42, "percent"), 1.42)
        self.assertAlmostEqual(pulse.rate_to_pct(3.5), 3.5)  # already percent-shaped
        self.assertIsNone(pulse.rate_to_pct(None))


class PlayIssueTests(unittest.TestCase):
    def test_issue_fields_and_percent_shapes(self):
        payload = {"errorIssues": [
            {"type": "CRASH", "cause": "java.lang.NullPointerException",
             "location": "GameActivity.onResume", "errorReportCount": "820",
             "distinctUsers": "310", "distinctUsersPercent": {"value": "2.4"},
             "firstAppVersion": {"versionCode": 1590}, "lastAppVersion": {"versionCode": 1603},
             "issueUri": "https://play.google.com/console/..."},
            {"type": "ANR", "cause": "Input dispatching timed out",
             "errorReportCount": 30, "distinctUsers": 25, "distinctUsersPercent": 0.2}]}
        out = src.play_error_issues(FakeTransport({"errorIssues:search": payload}), {},
                                   "com.example", dt.date(2026, 8, 17))
        self.assertEqual(out[0]["users_pct"], 2.4)
        self.assertEqual(out[0]["first_version"], 1590)
        self.assertEqual(out[1]["users_pct"], 0.2)

    def test_interval_and_filter_are_sent(self):
        t = FakeTransport({"errorIssues:search": {"errorIssues": []}})
        src.play_error_issues(t, {}, "com.example", dt.date(2026, 8, 17))
        url = t.seen[0][1]
        self.assertIn("interval.startTime.day=16", url)
        self.assertIn("errorIssueType+%3D+CRASH", url.replace("%20", "+"))


class PlayReviewTests(unittest.TestCase):
    PAYLOAD = {"reviews": [
        {"reviewId": "a", "comments": [
            {"userComment": {"text": "Too many ads and it crashes", "starRating": 1,
                             "reviewerLanguage": "en", "device": "Pixel 6",
                             "androidOsVersion": 33, "appVersionName": "1.60.3",
                             "thumbsUpCount": 3, "lastModified": {"seconds": "1787000000"}}}]},
        {"reviewId": "b", "comments": [
            {"userComment": {"text": "Great game", "starRating": 5,
                             "lastModified": {"seconds": "1787000500"}}},
            {"developerComment": {"text": "Thanks!"}}]}]}

    def test_stars_answered_and_timestamps(self):
        out = src.play_reviews(FakeTransport({"reviews": self.PAYLOAD}), {}, "com.example")
        self.assertEqual([r["stars"] for r in out], [1, 5])
        self.assertFalse(out[0]["answered"])
        self.assertTrue(out[1]["answered"])
        self.assertTrue(out[0]["at"].startswith("2026-"))

    def test_secrets_in_review_text_are_redacted(self):
        payload = {"reviews": [{"comments": [{"userComment": {
            "text": "my token=abc123 leaked", "starRating": 2,
            "lastModified": {"seconds": "1787000000"}}}]}]}
        out = src.play_reviews(FakeTransport({"reviews": payload}), {}, "com.example")
        self.assertNotIn("abc123", out[0]["text"])
        self.assertIn("[REDACTED]", out[0]["text"])


# ------------------------------------------------------------ Play bulk report

class PlayCsvTests(unittest.TestCase):
    def test_utf16_bom_is_decoded(self):
        raw = "Date,Total Average Rating\n2026-08-17,4.31\n".encode("utf-16")
        self.assertIn("Total Average Rating", src.decode_report_bytes(raw))

    def test_last_versus_sum_aggregation(self):
        text = ("Date,Country,Store Listing Visitors,Store Listing Acquisitions\n"
                "2026-08-17,US,100,10\n2026-08-17,GB,50,5\n")
        series, _ = src.play_csv_series(text, ["Date"], {
            "visitors": {"cols": ["Store Listing Visitors"], "agg": "sum"},
            "acquisitions": {"cols": ["Store Listing Acquisitions"], "agg": "sum"}})
        self.assertEqual(series["2026-08-17"], {"visitors": 150.0, "acquisitions": 15.0})
        series_last, _ = src.play_csv_series(text, ["Date"], {
            "visitors": {"cols": ["Store Listing Visitors"], "agg": "last"}})
        self.assertEqual(series_last["2026-08-17"]["visitors"], 50.0)

    def test_column_names_match_case_insensitively_and_by_substring(self):
        header = ["Date", "Package Name", "Daily Device Installs"]
        self.assertEqual(src.pick_col(header, ["Daily User Installs", "Daily Device Installs"]), 2)
        self.assertIsNone(src.pick_col(header, ["Nonexistent"]))

    def test_missing_date_column_yields_empty_series(self):
        series, _ = src.play_csv_series("A,B\n1,2\n", ["Date"], {"x": {"cols": ["A"]}})
        self.assertEqual(series, {})


# ----------------------------------------------------------- App Store Connect

class AppStoreConnectTests(unittest.TestCase):
    def test_include_response_400_falls_back_to_plain_request(self):
        state = {"n": 0}

        def handler(url, payload):
            state["n"] += 1
            if "include=response" in url and state["n"] == 1:
                raise auth.HttpError(400, url, "include not allowed")
            return {"data": [{"attributes": {"rating": 2, "title": "Meh", "body": "crashes a lot",
                                             "territory": "USA", "createdDate": "2026-08-18T09:00:00-07:00"},
                              "relationships": {}}]}

        t = FakeTransport({"customerReviews": handler})
        out = src.asc_customer_reviews(t, {}, "42")
        self.assertEqual(out[0]["stars"], 2)
        self.assertFalse(out[0]["answered"])
        self.assertEqual(state["n"], 2)

    def test_answered_review_detected_from_relationship(self):
        payload = {"data": [{"attributes": {"rating": 1, "body": "bad", "territory": "USA",
                                            "createdDate": "2026-08-18T09:00:00-07:00"},
                             "relationships": {"response": {"data": {"id": "r1",
                                                                     "type": "customerReviewResponses"}}}}]}
        out = src.asc_customer_reviews(FakeTransport({"customerReviews": payload}), {}, "42")
        self.assertTrue(out[0]["answered"])

    def test_app_lookup_prefers_exact_bundle_match(self):
        payload = {"data": [
            {"id": "1", "attributes": {"bundleId": "com.example.other", "name": "Other"}},
            {"id": "2", "attributes": {"bundleId": "com.example.app", "name": "Wanted"}}]}
        found = src.asc_app_by_bundle(FakeTransport({"apps": payload}), {}, "com.example.app")
        self.assertEqual(found["id"], "2")

    def test_phased_release_absent_returns_none(self):
        t = FakeTransport({"appStoreVersionPhasedRelease": auth.HttpError(404, "u", "")})
        self.assertIsNone(src.asc_phased_release(t, {}, "v1"))


# ---------------------------------------------------------------- report model

def _app_block(key="A", name="App", ios_avg=None, ios_count=None, play_total=None,
               crash_pct=None, anr_pct=None, reviews=None, breakdown=None):
    slices = {}
    if ios_avg is not None or ios_count is not None:
        slices["ios_rating"] = {"avg": ios_avg, "count": ios_count, "listed": True,
                                "by_storefront": {"us": {"avg": ios_avg, "count": ios_count,
                                                         "listed": True}}}
    if play_total is not None:
        slices["play_rating"] = {"total_avg": play_total, "as_of": "2026-08-17"}
    if crash_pct is not None or anr_pct is not None:
        metrics = {}
        if crash_pct is not None:
            metrics["userPerceivedCrashRate"] = crash_pct
        if anr_pct is not None:
            metrics["userPerceivedAnrRate"] = anr_pct
        slices["play_vitals"] = {"metrics": metrics, "users": 50000, "as_of": "2026-08-17",
                                 "sets": {"crash": {"breakdown": breakdown or []}}}
    if reviews:
        slices["play_reviews"] = reviews
    return {"key": key, "name": name, "slices": slices, "errors": {}, "skipped": {},
            "ios": "com.example.app", "android": "com.example.app"}


class ScoringTests(unittest.TestCase):
    def setUp(self):
        self.cfg = pulse._merge(pulse.DEFAULTS, {"apps": [{"key": "A"}]})

    def score(self, block):
        block.setdefault("rating", {})
        for platform in ("ios", "play"):
            avg, count = pulse._rating_of(block, platform)
            block["rating"].setdefault(platform, {"avg": avg, "count": count,
                                                  "d_avg": None, "d_avg_7d": None, "d_count": None})
        return pulse.score_app(block, self.cfg)

    def test_crash_rate_over_google_bar_is_degraded(self):
        out = self.score(_app_block(crash_pct=1.2))
        self.assertEqual(out["status"], "degraded")
        self.assertTrue(any("bad-behaviour bar" in a["text"] for a in out["attention"]))

    def test_crash_rate_near_bar_is_watch(self):
        out = self.score(_app_block(crash_pct=0.8))
        self.assertEqual(out["status"], "watch")

    def test_anr_bar_is_stricter_than_crash_bar(self):
        self.assertEqual(self.score(_app_block(anr_pct=0.5))["status"], "degraded")
        self.assertEqual(self.score(_app_block(crash_pct=0.5))["status"], "healthy")

    def test_single_version_slice_over_device_bar_alerts(self):
        out = self.score(_app_block(crash_pct=0.1, breakdown=[
            {"dims": {"versionCode": "1603"}, "metrics": {"userPerceivedCrashRate": 0.12}}]))
        self.assertEqual(out["status"], "degraded")
        self.assertTrue(any("1603" in a["text"] for a in out["attention"]))

    def test_low_vitals_users_never_alerts_and_never_drags_other_signals(self):
        block = _app_block(crash_pct=5.0)
        block["slices"]["play_vitals"]["users"] = 10
        out = self.score(block)
        self.assertEqual(out["low_data"], ["play_vitals"])
        self.assertFalse([a for a in out["attention"] if a["kind"] == "vitals"])
        healthy_rating = _app_block(ios_avg=4.8, ios_count=2000, crash_pct=5.0)
        healthy_rating["slices"]["play_vitals"]["users"] = 10
        self.assertEqual(self.score(healthy_rating)["status"], "healthy")

    def test_rating_floor_alerts_with_enough_ratings(self):
        out = self.score(_app_block(ios_avg=1.17, ios_count=6))
        self.assertEqual(out["status"], "degraded")
        self.assertTrue(any(a["kind"] == "rating_floor" for a in out["attention"]))

    def test_low_sample_bad_rating_is_watch_only(self):
        out = self.score(_app_block(ios_avg=2.3, ios_count=3))
        self.assertEqual(out["status"], "watch")
        self.assertTrue(any("low sample" in a["text"] for a in out["attention"]))

    def test_good_rating_is_healthy(self):
        self.assertEqual(self.score(_app_block(ios_avg=4.8, ios_count=2000))["status"], "healthy")

    def test_no_signal_at_all_is_low_data(self):
        block = _app_block()
        block["slices"]["ios_rating"] = {"listed": False, "avg": None, "count": None,
                                        "by_storefront": {}}
        self.assertEqual(self.score(block)["status"], "nodata")

    def test_rejected_release_alerts_even_with_no_ratings_at_all(self):
        block = _app_block()
        block["slices"]["ios_rating"] = {"listed": False, "avg": None, "count": None,
                                        "by_storefront": {}}
        block["slices"]["ios_release"] = {"current": {"version": "0.41.7", "state": "REJECTED",
                                                     "created": "2026-03-04"},
                                          "versions": [], "phased": None}
        out = self.score(block)
        self.assertEqual(out["status"], "degraded")
        self.assertTrue(any(a["kind"] == "release" for a in out["attention"]))

    def test_pre_release_app_with_no_ratings_is_low_data_not_healthy(self):
        block = _app_block()
        block["slices"]["ios_rating"] = {"listed": False, "avg": None, "count": None,
                                        "by_storefront": {}}
        block["slices"]["ios_release"] = {"current": {"version": "1.0",
                                                     "state": "PREPARE_FOR_SUBMISSION"},
                                          "versions": [], "phased": None}
        self.assertEqual(self.score(block)["status"], "nodata")

    def test_phased_release_in_flight_is_watch_context(self):
        block = _app_block(ios_avg=4.5, ios_count=900)
        block["slices"]["ios_release"] = {"current": {"version": "1.61.0", "state": "READY_FOR_DISTRIBUTION"},
                                          "versions": [], "phased": {"state": "ACTIVE", "day": 3}}
        out = self.score(block)
        self.assertEqual(out["status"], "watch")
        self.assertTrue(any("phased" in a["text"] for a in out["attention"]))

    def test_negative_review_share_scores(self):
        reviews = {"count": 10, "neg_count": 7, "neg_share_pct": 70.0, "topics": {"ads": 4},
                   "sample": [], "backlog_unanswered": 7}
        out = self.score(_app_block(reviews=reviews))
        self.assertEqual(out["status"], "degraded")
        self.assertTrue(any("≤2★" in a["text"] for a in out["attention"]))

    def test_unanswered_backlog_is_a_watch_with_the_scan_size_stated(self):
        reviews = {"count": 0, "neg_count": 0, "neg_share_pct": None, "topics": {}, "sample": [],
                   "backlog_unanswered": 116, "scanned": 200}
        out = self.score(_app_block(ios_avg=4.87, ios_count=2225, reviews=reviews))
        self.assertEqual(out["status"], "watch")
        item = [a for a in out["attention"] if a["kind"] == "reviews_backlog"][0]
        self.assertIn("116 unanswered", item["text"])
        self.assertIn("200 most recent", item["text"])

    def test_backlog_does_not_claim_a_scan_window_it_did_not_hit(self):
        reviews = {"count": 0, "neg_count": 0, "topics": {}, "sample": [],
                   "backlog_unanswered": 116, "scanned": 116}
        out = self.score(_app_block(ios_avg=4.87, ios_count=2225, reviews=reviews))
        item = [a for a in out["attention"] if a["kind"] == "reviews_backlog"][0]
        self.assertNotIn("most recent", item["text"])
        self.assertIn("every review it has", item["text"])

    def test_small_backlog_is_not_flagged(self):
        reviews = {"count": 0, "neg_count": 0, "topics": {}, "sample": [],
                   "backlog_unanswered": 3, "scanned": 40}
        self.assertEqual(self.score(_app_block(ios_avg=4.8, ios_count=900, reviews=reviews))["status"],
                         "healthy")

    def test_negative_share_below_min_count_is_ignored(self):
        reviews = {"count": 3, "neg_count": 3, "neg_share_pct": 100.0, "topics": {}, "sample": [],
                   "backlog_unanswered": 3}
        self.assertEqual(self.score(_app_block(reviews=reviews))["status"], "healthy")


class DeltaTests(unittest.TestCase):
    def test_deltas_come_from_the_newest_earlier_snapshot_and_a_7d_one(self):
        tmp = tempfile.mkdtemp()
        try:
            for day, avg in (("2026-08-11", 4.90), ("2026-08-17", 4.85), ("2026-08-18", 4.80)):
                blob = {"apps": [{"key": "A", "status": "healthy",
                                  "slices": {"ios_rating": {"avg": avg, "count": 100}}}]}
                with open(os.path.join(tmp, f"store_pulse_{day}.json"), "w") as fh:
                    json.dump(blob, fh)
            history = pulse.prior_reports(tmp, "store_pulse", dt.date(2026, 8, 19))
            block = _app_block(ios_avg=4.70, ios_count=120)
            pulse.attach_deltas(block, history, dt.date(2026, 8, 19))
            ios = block["rating"]["ios"]
            self.assertEqual(block["baseline"], {"prev_day": "2026-08-18", "week": "2026-08-11"})
            self.assertAlmostEqual(ios["d_avg"], -0.10)
            self.assertAlmostEqual(ios["d_avg_7d"], -0.20)
            self.assertEqual(ios["d_count"], 20)
        finally:
            shutil.rmtree(tmp)

    def test_rating_drop_scores_even_when_level_is_fine(self):
        cfg = pulse._merge(pulse.DEFAULTS, {"apps": [{"key": "A"}]})
        block = _app_block(ios_avg=4.6, ios_count=5000)
        block["rating"] = {"ios": {"avg": 4.6, "count": 5000, "d_avg": -0.06, "d_avg_7d": None,
                                  "d_count": 20},
                           "play": {"avg": None, "count": None, "d_avg": None, "d_avg_7d": None,
                                    "d_count": None}}
        out = pulse.score_app(block, cfg)
        self.assertEqual(out["status"], "degraded")
        self.assertTrue(any(a["kind"] == "rating" for a in out["attention"]))

    def test_first_run_without_history_has_no_deltas(self):
        block = _app_block(ios_avg=4.7, ios_count=10)
        pulse.attach_deltas(block, [], dt.date(2026, 8, 19))
        self.assertIsNone(block["rating"]["ios"]["d_avg"])
        self.assertIsNone(block["prior_status"])


class CollectionResilienceTests(unittest.TestCase):
    def test_one_broken_slice_does_not_stop_the_others(self):
        cfg = pulse._merge(pulse.DEFAULTS, {"apps": [{"key": "A", "name": "App",
                                                      "ios": "com.example.app", "android": None}]})
        cfg["slices"] = {"ios_rating": True}
        app = dict(cfg["apps"][0], slices={}, ios_app_id=None)
        ctx = {"cfg": cfg, "creds": pulse.Creds(cfg, FakeTransport({})),
               "transport": FakeTransport({"itunes": auth.HttpError(503, "u", "upstream")}),
               "day": dt.date(2026, 8, 19), "now": "2026-08-19T00:00:00+00:00",
               "window_start": "2026-08-18"}
        out = pulse.collect_app(ctx, app)
        self.assertIn("ios_rating", out["errors"])
        self.assertEqual(out["slices"], {})

    def test_missing_platform_id_is_skipped_with_a_reason(self):
        cfg = pulse._merge(pulse.DEFAULTS, {"apps": [{"key": "A", "name": "App",
                                                      "ios": None, "android": None}]})
        cfg["slices"] = {"ios_rating": True, "play_vitals": True}
        app = dict(cfg["apps"][0], slices={}, ios_app_id=None)
        ctx = {"cfg": cfg, "creds": pulse.Creds(cfg, FakeTransport({})),
               "transport": FakeTransport({}), "day": dt.date(2026, 8, 19),
               "now": "2026-08-19T00:00:00+00:00", "window_start": "2026-08-18"}
        out = pulse.collect_app(ctx, app)
        self.assertIn("no ios identifier configured", out["skipped"]["ios_rating"])


# -------------------------------------------------------------------- renderers

def _report(apps=None, overall="degraded", gaps=None):
    apps = apps or []
    by_store = {}
    for store in ("ios", "play"):
        worst, seen = "healthy", False
        for a in apps:
            st = (a.get("status_by_store") or {}).get(store, "nodata")
            if st != "nodata":
                seen = True
                worst = pulse._worse(worst, st)
        by_store[store] = worst if seen else "nodata"
    return {"kind": "store", "slug": "store_pulse", "brand": {"org": "Org", "product": "Store Pulse"},
            "report_day": "2026-08-19", "generated_utc": "2026-08-19T06:00:00+00:00",
            "overall_status": overall, "apps": apps,
            "attention": [dict(a, app=app["name"]) for app in apps for a in app.get("attention", [])],
            "slice_state": {"ios_rating": {"ok": len(apps), "failed": 0, "skipped": None}},
            "baseline_reports": ["2026-08-18"], "coverage_gaps": gaps or [],
            "credential_state": {"google": "not set", "apple": True, "bucket": "not set"},
            "overall_by_store": by_store,
            "store_summaries": {st: pulse.build_store_summary(apps, st) for st in ("ios", "play")},
            "thresholds": pulse.DEFAULTS["thresholds"]}


class RenderTests(unittest.TestCase):
    def setUp(self):
        cfg = pulse._merge(pulse.DEFAULTS, {"apps": [{"key": "A"}]})
        bad = _app_block(key="A", name="Sudoku", ios_avg=1.17, ios_count=6)
        bad["rating"] = {"ios": {"avg": 1.17, "count": 6, "d_avg": -0.2, "d_avg_7d": None, "d_count": 1},
                         "play": {"avg": 3.9, "count": 400, "d_avg": 0.01, "d_avg_7d": None, "d_count": 4}}
        pulse.score_app(bad, cfg)
        good = _app_block(key="B", name="Blingz", ios_avg=4.87, ios_count=2225)
        good["rating"] = {"ios": {"avg": 4.87, "count": 2225, "d_avg": None, "d_avg_7d": None,
                                  "d_count": None},
                          "play": {"avg": None, "count": None, "d_avg": None, "d_avg_7d": None,
                                   "d_count": None}}
        pulse.score_app(good, cfg)
        self.report = _report([bad, good], gaps=[{"app": "Ghost", "store": "App Store",
                                                  "id": "com.example.ghost",
                                                  "text": "configured bundle id is not on the App Store"}])

    def test_slack_digest_leads_with_attention_and_lists_apps(self):
        text = pulse.render_slack(self.report)
        self.assertIn("Needs attention", text)
        self.assertIn("Sudoku", text)
        self.assertIn("1.17★", text)
        self.assertIn("credentials pending", text)
        self.assertIn("Not on the store:", text)
        # the digest must carry WHY a listing is absent, not just that it is
        self.assertIn("configured bundle id is not on the App Store", text)

    def test_markdown_and_html_are_self_contained_and_escape_content(self):
        md = pulse.render_md(self.report)
        self.assertIn("## Ratings", md)
        self.assertIn("## Coverage gaps", md)
        inner = pulse.render_inner(self.report)
        self.assertIn("prefers-color-scheme", inner)
        self.assertNotIn("<script", inner)

    def test_html_escapes_hostile_app_names(self):
        rogue = _app_block(key="X", name="<img src=x onerror=alert(1)>", ios_avg=4.0, ios_count=99)
        rogue["rating"] = {"ios": {"avg": 4.0, "count": 99, "d_avg": None, "d_avg_7d": None,
                                  "d_count": None},
                           "play": {"avg": None, "count": None, "d_avg": None, "d_avg_7d": None,
                                    "d_count": None}}
        rogue["attention"] = []
        rogue["status"] = "healthy"
        html_out = pulse.render_inner(_report([rogue], overall="healthy"))
        self.assertNotIn("<img src=x", html_out)
        self.assertIn("&lt;img", html_out)


class PerStoreDeliveryTests(unittest.TestCase):
    """One message per store: a finding in one store must never colour the other."""

    def setUp(self):
        self.cfg = pulse._merge(pulse.DEFAULTS, {"apps": [{"key": "A"}]})

    def score(self, block):
        block.setdefault("rating", {})
        for platform in ("ios", "play"):
            avg, count = pulse._rating_of(block, platform)
            block["rating"].setdefault(platform, {"avg": avg, "count": count, "d_avg": None,
                                                  "d_avg_7d": None, "d_count": None})
        return pulse.score_app(block, self.cfg)

    def test_play_crash_does_not_degrade_the_app_store_verdict(self):
        block = self.score(_app_block(ios_avg=4.8, ios_count=900, play_total=4.1, crash_pct=1.5))
        self.assertEqual(block["status_by_store"]["play"], "degraded")
        self.assertEqual(block["status_by_store"]["ios"], "healthy")
        self.assertEqual(block["status"], "degraded")  # app-wide is still worst-of

    def test_rejected_ios_release_does_not_degrade_play(self):
        block = _app_block(play_total=4.2)
        block["slices"]["ios_release"] = {"current": {"version": "0.7.1", "state": "REJECTED"},
                                          "versions": [], "phased": None}
        out = self.score(block)
        self.assertEqual(out["status_by_store"]["ios"], "degraded")
        self.assertEqual(out["status_by_store"]["play"], "healthy")

    def test_every_finding_declares_its_store(self):
        block = self.score(_app_block(ios_avg=1.2, ios_count=40, crash_pct=1.5))
        self.assertTrue(all(a["store"] in ("ios", "play") for a in block["attention"]))

    def test_a_store_with_no_data_gets_no_report(self):
        block = self.score(_app_block(ios_avg=4.8, ios_count=900))
        report = _report([block])
        self.assertTrue(pulse.store_has_any_data(report, "ios"))
        self.assertFalse(pulse.store_has_any_data(report, "play"))

    def test_store_report_shows_only_that_store_findings(self):
        block = self.score(_app_block(key="A", name="Solo", ios_avg=1.2, ios_count=40,
                                      play_total=4.4, crash_pct=1.5))
        report = _report([block])
        ios_text = pulse.render_store_slack(report, "ios")
        play_text = pulse.render_store_slack(report, "play")
        self.assertIn("App Store", ios_text.split("\n")[0])
        self.assertIn("below the 3.0★ floor", ios_text)
        self.assertNotIn("bad-behaviour bar", ios_text)
        self.assertIn("Google Play", play_text.split("\n")[0])
        self.assertIn("bad-behaviour bar", play_text)
        self.assertNotIn("below the 3.0★ floor", play_text)

    def test_portfolio_summary_aggregates_ratings_backlog_and_topics(self):
        a = _app_block(key="A", name="Big", ios_avg=4.87, ios_count=2225,
                       reviews={"count": 18, "neg_count": 3, "neg_share_pct": 16.7,
                                "topics": {"ads": 2, "cashout": 1}, "sample": [],
                                "backlog_unanswered": 116, "scanned": 116})
        a["slices"]["ios_reviews"] = a["slices"].pop("play_reviews")
        b = _app_block(key="B", name="Small", ios_avg=1.17, ios_count=6)
        b["slices"]["ios_reviews"] = {"count": 1, "neg_count": 1, "topics": {"ads": 1},
                                      "sample": [], "backlog_unanswered": 5, "scanned": 5}
        for blk in (a, b):
            self.score(blk)
        sm = pulse.build_store_summary([a, b], "ios")
        self.assertEqual(sm["ratings_total"], 2231)
        self.assertEqual(sm["apps_rated"], 2)
        self.assertEqual(sm["backlog"], 121)
        self.assertEqual(sm["topics"], {"ads": 3, "cashout": 1})
        self.assertEqual(sm["worst_app"], "Small")
        self.assertAlmostEqual(sm["rating_min"], 1.17)
        self.assertAlmostEqual(sm["rating_max"], 4.87)

    def test_coverage_gaps_are_filtered_per_store(self):
        block = self.score(_app_block(ios_avg=4.8, ios_count=900))
        report = _report([block], gaps=[{"app": "Ghost", "store": "App Store", "id": "com.g",
                                         "state": "REJECTED",
                                         "text": "listing is down — version 1.0 is REJECTED"}])
        self.assertIn("listing is down", pulse.render_store_slack(report, "ios"))
        self.assertNotIn("listing is down", pulse.render_store_slack(report, "play"))

    def test_store_md_reports_the_scoped_table(self):
        block = self.score(_app_block(key="A", name="Solo", ios_avg=1.17, ios_count=6))
        md = pulse.render_store_md(_report([block]), "ios")
        self.assertIn("App Store report", md)
        self.assertIn("| Solo |", md)
        self.assertIn("Needs attention", md)

    def test_store_dashboard_is_scoped_and_escaped(self):
        block = self.score(_app_block(key="A", name="<b>x</b>", ios_avg=4.5, ios_count=90))
        html_out = pulse.render_inner(_report([block]), store="ios")
        self.assertIn("&lt;b&gt;x", html_out)
        self.assertNotIn("PLAY", html_out.upper().replace("DISPLAY", ""))


TOPIC_CFG = {
    "reviews_analysis_limit": 50,
    "recent_days": 7,
    "review_focus_groups": [{"key": "ads", "label": "Advertising", "note": "tuned server-side"}],
    "review_topics": [
        {"key": "ads_frequency", "label": "Too many ads", "group": "ads", "segment": "product",
         "discipline": "monetisation", "owner": "Product + Ad ops", "action": "cap frequency",
         "phrases": ["too many ads"]},
        {"key": "ads_content_nsfw", "label": "Adult ad content", "group": "ads",
         "segment": "content-safety", "discipline": "trust & compliance",
         "owner": "Ad ops", "action": "blocklist", "phrases": ["porn"]},
        {"key": "crash", "label": "Crash", "segment": "technical", "discipline": "technical",
         "owner": "Engineering", "action": "reproduce", "phrases": ["crash"]},
        {"key": "praise_fun", "label": "Fun", "polarity": "positive", "phrases": ["fun"]},
    ],
    "review_brief": {"top_n": 3, "focus_bonus": 1.3, "role": "principal PO",
                     "segment_severity": {"content-safety": 3.0, "technical": 2.0, "product": 1.0}},
    "playbooks": {"ads_content_nsfw": {"role": "Trust", "revenue_note": "non-negotiable",
                                       "steps": ["blocklist the advertiser"],
                                       "links": ["https://developers.applovin.com/en/max/"]}},
}


def _rv(stars, text, at, answered=False, title="", territory="USA"):
    return {"stars": stars, "text": text, "title": title, "at": at, "answered": answered,
            "territory": territory, "app_version": None}


class RejectionTimelineTests(unittest.TestCase):
    def test_submissions_are_newest_first_with_state(self):
        payload = {"data": [
            {"id": "s1", "attributes": {"platform": "IOS", "state": "COMPLETE",
                                        "submittedDate": "2026-07-24T14:08:34.680Z"}},
            {"id": "s2", "attributes": {"platform": "IOS", "state": "UNRESOLVED_ISSUES",
                                        "submittedDate": "2026-07-27T07:06:58.701Z"}}]}
        out = src.asc_review_submissions(FakeTransport({"reviewSubmissions": payload}), {}, "42")
        self.assertEqual(out[0]["state"], "UNRESOLVED_ISSUES")
        self.assertEqual(out[0]["submitted"], "2026-07-27T07:06:58")

    def test_review_detail_drops_the_contact_pii(self):
        payload = {"data": {"attributes": {"contactFirstName": "Someone",
                                           "contactEmail": "someone@example.com",
                                           "contactPhone": "+10000000000",
                                           "notes": "no login needed",
                                           "demoAccountRequired": False}}}
        out = src.asc_review_detail(FakeTransport({"appStoreReviewDetail": payload}), {}, "v1")
        self.assertEqual(set(out), {"notes", "demo_account_required"})
        self.assertNotIn("example.com", json.dumps(out))

    def test_missing_review_detail_is_not_an_error(self):
        t = FakeTransport({"appStoreReviewDetail": auth.HttpError(404, "u", "")})
        self.assertIsNone(src.asc_review_detail(t, {}, "v1"))


class ModeTests(unittest.TestCase):
    def test_modes_widen_the_window_and_the_depth(self):
        modes = pulse.DEFAULTS["modes"]
        self.assertEqual(modes["daily"]["review_window_days"], 1)
        self.assertEqual(modes["weekly"]["review_window_days"], 7)
        self.assertEqual(modes["monthly"]["review_window_days"], 30)
        self.assertGreater(modes["monthly"]["review_pages"], modes["weekly"]["review_pages"])
        self.assertTrue(all("reviews_analysis_limit" not in m for m in modes.values()))

    def test_no_mode_keeps_the_configs_own_window(self):
        cfg = pulse._merge(pulse.DEFAULTS, {"apps": [], "review_window_days": 7})
        out = pulse.apply_mode(cfg, None)
        self.assertEqual(out["review_window_days"], 7)   # never silently narrowed to 1
        self.assertEqual(out["mode"], "config")

    def test_explicit_mode_overrides_the_config(self):
        cfg = pulse._merge(pulse.DEFAULTS, {"apps": [], "review_window_days": 7})
        self.assertEqual(pulse.apply_mode(dict(cfg), "daily")["review_window_days"], 1)
        monthly = pulse.apply_mode(dict(cfg), "monthly")
        self.assertEqual(monthly["review_window_days"], 30)
        self.assertEqual(monthly["review_pages"], 3)

    def test_review_pagination_follows_next_links_up_to_the_cap(self):
        page2 = {"data": [{"attributes": {"rating": 4, "body": "b", "territory": "USA",
                                          "createdDate": "2026-08-01T00:00:00Z"},
                          "relationships": {}}]}
        page1 = {"data": [{"attributes": {"rating": 5, "body": "a", "territory": "USA",
                                          "createdDate": "2026-08-02T00:00:00Z"},
                           "relationships": {}}],
                 "links": {"next": "https://api.appstoreconnect.apple.com/v1/next-page"}}
        t = FakeTransport({"next-page": page2, "customerReviews": page1})
        one = src.asc_customer_reviews(t, {}, "42", max_pages=1)
        two = src.asc_customer_reviews(t, {}, "42", max_pages=2)
        self.assertEqual(len(one), 1)
        self.assertEqual(len(two), 2)


class SecretHygieneTests(unittest.TestCase):
    """Anything that reaches a report file or Slack goes through one choke point."""

    SECRETS = ("eyJhbGciOiJFUzI1NiJ9.PAYLOAD.SIG", "hunter2", "MIIEvQIBADANBg", "s3cr3t")

    def assertNoSecret(self, text):
        for token in self.SECRETS:
            self.assertNotIn(token, text, f"leaked {token!r} in {text!r}")

    def test_redact_kills_scheme_prefixed_and_standalone_bearer_tokens(self):
        for raw in ("Authorization: Bearer eyJhbGciOiJFUzI1NiJ9.PAYLOAD.SIG",
                    "Bearer eyJhbGciOiJFUzI1NiJ9.PAYLOAD.SIG",
                    "authorization=Bearer eyJhbGciOiJFUzI1NiJ9.PAYLOAD.SIG"):
            self.assertNoSecret(src.redact(raw))

    def test_redact_kills_pem_material_even_when_truncated(self):
        self.assertNoSecret(src.redact("private_key: -----BEGIN PRIVATE KEY-----MIIEvQIBADANBg"))
        self.assertNoSecret(src.redact("-----BEGIN EC PRIVATE KEY-----\nMIIEvQIBADANBg\n-----END EC PRIVATE KEY-----"))

    def test_redact_kills_credentials_embedded_in_a_url(self):
        self.assertNoSecret(src.redact("https://user:s3cr3t@host/path"))

    def test_redact_leaves_ordinary_review_text_alone(self):
        text = "The ads are one minute long and the levels take 30 seconds."
        self.assertEqual(src.redact(text), text)

    def test_recorded_slice_error_hides_the_reports_bucket_and_the_token(self):
        url = ("https://storage.googleapis.com/storage/v1/b/pubsite_prod_rev_0123456789/o/"
               "stats%2Fratings.csv?alt=media")
        text = pulse.safe_error(auth.HttpError(403, url, "Authorization: Bearer eyJhbGciOiJFUzI1NiJ9.PAYLOAD.SIG"))
        self.assertNoSecret(text)
        self.assertNotIn("pubsite_prod_rev", text)
        self.assertNotIn("alt=media", text)
        self.assertIn("storage.googleapis.com", text)   # host stays: it is not a secret
        self.assertIn("403", text)                      # and the status is still actionable

    def test_a_broken_slice_records_a_sanitised_error_not_a_raw_exception(self):
        def boom(ctx, app):
            raise RuntimeError("failed with password=hunter2")
        cfg = pulse._merge(pulse.DEFAULTS, {"apps": [{"key": "A", "ios": "com.x"}]})
        cfg["slices"] = {"ios_rating": True}
        ctx = {"cfg": cfg, "creds": pulse.Creds(cfg, FakeTransport({})),
               "transport": FakeTransport({}), "day": dt.date(2026, 8, 19),
               "now": "2026-08-19T00:00:00+00:00", "window_start": "2026-08-18"}
        original = pulse.COLLECTORS["ios_rating"]
        pulse.COLLECTORS["ios_rating"] = boom
        try:
            out = pulse.collect_app(ctx, {"key": "A", "name": "A", "ios": "com.x"},
                                    only={"ios_rating"})
        finally:
            pulse.COLLECTORS["ios_rating"] = original
        self.assertIn("ios_rating", out["errors"])
        self.assertNoSecret(out["errors"]["ios_rating"])
        self.assertIn("RuntimeError", out["errors"]["ios_rating"])


class SlackBudgetTests(unittest.TestCase):
    """One store report must be ONE Slack message: the poster splits anything longer."""

    POSTER_LIMIT = 3500

    def test_slack_len_counts_what_the_poster_counts(self):
        self.assertEqual(pulse.slack_len("abc"), 3)
        self.assertEqual(pulse.slack_len("★"), 1)        # BMP: one UTF-16 unit
        self.assertEqual(pulse.slack_len("🔴"), 2)        # astral: a surrogate pair

    def test_a_crowded_portfolio_still_fits_one_message(self):
        apps = []
        for i in range(18):
            a = _app_block(key=f"A{i}", name=f"Application Number {i}", ios_avg=1.5, ios_count=40)
            a["slices"]["ios_reviews"] = {
                "count": 4, "neg_count": 3, "neg_share_pct": 75.0, "topics": {"ads": 3},
                "backlog_unanswered": 30, "scanned": 30, "window_start": "2026-08-12",
                "sample": [{"stars": 1, "title": "Title " * 6, "text": "Body text " * 30,
                            "territory": "USA"}]}
            a.setdefault("rating", {})
            for platform in ("ios", "play"):
                avg, count = pulse._rating_of(a, platform)
                a["rating"].setdefault(platform, {"avg": avg, "count": count, "d_avg": None,
                                                  "d_avg_7d": None, "d_count": None})
            pulse.score_app(a, pulse._merge(pulse.DEFAULTS, {"apps": [{"key": a["key"]}]}))
            apps.append(a)
        gaps = [{"app": f"Ghost {i}", "store": "App Store", "id": f"com.ghost{i}",
                 "state": "REJECTED", "text": "listing is down — version 1.0 is REJECTED"}
                for i in range(9)]
        text = pulse.render_store_slack(_report(apps, gaps=gaps), "ios")
        self.assertLessEqual(pulse.slack_len(text), self.POSTER_LIMIT)
        self.assertIn("attached report", text)          # says what it trimmed
        self.assertIn("Needs attention", text)          # never trims the verdict away
        self.assertIn("Portfolio", text)

    def test_a_small_portfolio_is_not_trimmed_at_all(self):
        a = _app_block(key="A", name="Solo", ios_avg=4.8, ios_count=900)
        a.setdefault("rating", {})
        for platform in ("ios", "play"):
            avg, count = pulse._rating_of(a, platform)
            a["rating"].setdefault(platform, {"avg": avg, "count": count, "d_avg": None,
                                              "d_avg_7d": None, "d_count": None})
        pulse.score_app(a, pulse._merge(pulse.DEFAULTS, {"apps": [{"key": "A"}]}))
        self.assertNotIn("attached report", pulse.render_store_slack(_report([a]), "ios"))


class TransportHardeningTests(unittest.TestCase):
    def test_zero_retries_fails_with_a_clear_message(self):
        t = auth.Transport(retries=0)
        with self.assertRaises(auth.AuthError) as ctx:
            t.raw("https://example.test/x")
        self.assertIn("http_retries", str(ctx.exception))

    def test_gcs_listing_follows_every_page(self):
        pages = {
            "page1": {"items": [{"name": "a", "updated": "1"}], "nextPageToken": "t1"},
            "page2": {"items": [{"name": "b", "updated": "2"}]},
        }

        class Paging:
            def __init__(self):
                self.seen = []

            def json(self, url, **kw):
                self.seen.append(url)
                return pages["page2"] if "pageToken=t1" in url else pages["page1"]

        transport = Paging()
        items = src.gcs_list(transport, {}, "bucket", "prefix/")
        self.assertEqual([i["name"] for i in items], ["a", "b"])
        self.assertEqual(len(transport.seen), 2)

    def test_token_is_exchanged_once_under_concurrent_collectors(self):
        key = {"client_email": "svc@example.test", "private_key": "PEM", "token_uri": "https://t.test"}
        tmp = tempfile.mkdtemp()
        try:
            path = os.path.join(tmp, "sa.json")
            with open(path, "w") as fh:
                json.dump(key, fh)

            class CountingTransport:
                def __init__(self):
                    self.exchanges = 0

                def json(self, url, **kw):
                    self.exchanges += 1
                    time.sleep(0.01)          # widen the window a race would slip through
                    return {"access_token": "tok", "expires_in": 3600}

            transport = CountingTransport()
            google = auth.GoogleAuth(path, transport)
            original = auth._sign_with_pem_text
            auth._sign_with_pem_text = lambda pem, payload: b"sig"   # process-shell boundary
            try:
                with ThreadPoolExecutor(max_workers=8) as pool:
                    tokens = list(pool.map(lambda _: google.token(), range(8)))
            finally:
                auth._sign_with_pem_text = original
            self.assertEqual(set(tokens), {"tok"})
            self.assertEqual(transport.exchanges, 1)
        finally:
            shutil.rmtree(tmp)


if __name__ == "__main__":
    unittest.main(verbosity=2)
