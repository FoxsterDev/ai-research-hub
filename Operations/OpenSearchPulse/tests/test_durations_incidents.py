"""Offline tests for duration metrics and portfolio-wide incident windows.

Run: python3 -m unittest discover -s tests   (from the module directory)
"""

import datetime as dt
import importlib.util
import sys
import unittest
from pathlib import Path

MODULE_DIR = Path(__file__).parents[1]
sys.path.insert(0, str(MODULE_DIR))

spec = importlib.util.spec_from_file_location("opensearch_pulse",
                                              MODULE_DIR / "opensearch_pulse.py")
pulse = importlib.util.module_from_spec(spec)
sys.modules["opensearch_pulse"] = pulse
spec.loader.exec_module(pulse)

UTC = dt.timezone.utc


def _spec(**over):
    base = {"key": "backend_5xx", "label": "Backend HTTP 5xx", "phrases": ["HTTP/1.1 500"],
            "interval_minutes": 5, "min_users": 40, "spike_factor": 5, "max_gap_buckets": 1}
    base.update(over)
    return pulse.normalize_incidents([base])[0]


def _buckets(users, start=dt.datetime(2026, 10, 9, 21, 0, tzinfo=UTC)):
    return [(start + dt.timedelta(minutes=5 * i), u) for i, u in enumerate(users)]


class IncidentDetection(unittest.TestCase):
    def test_quiet_window_has_no_incident(self):
        b = _buckets([0, 1, 2, 0, 3, 1, 0, 0, 2, 1, 0, 0])
        self.assertEqual(pulse.detect_incident_windows(b, _spec(), b[-1][0] + dt.timedelta(minutes=5)), [])

    def test_spike_becomes_one_window_with_a_short_gap(self):
        # 22:10–22:55 like the measured outage: hot, hot, hot, quiet(43<min? no: 43>=40), …
        users = [0, 2, 150, 324, 330, 43, 193, 145, 91, 333, 23, 0, 0]
        b = _buckets(users, dt.datetime(2026, 10, 9, 22, 0, tzinfo=UTC))
        hi = b[-1][0] + dt.timedelta(minutes=5)
        windows = pulse.detect_incident_windows(b, _spec(), hi)
        self.assertEqual(len(windows), 1)
        w = windows[0]
        self.assertEqual(w["start"], dt.datetime(2026, 10, 9, 22, 10, tzinfo=UTC))
        self.assertEqual(w["end"], dt.datetime(2026, 10, 9, 22, 50, tzinfo=UTC))
        self.assertEqual(w["duration_min"], 40)
        self.assertEqual(w["peak_users"], 333)
        self.assertEqual(w["status"], "resolved")
        self.assertGreaterEqual(w["threshold_users"], 40)

    def test_touching_the_window_end_is_ongoing(self):
        users = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 120, 200]
        b = _buckets(users)
        hi = b[-1][0] + dt.timedelta(minutes=5)
        w = pulse.detect_incident_windows(b, _spec(), hi)
        self.assertEqual(len(w), 1)
        self.assertEqual(w[0]["status"], "ongoing")

    def test_two_separate_windows(self):
        users = [0, 100, 100, 0, 0, 0, 0, 90, 0, 0, 0, 0]
        b = _buckets(users)
        w = pulse.detect_incident_windows(b, _spec(), b[-1][0] + dt.timedelta(minutes=5))
        self.assertEqual([x["hot_buckets"] for x in w], [2, 1])

    def test_spike_factor_guards_a_noisy_window(self):
        # typical level 60/bucket: 100 is above min_users but not a spike
        # typical level 20/bucket: 90 is above min_users but below 5x the quiet median
        users = [20] * 10 + [90, 20]
        b = _buckets(users)
        self.assertEqual(pulse.detect_incident_windows(b, _spec(), b[-1][0] + dt.timedelta(minutes=5)), [])
        users = [20] * 10 + [100, 20]
        b = _buckets(users)
        self.assertEqual(len(pulse.detect_incident_windows(b, _spec(), b[-1][0] + dt.timedelta(minutes=5))), 1)

    def test_config_validation(self):
        with self.assertRaises(ValueError):
            pulse.normalize_incidents([{"key": "x"}])
        with self.assertRaises(ValueError):
            pulse.normalize_incidents([{"key": "x", "phrases": ["a"], "min_users": 0}])


