"""Offline tests for the cross-source health panel.

The panel joins this engine's log metrics with a snapshot written by the store reporter,
so the interesting cases are all about the join: which snapshot is used, what happens when
there is none, and which ratios are allowed to exist given that Apple's numbers are
iOS-only while DAU is not.

Run: python3 -m unittest discover -s tests   (from the module directory)
"""

import datetime as dt
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

MODULE_DIR = Path(__file__).parents[1]
sys.path.insert(0, str(MODULE_DIR))

spec = importlib.util.spec_from_file_location("opensearch_pulse",
                                              MODULE_DIR / "opensearch_pulse.py")
pulse = importlib.util.module_from_spec(spec)
sys.modules["opensearch_pulse"] = pulse
spec.loader.exec_module(pulse)


def _project(key="EX", name="Example App", dau=1000, ios_users=600, status="healthy",
             err_per_user=3.5, funnels=None):
    return {"key": key, "name": name, "status": status, "dau": dau,
            "platform_users": ({"iOS": ios_users, "Android": dau - ios_users}
                               if ios_users is not None else {}),
            "err_per_user": err_per_user, "err_per_user_base": err_per_user / 1.12,
            "err_per_user_delta_pct": 12.0,
            "err_pct_users": 29.0, "top_error_reach": 12.5,
            # the rest is what render_slack reads; the panel itself ignores them
            "err_total": 3500, "warn_total": 9000, "warn_per_user": 9.0,
            "warn_per_user_delta_pct": -6.0, "top_warn_reach": 15.8, "fresh_pct": 14.0,
            "prior_status": None, "new_releases": [], "operations": [], "hygiene": [],
            "impact": [], "appeared_errors": [], "disappeared_errors": [],
            "appeared_warnings": [], "disappeared_warnings": [],
            "top_errors": [], "top_warns": [], "low_data": [],
            "funnels": funnels if funnels is not None else [
                {"key": "loading", "label": "Loading (server boot)",
                 "rates": [{"label": "login success", "pct": 98.0}],
                 "platforms": {
                     "iOS": {"rates": [{"label": "login success", "pct": 97.0}]},
                     "Android": {"rates": [{"label": "login success", "pct": 99.0}]},
                 }},
                {"key": "startup", "label": "Startup / login", "rates": [{"label": "startup success",
                                                        "pct": 91.0}],
                 "platforms": {
                     "iOS": {"stages": [{"key": "entry", "label": "StartGame",
                                            "users": 590, "total": 2400, "pct": 98.3}]},
                     "Android": {"stages": [{"key": "entry", "label": "StartGame",
                                                "users": 390, "total": 1500, "pct": 97.5}]},
                 }}]}


def _store_app(key="EX", rating=4.25, rate=3.0, d=0.5, sessions=12000.0, crashes=36.0,
               perf=True):
    slices = {"ios_release": {
        "current": {"version": "2.5.0", "state": "READY_FOR_DISTRIBUTION"},
        "phased": None,
    }}
    if sessions is not None:
        slices["ios_analytics"] = {
            "metrics": {"sessions": {"value": sessions}, "crashes": {"value": crashes}},
            "derived": {"crashes_per_1k_sessions": rate}, "pending": None}
    else:
        slices["ios_analytics"] = {"metrics": {"crashes": {"value": None,
                                                          "no_instance": True}},
                                   "derived": {}, "pending": "registered, waiting"}
    if perf:
        slices["ios_perf"] = {"version": "2.4.1", "metrics": {
            "hang": {"label": "Hang rate", "unit": "seconds/hour", "value": 15.6,
                     "watch": 10.0, "alert": 20.0},
            "launch": {"label": "Launch time", "unit": "ms", "value": 1747.0,
                       "watch": 2000.0, "alert": 3000.0}}}
    return {"key": key, "name": "Example App", "slices": slices,
            "rating": {"ios": {"avg": rating, "count": 1250, "d_avg": -0.01},
                       "play": {"avg": None, "count": None, "d_avg": None}},
            "status_by_store": {"ios": "watch"},
            "crash_delta": ({"rate": rate, "d": d, "d_7d": 0.9, "sessions": sessions,
                             "between_versions": {"version": "1.63.1", "rate": 3.4,
                                                  "prev_version": "1.62.0", "prev_rate": 2.6,
                                                  "delta": 0.8, "delta_pct": 30.8}}
                            if sessions is not None else
                            {"rate": None, "d": None, "d_7d": None, "sessions": 0,
                             "between_versions": None})}


def _report(projects=None, health=None):
    return {"projects": projects if projects is not None else [_project()],
            "brand": {"org": "Example Org", "product": "Production Pulse"},
            "overview": {"portfolio_name": "Hyperfan", "default_family": "Hyperfan",
                         "family_by_app": {},
                         "primary_flow": {"key": "video_grid", "label": "VideoGrid Flow",
                                          "kind": "funnel_rate", "funnel": "video_grid",
                                          "rate": "completion"},
                         "secondary_metrics": [
                             {"key": "loading", "label": "load", "kind": "funnel_rate",
                              "funnel": "loading", "rate": "login success"}]},
            "report_day": "2026-08-26", "window_utc": "2026-08-26 00:00 → 2026-08-27 00:00",
            "baseline_days": 3, "baseline_dates": ["2026-08-25"],
            "baseline_source": "saved reports", "overall_status": "healthy",
            "generated_utc": "2026-08-27 05:30 UTC", "source": "prod",
            "errors": [], "is_last_complete": True, "health": health}


class StoreSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.cfg = {"store_snapshot": {"dir": self.tmp, "slug": "store_pulse",
                                       "max_age_days": 3}}

    def _write(self, day, payload=None):
        with open(os.path.join(self.tmp, f"store_pulse_{day}.json"), "w") as fh:
            json.dump(payload if payload is not None else {"apps": []}, fh)

    def test_history_none_ignores_undelivered_dry_run_files(self):
        self.assertEqual(pulse.load_health_history(
            self.tmp, "prod_pulse_12h", "2026-08-27T2200Z",
            kind="rolling", through="none"), [])

    def test_the_newest_snapshot_wins_even_when_it_postdates_the_log_day(self):
        """The store half is a current-state reading generated the morning after the log day.

        A strict "not after the report day" rule dropped the entire store half every real
        run, so the newest snapshot wins and its own date is reported instead.
        """
        self._write("2026-08-24")
        self._write("2026-08-26")
        self._write("2026-08-27")
        snap, why = pulse.load_store_snapshot(self.cfg, None, "2026-08-26")
        self.assertIsNone(why)
        self.assertEqual(snap["day"], "2026-08-27")
        self.assertEqual(snap["age_days"], -1)          # negative = read after the log window

    def test_a_snapshot_far_ahead_of_the_report_day_is_refused(self):
        self._write("2026-09-10")
        snap, why = pulse.load_store_snapshot(self.cfg, None, "2026-08-26")
        self.assertIsNone(snap)
        self.assertIn("ahead of the report day", why)

    def test_a_pinned_snapshot_still_obeys_the_date_window(self):
        self._write("2026-09-10")
        path = os.path.join(self.tmp, "store_pulse_2026-09-10.json")
        snap, why = pulse.load_store_snapshot(self.cfg, None, "2026-08-26", pinned=path)
        self.assertIsNone(snap)
        self.assertIn("ahead of the report day", why)

    def test_a_pinned_snapshot_that_does_not_exist_is_reported(self):
        snap, why = pulse.load_store_snapshot(
            self.cfg, None, "2026-08-26",
            pinned=os.path.join(self.tmp, "store_pulse_2026-01-01.json"))
        self.assertIsNone(snap)
        self.assertIn("does not exist", why)

    def test_a_rolling_report_id_uses_its_calendar_day_for_store_freshness(self):
        self._write("2026-08-27")
        snap, why = pulse.load_store_snapshot(
            self.cfg, None, "2026-08-27T2030Z")
        self.assertIsNone(why)
        self.assertEqual("2026-08-27", snap["day"])
        self.assertEqual(0, snap["age_days"])

    def test_an_invalid_report_id_degrades_the_join_instead_of_crashing(self):
        self._write("2026-08-27")
        snap, why = pulse.load_store_snapshot(self.cfg, None, "not-a-report-id")
        self.assertIsNone(snap)
        self.assertIn("invalid report day", why)

    def test_the_technical_section_is_read_from_beside_the_snapshot(self):
        self._write("2026-08-26")
        with open(os.path.join(self.tmp, "store_pulse_2026-08-26.technical.slack.txt"), "w") as fh:
            fh.write("*From the stores*\n• hang rate 20.2 seconds/hour\n")
        snap, _ = pulse.load_store_snapshot(self.cfg, None, "2026-08-26")
        self.assertEqual(snap["technical_section"][0], "*From the stores*")

    def test_out_of_bounds_store_submetric_is_suppressed(self):
        self._write("2026-08-27", {"apps": [{"key": "EX", "slices": {"ios_analytics": {
            "as_of": "2026-09-10", "metrics": {"crashes": {"value": 99}},
            "derived": {"crashes_per_1k_sessions": 9.9}}}}]})
        snap, why = pulse.load_store_snapshot(self.cfg, None, "2026-08-26")
        self.assertIsNone(why)
        analytics = snap["report"]["apps"][0]["slices"]["ios_analytics"]
        self.assertIsNone(analytics["metrics"]["crashes"]["value"])
        self.assertTrue(analytics["metrics"]["crashes"]["date_out_of_bounds"])
        self.assertEqual(analytics["derived"], {})
        self.assertFalse(snap["report"]["trust"]["complete"])

    def test_a_stale_snapshot_is_refused_with_its_age(self):
        self._write("2026-08-01")
        snap, why = pulse.load_store_snapshot(self.cfg, None, "2026-08-26")
        self.assertIsNone(snap)
        self.assertIn("2026-08-01", why)
        self.assertIn("older than the report day", why)

    def test_no_snapshot_and_no_config_are_both_reported_not_raised(self):
        snap, why = pulse.load_store_snapshot(self.cfg, None, "2026-08-26")
        self.assertIsNone(snap)
        self.assertIn("no store_pulse_*.json", why)
        snap, why = pulse.load_store_snapshot({}, None, "2026-08-26")
        self.assertIsNone(snap)
        self.assertIn("no store snapshot configured", why)

    def test_a_corrupt_snapshot_degrades_instead_of_failing_the_log_report(self):
        with open(os.path.join(self.tmp, "store_pulse_2026-08-26.json"), "w") as fh:
            fh.write("{not json")
        snap, why = pulse.load_store_snapshot(self.cfg, None, "2026-08-26")
        self.assertIsNone(snap)
        self.assertIn("could not read", why)

    def test_a_relative_dir_resolves_against_the_config_directory(self):
        sub = os.path.join(self.tmp, "Store", "Reports")
        os.makedirs(sub)
        with open(os.path.join(sub, "store_pulse_2026-08-26.json"), "w") as fh:
            json.dump({"apps": []}, fh)
        cfg = {"store_snapshot": {"dir": "Store/Reports"}}
        snap, why = pulse.load_store_snapshot(cfg, self.tmp, "2026-08-26")
        self.assertIsNone(why)
        self.assertEqual(snap["day"], "2026-08-26")


class HealthJoinTests(unittest.TestCase):
    def _health(self, projects=None, apps=None, day="2026-08-26"):
        snapshot = None if apps is None else {"day": day, "age_days": 0,
                                             "report": {"apps": apps}}
        return pulse.build_health(_report(projects), snapshot)

    def test_the_join_is_by_app_key_and_carries_both_sides(self):
        row = self._health(apps=[_store_app()])["rows"][0]
        self.assertTrue(row["in_store_report"])
        self.assertEqual(row["dau"], 1000)
        self.assertEqual(row["rating"], 4.25)
        self.assertEqual(row["crash_per_1k_sessions"], 3.0)

    def test_ios_only_ratios_use_the_ios_dau_not_the_total(self):
        row = self._health(apps=[_store_app(sessions=12000.0, crashes=36.0)])["rows"][0]
        self.assertAlmostEqual(row["sessions_per_ios_dau"], 20.0)          # 12000 / 600
        self.assertAlmostEqual(row["crashes_per_1k_ios_dau"], 60.0)        # 36 / 600 * 1000
        self.assertAlmostEqual(row["ios_share_pct"], 60.0)

    def test_without_an_ios_dau_the_cross_source_ratios_are_omitted(self):
        rows = self._health(projects=[_project(ios_users=None)],
                            apps=[_store_app()])["rows"]
        self.assertIsNone(rows[0]["ios_share_pct"])
        self.assertIsNone(rows[0]["sessions_per_ios_dau"])
        self.assertIsNone(rows[0]["crashes_per_1k_ios_dau"])
        self.assertEqual(rows[0]["crash_per_1k_sessions"], 3.0)   # Apple's own ratio survives

    def test_a_project_absent_from_the_store_report_keeps_its_log_metrics(self):
        row = self._health(apps=[_store_app(key="OTHER")])["rows"][0]
        self.assertFalse(row["in_store_report"])
        self.assertEqual(row["err_per_user"], 3.5)
        self.assertIsNone(row["rating"])

    def test_with_no_snapshot_at_all_the_log_columns_still_build(self):
        rows = self._health()["rows"]
        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0]["rating"])
        self.assertFalse(rows[0]["in_store_report"])

    def test_the_worst_device_metric_is_the_one_furthest_past_its_bar(self):
        row = self._health(apps=[_store_app()])["rows"][0]
        self.assertEqual(row["worst_device_metric"]["label"], "Hang rate")

    def test_startup_success_beats_a_login_success_earlier_in_the_funnels(self):
        row = self._health(apps=[_store_app()])["rows"][0]
        self.assertEqual(row["startup"]["label"], "startup success")
        self.assertEqual(row["startup"]["pct"], 91.0)

    def test_with_no_startup_rate_the_first_success_rate_is_used(self):
        project = _project(funnels=[{"label": "Ads", "rates": [{"label": "reward-grant rate",
                                                               "pct": 98.0}]},
                                    {"label": "Loading",
                                     "rates": [{"label": "login success", "pct": 97.0}]}])
        row = self._health(projects=[project], apps=[_store_app()])["rows"][0]
        self.assertEqual(row["startup"]["label"], "login success")


