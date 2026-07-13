import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch


ENGINE_PATH = Path(__file__).parents[1] / "opensearch_pulse.py"
SPEC = importlib.util.spec_from_file_location("opensearch_pulse", ENGINE_PATH)
pulse = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pulse)


def signature(msg, total, users):
    return {"msg": msg, "total": total, "users": users, "pct": users, "per_user": total / users,
            "cat": "Network", "plats": [], "ver": "1.0"}


class WarningDynamicsTests(unittest.TestCase):
    def test_build_project_and_renderers_preserve_warning_dynamics(self):
        today = {
            "dau": 100, "err_total": 10, "err_users": 10, "warn_total": 30, "warn_users": 30,
            "top_errors": [signature("Error still present", 10, 10)],
            "top_warns": [signature("Warning still present", 10, 10), signature("New warning", 20, 30)],
            "errors_by_cat": [], "warns_by_cat": [], "versions": [("1.0", 100)],
            "versions_detail": [], "platforms": [], "signals": {}, "funnels_raw": {},
        }
        previous = {
            "err_per_user": 0.1, "warn_per_user": 0.1, "dau": 100, "status": "healthy",
            "top_errors": [signature("Error still present", 10, 10)],
            "top_warns": [signature("Warning still present", 10, 10), signature("Gone warning", 15, 15)],
            "versions": [("0.9", 100)],
        }
        cfg = {
            "thresholds": {"degraded_pct": 40, "watch_pct": 15, "new_release_min_share": 0.02},
            "min_dau": 1, "hygiene": {"default": {"verdict": "review"}}, "funnels": [],
        }

        with patch.object(pulse, "collect_day", return_value=today):
            project = pulse.build_project(
                client=None, cfg=cfg, key="APP", name="App", prefix="logs-", app_id=None,
                report_day="2026-07-12", os_base_dates=[], operation_base_dates=[], prior_by_date={"2026-07-11": {"APP": previous}},
                disk_dates_desc=["2026-07-11"], n=3,
            )

        self.assertEqual(30.0, project["top_warn_reach"])
        self.assertEqual("New warning", project["top_warn_reach_msg"])
        self.assertEqual(["New warning"], [item["msg"] for item in project["appeared_warnings"]])
        self.assertEqual(["Gone warning"], [item["msg"] for item in project["disappeared_warnings"]])

        report = {
            "brand": {"org": "Test", "product": "Pulse"}, "report_day": "2026-07-12",
            "overall_status": "healthy", "window_utc": "test", "baseline_days": 3,
            "baseline_source": "saved reports", "baseline_dates": ["2026-07-11"], "generated_utc": "test",
            "signals_meta": {}, "source": "test", "projects": [project],
        }
        slack = pulse.render_slack(report)
        dashboard = pulse.render_inner(report)
        card = pulse.project_card(project, {})
        markdown = pulse.render_md(report, {})
        self.assertIn("30 warn (0.3/user (+200%), worst 30.0% DAU)", slack)
        self.assertIn("New warning signatures today", slack)
        self.assertIn("worst warn %", dashboard)
        self.assertIn("worst warning", card)
        self.assertIn("Top warning", markdown)

    def test_operation_flow_separates_terminal_retry_and_transport_classes(self):
        class Client:
            def __init__(self):
                self.responses = [
                    {"aggregations": {"dau": {"value": 1000}, "outcomes": {"buckets": {
                        "success": {"doc_count": 800, "users": {"value": 700}},
                        "failure": {"doc_count": 2, "users": {"value": 2}},
                        "retry": {"doc_count": 5, "users": {"value": 3}},
                    }}}},
                    {"hits": {"total": {"value": 7}, "hits": [
                        {"_source": {"Message": "endpoint FAILED", "Attributes": '{"httpCode":0,"errorKind":"Transport","errorType":"Timeout"}'}},
                        {"_source": {"Message": "endpoint FAILED", "Attributes": '{"httpCode":0,"errorKind":"Transport"}'}},
                        {"_source": {"Message": "endpoint RETRY SCHEDULED", "Attributes": '{"httpCode":0,"errorKind":"Transport"}'}},
                    ]}, "aggregations": {
                        "hours": {"buckets": [{"key": 1, "key_as_string": "2026-07-12T16:00:00.000Z", "doc_count": 7}]},
                        "versions": {"buckets": [{"key": "1.2.3", "doc_count": 7, "users": {"value": 3}}]},
                        "platforms": {"buckets": [{"key": "Android", "doc_count": 7, "users": {"value": 3}}]},
                    }},
                ]

            def search(self, _index, _body):
                return self.responses.pop(0)

        cfg = {
            "fields": {"time": "TimeUTC", "user": "UUID.keyword", "app_id": "AppId.keyword",
                       "message_text": "Message", "attributes": "Attributes", "version": "GameVersion.keyword",
                       "platform": "Platform.keyword", "category": "Category.keyword"},
            "server_type": {"field": "ServerType.keyword", "value": "Prod"},
        }
        flow = {
            "key": "catalog", "label": "Catalog", "scope": {"message_phrase": "endpoint"},
            "success": "SUCCEEDED", "failure": "FAILED", "retry": "RETRY SCHEDULED",
            "thresholds": {"terminal_failure_watch_pct": 0.5, "terminal_failure_alert_pct": 1,
                           "retry_reach_watch_pct_dau": 0.2, "retry_reach_alert_pct_dau": 1},
        }
        result = pulse.collect_operation_flow(Client(), cfg, "logs-", "BZ", "2026-07-12", {}, flow, 1000)

        self.assertEqual(0.249, result["terminal_failure_rate_pct"])
        self.assertEqual(0.3, result["retry_reach_pct_dau"])
        self.assertEqual("watch", result["status"])
        self.assertEqual({"transport_timeout": 1, "transport_failure": 1}, result["classes"]["failure"])
        self.assertEqual({"transport_failure": 1}, result["classes"]["retry"])
        self.assertEqual("2026-07-12T16:00:00.000Z", result["drilldown"]["hours"][0]["hour"])
        html = pulse.operation_section({"operations": [{"key": "tango", "label": "Tango", "flows": [result]}]})
        self.assertIn("0.249%", html)
        self.assertIn("Transport timeout", html)

    def test_operation_baseline_prefers_saved_daily_blocks(self):
        current = [{"key": "tango", "label": "Tango", "flows": [{
            "key": "catalog", "terminal_failure_rate_pct": 0.3, "retry_reach_pct_dau": 1.2,
        }]}]
        profile = {"key": "tango", "flows": [{"key": "catalog", "baseline_days": 2}]}
        prior = {
            "2026-07-11": {"BZ": {"operations": [{"key": "tango", "flows": [{
                "key": "catalog", "terminal_failure_rate_pct": 0.2, "retry_reach_pct_dau": 1.0,
            }]}]}},
            "2026-07-10": {"BZ": {"operations": [{"key": "tango", "flows": [{
                "key": "catalog", "terminal_failure_rate_pct": 0.1, "retry_reach_pct_dau": 0.5,
            }]}]}},
        }
        pulse.attach_operation_baselines(
            client=None, cfg={"operations": [profile], "operation_baseline_days": 7}, key="BZ",
            prefix="logs-", app_id="BZ", operations=current, prior_by_date=prior,
            disk_dates_desc=["2026-07-11", "2026-07-10"], operation_base_dates=[],
        )
        flow = current[0]["flows"][0]
        self.assertEqual("saved reports", flow["baseline"]["source"])
        self.assertEqual(0.15, flow["baseline"]["terminal_failure_rate_pct"])
        self.assertEqual(0.75, flow["baseline"]["retry_reach_pct_dau"])
        self.assertEqual(100.0, flow["terminal_failure_delta_pct"])
        self.assertEqual(60.0, flow["retry_reach_delta_pct"])


if __name__ == "__main__":
    unittest.main()