def _window(status="resolved", users=1391):
    return {"detector": "backend_5xx", "label": "Backend HTTP 5xx", "interval_minutes": 5,
            "start": "2026-10-09T22:10:00.000Z", "end": "2026-10-09T22:55:00.000Z",
            "duration_min": 45, "users": users, "peak_users": 333, "peak_at": "2026-10-09T22:45:00.000Z",
            "hot_buckets": 8, "status": status, "threshold_users": 40.0, "typical_users": 1.0,
            "endpoints": [{"endpoint": "api/core/Login", "events": 2861, "users": 1391},
                          {"endpoint": "api/core/GetClientProperties", "events": 459, "users": 325},
                          {"endpoint": "api/core/GetUIElements", "events": 408, "users": 304},
                          {"endpoint": "api/core/GetShare", "events": 156, "users": 106}],
            "apps": [{"app": "BZ", "name": "Blingz (Hub)", "events": 2145, "users": 1100},
                     {"app": "OB", "name": "OceanBlast", "events": 213, "users": 180},
                     {"app": "BS", "name": "BallSort", "events": 187, "users": 160}],
            "messages": [{"msg": "<Server> >> 'api/core/Login' RETRY SCHEDULED ServerError: HTTP/1.1 500",
                          "events": 2861, "users": 1391}]}


def _report(windows, projects=10, error=None):
    det = {"key": "backend_5xx", "label": "Backend HTTP 5xx", "interval_minutes": 5,
           "min_users": 40, "spike_factor": 5.0, "windows": windows}
    if error:
        det["error"] = error
    return {"incidents": [det], "errors": [],
            "projects": [{"name": f"P{i}", "status": "healthy", "durations": []} for i in range(projects)]}


class IncidentRendering(unittest.TestCase):
    def test_text_names_window_users_endpoints_apps_and_status(self):
        text = pulse.incident_text({**_window(), "label": "Backend HTTP 5xx"}, total_apps=10)
        self.assertIn("22:10–22:55 UTC (45 min)", text)
        self.assertIn("1,391 users", text)
        self.assertIn("peak 333/5min", text)
        self.assertIn("api/core/Login, api/core/GetClientProperties, api/core/GetUIElements +1", text)
        self.assertIn("portfolio-wide (3 apps", text)
        self.assertTrue(text.endswith("resolved"))

    def test_ongoing_is_loud(self):
        text = pulse.incident_text({**_window("ongoing"), "label": "Backend HTTP 5xx"})
        self.assertIn("ONGOING", text)

    def test_head_lines_only_when_something_fired(self):
        self.assertEqual(pulse.incident_head_lines(_report([])), [])
        lines = pulse.incident_head_lines(_report([_window()]))
        self.assertIn("*🔴 Backend incidents (1, all resolved)*", lines)
        self.assertTrue(any("22:10–22:55 UTC" in l for l in lines))
        failed = pulse.incident_head_lines(_report([], error="boom"))
        self.assertTrue(any("not measured" in l for l in failed))

    def test_attention_and_markdown_carry_incidents(self):
        rep = _report([_window("ongoing")])
        att = pulse.build_attention(rep)
        self.assertEqual(att[0]["proj"], "Backend")
        self.assertEqual(att[0]["sev"], "degraded")
        md = "\n".join(pulse.incident_section_md(rep, detailed=True))
        self.assertIn("| Backend HTTP 5xx |", md)
        self.assertIn("ONGOING", md)
        self.assertIn("api/core/Login", md)
        quiet = "\n".join(pulse.incident_section_md(_report([])))
        self.assertIn("None detected", quiet)