class TechnicalMessageBudgetTests(unittest.TestCase):
    """Going over one message turns the three-message structure into four without saying so."""

    def _big_report(self, projects=25, signatures=40):
        report = _report([_project(key=f"P{i}", name=f"Project{i}", dau=1000 + i,
                                  status="watch")
                          for i in range(projects)])
        for p in report["projects"]:
            p["appeared_errors"] = [{"msg": f"Some very long error signature number {n} "
                                            f"with plenty of text", "total": 500 + n,
                                     "pct": 1.5}
                                    for n in range(signatures)]
            p["disappeared_errors"] = [{"msg": f"Resolved signature {n}", "total": 100}
                                       for n in range(5)]
        report["health"] = pulse.build_health(report, None)
        return report

    def test_a_huge_report_still_fits_one_message(self):
        text = pulse.compose_technical_message(self._big_report())
        self.assertLessEqual(pulse.slack_len(text), pulse.SLACK_ONE_MESSAGE_BUDGET)
        self.assertIn("technical report", text)          # the header always survives

    def test_a_huge_store_section_cannot_push_it_over(self):
        section = [f"• store line {i} with a fair amount of text on it" for i in range(120)]
        text = pulse.compose_technical_message(self._big_report(), section)
        self.assertLessEqual(pulse.slack_len(text), pulse.SLACK_ONE_MESSAGE_BUDGET)

    def test_the_trim_note_counts_the_facts_not_the_lines_it_happened_to_hold(self):
        # 40 new signatures per project; the block only ever holds 5, so a note that says
        # "+5" would contradict the header the reader just read
        text = pulse.compose_technical_message(self._big_report(projects=2, signatures=40))
        self.assertIn("New error signatures (80)", text)
        self.assertNotIn("+5 new signatures", text)
        # whether it was trimmed or merely capped at build time, the shortfall is stated
        # and the number agrees with the header
        self.assertTrue("+75 more in the attached report" in text
                        or "all 80 new signatures are in the attached report" in text
                        or "+80 new signatures in the attached report" in text, text)


