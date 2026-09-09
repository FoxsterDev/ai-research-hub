"""Run-budget and failed-project-retry contracts.

These lock in the 2026-09-08 incident: the host slept mid-run, the 900s run budget was measured
on time.monotonic() (mach_absolute_time on macOS, which freezes while asleep) so a 126-minute run
never tripped it, and one transient socket death on one project of twelve discarded the other
eleven and blocked the whole day's delivery.
"""
import importlib.util
import pathlib
import socket
import sys
import unittest
import urllib.error
from unittest import mock


MODULE = pathlib.Path(__file__).parents[1] / "opensearch_pulse.py"
spec = importlib.util.spec_from_file_location("opensearch_pulse_budget", MODULE)
pulse = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = pulse
spec.loader.exec_module(pulse)


class RunBudgetIsWallClockTests(unittest.TestCase):
    """The budget must bound elapsed time, not awake time."""

    def test_frozen_monotonic_clock_does_not_void_the_run_budget(self):
        # The incident's exact shape: the process is suspended, so monotonic barely advances
        # while two hours of wall clock pass. Anchoring on monotonic returned a live timeout
        # here and let the run continue; the budget must be spent.
        client = pulse.Client("https://example.invalid", {}, timeout=90,
                              deadline=1_000.0)
        with mock.patch.object(pulse.time, "monotonic", return_value=5.0), \
                mock.patch.object(pulse.time, "time", return_value=8_200.0):
            with self.assertRaises(pulse.RunDeadlineExceeded):
                client._remaining_timeout()

    def test_budget_still_available_is_clamped_to_the_remaining_wall_clock(self):
        client = pulse.Client("https://example.invalid", {}, timeout=90, deadline=1_000.0)
        with mock.patch.object(pulse.time, "time", return_value=950.0):
            self.assertEqual(client._remaining_timeout(), 50.0)
        with mock.patch.object(pulse.time, "time", return_value=100.0):
            self.assertEqual(client._remaining_timeout(), 90.0)   # capped by http_timeout

    def test_no_deadline_means_the_plain_request_timeout(self):
        client = pulse.Client("https://example.invalid", {}, timeout=90)
        self.assertEqual(client._remaining_timeout(), 90)


class SpentBudgetPreemptsTheRetryLadderTests(unittest.TestCase):
    """An out-of-time run must abort, not spend 3 x http_timeout more and then be reported as
    an unreachable project."""

    def test_run_deadline_is_not_retried_and_not_a_timeout_error(self):
        # RunDeadlineExceeded must not be a TimeoutError, or the except-tuple in _req swallows
        # the engine's own budget breach and retries it.
        self.assertFalse(issubclass(pulse.RunDeadlineExceeded, TimeoutError))
        self.assertFalse(issubclass(pulse.RunDeadlineExceeded, OSError))

        client = pulse.Client("https://example.invalid", {}, timeout=90, retries=3,
                              backoff=0, deadline=1_000.0)
        with mock.patch.object(pulse.urllib.request, "urlopen") as opened, \
                mock.patch.object(pulse.time, "time", return_value=9_999.0):
            with self.assertRaises(pulse.RunDeadlineExceeded):
                client._req("/idx/_search", {"size": 0})
        self.assertEqual(opened.call_count, 0, "a spent budget must issue no request at all")

    def test_backoff_that_would_outlast_the_budget_aborts_instead_of_sleeping(self):
        client = pulse.Client("https://example.invalid", {}, timeout=90, retries=3,
                              backoff=30, deadline=1_000.0)
        with mock.patch.object(pulse.urllib.request, "urlopen",
                               side_effect=socket.timeout("The read operation timed out")), \
                mock.patch.object(pulse.time, "time", return_value=990.0), \
                mock.patch.object(pulse.time, "sleep") as slept:
            with self.assertRaises(pulse.RunDeadlineExceeded):
                client._req("/idx/_search", {"size": 0})
        self.assertEqual(slept.call_count, 0)