def _duration_spec():
    return pulse.normalize_durations([{
        "key": "time_to_lobby", "label": "Time to lobby", "short_label": "Load time",
        "phrase": "StartupSummary", "attribute": "durationMs", "divisor": 1000, "unit": "s",
        "percentiles": [50, 90], "min_samples": 30,
        "cohorts": [{"key": "new", "label": "new install", "attributes_phrase": "sessionNumber 1 durationMs"},
                    {"key": "returning", "label": "existing", "exclude_attributes_phrase": "sessionNumber 1 durationMs"}],
        "thresholds": {"returning": {"p50": {"watch": 3, "alert": 6}, "p90": {"watch": 6, "alert": 10}}}}])[0]


def _agg_bucket(n, users, p50, p90):
    return {"doc_count": n, "u": {"value": users}, "p": {"values": {"50.0": p50, "90.0": p90}}}


class _FakeClient:
    def __init__(self, aggs):
        self.aggs = aggs
        self.bodies = []

    def search(self, index, body):
        self.bodies.append((index, body))
        return {"aggregations": self.aggs}


class DurationMetrics(unittest.TestCase):
    def setUp(self):
        self.cfg = pulse.load_config(str(MODULE_DIR / "config.example.json"))
        self.cfg["durations"] = [_duration_spec()]
        coh = {"new": _agg_bucket(693, 643, 11594.0, 31035.0),
               "returning": _agg_bucket(3557, 1367, 1616.0, 3914.0)}
        slow = {"new": _agg_bucket(10, 10, 9000.0, 20000.0),
                "returning": _agg_bucket(500, 400, 7200.0, 12000.0)}
        self.aggs = {"plat": {"buckets": [{"key": "IPhonePlayer", "doc_count": 4250, "coh": {"buckets": coh}},
                                           {"key": "Android", "doc_count": 510, "coh": {"buckets": slow}}]},
                     "all": {"coh": {"buckets": coh}}}

    def test_query_shape_regexes_the_attribute_from_source(self):
        body = pulse.duration_query(self.cfg, self.cfg["durations"][0], "APP1", "2026-10-09")
        script = body["aggs"]["plat"]["aggs"]["coh"]["aggs"]["p"]["percentiles"]["script"]["source"]
        self.assertIn("durationMs", script)
        self.assertIn("params._source['Attributes']", script)
        filters = body["aggs"]["plat"]["aggs"]["coh"]["filters"]["filters"]
        self.assertEqual(filters["new"]["bool"]["must"][0]["match_phrase"]["Attributes"], "sessionNumber 1 durationMs")
        self.assertIn("must_not", filters["returning"]["bool"])

    def test_collect_scales_and_statuses(self):
        client = _FakeClient(self.aggs)
        out = pulse.collect_durations(client, self.cfg, "shared-core-logs-", "APP1", "2026-10-09", project_key="APP1")
        self.assertEqual(len(out), 1)
        ios = out[0]["platforms"]["iOS"]["cohorts"]
        self.assertAlmostEqual(ios["returning"]["p50"], 1.62, places=2)
        self.assertAlmostEqual(ios["new"]["p90"], 31.04, places=2)
        self.assertEqual(ios["returning"]["status"], "healthy")
        self.assertEqual(ios["new"]["status"], "nodata")  # no bar configured for new installs -> no verdict
        android = out[0]["platforms"]["Android"]["cohorts"]
        self.assertEqual(android["returning"]["status"], "degraded")   # p50 7.2 s > alert 6
        self.assertFalse(android["new"]["enough_samples"])
        self.assertEqual(android["new"]["status"], "nodata")
        self.assertEqual(out[0]["status"], "degraded")

    def test_failed_query_is_reported_not_zeroed(self):
        class Boom:
            def search(self, index, body):
                raise RuntimeError("script disabled")
        out = pulse.collect_durations(Boom(), self.cfg, "shared-core-logs-", "APP1", "2026-10-09", project_key="APP1")
        self.assertIn("error", out[0])
        line = pulse.duration_line(pulse.platform_durations({"durations": out}, "iOS")[0])
        self.assertIn("query failed", line)

    def test_overview_line_and_attention(self):
        client = _FakeClient(self.aggs)
        durations = pulse.collect_durations(client, self.cfg, "shared-core-logs-", "APP1", "2026-10-09", project_key="APP1")
        project = {"name": "First App", "status": "healthy", "durations": durations}
        ios = pulse.platform_durations(project, "iOS")[0]
        line = pulse.duration_line(ios, status_wrap=pulse._overview_value)
        self.assertEqual(line, "Load time (p50/p90): new install 11.6s/31.0s · existing 1.6s/3.9s")
        compact = pulse.duration_line(ios, compact=True)
        self.assertEqual(compact, "Load time: new 11.6/31.0s · existing 1.6/3.9s")
        android = pulse.platform_durations(project, "Android")[0]
        self.assertEqual(android["status"], "degraded")
        self.assertIn("new install —", pulse.duration_line(android))
        att = pulse.build_attention({"projects": [project], "errors": [], "incidents": []})
        self.assertEqual(len(att), 1)
        self.assertIn("Time to lobby Android · existing: 7.2s/12.0s (p50/p90) — p50 7.2s > degraded 6s; p90 12.0s > degraded 10s", att[0]["text"])
        self.assertEqual(att[0]["sev"], "degraded")

    def test_baselines_from_prior_reports(self):
        client = _FakeClient(self.aggs)
        today = pulse.collect_durations(client, self.cfg, "shared-core-logs-", "APP1", "2026-10-09", project_key="APP1")
        prior = pulse.collect_durations(client, self.cfg, "shared-core-logs-", "APP1", "2026-10-08", project_key="APP1")
        prior[0]["platforms"]["iOS"]["cohorts"]["returning"]["p50"] = 1.2
        pulse.attach_duration_baselines(today, [{"durations": prior}], "saved reports")
        ret = today[0]["platforms"]["iOS"]["cohorts"]["returning"]
        self.assertEqual(ret["baseline_p50"], 1.2)
        self.assertAlmostEqual(ret["delta_p50"], 0.42, places=2)
        self.assertEqual(today[0]["baseline_source"], "saved reports")
        md = "\n".join(pulse.duration_table_md({"durations": today}))
        self.assertIn("| iOS | existing | 3,557 | 1,367 | 1.6s | 3.9s | +0.4", md)