class PortfolioOverviewTests(unittest.TestCase):
    def _overview(self, projects=None, apps=None, thresholds=None):
        report = _report(projects)
        snapshot = {"day": "2026-08-26", "age_days": 0,
                    "report": {"apps": apps or [], "thresholds": thresholds or {}}}
        report["health"] = pulse.build_health(report, snapshot)
        return report

    @staticmethod
    def _with_ios_focus(project, version="2.5.0"):
        project["release_cohorts"] = {"iOS": {
            "current": {"ver": version, "rollout_pct": 80.0, "dau": 480,
                        "err_per_user": 0.2},
            "previous": {"ver": "2.4.0", "rollout_pct": 20.0, "dau": 120,
                         "err_per_user": 0.2},
            "err_per_user_delta_pct": 0.0,
        }}
        return project

    def test_every_project_uses_one_fixed_row_and_missing_cells_are_visible(self):
        report = self._overview(
            projects=[_project(), _project(key="BS", name="BallSort")],
            apps=[_store_app(), _store_app(key="BS")])
        text = pulse.render_status_slack(report)
        self.assertEqual(text.count("Example App"), 1)
        self.assertEqual(text.count("BallSort"), 1)
        self.assertNotIn("Needs attention", text)
        self.assertNotIn("Healthy (", text)
        self.assertNotIn("🟢 *Example App*", text)
        self.assertNotIn("VideoGrid", text)
        self.assertIn("Loading: StartGame 2.4k events (100% ref) · load 97.0%", text)
        self.assertIn("Loading: StartGame 1.5k events (100% ref) · load 99.0%", text)
        self.assertIn("*iOS* · DAU 600 · App Store", text)
        self.assertIn("*Android* · DAU 400 · Google Play", text)
        self.assertIn("Loading: StartGame 2.4k events (100% ref) · load 97.0%", text)
        self.assertIn("Loading: StartGame 1.5k events (100% ref) · load 99.0%", text)
        self.assertNotIn("DAU 600 · StartGame", text)
        self.assertNotIn("Traffic", text)
        self.assertIn("App Store: Live v2.5.0 · Rating 4.25★ (1.2k)", text)
        self.assertIn("Google Play: — · Rating —", text)
        self.assertIn("Stability: Crash rate 0.30% all versions · ANR rate —", text)
        self.assertIn("• *BallSort*", text)

    def test_start_game_is_not_inferred_from_a_server_boot_stage(self):
        project = _project()
        project["funnels"] = [f for f in project["funnels"] if f.get("key") != "startup"]
        report = self._overview(projects=[project], apps=[_store_app()])
        text = pulse.render_status_slack(report)
        self.assertEqual(2, text.count("Loading: StartGame —"))
        self.assertNotIn("DAU 600 · StartGame", text)

    def test_start_game_events_and_users_are_distinct_denominators(self):
        report = self._overview(apps=[_store_app()])
        ios = report["health"]["rows"][0]["platform_overview"]["iOS"]
        self.assertEqual(2400, ios["start_game_events"])
        self.assertEqual(590, ios["start_game_users"])

    def test_inactive_project_is_one_store_state_line_without_empty_metric_scaffolding(self):
        report = self._overview(projects=[] , apps=[_store_app(key="NEW")])
        row = report["health"]["rows"][0]
        row["data_state"] = "no_data"
        row["overview_status"] = "nodata"
        row["name"] = "New Project"
        text = pulse.render_status_slack(report)
        self.assertIn("◻ *New Project* · No production data · "
                      "App Store: Live v2.5.0 · Google Play: —", text)
        self.assertNotIn("DAU —", text)
        self.assertNotIn("Loading: StartGame —", text)
        self.assertNotIn("Stability: Crash rate", text)

    def test_rewarded_funnel_names_every_stage_and_end_to_end_rate(self):
        text = pulse._platform_flows({"flows": [
            {"key": "reward_complete", "available": True, "value": 90.8,
             "status": "healthy", "denominator": 23592, "numerator": 21432},
            {"key": "reward_grant", "available": True, "value": 94.9,
             "status": "watch", "denominator": 21432, "numerator": 20335},
        ]}, compact=True)
        self.assertIn("Rewarded: 23.6k started → 21.4k completed (91% Δ—)", text)
        self.assertIn("→ 20.3k rewarded (*95%* Δ—) · End-to-end: 86% Δ—", text)
        self.assertNotIn("\n    End-to-end", text)

    def test_a_platform_threshold_marks_the_project_and_the_exact_metric(self):
        app = _store_app()
        app["slices"]["play_vitals"] = {
            "metrics": {"userPerceivedCrashRate": 1.0,
                        "userPerceivedAnrRate": 0.2}}
        report = self._overview(
            apps=[app], thresholds={"play_crash_alert_pct": 0.5,
                                    "play_anr_alert_pct": 0.47,
                                    "watch_fraction": 0.6})
        text = pulse.render_status_slack(report)
        self.assertIn("🔴 *Example App*", text)
        self.assertIn("Stability: Crash rate *1.00% 🔴* all versions · "
                      "ANR rate 0.20% all versions", text)
        self.assertNotIn("*0.20%", text)

    def test_store_state_is_platform_context_and_android_is_not_inferred_from_traffic(self):
        report = self._overview(apps=[_store_app()])
        platforms = report["health"]["rows"][0]["platform_overview"]
        self.assertEqual("Live", platforms["iOS"]["store_state"])
        self.assertEqual("2.5.0", platforms["iOS"]["store_version"])
        self.assertEqual("—", platforms["Android"]["store_state"])
        self.assertIsNone(platforms["Android"]["store_version"])

    def test_each_platform_title_uses_its_own_store_rating(self):
        app = _store_app(rating=4.25)
        app["rating"]["play"] = {"avg": 3.2, "count": 4200, "d_avg": 0.02}
        report = self._overview(apps=[app])
        text = pulse.render_status_slack(report)
        self.assertIn("App Store: Live v2.5.0 · Rating 4.25★ (1.2k)", text)
        self.assertIn("Google Play: — · Rating 3.20★ (4.2k)", text)

    def test_store_release_states_are_rendered_in_plain_business_language(self):
        expected = {
            "IN_REVIEW": "In review",
            "REJECTED": "Rejected",
            "PREPARE_FOR_SUBMISSION": "Pre-release",
            "REMOVED_FROM_SALE": "Not listed",
        }
        for raw, label in expected.items():
            with self.subTest(raw=raw):
                app = _store_app()
                app["slices"]["ios_release"]["current"]["state"] = raw
                report = self._overview(apps=[app])
                platform = report["health"]["rows"][0]["platform_overview"]["iOS"]
                self.assertEqual(label, platform["store_state"])

    def test_ios_crash_rate_is_presented_as_percent_but_thresholds_keep_per_1k_units(self):
        report = self._overview(apps=[_store_app(rate=3.0)])
        platform = report["health"]["rows"][0]["platform_overview"]["iOS"]
        self.assertEqual(3.0, platform["crash_rate"])
        self.assertEqual("/1k sessions", platform["crash_rate_unit"])
        self.assertEqual(0.3, platform["crash_rate_pct"])
        self.assertIn("Stability: Crash rate 0.30% all versions · ANR rate —",
                      pulse.render_status_slack(report))

    def test_stability_line_is_always_present_when_store_metrics_are_missing(self):
        report = self._overview(apps=[])
        text = pulse.render_status_slack(report)
        self.assertEqual(2, text.count("Stability: Crash rate — · ANR rate —"))

    def test_ios_stability_falls_back_to_latest_measured_release_while_focus_is_pending(self):
        app = _store_app(sessions=None)
        app["crash_delta"]["versions"] = [
            {"version": "2.4.0", "rate": 2.4, "sessions": 12000, "crashes": 29},
        ]
        report = self._overview(
            projects=[self._with_ios_focus(_project())], apps=[app])
        text = pulse.render_status_slack(report)
        self.assertIn(
            "Stability: Crash rate 0.24% @ v2.4.0 (v2.5.0 pending) · ANR rate —",
            text)
        self.assertNotIn("🔴 *Example App*", text)

    def test_ios_stability_compares_sampled_focus_with_weighted_previous_release_average(self):
        app = _store_app(sessions=None)
        app["crash_delta"]["versions"] = [
            {"version": "2.5.0", "rate": 4.0, "sessions": 1000, "crashes": 4},
            {"version": "2.4.0", "rate": 2.0, "sessions": 2000, "crashes": 4},
            {"version": "2.3.0", "rate": 1.0, "sessions": 1000, "crashes": 1},
        ]
        report = self._overview(
            projects=[self._with_ios_focus(_project())], apps=[app])
        text = pulse.render_status_slack(report)
        self.assertIn(
            "Crash rate 0.40% @ v2.5.0 vs 0.17% previous 2-version avg (*↑140% 🔴*)",
            text)
        self.assertIn("🔴 *Example App*", text)

    def test_android_stability_uses_newest_sampled_version_code_and_previous_average(self):
        app = _store_app(sessions=None)
        app["slices"]["play_vitals"] = {
            "metrics": {"userPerceivedCrashRate": 0.4,
                        "userPerceivedAnrRate": 0.1},
            "users": 5000,
            "sets": {
                "crash": {"breakdown": [
                    {"dims": {"versionCode": "205"},
                     "metrics_pct": {"userPerceivedCrashRate": 0.6,
                                     "distinctUsers": 1000}},
                    {"dims": {"versionCode": "204"},
                     "metrics_pct": {"userPerceivedCrashRate": 0.3,
                                     "distinctUsers": 2000}},
                ]},
                "anr": {"breakdown": [
                    {"dims": {"versionCode": "205"},
                     "metrics_pct": {"userPerceivedAnrRate": 0.1,
                                     "distinctUsers": 1000}},
                    {"dims": {"versionCode": "204"},
                     "metrics_pct": {"userPerceivedAnrRate": 0.08,
                                     "distinctUsers": 2000}},
                ]},
            },
        }
        report = self._overview(apps=[app], thresholds={
            "min_vitals_users": 100, "play_crash_alert_pct": 0.5,
            "play_anr_alert_pct": 0.47, "watch_fraction": 0.6,
        })
        text = pulse.render_status_slack(report)
        self.assertIn("Crash rate *0.60% 🔴* @ build 205 vs 0.30% prod avg ", text)
        self.assertIn("ANR rate 0.10% @ build 205 vs 0.08% prod avg", text)

    def test_android_store_state_comes_from_the_release_catalog(self):
        app = _store_app()
        app["slices"]["play_release_catalog"] = {"tracks": [
            {"track": "production", "releases": [
                {"name": "0.36.1", "codes": ["50248293"]},
                {"name": "0.37.2", "codes": ["52059486"]}]},
            {"track": "internal", "releases": [{"name": "0.37.3", "codes": ["52070000"]}]},
        ], "version_names": {"52059486": {"name": "0.37.2", "track": "production"}}}
        report = self._overview(apps=[app])
        platform = report["health"]["rows"][0]["platform_overview"]["Android"]
        self.assertEqual("Live", platform["store_state"])
        self.assertEqual("0.37.2", platform["store_version"])   # newest serving code wins
        self.assertIn("Google Play: Live v0.37.2", pulse.render_status_slack(report))

    def test_android_catalog_without_a_production_release_says_so(self):
        app = _store_app()
        app["slices"]["play_release_catalog"] = {"tracks": [
            {"track": "internal", "releases": [{"name": "155434 (15.54.34)",
                                                "codes": ["155434"]}]}],
            "version_names": {}}
        report = self._overview(apps=[app])
        platform = report["health"]["rows"][0]["platform_overview"]["Android"]
        self.assertEqual("No production release", platform["store_state"])
        self.assertIsNone(platform["store_version"])
        self.assertEqual("15.54.34", pulse._play_release_display("155434 (15.54.34)", "155434"))

    def test_catalog_name_confirms_the_build_and_a_zero_baseline_shows_the_absolute_move(self):
        app = _store_app(sessions=None)
        app["slices"]["play_release_catalog"] = {"tracks": [
            {"track": "production", "releases": [{"name": "0.37.2", "codes": ["52059486"]}]}],
            "version_names": {"52059486": {"name": "0.37.2", "track": "production"}}}
        app["slices"]["play_vitals"] = {
            "metrics": {"userPerceivedCrashRate": 0.0, "userPerceivedAnrRate": 0.7},
            "users": 1100,
            "sets": {
                "crash": {"breakdown": [
                    {"dims": {"versionCode": "52059486"},
                     "metrics_pct": {"userPerceivedCrashRate": 0.0, "distinctUsers": 1000}},
                    {"dims": {"versionCode": "50248293"},
                     "metrics_pct": {"userPerceivedCrashRate": 0.0, "distinctUsers": 100}}]},
                "anr": {"breakdown": [
                    {"dims": {"versionCode": "52059486"},
                     "metrics_pct": {"userPerceivedAnrRate": 0.77, "distinctUsers": 1000}},
                    {"dims": {"versionCode": "50248293"},
                     "metrics_pct": {"userPerceivedAnrRate": 0.0, "distinctUsers": 100}}]},
            }}
        project = _project()
        project["release_cohorts"] = {"Android": {
            "current": {"ver": "0.37.2", "rollout_pct": 90.0, "dau": 1400,
                        "err_per_user": 0.8},
            "previous": {"ver": "0.36.1", "rollout_pct": 10.0, "dau": 100,
                         "err_per_user": 0.6}}}
        report = self._overview(projects=[project], apps=[app], thresholds={
            "min_vitals_users": 100, "play_crash_alert_pct": 1.09,
            "play_anr_alert_pct": 0.47, "watch_fraction": 0.6})
        text = pulse.render_status_slack(report)
        self.assertIn("Crash rate 0.00% @ v0.37.2 (build 52059486) "
                      "vs 0.00% prod avg (+0.00 pp)", text)
        self.assertIn("ANR rate *0.77% 🔴* @ v0.37.2 (build 52059486) "
                      "vs 0.00% prod avg (+0.77 pp)", text)
        self.assertNotIn("(v0.37.2 pending)", text)

    def test_a_test_track_build_is_never_the_focus_nor_in_the_prod_pool(self):
        app = _store_app(sessions=None)
        app["slices"]["play_release_catalog"] = {"tracks": [
            {"track": "production", "releases": [{"name": "2.5.0", "codes": ["205"]}]},
            {"track": "internal", "releases": [{"name": "2.6.0-int", "codes": ["206"]}]}],
            "version_names": {"205": {"name": "2.5.0", "track": "production"},
                              "206": {"name": "2.6.0-int", "track": "internal"}}}
        app["slices"]["play_vitals"] = {"metrics": {}, "users": 3300, "sets": {
            "crash": {"breakdown": [
                {"dims": {"versionCode": "206"},
                 "metrics_pct": {"userPerceivedCrashRate": 5.0, "distinctUsers": 300}},
                {"dims": {"versionCode": "205"},
                 "metrics_pct": {"userPerceivedCrashRate": 0.6, "distinctUsers": 1000}},
                {"dims": {"versionCode": "204"},
                 "metrics_pct": {"userPerceivedCrashRate": 0.3, "distinctUsers": 2000}}]},
            "anr": {"breakdown": []}}}
        report = self._overview(apps=[app], thresholds={
            "min_vitals_users": 100, "play_crash_alert_pct": 1.09,
            "play_anr_alert_pct": 0.47, "watch_fraction": 0.6})
        stability = report["health"]["rows"][0]["platform_overview"]["Android"]["crash_stability"]
        self.assertEqual("205", stability["version"])
        self.assertEqual(["204"], stability["baseline_versions"])
        self.assertEqual(["206"], stability["non_production_builds"])
        text = pulse.render_status_slack(report)
        self.assertIn("Crash rate 0.60% @ v2.5.0 (build 205) vs 0.30% prod avg", text)
        self.assertIn("non-prod build sampled: 206", text)

    def test_android_all_versions_rate_moves_against_the_prior_days_average(self):
        app = _store_app(sessions=None)
        app["slices"]["play_vitals"] = {
            "metrics": {"userPerceivedCrashRate": 0.30, "userPerceivedAnrRate": 0.50},
            "users": 5000,
            "sets": {
                "crash": {"as_of": "2026-08-26", "pct": {"userPerceivedCrashRate": 0.30},
                          "trail": {"2026-08-23": {"userPerceivedCrashRate": 0.10},
                                    "2026-08-24": {"userPerceivedCrashRate": 0.20},
                                    "2026-08-25": {"userPerceivedCrashRate": 0.30},
                                    "2026-08-20": {"userPerceivedCrashRate": 9.0}},
                          "breakdown": []},
                "anr": {"as_of": "2026-08-26", "pct": {"userPerceivedAnrRate": 0.50},
                        "trail": {}, "breakdown": []}}}
        report = self._overview(apps=[app], thresholds={
            "play_crash_alert_pct": 1.09, "play_anr_alert_pct": 0.47, "watch_fraction": 0.6})
        platform = report["health"]["rows"][0]["platform_overview"]["Android"]
        self.assertEqual(3, platform["crash_period"]["days"])     # only the 3 prior days count
        self.assertAlmostEqual(0.10, platform["crash_period"]["delta_pp"])
        self.assertIsNone(platform["anr_period"]["delta_pp"])
        text = pulse.render_status_slack(report)
        self.assertIn("all versions: crash 0.30% ↑0.10 pp · ANR 0.50% Δ—", text)

    def test_temporal_trigger_prints_the_exact_breached_bar(self):
        project = _project(status="degraded", err_per_user=1.0)
        project["err_per_user_base"] = 0.64
        project["err_per_user_delta_pct"] = 56.0
        report = self._overview(projects=[project])
        text = pulse.render_status_slack(report)
        self.assertIn("• *Example App*", text)
        self.assertIn("errors/user 1.00 (*↑56%*)", text)
        self.assertNotIn("🔴 *Example App*", text)

    def test_absolute_error_level_can_still_make_a_project_critical(self):
        project = _project(status="degraded", err_per_user=12.0)
        project["err_per_user_base"] = 15.0
        project["err_per_user_delta_pct"] = -20.0
        project["status_components"] = {"absolute_errors": "degraded",
                                         "trend": "healthy", "traffic": "healthy"}
        report = self._overview(projects=[project])
        text = pulse.render_status_slack(report)
        self.assertIn("🔴 *Example App*", text)
        self.assertIn("errors/user *12.00 🔴*", text)

    def test_current_portfolio_shape_uses_slack_safe_parts_without_dropping_apps(self):
        projects = [_project(key=f"P{i}", name=f"Project{i}", dau=1000 + i)
                    for i in range(15)]
        report = self._overview(projects=projects)
        parts = pulse.render_status_slack_parts(report)
        self.assertTrue(all(pulse.slack_len(part) <= pulse.SLACK_ONE_MESSAGE_BUDGET
                            for part in parts))
        text = "\n".join(parts)
        for i in range(15):
            self.assertIn(f"Project{i}", text)

    def test_oversized_portfolio_splits_only_between_project_cards(self):
        projects = [_project(key=f"P{i}", name=f"Project{i}", dau=1000 + i)
                    for i in range(40)]
        report = self._overview(projects=projects)
        parts = pulse.render_status_slack_parts(report)
        self.assertGreater(len(parts), 1)
        self.assertTrue(all(pulse.slack_len(part) <= pulse.SLACK_ONE_MESSAGE_BUDGET
                            for part in parts))
        joined = "\n".join(parts)
        for i in range(40):
            self.assertEqual(joined.count(f"*Project{i}*"), 1)
        self.assertTrue(all("*Projects · part " in part for part in parts))

    def test_projects_are_sorted_by_total_dau_descending(self):
        projects = [
            _project(key="SM", name="Small", dau=100),
            _project(key="LG", name="Large", dau=5000),
            _project(key="MD", name="Medium", dau=900),
        ]
        text = pulse.render_status_slack(self._overview(projects=projects))
        self.assertLess(text.index("*Large*"), text.index("*Medium*"))
        self.assertLess(text.index("*Medium*"), text.index("*Small*"))
        self.assertIn("\n\n────────────────────────\n\n• *Medium*", text)
        self.assertIn("\n\n────────────────────────\n\n• *Small*", text)

    def test_project_cards_have_one_solid_divider_between_them(self):
        projects = [_project(key=f"P{i}", name=f"Project{i}", dau=1000 + i)
                    for i in range(6)]
        parts = pulse.render_status_slack_parts(self._overview(projects=projects))
        self.assertEqual(len(projects) - len(parts),
                         sum(part.count("────────────────────────") for part in parts))

    def test_overview_has_metric_directions_without_prescribed_decisions(self):
        projects = [_project(key=f"P{i}", name=f"Project{i}", dau=1000 + i)
                    for i in range(15)]
        report = self._overview(projects=projects)
        pulse.apply_overview_context(report, [])
        parts = pulse.render_status_slack_parts(report)
        self.assertTrue(all(pulse.slack_len(part) <= pulse.SLACK_ONE_MESSAGE_BUDGET
                            for part in parts))
        text = "\n".join(parts)
        self.assertIn("err ↑worse/↓better", text)
        self.assertNotIn("Decisions now", text)
        self.assertNotIn(" → _", text)
        self.assertNotIn("investigate", text.lower())
        self.assertNotIn("hold", text.lower())
        self.assertNotIn("decisions", report["health"])
        for i in range(15):
            self.assertIn(f"Project{i}", text)

    def test_boot_to_login_keeps_precision_and_md_explains_the_denominator(self):
        report = self._overview()
        ios = report["health"]["rows"][0]["platform_overview"]["iOS"]
        loading = next(m for m in ios["flows"] if m["key"] == "loading")
        loading.update({"value": 99.7, "numerator": 14862, "denominator": 14904})
        slack = pulse.render_status_slack(report)
        markdown = pulse.render_status_md(report)
        self.assertIn("Loading: StartGame 2.4k events (100% ref) · load 99.7%", slack)
        self.assertNotIn("· load 100%", slack)
        self.assertIn("14,904 boot users", markdown)
        self.assertIn("Login reached: **14,862 users**", markdown)
        self.assertIn("not correlated launch conversions or TTI", markdown)

    def test_loading_subflow_adds_human_names_for_ready_events(self):
        project = _project(key="BZ")
        project["funnels"].append({
            "key": "hub_loading_ux", "label": "Loading UX completion (Blingz)",
            "rates": [],
            "platforms": {
                "iOS": {"rates": [
                    {"label": "home ready reach", "pct": 94.1, "num": 14765,
                     "den": 15694, "num_stage": "home_ready", "den_stage": "boot"},
                    {"label": "popups settled reach", "pct": 92.8, "num": 14559,
                     "den": 15694, "num_stage": "popups_settled", "den_stage": "boot"},
                ]},
                "Android": {"rates": [
                    {"label": "home ready reach", "pct": 97.2, "num": 8377,
                     "den": 8619, "num_stage": "home_ready", "den_stage": "boot"},
                    {"label": "popups settled reach", "pct": 94.0, "num": 8106,
                     "den": 8619, "num_stage": "popups_settled", "den_stage": "boot"},
                ]},
            },
        })
        project["funnel_applicability"] = {"loading": True, "hub_loading_ux": True}
        report = _report([project])
        report["overview"]["secondary_metrics"] += [
            {"key": "home_ready", "label": "Home ready", "display_label": "Home ready",
             "kind": "funnel_rate", "funnel": "hub_loading_ux", "rate": "home ready reach"},
            {"key": "popups_settled", "label": "Popups settled", "display_label": "Popups settled",
             "kind": "funnel_rate", "funnel": "hub_loading_ux", "rate": "popups settled reach"},
        ]
        report["health"] = pulse.build_health(report, {"day": "2026-08-26", "age_days": 0,
                                                        "report": {"apps": []}})
        slack = pulse.render_status_slack(report)
        self.assertIn("Loading: StartGame 2.4k events (100% ref) · load 97.0% Δ— · "
                      "Home ready 94.1% Δ— · Popups settled 92.8% Δ—", slack)
        self.assertNotIn("APP_READY", slack)
        markdown = pulse.render_status_md(report)
        self.assertIn("source `APP_READY`", markdown)
        self.assertIn("source `APP_POPUPS_SETTLED`", markdown)

    def test_funnel_baseline_is_an_average_and_delta_is_percentage_points(self):
        funnels = [{"key": "loading", "platforms": {"iOS": {"rates": [
            {"label": "login success", "pct": 97.5},
        ]}}}]
        key = pulse._funnel_rate_key("loading", "iOS", "login success")
        pulse.attach_funnel_baselines(funnels, {key: 98.2}, 3, "prior windows")
        rate = funnels[0]["platforms"]["iOS"]["rates"][0]
        self.assertEqual(98.2, rate["baseline_pct"])
        self.assertEqual(-0.7, rate["delta_pp"])
        self.assertEqual(3, rate["baseline_periods"])

    def test_flow_delta_colors_only_meaningful_moves(self):
        self.assertEqual("±0", pulse._flow_delta_text(
            {"delta_pp": 0.0, "delta_status": "healthy"}))
        self.assertEqual("*▲1.2% 🟢*".replace("%", ""), pulse._flow_delta_text(
            {"delta_pp": 1.2, "delta_status": "improved"}))
        self.assertEqual("▼0.4", pulse._flow_delta_text(
            {"delta_pp": -0.4, "delta_status": "healthy"}))
        self.assertEqual("*▼3.2 🔴*", pulse._flow_delta_text(
            {"delta_pp": -3.2, "delta_status": "degraded"}))

    def test_delta_color_appears_only_after_the_meaningful_threshold(self):
        self.assertEqual(pulse._error_delta(-26.0, "healthy", 15.0), "*↓26% 🟢*")
        self.assertEqual(pulse._error_delta(-5.0, "healthy", 15.0), "↓5%")
        self.assertEqual(pulse._error_delta(50.0, "degraded", 15.0), "*↑50% 🔴*")
        self.assertEqual(pulse._error_delta(20.0, "watch", 15.0), "*↑20%*")
        self.assertEqual(pulse._volume_delta(12.0, "healthy", 40.0), "▲12%")

    def test_version_rollout_query_keeps_real_platform_cohorts(self):
        cfg = {
            "fields": {"user": "user", "app_id": "app", "level": "level",
                       "message_keyword": "message.keyword", "message_text": "message",
                       "category": "category", "platform": "platform",
                       "version": "version", "time": "@timestamp"},
            "server_type": {"field": "server", "value": None},
            "levels": {"error": "Error", "warn": "Warn"},
            "signals": {}, "funnels": [],
        }
        query = pulse.day_query(cfg, day="2026-08-26")
        platform = query["aggs"]["versions"]["aggs"]["plat"]
        self.assertIn("users", platform["aggs"])
        self.assertIn("err", platform["aggs"])

    def test_funnel_query_keeps_stage_counts_by_platform(self):
        cfg = {
            "fields": {"user": "user", "app_id": "app", "level": "level",
                       "message_keyword": "message.keyword", "message_text": "message",
                       "category": "category", "platform": "platform",
                       "version": "version", "time": "@timestamp"},
            "server_type": {"field": "server", "value": None},
            "levels": {"error": "Error", "warn": "Warn"}, "signals": {},
            "funnels": [{"key": "loading", "stages": [
                {"key": "start", "label": "Start", "phrase": "start"},
                {"key": "done", "label": "Done", "phrase": "done"}]}],
        }
        query = pulse.day_query(cfg, day="2026-08-26")
        self.assertIn("by_platform", query["aggs"]["funnels"]["aggs"])

    def test_project_adapter_maps_raw_events_to_the_same_canonical_stage(self):
        cfg = {
            "fields": {"user": "user", "app_id": "app", "level": "level",
                       "message_keyword": "message.keyword", "message_text": "message",
                       "category": "category", "platform": "platform",
                       "version": "version", "time": "@timestamp"},
            "server_type": {"field": "server", "value": None},
            "levels": {"error": "Error", "warn": "Warn"}, "signals": {},
            "funnels": [{"key": "ads", "stages": [
                {"key": "rv_show", "label": "Rewarded shown",
                 "phrase": "Showing Rewarded", "category": "Ads"}],
                "stage_overrides_by_app": {"SR": {"rv_show": {
                    "phrase": "RewardedVideoAdOpenedEvent", "category": "Ads"}}}}],
        }
        shared = pulse.day_query(cfg, day="2026-08-26", project_key="BZ")
        solitaire = pulse.day_query(cfg, day="2026-08-26", project_key="SR")
        shared_match = shared["aggs"]["funnels"]["filters"]["filters"]["ads::rv_show"]
        solitaire_match = solitaire["aggs"]["funnels"]["filters"]["filters"]["ads::rv_show"]
        self.assertEqual(shared_match["bool"]["must"][0]["match_phrase"]["message"],
                         "Showing Rewarded")
        self.assertEqual(solitaire_match["bool"]["must"][0]["match_phrase"]["message"],
                         "RewardedVideoAdOpenedEvent")

    def test_project_adapter_can_merge_multiple_raw_phrases_into_one_stage(self):
        fields = {"message_text": "message", "category": "category", "level": "level"}
        query = pulse.stage_filter(fields, {
            "key": "done", "phrases": ["RewardedEvent", "RewardGrantedEvent"]})
        message_clause = query["bool"]["must"][0]["bool"]
        self.assertEqual(message_clause["minimum_should_match"], 1)
        self.assertEqual(len(message_clause["should"]), 2)

    def test_platform_funnels_use_platform_counts_and_platform_dau(self):
        cfg = {"funnels": [{"key": "loading", "label": "Loading", "stages": [
            {"key": "start", "label": "Start"}, {"key": "done", "label": "Done"}],
            "rates": [{"label": "success", "num": "done", "den": "start",
                       "good": "high", "good_at": 97, "bad_at": 90}]}]}
        today = {
            "funnels_raw": {"loading::start": {"users": 100, "total": 100},
                            "loading::done": {"users": 85, "total": 85}},
            "funnels_platform_raw": {
                "loading::start": {"iOS": {"users": 40, "total": 40},
                                   "Android": {"users": 60, "total": 60}},
                "loading::done": {"iOS": {"users": 38, "total": 38},
                                  "Android": {"users": 47, "total": 47}}},
            "platform_users": {"iOS": 50, "Android": 70},
        }
        funnel = pulse.assemble_funnels(cfg, today, 120, "EX")[0]
        self.assertEqual(funnel["platforms"]["iOS"]["rates"][0]["pct"], 95.0)
        self.assertEqual(funnel["platforms"]["Android"]["rates"][0]["pct"], 78.3)

    def test_impossible_funnel_ratio_is_data_quality_not_project_health(self):
        project = _project()
        project["funnels"][0]["rates"][0].update(
            {"pct": 101.0, "data_quality": "numerator_exceeds_denominator"})
        for platform in ("iOS", "Android"):
            project["funnels"][0]["platforms"][platform]["rates"][0].update(
                {"pct": 101.0, "data_quality": "numerator_exceeds_denominator"})
        report = self._overview(projects=[project])
        text = pulse.render_status_slack(report)
        self.assertIn("• *Example App*", text)
        self.assertIn("telemetry mismatch", text)
        self.assertNotIn("⚠ *Example App*", text)

    def test_single_release_cohort_has_no_version_delta(self):
        current = {"ver": "1.0", "err_per_user": 0.4}
        self.assertEqual(pulse.release_error_delta(current, None), (None, None))

    def test_release_cohort_delta_compares_with_previous_version(self):
        current = {"ver": "2.0", "err_per_user": 1.5}
        previous = {"ver": "1.0", "err_per_user": 1.0}
        self.assertEqual(pulse.release_error_delta(current, previous), (0.5, 50.0))

    def test_observed_release_cohort_uses_version_order_not_largest_traffic(self):
        cohort = pulse.select_observed_release_cohort([
            {"ver": "1.60.3", "dau": 7178, "err_per_user": 3.37},
            {"ver": "1.63.1", "dau": 1824, "err_per_user": 0.77},
        ])
        self.assertEqual(cohort["current"]["ver"], "1.63.1")
        self.assertEqual(cohort["previous"]["ver"], "1.60.3")
        self.assertEqual(cohort["err_per_user_delta_pct"], -77.2)
        self.assertEqual(cohort["selection"], "newest sufficiently sampled versions")

    def test_tiny_newer_test_build_does_not_replace_sampled_focus_version(self):
        cohort = pulse.select_observed_release_cohort([
            {"ver": "1.64.0", "dau": 12, "rollout_pct": 0.2, "err_per_user": 9.0},
            {"ver": "1.63.2", "dau": 2000, "rollout_pct": 30.0, "err_per_user": 0.8},
            {"ver": "1.63.1", "dau": 4000, "rollout_pct": 60.0, "err_per_user": 1.0},
            {"ver": "1.60.3", "dau": 5000, "rollout_pct": 80.0, "err_per_user": 2.0},
        ], min_cohort_dau=100, min_rollout_pct=1.0)
        self.assertEqual(cohort["current"]["ver"], "1.63.2")
        self.assertEqual(cohort["previous"]["ver"], "1.63.1")
        self.assertEqual(cohort["err_per_user_delta_pct"], -20.0)
        self.assertEqual([v["ver"] for v in cohort["excluded_newer_versions"]], ["1.64.0"])

    def test_unorderable_versions_suppress_previous_version_delta(self):
        cohort = pulse.select_observed_release_cohort([
            {"ver": "release-blue", "dau": 700, "err_per_user": 2.0},
            {"ver": "release-green", "dau": 300, "err_per_user": 1.0},
        ])
        self.assertEqual(cohort["current"]["ver"], "release-blue")
        self.assertIsNone(cohort["previous"])
        self.assertIsNone(cohort["err_per_user_delta_pct"])
        self.assertEqual(cohort["selection"], "release order unknown")

    def test_ios_rollout_uses_highest_released_version_not_list_or_traffic_order(self):
        project = _project()
        project["versions_detail"] = [
            {"ver": "1.9", "plat": "iOS", "dau": 500, "rollout_pct": 83.3,
             "err_per_user": 1.0},
            {"ver": "2.0", "plat": "iOS", "dau": 100, "rollout_pct": 16.7,
             "err_per_user": 1.6},
        ]
        project["release_cohorts"] = {"iOS": {
            "current": project["versions_detail"][0], "previous": project["versions_detail"][1],
            "err_per_user_delta_pct": -37.5, "selection": "largest live cohort"}}
        app = _store_app()
        app["slices"]["ios_release"] = {"versions": [
            {"version": "1.9", "state": "READY_FOR_DISTRIBUTION"},
            {"version": "2.0", "state": "READY_FOR_DISTRIBUTION"},
        ]}
        report = self._overview(projects=[project], apps=[app])
        ios = report["health"]["rows"][0]["platform_overview"]["iOS"]
        self.assertEqual(ios["version"], "2.0")
        self.assertEqual(ios["previous_version"], "1.9")
        self.assertEqual(ios["rollout_pct"], 16.7)
        self.assertEqual(ios["version_err_delta_pct"], 60.0)
        self.assertEqual(ios["cohort_selection"], "newest sufficiently sampled versions")