class TransientClassificationTests(unittest.TestCase):
    """Transient-vs-permanent is decided at the raise site. Re-deriving it upstairs is a trap:
    under the interpreter launchd resolves (3.9) socket.timeout is not TimeoutError, so an
    isinstance() classifier passes in a shell and misreads production."""

    def _raise_through_req(self, error, retries=1):
        client = pulse.Client("https://example.invalid", {}, timeout=5, retries=retries,
                              backoff=0)
        with mock.patch.object(pulse.urllib.request, "urlopen", side_effect=error):
            try:
                client._req("/idx/_search", {"size": 0})
            except Exception as raised:      # noqa: BLE001 - the tag is what we assert
                return raised
        self.fail("expected the error to propagate")

    def test_socket_timeout_is_tagged_transient(self):
        raised = self._raise_through_req(socket.timeout("The read operation timed out"))
        self.assertTrue(getattr(raised, "pulse_transient", False))

    def test_server_side_http_error_is_tagged_transient(self):
        raised = self._raise_through_req(
            urllib.error.HTTPError("https://x", 503, "busy", {}, None))
        self.assertTrue(getattr(raised, "pulse_transient", False))

    def test_client_side_http_error_is_tagged_permanent_and_not_retried(self):
        client = pulse.Client("https://example.invalid", {}, timeout=5, retries=3, backoff=0)
        error = urllib.error.HTTPError("https://x", 404, "gone", {}, None)
        with mock.patch.object(pulse.urllib.request, "urlopen", side_effect=error) as opened:
            with self.assertRaises(urllib.error.HTTPError) as caught:
                client._req("/idx/_search", {"size": 0})
        self.assertFalse(getattr(caught.exception, "pulse_transient", True))
        self.assertEqual(opened.call_count, 1, "a permanent 404 must not be retried")

    def test_a_transient_read_timeout_inside_the_budget_is_still_retried(self):
        # Guard against over-tightening: the fix must not turn a recoverable blip into a failure.
        client = pulse.Client("https://example.invalid", {}, timeout=5, retries=3, backoff=0)
        with mock.patch.object(pulse.urllib.request, "urlopen",
                               side_effect=socket.timeout("The read operation timed out")) as opened, \
                mock.patch.object(pulse.time, "sleep"):
            with self.assertRaises(socket.timeout):
                client._req("/idx/_search", {"size": 0})
        self.assertEqual(opened.call_count, 3, "all three attempts must be spent")

    def test_a_shard_partial_is_transient_but_a_missing_index_is_not(self):
        partial = pulse.Client("https://example.invalid", {})
        with mock.patch.object(partial, "_req", return_value={
                "timed_out": True, "_shards": {"failed": 0}, "aggregations": {}}):
            with self.assertRaises(pulse.PartialSearchError) as caught:
                partial.search("logs-2026-09-08", {"size": 0})
        self.assertTrue(getattr(caught.exception, "pulse_transient", False))
        self.assertFalse(getattr(pulse.PartialSearchError("index missing"),
                                 "pulse_transient", False))