if __name__ == "__main__":
    unittest.main()


class ReleaseComparison(unittest.TestCase):
    def _overview_cfg(self):
        return {"secondary_metrics": [
            {"key": "loading", "label": "Loading", "display_label": "Login", "kind": "funnel_rate",
             "funnel": "loading", "rate": "login success", "delta_watch_pp": 1.0, "delta_alert_pp": 3.0},
            {"key": "reward_complete", "label": "reward", "kind": "funnel_rate", "funnel": "ads",
             "rate": "rewarded completion", "delta_watch_pp": 1.0, "delta_alert_pp": 3.0}],
            "rollout_err_watch_pct": 25.0, "rollout_err_alert_pct": 50.0}

    def _project(self, login=(98.0, 98.2), rv=(86.5, 86.5), load=(3.8, 3.9)):
        def rates(label, v):
            return {"rates": [{"label": label, "pct": v}]}
        durations = [{"key": "time_to_lobby", "label": "Time to lobby", "short_label": "Load time",
                      "unit": "s", "percentiles": [50, 90],
                      "cohort_labels": {"new": "new install", "returning": "existing"},
                      "platforms": {"iOS": {"cohorts": {"returning": {"thresholds": {"p90": {"watch": 6, "alert": 10}}}},
                                            "versions": {"2.5.0": {"cohorts": {"returning": {"enough_samples": True, "p50": 1.6, "p90": load[0]}}},
                                                         "2.4.0": {"cohorts": {"returning": {"enough_samples": True, "p50": 1.5, "p90": load[1]}}}}}}}]
        return {"key": "EX", "durations": durations, "funnels": [
            {"key": "loading", "platforms": {"iOS": {"versions": {"2.5.0": rates("login success", login[0]),
                                                                  "2.4.0": rates("login success", login[1])}}}},
            {"key": "ads", "platforms": {"iOS": {"versions": {"2.5.0": rates("rewarded completion", rv[0]),
                                                              "2.4.0": rates("rewarded completion", rv[1])}}}}]}

    def _pdata(self, err=(0.2, 0.2), delta=0.0, crash=None, sufficient=True):
        return {"version": "2.5.0", "previous_version": "2.4.0", "rollout_pct": 80.0,
                "version_err_per_user": err[0], "previous_version_err_per_user": err[1],
                "version_err_delta_pct": delta, "version_sample_sufficient": sufficient,
                "metric_status": {"rollout": "nodata"}, "crash_stability": crash}

    def test_same_release_reads_as_same(self):
        rel = pulse.release_comparison(self._project(), self._pdata(), "iOS", self._overview_cfg())
        self.assertEqual(rel["verdict"], "SAME")
        texts = {m["key"]: m["delta_text"] for m in rel["metrics"]}
        self.assertEqual(texts, {"err": "=", "crash": "—", "startup": "=", "load": "=", "rv": "="})
        self.assertEqual(pulse.release_row_text(rel, rollout_pct=80.0),
                         "v2.5.0 (80%) vs 2.4.0: SAME — err = · crash — · login = · load p90 = · RV =")

    def test_alert_level_regression_is_worse(self):
        crash = {"value_pct": 0.4, "baseline_pct": 0.17, "scope": "focus", "delta_pct": 140.0, "delta_status": "degraded"}
        rel = pulse.release_comparison(self._project(), self._pdata(delta=71.0, crash=crash), "iOS", self._overview_cfg())
        self.assertEqual(rel["verdict"], "WORSE")
        self.assertEqual(rel["status"], "degraded")
        row = pulse.release_row_text(rel, rollout_pct=80.0)
        self.assertIn("*WORSE 🔴* — err *↑71% 🔴* · crash *↑140% 🔴*", row)

    def test_two_watch_regressions_are_worse_one_is_watch(self):
        rel = pulse.release_comparison(self._project(login=(96.5, 98.2)), self._pdata(delta=30.0), "iOS", self._overview_cfg())
        self.assertEqual(rel["verdict"], "WORSE")           # err watch + login -1.7 pp watch
        rel = pulse.release_comparison(self._project(), self._pdata(delta=30.0), "iOS", self._overview_cfg())
        self.assertEqual(rel["verdict"], "WATCH")

    def test_improvement_without_regression_is_better(self):
        rel = pulse.release_comparison(self._project(load=(3.0, 3.9), rv=(88.0, 86.5)), self._pdata(delta=-30.0), "iOS", self._overview_cfg())
        self.assertEqual(rel["verdict"], "BETTER")
        row = pulse.release_row_text(rel)
        self.assertIn("BETTER 🟢 — err *↓30% 🟢*", row)
        self.assertIn("load p90 *-0.9s 🟢*", row)

    def test_sample_gates_withhold_the_verdict(self):
        rel = pulse.release_comparison(self._project(), self._pdata(sufficient=False), "iOS", self._overview_cfg())
        self.assertIsNone(rel["verdict"])
        self.assertEqual(pulse.release_row_text(rel, rollout_pct=3.0), "v2.5.0 (3%) vs 2.4.0: v2.5.0 not sampled enough yet")
        rel = pulse.release_comparison(self._project(), {**self._pdata(), "previous_version": None}, "iOS", self._overview_cfg())
        self.assertEqual(rel["note"], "no previous version to compare")

    def test_minor_movement_prints_the_delta_without_a_marker(self):
        rel = pulse.release_comparison(self._project(), self._pdata(delta=15.0), "iOS", self._overview_cfg())
        err = next(m for m in rel["metrics"] if m["key"] == "err")
        self.assertEqual((err["status"], err["delta_text"]), ("minor", "↑15%"))
        self.assertEqual(rel["verdict"], "SAME")