class HealthRenderTests(unittest.TestCase):
    def _report_with_health(self, apps=None, projects=None, snapshot_day="2026-08-26"):
        # "watch" so the panel renders a detailed row: healthy projects collapse to one line
        report = _report(projects if projects is not None else [_project(status="watch")])
        snapshot = None if apps is None else {"day": snapshot_day, "age_days": 0,
                                              "report": {"apps": apps}}
        report["health"] = pulse.build_health(report, snapshot)
        return report

    def test_the_panel_leads_the_message_and_names_its_sources(self):
        text = pulse.render_slack(self._report_with_health(apps=[_store_app()]))
        head, panel = text.split("*Per-project metrics", 1)
        self.assertIn("technical report", head)
        self.assertNotIn("Needs attention", head)      # the panel comes first
        self.assertIn("store data 2026-08-26", panel)
        self.assertIn("1,000 DAU", panel)
        self.assertIn("iOS crash 3.00/1k sess", panel)
        self.assertIn("20.0 sess/iOS user", panel)
        self.assertIn("startup success 91%", panel)

    def test_a_sub_one_percent_ios_share_is_not_printed_as_zero(self):
        report = self._report_with_health(
            projects=[_project(dau=2000, ios_users=3, status="watch")], apps=[_store_app()])
        self.assertIn("iOS 0.1%", pulse.render_slack(report))

    def test_a_handful_of_ios_users_produces_no_cross_source_ratio(self):
        report = self._report_with_health(
            projects=[_project(dau=2000, ios_users=3, status="watch")], apps=[_store_app()])
        row = report["health"]["rows"][0]
        self.assertIsNone(row["sessions_per_ios_dau"])
        self.assertIsNone(row["crashes_per_1k_ios_dau"])
        text = pulse.render_slack(report)
        self.assertNotIn("sess/iOS user", text)
        self.assertIn("iOS crash 3.00/1k sess", text)   # Apple's own ratio is unaffected

    def test_the_worst_device_metric_keeps_its_decimal(self):
        text = pulse.render_slack(self._report_with_health(apps=[_store_app()]))
        self.assertIn("hang rate 15.6 seconds/hour", text)

    def test_a_movement_below_the_printed_precision_is_not_shown(self):
        self.assertEqual(pulse._health_move(-0.001), "")
        self.assertEqual(pulse._health_move(0), "")
        self.assertEqual(pulse._health_move(None), "")
        self.assertEqual(pulse._health_move(-0.31), " ▼0.31")

    def test_a_pending_crash_rate_says_pending_rather_than_going_silent(self):
        # uniform across the portfolio: stated once, in the panel note
        report = self._report_with_health(apps=[_store_app(sessions=None)])
        self.assertIn("registered, waiting", pulse.render_slack(report))

    def test_a_mixed_pending_state_is_marked_on_the_row_that_is_waiting(self):
        report = self._report_with_health(
            projects=[_project(status="watch"),
                      _project(key="BS", name="BallSort", status="watch")],
            apps=[_store_app(), _store_app(key="BS", sessions=None)])
        panel = "\n".join(pulse.render_health_slack(report))
        self.assertIn("iOS crash pending", panel)          # only BallSort is waiting
        self.assertIn("iOS crash 3.00/1k sess", panel)     # the other has real data

    def test_the_missing_store_reason_reaches_the_reader(self):
        report = _report()
        report["health"] = pulse.build_health(report, None)
        report["health"]["store_unavailable"] = "no store snapshot configured"
        text = pulse.render_slack(report)
        self.assertIn("no store data (no store snapshot configured)", text)
        self.assertIn("Not in the store report", text)

    def test_healthy_projects_collapse_into_one_line_with_their_numbers(self):
        report = self._report_with_health(
            projects=[_project(status="healthy"), _project(key="BS", name="BallSort",
                                                          dau=6617, status="healthy")],
            apps=[_store_app()])
        panel = "\n".join(pulse.render_health_slack(report))
        self.assertIn("*Healthy (2):*", panel)
        self.assertIn("BallSort (6,617 DAU", panel)
        self.assertNotIn("users hit an error", panel)   # the detail is in the .md

    def test_a_uniform_analytics_wait_is_stated_once_not_per_row(self):
        report = self._report_with_health(
            projects=[_project(status="watch"), _project(key="BS", name="BallSort",
                                                        status="watch")],
            apps=[_store_app(sessions=None), _store_app(key="BS", sessions=None)])
        panel = "\n".join(pulse.render_health_slack(report))
        self.assertEqual(panel.count("registered, waiting"), 1)
        self.assertNotIn("iOS crash pending", panel)

    def test_the_markdown_table_states_the_ios_only_denominator_rule(self):
        md = "\n".join(pulse.render_health_md(self._report_with_health(apps=[_store_app()])))
        self.assertIn("## Portfolio health — logs joined with the stores", md)
        self.assertIn("iOS-only", md)
        self.assertIn("| crashes /1k iOS users |", md)
        self.assertIn("iOS crash rate between releases", md)
        self.assertIn("| 1.63.1 | 3.40 | 1.62.0 | 2.60 | +0.80 |", md)


if __name__ == "__main__":
    unittest.main(verbosity=2)