class FailedProjectRetryPassTests(unittest.TestCase):
    """One dead socket on one project must not cost the whole day - but a day that is still
    incomplete afterwards must still fail closed."""

    JOBS = [("BZ", "Blingz (Hub)", "bz-", "BZ", [], []),
            ("BS", "BallSort", "bs-", "BS", [], [])]

    def _cfg(self, **over):
        cfg = {"max_workers": 4, "retry_budget": 300, "retry_backoff": 0}
        cfg.update(over)
        return cfg

    def test_a_transient_failure_that_succeeds_on_the_second_pass_completes_the_day(self):
        projects = [
            {"key": "BZ", "name": "Blingz (Hub)",
             "error": "timeout: The read operation timed out", "transient": True},
            {"key": "BS", "name": "BallSort", "status": "healthy", "dau": 7435},
        ]

        def attempt(job, client):
            return {"key": job[0], "name": job[1], "status": "degraded", "dau": 39465}

        healed = pulse.retry_failed_projects(projects, self.JOBS, self._cfg(),
                                             attempt, pulse.Client("https://x", {}))
        self.assertEqual([p["key"] for p in healed], ["BZ", "BS"], "order is preserved")
        self.assertNotIn("error", healed[0])
        self.assertEqual(healed[0]["dau"], 39465)
        self.assertEqual([p for p in healed if "error" in p], [],
                         "no errors left means trust.complete can become true")

    def test_a_project_that_fails_twice_keeps_the_first_pass_diagnosis_and_fails_closed(self):
        first = {"key": "BZ", "name": "Blingz (Hub)",
                 "error": "timeout: The read operation timed out", "transient": True}
        projects = [first, {"key": "BS", "name": "BallSort", "status": "healthy", "dau": 1}]

        def attempt(job, client):
            return {"key": job[0], "name": job[1], "error": "TimeoutError: something vaguer"}

        out = pulse.retry_failed_projects(projects, self.JOBS, self._cfg(), attempt,
                                          pulse.Client("https://x", {}))
        self.assertEqual(out[0]["error"], "timeout: The read operation timed out")
        self.assertTrue(any("error" in p for p in out), "the day must still fail closed")

    def test_a_retry_that_raises_keeps_the_first_pass_entry(self):
        projects = [{"key": "BZ", "name": "Blingz (Hub)", "error": "timeout: x",
                     "transient": True}]

        def attempt(job, client):
            raise pulse.RunDeadlineExceeded("out of time")

        out = pulse.retry_failed_projects(projects, self.JOBS, self._cfg(), attempt,
                                          pulse.Client("https://x", {}))
        self.assertEqual(out[0]["error"], "timeout: x")

    def test_permanent_failures_are_not_retried(self):
        projects = [{"key": "BZ", "name": "Blingz (Hub)",
                     "error": "PartialSearchError: required source index missing",
                     "transient": False}]
        calls = []

        def attempt(job, client):
            calls.append(job)
            return {"key": job[0]}

        out = pulse.retry_failed_projects(projects, self.JOBS, self._cfg(), attempt,
                                          pulse.Client("https://x", {}))
        self.assertEqual(calls, [], "a missing index will not fix itself in 5 seconds")
        self.assertIn("error", out[0])

    def test_the_retry_pass_gets_a_fresh_budget_not_the_exhausted_one(self):
        projects = [{"key": "BZ", "name": "Blingz (Hub)", "error": "timeout: x",
                     "transient": True}]
        seen = {}

        def attempt(job, client):
            seen["deadline"] = client.deadline
            seen["retries"] = client.retries
            return {"key": job[0], "name": job[1], "status": "healthy", "dau": 1}

        spent = pulse.Client("https://x", {}, timeout=90, deadline=pulse.time.time() - 5_000)
        pulse.retry_failed_projects(projects, self.JOBS, self._cfg(), attempt, spent)
        self.assertGreater(seen["deadline"], pulse.time.time(),
                           "the retry must not inherit the spent first-pass budget")
        self.assertEqual(seen["retries"], 1, "the pass is one extra attempt, not another ladder")

    def test_a_zero_budget_disables_the_pass(self):
        projects = [{"key": "BZ", "name": "x", "error": "timeout: x", "transient": True}]
        calls = []
        pulse.retry_failed_projects(projects, self.JOBS, self._cfg(retry_budget=0),
                                    lambda job, client: calls.append(job),
                                    pulse.Client("https://x", {}))
        self.assertEqual(calls, [])


class FailedQueryIsNotNoDataTests(unittest.TestCase):
    """A project whose query failed must never render as an app without telemetry."""

    def test_the_overview_row_says_the_query_failed(self):
        row = {"key": "BZ", "name": "Blingz (Hub)", "overview_status": "degraded",
               "data_state": "no_data", "log_query_failed": True, "platform_overview": {}}
        rendered = pulse._overview_row(row, compact=True)
        self.assertIn("Log query FAILED", rendered)
        self.assertNotIn("No production data", rendered)

    def test_a_genuinely_silent_app_still_says_no_production_data(self):
        row = {"key": "MM", "name": "MM", "overview_status": "nodata",
               "data_state": "no_data", "log_query_failed": False, "platform_overview": {}}
        self.assertIn("No production data", pulse._overview_row(row, compact=True))


if __name__ == "__main__":
    unittest.main()
