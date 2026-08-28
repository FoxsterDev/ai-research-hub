#!/usr/bin/env python3
"""OpenSearch Pulse — a generic, config-driven daily health reporter.

Model: report a single day (the report day) and compare it to a baseline = the
N complete days before it. Baseline is taken from prior report JSONs already on
disk in the output dir when available (so history is reused and we learn which
signatures appeared/disappeared); only when no prior report covers a project is
the baseline pulled from OpenSearch. Read-only: only _cat/_search.

Per project, for the report day:
  - DAU: distinct users (config 'user' field, e.g. UUID)
  - errors / warnings: TOTAL events + affected users + % of that day's DAU
  - top error/warning signatures: each with total, affected users, % of DAU
  - errors/warns by category, custom message signals
  - versions in prod tagged by platform (iOS / Android)
  - diff %: report-day error/warn rate vs the baseline daily average
  - appeared / disappeared signatures vs recent history

Outputs (never posts anywhere): <slug>_<day>.{json,html,inner.html,slack.txt,md}
The .md is a structured, fix-oriented report (context + sample stacktraces) meant
to be handed to an AI or engineer for triage and fixes.

Usage: python3 opensearch_pulse.py --config <cfg.json> [--out DIR] [--day YYYY-MM-DD] [--baseline-days N]
"""

import argparse
import datetime as dt
import email.utils
import glob
import html
import json
import os
import re
import socket
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from report_safety import atomic_write_json, atomic_write_text, redact as safety_redact, safe_error

DATE_RE = re.compile(r"^(.*-)(\d{4})-(\d{2})-(\d{2})$")
PLATFORM_LABELS = {"IPhonePlayer": "iOS", "iOS": "iOS", "Android": "Android",
                   "OSXEditor": "Editor", "WindowsEditor": "Editor"}


def plat_label(p):
    return PLATFORM_LABELS.get(p, p or "Other")


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else 0.0


# ------------------------------------------------------------------ config

def load_config(path):
    with open(path) as f:
        cfg = json.load(f)
    cfg.setdefault("baseline_days", cfg.get("window_days", 3))
    cfg.setdefault("max_workers", 8)
    cfg.setdefault("http_timeout", 120)
    cfg.setdefault("http_retries", 3)
    cfg.setdefault("run_timeout", 900)
    cfg.setdefault("min_dau", 100)
    cfg.setdefault("signals", {})
    cfg.setdefault("operations", [])  # config-driven endpoint/provider health sections
    cfg.setdefault("funnels", [])          # business-metric funnels (phrase-counted stages)
    cfg.setdefault("funnel_top_dau", None)  # if set, only the top-N DAU projects render funnels
    cfg.setdefault("funnels_summary_note", "")  # HTML note under the funnels summary (org copy lives in config)
    cfg.setdefault("md_observations", [])       # trailing md bullets (org-specific observations live in config)
    overview = cfg.setdefault("overview", {})
    overview.setdefault("default_family", cfg.get("brand", {}).get("org", "Portfolio"))
    overview.setdefault("family_by_app", {})
    overview.setdefault("secondary_metrics", [])
    overview.setdefault("rollout_min_cohort_dau", 100)
    overview.setdefault("rollout_min_pct", 1.0)
    overview.setdefault("rollout_err_watch_absolute", 0.5)
    overview.setdefault("rollout_err_alert_absolute", 2.0)
    overview.setdefault("rollout_excess_events_watch", 100)
    overview.setdefault("rollout_excess_events_alert", 1000)
    overview.setdefault("stability_regression_watch_pct", 25.0)
    overview.setdefault("stability_regression_alert_pct", 50.0)
    hy = cfg.setdefault("hygiene", {})     # shared issue rule table (log-sanitation + impact bar)
    hy.setdefault("rules", [])
    hy.setdefault("default", {"verdict": "review"})
    cfg.setdefault("levels", {"error": "Error", "warn": "Warn"})
    cfg.setdefault("sources", [])
    th = cfg.setdefault("thresholds", {})
    th.setdefault("degraded_pct", 40)
    th.setdefault("watch_pct", 15)
    th.setdefault("absolute_err_per_user_watch", 5.0)
    th.setdefault("absolute_err_per_user_degraded", 10.0)
    th.setdefault("dau_drop_watch_pct", 40.0)
    th.setdefault("dau_drop_degraded_pct", 70.0)
    th.setdefault("new_release_min_share", 0.02)
    b = cfg.setdefault("brand", {})
    b.setdefault("org", "OpenSearch")
    b.setdefault("product", "Production Pulse")
    F = cfg.setdefault("fields", {})
    F.setdefault("level", "LogLevel.keyword")
    F.setdefault("message_keyword", "Message.keyword")
    F.setdefault("message_text", "Message")
    F.setdefault("category", "Category.keyword")
    F.setdefault("user", "UUID.keyword")
    F.setdefault("app_id", "AppId.keyword")
    F.setdefault("version", "GameVersion.keyword")
    F.setdefault("platform", "Platform.keyword")
    F.setdefault("attributes", "Attributes")
    F.setdefault("stacktrace", "Stacktrace")
    F.setdefault("device", "DeviceModel")
    F.setdefault("time", "TimeUTC")  # timestamp field; bounds the report day to exact UTC 00:00–24:00
    st = cfg.setdefault("server_type", {})
    st.setdefault("field", "ServerType.keyword")
    st.setdefault("value", "")
    if not cfg["sources"]:
        raise ValueError("config must declare at least one source")
    if cfg["baseline_days"] < 1 or cfg["max_workers"] < 1 or cfg["http_retries"] < 1:
        raise ValueError("baseline_days, max_workers and http_retries must be positive")
    if th["degraded_pct"] < th["watch_pct"]:
        raise ValueError("thresholds.degraded_pct must be >= thresholds.watch_pct")
    if th["absolute_err_per_user_degraded"] < th["absolute_err_per_user_watch"]:
        raise ValueError("absolute error degraded threshold must be >= watch threshold")
    if th["dau_drop_degraded_pct"] < th["dau_drop_watch_pct"]:
        raise ValueError("DAU-drop degraded threshold must be >= watch threshold")
    return cfg


def resolve_base_url(cfg):
    if cfg.get("base_url"):
        return cfg["base_url"]
    env = cfg.get("base_url_env")
    if env and os.environ.get(env):
        return os.environ[env]
    raise SystemExit("No endpoint: set 'base_url' or export the var named by 'base_url_env'.")


def resolve_headers(cfg):
    headers = {"Content-Type": "application/json"}
    env = cfg.get("api_key_env")
    if env and os.environ.get(env):
        headers[cfg.get("api_key_header", "x-api-key")] = os.environ[env]
    return headers


# ------------------------------------------------------------------ client

class PartialSearchError(RuntimeError):
    """OpenSearch answered HTTP 200 but did not produce a complete result."""


class Client:
    def __init__(self, base, headers, timeout=120, retries=3, backoff=2.0, deadline=None):
        self.base = base.rstrip("/")
        self.headers = headers
        self.timeout = timeout
        self.retries = max(1, int(retries))
        self.backoff = backoff
        self.deadline = deadline

    def _remaining_timeout(self):
        if self.deadline is None:
            return self.timeout
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("OpenSearch Pulse run deadline exceeded")
        return min(self.timeout, max(0.1, remaining))

    def _req(self, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        last = None
        for attempt in range(self.retries):
            req = urllib.request.Request(self.base + path, data=data,
                                         method="POST" if body is not None else "GET", headers=self.headers)
            try:
                with urllib.request.urlopen(req, timeout=self._remaining_timeout()) as resp:
                    return json.loads(resp.read().decode())
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError,
                    socket.timeout, ConnectionError, OSError, json.JSONDecodeError) as e:
                last = e
                code = getattr(e, "code", None)
                transient = code in (408, 425, 429, 500, 502, 503, 504) or not isinstance(
                    e, urllib.error.HTTPError)
                if not transient or attempt == self.retries - 1:
                    raise
                retry_after = None
                headers = getattr(e, "headers", None)
                if headers:
                    raw_retry_after = ""
                    try:
                        raw_retry_after = headers.get("Retry-After", "")
                        retry_after = float(raw_retry_after)
                    except (TypeError, ValueError):
                        try:
                            retry_after = max(0.0, email.utils.parsedate_to_datetime(
                                raw_retry_after).timestamp() - time.time())
                        except (TypeError, ValueError, OverflowError):
                            pass
                delay = min(30.0, retry_after if retry_after is not None
                            else self.backoff * (2 ** attempt))
                if self.deadline is not None and time.monotonic() + delay >= self.deadline:
                    raise TimeoutError("OpenSearch Pulse run deadline exceeded during retry") from e
                time.sleep(delay)
        raise last

    def cat_indices(self):
        return self._req("/_cat/indices?h=index&format=json")

    def search(self, index_list, body):
        result = self._req(f"/{index_list}/_search", body)
        shards = result.get("_shards") or {}
        failed = int(shards.get("failed") or 0)
        if result.get("timed_out") or failed or result.get("error"):
            detail = result.get("error") or (shards.get("failures") or [])[:2]
            raise PartialSearchError(
                safety_redact(f"partial OpenSearch result: timed_out={bool(result.get('timed_out'))}, "
                              f"failed_shards={failed}, detail={detail}")[:500])
        if (body or {}).get("aggs") and "aggregations" not in result:
            raise PartialSearchError("OpenSearch result has no aggregations")
        return result


def discover_indices(client):
    out = {}
    for row in client.cat_indices():
        idx = row["index"]
        if idx.startswith("."):
            continue
        m = DATE_RE.match(idx)
        if not m:
            continue
        prefix, y, mo, d = m.groups()
        out.setdefault(prefix, set()).add(f"{y}-{mo}-{d}")
    return {p: sorted(ds) for p, ds in out.items()}


def server_filter(cfg):
    if cfg["server_type"]["value"]:
        return [{"term": {cfg["server_type"]["field"]: cfg["server_type"]["value"]}}]
    return []


def _day_bounds(day):
    d = dt.date.fromisoformat(day)
    return f"{day}T00:00:00.000Z", f"{(d + dt.timedelta(days=1)).isoformat()}T00:00:00.000Z"


def window_label(day):
    """Exact UTC window the report covers, e.g. '2026-07-09 00:00 → 2026-07-10 00:00 UTC'."""
    lo, hi = _day_bounds(day)
    return f"{lo[:10]} 00:00 → {hi[:10]} 00:00 UTC"


def time_filter(cfg, day):
    """Bound a query to exactly the report day's UTC window — the per-day index also
    accumulates a small tail of late/buffered docs stamped with the following day(s)."""
    tf = cfg["fields"].get("time")
    if not tf or not day:
        return []
    lo, hi = _day_bounds(day)
    return [{"range": {tf: {"gte": lo, "lt": hi}}}]


def time_range_filter(cfg, days):
    tf = cfg["fields"].get("time")
    if not tf or not days:
        return []
    lo, _ = _day_bounds(min(days))
    _, hi = _day_bounds(max(days))
    return [{"range": {tf: {"gte": lo, "lt": hi}}}]


# ---------------------------------------------------------------- rolling window (intermediate report)

def time_bounds_filter(cfg, lo, hi):
    """Explicit [lo, hi) range on the timestamp field — used only by the rolling-window
    (intermediate) report. The daily report stays index-scoped (this returns nothing there)."""
    tf = cfg.get("time_field")
    return [{"range": {tf: {"gte": lo, "lt": hi}}}] if tf else []


def _iso_z(dtobj):
    return dtobj.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def window_dates(lo_dt, hi_dt):
    """UTC date strings whose per-day indices a [lo, hi) window touches (usually 1-2)."""
    d, end, out = lo_dt.date(), (hi_dt - dt.timedelta(seconds=1)).date(), []
    while d <= end:
        out.append(d.isoformat())
        d += dt.timedelta(days=1)
    return out


def make_window(cfg, prefix, idx, lo_dt, hi_dt):
    """A rolling-window descriptor {index, lo, hi, hours, label, partial} or None if no index covers it."""
    dates = window_dates(lo_dt, hi_dt)
    avail = [d for d in dates if prefix in idx and d in idx[prefix]]
    if not avail:
        return None
    partial = len(avail) < len(dates)
    label = f"{lo_dt.strftime('%Y-%m-%d %H:%M')} → {hi_dt.strftime('%Y-%m-%d %H:%M')} UTC"
    if partial:
        label += " · partial index coverage"
    return {"index": ",".join(prefix + d for d in avail),
            "lo": _iso_z(lo_dt), "hi": _iso_z(hi_dt),
            "hours": int(round((hi_dt - lo_dt).total_seconds() / 3600)),
            "label": label, "partial": partial}


def discover_app_ids(client, cfg, prefix, day, index=None, extra_filter=None):
    q = {"size": 0, "query": {"bool": {"filter": server_filter(cfg) + (extra_filter or [])}},
         "aggs": {"apps": {"terms": {"field": cfg["fields"]["app_id"], "size": 100}}}}
    a = client.search(index or (prefix + day), q)["aggregations"]
    return [b["key"] for b in a["apps"]["buckets"] if b["key"]]


# ---------------------------------------------------------------- redaction

def redact(s):
    return safety_redact(s)


EMPTY_MSG = "⟨no message — exception / stack-only⟩"


def norm_msg(s):
    if not s or not s.strip():
        return EMPTY_MSG
    return redact(re.sub(r"\s+", " ", s).strip())


# ------------------------------------------------------- store-snapshot join

def load_store_snapshot(cfg, config_dir, report_day, pinned=None):
    """The store snapshot to join, and why not, when there is none.

    The store half is a *current-state* reading — a lifetime rating, a per-version device
    metric — not a day-partitioned measurement, and it is generated the morning after the log
    day it accompanies. So the snapshot legitimately carries the next day's stamp, and the
    honest handling is to accept it and print its date, not to reject it for being "in the
    future" (which is what a strict `<= report_day` rule does, silently dropping the whole
    store half). Dated sub-metrics inside it — App Analytics instances — carry their own
    `as_of` and are unaffected.

    `pinned` short-circuits the search: the orchestrator knows exactly which file it just
    generated and should not have to rely on a date window at all.
    """
    spec = cfg.get("store_snapshot") or {}
    try:
        # Daily reports use YYYY-MM-DD; rolling reports deliberately use a sortable
        # YYYY-MM-DDTHHMMZ id. Store freshness is calendar-day based in both cases.
        report_date = dt.date.fromisoformat(str(report_day)[:10])
    except (TypeError, ValueError):
        return None, f"invalid report day {report_day!r} for store snapshot join"
    directory = spec.get("dir")
    max_age = int(spec.get("max_age_days", 3))
    max_ahead = int(spec.get("max_ahead_days", 2))
    if pinned:
        path, stamp = pinned, os.path.basename(pinned)
        stamp = stamp[stamp.rfind("_") + 1:-5] if "_" in stamp else report_day
        if not os.path.exists(path):
            return None, f"pinned store snapshot {os.path.basename(path)} does not exist"
        candidates = [(stamp, path)]
    else:
        if not directory:
            return None, "no store snapshot configured"
        if not os.path.isabs(directory):
            directory = os.path.join(config_dir or ".", directory)
        slug = spec.get("slug", "store_pulse")
        candidates = []
        for path in glob.glob(os.path.join(directory, f"{slug}_*.json")):
            stamp = os.path.basename(path)[len(slug) + 1:-5]
            if re.match(r"^\d{4}-\d{2}-\d{2}$", stamp):
                candidates.append((stamp, path))
        if not candidates:
            return None, f"no {slug}_*.json in {directory}"
    stamp, path = max(candidates)
    age = (report_date - dt.date.fromisoformat(stamp)).days
    if age > max_age:
        return None, f"newest store snapshot is {stamp}, {age}d older than the report day"
    if -age > max_ahead:
        return None, f"newest store snapshot is {stamp}, {-age}d ahead of the report day"
    try:
        with open(path) as fh:
            snapshot = {"day": stamp, "age_days": age, "report": json.load(fh)}
    except (OSError, ValueError) as exc:
        return None, f"could not read {os.path.basename(path)}: {type(exc).__name__}"
    violations = []
    for app in snapshot["report"].get("apps", []):
        analytics = (app.get("slices") or {}).get("ios_analytics") or {}
        for key, metric in (analytics.get("metrics") or {}).items():
            metric_day = metric.get("as_of") or analytics.get("as_of")
            try:
                metric_age = (report_date - dt.date.fromisoformat(metric_day)).days
            except (TypeError, ValueError):
                continue
            if metric_age > max_age or -metric_age > max_ahead:
                violations.append({"app": app.get("key") or app.get("name"),
                                   "metric": key, "as_of": metric_day})
                metric["value"] = None
                metric["incomplete"] = True
                metric["date_out_of_bounds"] = True
        if any(v["app"] == (app.get("key") or app.get("name")) for v in violations):
            analytics["derived"] = {}
            analytics["pending"] = "analytics instance date is outside the joined-report bounds"
    if violations:
        snapshot["date_violations"] = violations
        snapshot["report"].setdefault("trust", {})["complete"] = False
    section = path[:-len(".json")] + ".technical.slack.txt"
    snapshot["technical_section"] = []
    if os.path.exists(section):
        try:
            with open(section) as fh:
                snapshot["technical_section"] = [l.rstrip("\n") for l in fh]
        except OSError:
            pass
    return snapshot, None


HEALTH_MIN_IOS_DAU = 100


def _coverage_note(project, store_app, store_gaps, in_logs):
    """Why an app measured nothing — from both sides, not just the one that noticed first."""
    parts = []
    if not in_logs:
        parts.append("no client logs")
    gap = store_gaps.get(store_app.get("name") or project.get("name"))
    if gap:
        state = (gap.get("state") or "").upper()
        if any(bad in state for bad in ("REJECT", "INVALID", "REMOVED")):
            parts.append(f"listing down ({state.replace('_', ' ').lower()})")
        elif state:
            parts.append(f"not on the store yet ({state.replace('_', ' ').lower()})")
        else:
            parts.append("not on the store")
    elif not store_app:
        parts.append("not in the store report")
    return " · ".join(parts) or None


def _configured_overview_metric(project, spec, platform=None):
    """Resolve one config-owned overview cell without inventing missing telemetry."""
    override = (spec.get("overrides") or {}).get(project.get("key")) or {}
    if override:
        spec = {**spec, **override}
    kind = spec.get("kind")
    base = {"key": spec.get("key"), "label": spec.get("label") or spec.get("key"),
            "display_label": spec.get("display_label") or spec.get("label") or spec.get("key"),
            "kind": kind, "platform": platform, "available": False,
            "availability": "missing_telemetry", "status": "nodata"}
    if kind == "funnel_rate":
        applicability = (project.get("funnel_applicability") or {}).get(spec.get("funnel"))
        if applicability is False:
            return {**base, "availability": "not_applicable"}
        telemetry_note = (project.get("funnel_telemetry_notes") or {}).get(spec.get("funnel"))
        if telemetry_note:
            return {**base, "available": True, "availability": "data_quality",
                    "status": "data_quality", "data_quality": telemetry_note}
        if platform is not None and not (project.get("platform_users") or {}).get(platform):
            return {**base, "availability": "no_traffic"}
        funnel = next((f for f in project.get("funnels", [])
                       if f.get("key") == spec.get("funnel")), None)
        if not funnel:
            return base
        rate_source = ((funnel.get("platforms") or {}).get(platform) or {}
                       if platform is not None else funnel)
        rate_name = (spec.get("rate") or "").casefold()
        rate = next((r for r in rate_source.get("rates", [])
                     if (r.get("label") or "").casefold() == rate_name), None)
        if not rate:
            return {**base, "availability": "zero_events"}
        if rate.get("data_quality"):
            return {**base, "available": True, "availability": "data_quality",
                    "value": rate["pct"], "unit": "%", "status": "data_quality",
                    "data_quality": rate["data_quality"],
                    "numerator": rate.get("num"), "denominator": rate.get("den"),
                    "count_unit": rate.get("count_unit", "users"),
                    "source": f"{funnel.get('label')} / {rate.get('label')}"}
        if rate.get("pct") is None:
            return {**base, "availability": "zero_events"}
        tone = rate_tone(rate)
        delta_pp = rate.get("delta_pp")
        delta_status = _flow_delta_status(
            delta_pp, rate.get("good", "high"), spec.get("delta_watch_pp"),
            spec.get("delta_alert_pp"))
        absolute_status = ("degraded" if tone == "bad" else
                           "watch" if tone == "watch" else "healthy")
        status = _worst_status([absolute_status, delta_status])
        return {**base, "available": True, "availability": "measured",
                "value": rate["pct"], "unit": "%",
                "numerator": rate.get("num"), "denominator": rate.get("den"),
                "count_unit": rate.get("count_unit", "users"),
                "numerator_stage": rate.get("num_stage"),
                "denominator_stage": rate.get("den_stage"),
                "status": status, "absolute_status": absolute_status,
                "baseline_value": rate.get("baseline_pct"),
                "delta_pp": delta_pp, "delta_status": delta_status,
                "target": {"good": rate.get("good"), "good_at": rate.get("good_at"),
                           "bad_at": rate.get("bad_at")},
                "source": f"{funnel.get('label')} / {rate.get('label')}"}
    if kind == "operation":
        profile = next((p for p in project.get("operations", [])
                        if p.get("key") == spec.get("profile")), None)
        flow = next((f for f in (profile or {}).get("flows", [])
                     if f.get("key") == spec.get("flow")), None)
        if not flow:
            return base
        raw_status = flow.get("status", "healthy")
        thresholds = flow.get("thresholds") or {}
        failure = flow.get("terminal_failure_rate_pct")
        retry = flow.get("retry_reach_pct_dau")
        failure_status = _bar_status(
            failure, thresholds.get("terminal_failure_watch_pct"),
            thresholds.get("terminal_failure_alert_pct"))
        retry_status = _bar_status(
            retry, thresholds.get("retry_reach_watch_pct_dau"),
            thresholds.get("retry_reach_alert_pct_dau"))
        return {**base, "available": True, "availability": "measured",
                "value": failure, "unit": "% fail", "retry_pct_dau": retry,
                "start_events": (flow.get("start") or {}).get("events"),
                "success_events": (flow.get("success") or {}).get("events"),
                "failure_events": (flow.get("failure") or {}).get("events"),
                "status": "degraded" if raw_status == "alert" else raw_status,
                "component_status": {"failure": failure_status, "retry": retry_status},
                "thresholds": thresholds,
                "source": f"{(profile or {}).get('label')} / {flow.get('label')}"}
    return base


def _bar_status(value, watch, alert, higher_is_bad=True):
    if value is None or watch is None or alert is None:
        return "nodata"
    if higher_is_bad:
        return "degraded" if value >= alert else ("watch" if value >= watch else "healthy")
    return "degraded" if value <= alert else ("watch" if value <= watch else "healthy")


def _flow_delta_status(delta_pp, good, watch, alert):
    """Classify a conversion-rate move in percentage points."""
    if delta_pp is None or watch is None or alert is None:
        return "nodata"
    improvement = delta_pp if good != "low" else -delta_pp
    if improvement <= -abs(alert):
        return "degraded"
    if improvement <= -abs(watch):
        return "watch"
    if improvement >= abs(watch):
        return "improved"
    return "healthy"


def _worst_status(statuses, default="nodata"):
    measured = [s for s in statuses if s in ("degraded", "watch", "healthy")]
    return min(measured, key=lambda s: SEVERITY_RANK.get(s, 9)) if measured else default


def _decision_error_trend_status(project, thresholds, overview_cfg):
    """Severity for a relative error move after sample and absolute-impact gates.

    Relative changes from a near-zero baseline remain useful diagnostics, but they must not
    make a portfolio project Critical without either a bad absolute level or meaningful excess
    event volume.
    """
    delta = project.get("err_per_user_delta_pct")
    current = project.get("err_per_user")
    base = project.get("err_per_user_base")
    dau = project.get("dau") or 0
    if delta is None or current is None or base is None or dau < 1:
        return "nodata", None
    excess = max(0.0, (current - base) * dau)
    alert_impact = (current >= thresholds.get("absolute_err_per_user_degraded", 10.0)
                    or excess >= overview_cfg.get("rollout_excess_events_alert", 1000))
    watch_impact = (current >= overview_cfg.get("rollout_err_watch_absolute", 0.5)
                    or excess >= overview_cfg.get("rollout_excess_events_watch", 100))
    if delta >= thresholds.get("degraded_pct", 40.0) and alert_impact:
        return "degraded", round(excess)
    if delta >= thresholds.get("watch_pct", 15.0) and watch_impact:
        return "watch", round(excess)
    return "healthy", round(excess)


def _store_state(slices, platform):
    """Human store lifecycle state; never infer Android production state from log traffic."""
    if platform == "iOS":
        release = slices.get("ios_release") or {}
        current = release.get("current") or {}
        rating = slices.get("ios_rating") or {}
        raw = (current.get("state") or "").upper()
        labels = {
            "READY_FOR_DISTRIBUTION": "Live",
            "IN_REVIEW": "In review",
            "WAITING_FOR_REVIEW": "Waiting review",
            "PENDING_DEVELOPER_RELEASE": "Ready to release",
            "PROCESSING_FOR_DISTRIBUTION": "Processing",
            "PREPARE_FOR_SUBMISSION": "Pre-release",
            "REJECTED": "Rejected",
            "DEVELOPER_REJECTED": "Withdrawn",
            "REMOVED_FROM_SALE": "Not listed",
            "DEVELOPER_REMOVED_FROM_SALE": "Not listed",
        }
        if raw:
            label = labels.get(raw, raw.replace("_", " ").title())
        elif rating.get("listed") is True:
            label = "Live"
        elif rating.get("listed") is False:
            label = "Not listed"
        else:
            label = "—"
        phased = release.get("phased") or {}
        phased_state = (phased.get("state") or "").upper()
        phased_label = None
        if phased_state in ("ACTIVE", "PAUSED"):
            phased_label = f"phased {phased_state.lower()} d{phased.get('day') or '—'}"
        return {
            "label": label,
            "raw": raw or None,
            "version": current.get("version") or rating.get("version"),
            "phased": phased_label,
        }

    # StorePulse currently has Play vitals/ratings/reviews but no Publishing API release-track
    # collector. Log traffic proves an Android build runs; it does not prove its store state.
    return {"label": "—", "raw": None, "version": None, "phased": None}


def _clean_version(value):
    return str(value or "").strip().lstrip("vV")


def _weighted_stability_average(rows):
    """Weighted rate across already sample-qualified historical release rows."""
    usable = [r for r in rows
              if r.get("value_pct") is not None and (r.get("sample") or 0) > 0]
    denominator = sum(r["sample"] for r in usable)
    if not denominator:
        return None
    return sum(r["value_pct"] * r["sample"] for r in usable) / denominator


def _stability_delta(current, baseline, overview_cfg):
    if current is None or baseline in (None, 0):
        return None, "nodata"
    delta = (current - baseline) / baseline * 100.0
    if delta >= overview_cfg.get("stability_regression_alert_pct", 50.0):
        status = "degraded"
    elif delta >= overview_cfg.get("stability_regression_watch_pct", 25.0):
        status = "watch"
    elif delta <= -overview_cfg.get("stability_regression_watch_pct", 25.0):
        status = "improved"
    else:
        status = "healthy"
    return round(delta, 1), status


def _ios_crash_stability(store_app, focus_version, thresholds, overview_cfg):
    """Best truthful iOS crash release: focus version, or latest measured fallback."""
    crash = store_app.get("crash_delta") or {}
    rows = [{"version": r.get("version"), "value_pct": r.get("rate") / 10.0,
             "sample": r.get("sessions"), "crashes": r.get("crashes")}
            for r in crash.get("versions") or [] if r.get("rate") is not None]
    focus = _clean_version(focus_version)
    current_index = next((i for i, r in enumerate(rows)
                          if _clean_version(r.get("version")) == focus), None)
    if current_index is not None:
        current = rows[current_index]
        historical = rows[current_index + 1:]
        baseline = _weighted_stability_average(historical)
        delta, delta_status = _stability_delta(
            current["value_pct"], baseline, overview_cfg)
        absolute_status = _bar_status(
            current["value_pct"] * 10.0,
            thresholds.get("ios_crash_per_1k_watch"),
            thresholds.get("ios_crash_per_1k_alert"))
        return {**current, "scope": "focus", "focus_version": focus_version,
                "baseline_pct": baseline,
                "baseline_versions": [r.get("version") for r in historical],
                "delta_pct": delta, "delta_status": delta_status,
                "absolute_status": absolute_status}
    if rows:
        latest = rows[0]
        return {**latest, "scope": "latest_measured", "focus_version": focus_version,
                "baseline_pct": None, "baseline_versions": [], "delta_pct": None,
                "delta_status": "nodata", "absolute_status": "historical"}
    overall = crash.get("rate")
    if overall is not None:
        return {"value_pct": overall / 10.0, "version": None,
                "sample": crash.get("sessions"), "scope": "all_versions",
                "focus_version": focus_version, "baseline_pct": None,
                "baseline_versions": [], "delta_pct": None,
                "delta_status": "nodata",
                "absolute_status": _bar_status(
                    overall, thresholds.get("ios_crash_per_1k_watch"),
                    thresholds.get("ios_crash_per_1k_alert"))}
    return None


def _play_stability(vitals, set_key, metric, focus_version, thresholds, overview_cfg):
    """Newest well-sampled Play versionCode, falling back to the all-version rate."""
    metric_set = ((vitals.get("sets") or {}).get(set_key) or {})
    floor = thresholds.get("min_vitals_users", 100)
    rows = []
    for row in metric_set.get("breakdown") or []:
        dims = row.get("dims") or {}
        version = dims.get("versionCode")
        values = row.get("metrics_pct") or {}
        value = values.get(metric)
        users = values.get("distinctUsers")
        if value is None or version is None or users is None or users < floor:
            continue
        rows.append({"version": str(version), "value_pct": value, "sample": users})
    rows.sort(key=lambda r: (int(r["version"]) if r["version"].isdigit() else -1,
                             r["version"]), reverse=True)
    alert_key = "play_crash_alert_pct" if set_key == "crash" else "play_anr_alert_pct"
    alert = thresholds.get(alert_key)
    watch = alert * thresholds.get("watch_fraction", 0.6) if alert is not None else None
    if rows:
        current, historical = rows[0], rows[1:]
        baseline = _weighted_stability_average(historical)
        delta, delta_status = _stability_delta(current["value_pct"], baseline, overview_cfg)
        return {**current, "version_kind": "build", "scope": "latest_measured",
                "focus_version": focus_version, "baseline_pct": baseline,
                "baseline_versions": [r.get("version") for r in historical],
                "delta_pct": delta, "delta_status": delta_status,
                "absolute_status": _bar_status(current["value_pct"], watch, alert)}
    overall = (vitals.get("metrics") or {}).get(metric)
    if overall is not None:
        return {"value_pct": overall, "version": None, "sample": vitals.get("users"),
                "scope": "all_versions", "focus_version": focus_version,
                "baseline_pct": None, "baseline_versions": [], "delta_pct": None,
                "delta_status": "nodata", "absolute_status": _bar_status(overall, watch, alert)}
    return None


def _start_game_activity(project, platform):
    """Return canonical StartGame activity without relabelling server-boot sessions."""
    startup = next((f for f in project.get("funnels", [])
                    if f.get("key") == "startup"), None)
    platform_funnel = ((startup or {}).get("platforms") or {}).get(platform) or {}
    entry = next((stage for stage in platform_funnel.get("stages", [])
                  if (stage.get("key") == "entry"
                      and str(stage.get("label") or "").casefold() == "startgame")), None)
    return {
        # total = emitted StartGame events; users = distinct people reaching the event.
        "start_game_events": (entry or {}).get("total"),
        "start_game_users": (entry or {}).get("users"),
        "start_game_reach_pct": (entry or {}).get("pct"),
    }


def _platform_overview(project, store_app, slices, platform, thresholds, overview_cfg):
    users = (project.get("platform_users") or {}).get(platform)
    total = project.get("dau")
    observed_cohorts = [v for v in project.get("versions_detail", [])
                        if v.get("plat") == platform]
    cohort = (select_observed_release_cohort(
                  observed_cohorts,
                  min_cohort_dau=overview_cfg.get("rollout_min_cohort_dau", 100),
                  min_rollout_pct=overview_cfg.get("rollout_min_pct", 1.0))
              if observed_cohorts else
              (project.get("release_cohorts") or {}).get(platform) or {})
    current = cohort.get("current") or {}
    previous = cohort.get("previous") or {}
    cohort_delta = cohort.get("err_per_user_delta_pct")
    cohort_selection = cohort.get("selection")

    out = {
        # Platform status below is derived only from the metrics printed in this cell.
        # Ratings/reviews/release workflow stay in the experience attachment and cannot
        # paint a technical project red without an attributable production-health trigger.
        "status": "nodata",
        "dau": users,
        "share_pct": (users / total * 100.0 if users is not None and total else None),
        "version": current.get("ver"), "rollout_pct": current.get("rollout_pct"),
        "previous_version": (previous or {}).get("ver"),
        "version_err_per_user": current.get("err_per_user"),
        "previous_version_err_per_user": (previous or {}).get("err_per_user"),
        "version_cohort_dau": current.get("dau"),
        "version_err_total": current.get("err_total"),
        "version_err_delta_pct": (round(cohort_delta, 1)
                                  if cohort_delta is not None else None),
        "cohort_selection": cohort_selection,
        "excluded_newer_versions": cohort.get("excluded_newer_versions") or [],
    }
    out.update(_start_game_activity(project, platform))
    store_state = _store_state(slices, platform)
    store_key = "ios" if platform == "iOS" else "play"
    rating = ((store_app.get("rating") or {}).get(store_key) or {})
    out.update({
        "store_name": "App Store" if platform == "iOS" else "Google Play",
        "store_state": store_state["label"],
        "store_state_raw": store_state["raw"],
        "store_version": store_state["version"],
        "store_phased": store_state["phased"],
        "store_rating": rating.get("avg"),
        "store_rating_count": rating.get("count"),
        "store_rating_delta": rating.get("d_avg"),
    })
    if platform == "iOS":
        analytics = slices.get("ios_analytics") or {}
        metrics = analytics.get("metrics") or {}
        crash = store_app.get("crash_delta") or {}
        release = slices.get("ios_release") or {}
        out.update({
            "sessions": (metrics.get("sessions") or {}).get("value"),
            "crashes": (metrics.get("crashes") or {}).get("value"),
            "crash_rate": crash.get("rate"), "crash_rate_unit": "/1k sessions",
            "crash_rate_pct": (crash.get("rate") / 10.0
                               if crash.get("rate") is not None else None),
            "crash_time_delta": crash.get("d"), "anr_rate": None,
            "anr_rate_pct": None,
            "analytics_pending": analytics.get("pending"),
            "store_release": release.get("current"),
        })
        out["metric_thresholds"] = {
            "crash": {"watch": thresholds.get("ios_crash_per_1k_watch"),
                      "alert": thresholds.get("ios_crash_per_1k_alert")},
            "anr": {"watch": None, "alert": None},
        }
        crash_status = _bar_status(
            out["crash_rate"], thresholds.get("ios_crash_per_1k_watch"),
            thresholds.get("ios_crash_per_1k_alert"))
        out["metric_status"] = {"crash": crash_status, "anr": "nodata"}
        out["crash_stability"] = _ios_crash_stability(
            store_app, out.get("version"), thresholds, overview_cfg)
        out["anr_stability"] = None
        if out["crash_stability"] and out["crash_stability"].get("scope") != "latest_measured":
            out["metric_status"]["crash"] = out["crash_stability"].get("absolute_status")
        if (out["crash_stability"] or {}).get("delta_status") in ("watch", "degraded"):
            out["metric_status"]["crash_delta"] = out["crash_stability"]["delta_status"]
    else:
        vitals = slices.get("play_vitals") or {}
        metrics = vitals.get("metrics") or {}
        out.update({
            "sessions": None, "crashes": None,
            "crash_rate": metrics.get("userPerceivedCrashRate"),
            "crash_rate_unit": "% users", "crash_time_delta": None,
            "crash_rate_pct": metrics.get("userPerceivedCrashRate"),
            "anr_rate": metrics.get("userPerceivedAnrRate"),
            "anr_rate_pct": metrics.get("userPerceivedAnrRate"),
            "analytics_pending": None,
            "store_release": (slices.get("play_release") or {}).get("current"),
        })
        watch_fraction = thresholds.get("watch_fraction", 0.6)
        crash_alert = thresholds.get("play_crash_alert_pct")
        anr_alert = thresholds.get("play_anr_alert_pct")
        crash_watch = crash_alert * watch_fraction if crash_alert is not None else None
        anr_watch = anr_alert * watch_fraction if anr_alert is not None else None
        out["metric_status"] = {
            "crash": _bar_status(out["crash_rate"], crash_watch, crash_alert),
            "anr": _bar_status(out["anr_rate"], anr_watch, anr_alert),
        }
        out["metric_thresholds"] = {
            "crash": {"watch": crash_watch, "alert": crash_alert},
            "anr": {"watch": anr_watch, "alert": anr_alert},
        }
        out["crash_stability"] = _play_stability(
            vitals, "crash", "userPerceivedCrashRate", out.get("version"),
            thresholds, overview_cfg)
        out["anr_stability"] = _play_stability(
            vitals, "anr", "userPerceivedAnrRate", out.get("version"),
            thresholds, overview_cfg)
        if out["crash_stability"]:
            out["metric_status"]["crash"] = out["crash_stability"].get("absolute_status")
        if out["anr_stability"]:
            out["metric_status"]["anr"] = out["anr_stability"].get("absolute_status")
        for key in ("crash", "anr"):
            stability = out.get(f"{key}_stability") or {}
            if stability.get("delta_status") in ("watch", "degraded"):
                out["metric_status"][f"{key}_delta"] = stability["delta_status"]
    cohort_dau = out.get("version_cohort_dau") or 0
    rollout_pct = out.get("rollout_pct") or 0
    current_err = out.get("version_err_per_user")
    previous_err = out.get("previous_version_err_per_user")
    excess_events = (max(0.0, (current_err - previous_err) * cohort_dau)
                     if current_err is not None and previous_err is not None else None)
    out["version_excess_error_events"] = (round(excess_events)
                                          if excess_events is not None else None)
    sampled = (cohort_dau >= overview_cfg.get("rollout_min_cohort_dau", 100)
               and rollout_pct >= overview_cfg.get("rollout_min_pct", 1.0)
               and previous_err is not None)
    out["version_sample_sufficient"] = sampled
    delta = out.get("version_err_delta_pct")
    rollout_status = "nodata"
    if sampled and delta is not None:
        alert_impact = ((current_err or 0) >= overview_cfg.get(
            "rollout_err_alert_absolute", 2.0)
            or (excess_events or 0) >= overview_cfg.get("rollout_excess_events_alert", 1000))
        watch_impact = ((current_err or 0) >= overview_cfg.get(
            "rollout_err_watch_absolute", 0.5)
            or (excess_events or 0) >= overview_cfg.get("rollout_excess_events_watch", 100))
        if delta >= overview_cfg.get("rollout_err_alert_pct", 50.0) and alert_impact:
            rollout_status = "degraded"
        elif delta >= overview_cfg.get("rollout_err_watch_pct", 25.0) and watch_impact:
            rollout_status = "watch"
    out["metric_status"]["rollout"] = rollout_status
    out["metric_thresholds"]["rollout"] = {
        "watch": overview_cfg.get("rollout_err_watch_pct", 25.0),
        "alert": overview_cfg.get("rollout_err_alert_pct", 50.0),
    }
    statuses = [v for v in out["metric_status"].values() if v != "nodata"]
    out["status"] = (min(statuses, key=lambda v: SEVERITY_RANK.get(v, 9))
                     if statuses else "nodata")
    return out


def build_health(report, snapshot, min_ios_dau=HEALTH_MIN_IOS_DAU):
    """One health row per project: log metrics joined with the store/technical ones.

    The two sources share the app-key vocabulary, so the join needs no name mapping. What
    it does need is honesty about the denominator: OpenSearch DAU counts every platform,
    while Apple's crashes and sessions are iOS-only, so any ratio between them is computed
    against the project's **iOS** DAU and labelled as such. Where the iOS DAU is unknown
    the ratio is omitted rather than mixed.
    """
    store_apps = {}
    if snapshot:
        for a in (snapshot["report"].get("apps") or []):
            store_apps[a.get("key")] = a
    log_projects = {p["key"]: p for p in report["projects"]}
    log_errors = {p["key"]: p for p in report.get("errors", [])}
    # The tracked portfolio is the union: an app can be on the store without streaming logs
    # (pre-submission, or a satellite whose logs are not wired yet) and it still has to appear
    # in the status report — "не показали" and "всё хорошо" must not look the same.
    order = (list(log_projects) + [k for k in log_errors if k not in log_projects]
             + [k for k in store_apps if k not in log_projects and k not in log_errors])
    store_gaps = {}
    store_date_violations = {}
    if snapshot:
        for g in (snapshot["report"].get("coverage_gaps") or []):
            store_gaps[g.get("app")] = g
        for violation in snapshot.get("date_violations") or []:
            store_date_violations.setdefault(violation.get("app"), []).append(violation)
    log_attention = {}
    for item in build_attention(report):
        log_attention.setdefault(item["proj"], []).append(item)
    rows = []
    overview_cfg = report.get("overview") or {}
    log_thresholds = report.get("thresholds") or {}
    store_thresholds = (((snapshot or {}).get("report") or {}).get("thresholds") or {})
    family_by_app = overview_cfg.get("family_by_app") or {}
    default_family = overview_cfg.get("default_family") or report.get("brand", {}).get("org", "Portfolio")
    primary_spec = overview_cfg.get("primary_flow")
    secondary_specs = overview_cfg.get("secondary_metrics") or []
    for key in order:
        failed = log_errors.get(key)
        p = log_projects.get(key) or {"key": key,
                                      "name": (failed or {}).get("name")
                                      or (store_apps.get(key) or {}).get("name") or key,
                                      "status": "degraded" if failed else "nodata",
                                      "funnels": []}
        a = store_apps.get(p["key"]) or {}
        slices = a.get("slices") or {}
        ios_dau = (p.get("platform_users") or {}).get("iOS")
        if p.get("dau") is None:
            ios_dau = None
        crash = a.get("crash_delta") or {}
        analytics = slices.get("ios_analytics") or {}
        sessions = ((analytics.get("metrics") or {}).get("sessions") or {}).get("value")
        crashes = ((analytics.get("metrics") or {}).get("crashes") or {}).get("value")
        perf = (slices.get("ios_perf") or {}).get("metrics") or {}
        over_bar = [m for m in perf.values()
                    if m.get("value") is not None and m.get("watch") is not None
                    and m["value"] >= m["watch"]]
        over_bar.sort(key=lambda m: -(m["value"] / m["watch"]))
        candidates = [{"label": rate["label"], "pct": rate["pct"], "funnel": fn["label"]}
                      for fn in p.get("funnels", [])
                      for rate in fn.get("rates", [])
                      if rate.get("pct") is not None
                      and "success" in (rate.get("label") or "").lower()]
        # "startup success" is the one that answers "did the app come up at all"; a bare
        # "login success" is a step inside it and was winning purely on funnel order.
        startup = next((c for c in candidates if "startup" in c["label"].lower()),
                       candidates[0] if candidates else None)
        # Below the floor a ratio is arithmetic, not information: three iOS users and one
        # crash would print "333 crashes per 1k iOS users" and read like a catastrophe.
        ratio_dau = ios_dau if (ios_dau or 0) >= min_ios_dau else None
        by_nature = a.get("status_by_nature") or {}
        statuses = [p["status"]] + [v for v in by_nature.values()]
        reasons = [{"sev": x["sev"], "text": x["text"], "side": "logs"}
                   for x in log_attention.get(p["name"], [])]
        reasons += [{"sev": x["sev"], "text": x["text"],
                     "side": x.get("nature", "technical")}
                    for x in (a.get("attention") or [])]
        if failed and not any(r["side"] == "logs" for r in reasons):
            reasons.append({"sev": "degraded",
                            "text": f"query failed — {failed.get('error', 'unknown error')[:100]}",
                            "side": "logs"})
        if key in store_date_violations:
            reasons.append({"sev": "watch", "side": "technical",
                            "text": "store analytics date outside joined-report bounds — "
                                    + ", ".join(v["metric"] for v in store_date_violations[key])})
        reason_statuses = [r["sev"] for r in reasons]
        coverage_status = "watch" if "nodata" in statuses and any(v != "nodata" for v in statuses) else None
        candidates_status = [v for v in statuses + reason_statuses + [coverage_status]
                             if v and v != "nodata"]
        combined = (min(candidates_status, key=lambda v: SEVERITY_RANK.get(v, 9))
                    if candidates_status else "nodata")
        reasons.sort(key=lambda r: SEVERITY_RANK.get(r["sev"], 9))
        primary_flow = (_configured_overview_metric(p, primary_spec) if primary_spec else
                        {"available": False, "status": "nodata"})
        secondary_metrics = [_configured_overview_metric(p, spec) for spec in secondary_specs]
        platform_overview = {
            platform: _platform_overview(p, a, slices, platform, store_thresholds,
                                         overview_cfg)
            for platform in ("iOS", "Android")
        }
        platform_funnel_specs = [s for s in secondary_specs if s.get("kind") == "funnel_rate"]
        for platform, pdata in platform_overview.items():
            pdata["flows"] = [_configured_overview_metric(p, spec, platform)
                              for spec in platform_funnel_specs]
            for metric in pdata["flows"]:
                pdata["metric_status"][f"flow:{metric.get('key')}"] = metric.get(
                    "status", "nodata")
            pdata["status"] = _worst_status(
                list((pdata.get("metric_status") or {}).values()))
        components = p.get("status_components") or {}
        decision_trend_status, excess_error_events = _decision_error_trend_status(
            p, log_thresholds, overview_cfg)
        time_metric_status = {
            "errors": decision_trend_status,
            "absolute_errors": components.get("absolute_errors") or "nodata",
            "dau": components.get("traffic") or (
                "healthy" if p.get("dau") is not None else "nodata"),
        }
        time_metric_thresholds = {
            "errors": {
                "watch": log_thresholds.get("watch_pct", 15.0),
                "alert": log_thresholds.get("degraded_pct", 40.0),
            },
            "absolute_errors": {
                "watch": log_thresholds.get("absolute_err_per_user_watch", 5.0),
                "alert": log_thresholds.get("absolute_err_per_user_degraded", 10.0),
            },
            "dau": {
                "watch": -log_thresholds.get("dau_drop_watch_pct", 40.0),
                "alert": -log_thresholds.get("dau_drop_degraded_pct", 70.0),
            },
        }
        overview_statuses = [m.get("status", "nodata") for m in secondary_metrics]
        if primary_spec:
            overview_statuses.append(primary_flow.get("status", "nodata"))
        overview_statuses += [v.get("status", "nodata") for v in platform_overview.values()]
        overview_statuses += list(time_metric_status.values())
        overview_statuses = [v for v in overview_statuses if v != "nodata"]
        overview_status = _worst_status(overview_statuses)
        triggers = []
        for platform, pdata in platform_overview.items():
            for metric, metric_status in (pdata.get("metric_status") or {}).items():
                if metric_status in ("degraded", "watch"):
                    trigger = {"status": metric_status, "scope": platform,
                               "metric": metric, "impact_dau": pdata.get("dau") or 0}
                    if metric == "rollout":
                        trigger.update({
                            "version": pdata.get("version"),
                            "previous_version": pdata.get("previous_version"),
                            "rollout_pct": pdata.get("rollout_pct"),
                            "value": pdata.get("version_err_delta_pct"),
                            "current": pdata.get("version_err_per_user"),
                            "previous": pdata.get("previous_version_err_per_user"),
                            "cohort_dau": pdata.get("version_cohort_dau"),
                            "excess_events": pdata.get("version_excess_error_events"),
                        })
                    elif metric in ("crash", "anr"):
                        trigger["value"] = (pdata.get("crash_rate") if metric == "crash"
                                            else pdata.get("anr_rate"))
                    elif metric.startswith("flow:"):
                        flow_key = metric.split(":", 1)[1]
                        flow = next((m for m in pdata.get("flows", [])
                                     if m.get("key") == flow_key), {})
                        trigger.update({"metric": flow_key, "value": flow.get("value"),
                                        "label": flow.get("label")})
                    triggers.append(trigger)
        for metric in ([primary_flow] if primary_spec else []) + secondary_metrics:
            if metric.get("status") in ("degraded", "watch"):
                triggers.append({"status": metric["status"], "scope": "Flow",
                                 "metric": metric.get("key"), "label": metric.get("label"),
                                 "value": metric.get("value"),
                                 "impact_dau": p.get("dau") or 0})
        dau_time_delta = delta_pct(p.get("dau"), p.get("base_dau"))
        for metric, metric_status in time_metric_status.items():
            if metric_status in ("degraded", "watch"):
                triggers.append({"status": metric_status, "scope": "Time delta",
                                 "metric": metric,
                                 "value": (p.get("err_per_user") if metric == "absolute_errors"
                                           else p.get("err_per_user_delta_pct") if metric == "errors"
                                           else dau_time_delta),
                                 "impact_dau": p.get("dau") or 0,
                                 "excess_events": excess_error_events})
        data_quality = []
        for metric in secondary_metrics:
            if metric.get("status") == "data_quality":
                data_quality.append({"scope": "All", "metric": metric.get("key"),
                                     "issue": metric.get("data_quality")})
        for platform, pdata in platform_overview.items():
            for metric in pdata.get("flows", []):
                if metric.get("status") == "data_quality":
                    data_quality.append({"scope": platform, "metric": metric.get("key"),
                                         "issue": metric.get("data_quality")})
        has_any_data = (p.get("dau") is not None
                        or any((platform_overview.get(platform) or {}).get("version")
                               for platform in ("iOS", "Android"))
                        or any(m.get("available") for m in secondary_metrics))
        rows.append({
            "key": p["key"], "name": p["name"], "status": combined,
            "family": family_by_app.get(p["key"]) or p.get("family") or a.get("family")
                      or default_family,
            "in_logs": p["key"] in log_projects,
            "status_technical": by_nature.get("technical", "nodata"),
            "status_experience": by_nature.get("experience", "nodata"),
            "reasons": reasons,
            "log_status": p["status"], "store_status": (a.get("status_by_store") or {}).get("ios"),
            "dau": p.get("dau"), "ios_dau": ios_dau,
            "android_dau": (p.get("platform_users") or {}).get("Android"),
            "ios_share_pct": (ios_dau / p["dau"] * 100.0
                              if ios_dau and p.get("dau") else None),
            "err_per_user": p.get("err_per_user"),
            "err_per_user_delta_pct": p.get("err_per_user_delta_pct"),
            "coverage_note": _coverage_note(p, a, store_gaps,
                                            p["key"] in log_projects),
            "err_pct_users": p.get("err_pct_users"),
            "top_error_reach": p.get("top_error_reach"),
            "rating": ((a.get("rating") or {}).get("ios") or {}).get("avg"),
            "rating_delta": ((a.get("rating") or {}).get("ios") or {}).get("d_avg"),
            "crashes": crashes, "sessions": sessions,
            "crash_per_1k_sessions": crash.get("rate"),
            "crash_per_1k_delta": crash.get("d"),
            "crash_per_1k_delta_7d": crash.get("d_7d"),
            "between_versions": crash.get("between_versions"),
            "sessions_per_ios_dau": (sessions / ratio_dau if sessions and ratio_dau else None),
            "crashes_per_1k_ios_dau": (crashes / ratio_dau * 1000.0
                                       if crashes is not None and ratio_dau else None),
            "ratio_dau": ratio_dau, "ratio_floor": min_ios_dau,
            "worst_device_metric": over_bar[0] if over_bar else None,
            "device_version": (slices.get("ios_perf") or {}).get("version"),
            "startup": startup,
            "in_store_report": bool(a),
            "analytics_pending": analytics.get("pending"),
            "time_delta": {
                "baseline_days": report.get("baseline_days"),
                "dau_pct": None if dau_time_delta is None else round(dau_time_delta, 1),
                "err_per_user_pct": p.get("err_per_user_delta_pct"),
            },
            "primary_flow": primary_flow,
            "secondary_metrics": secondary_metrics,
            "platform_overview": platform_overview,
            "overview_status": overview_status,
            "overview_triggers": triggers,
            "data_state": "observed" if has_any_data else "no_data",
            "data_quality": data_quality,
            "excess_error_events": excess_error_events,
            "time_metric_status": time_metric_status,
            "time_metric_thresholds": time_metric_thresholds,
        })
    rows.sort(key=lambda r: (0 if r.get("overview_status") == "degraded" else
                             1 if r.get("overview_status") == "watch" else 2,
                             -(r.get("dau") or 0),
                             r["name"].lower()))
    counts = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    return {"rows": rows, "counts": counts,
            "store_day": (snapshot or {}).get("day"),
            "store_age_days": (snapshot or {}).get("age_days")}


def load_health_history(out_dir, slug, report_day, kind=None, limit=5, through=None):
    """Load preceding reports of the same cadence for lifecycle/change annotations."""
    if through == "none":
        return []
    candidates = []
    for path in glob.glob(os.path.join(out_dir, f"{slug}_*.json")):
        report_id = os.path.basename(path)[len(slug) + 1:-5]
        if report_id >= str(report_day):
            continue
        if through and report_id > through:
            continue
        try:
            with open(path) as handle:
                prior = json.load(handle)
        except (OSError, ValueError):
            continue
        prior_kind = prior.get("kind")
        if (kind == "rolling") != (prior_kind == "rolling"):
            continue
        if not (prior.get("health") or {}).get("rows"):
            continue
        candidates.append((report_id, prior))
    candidates.sort(key=lambda item: item[0], reverse=True)
    return [report for _, report in candidates[:limit]]


def _alert_id(row, trigger):
    scope = re.sub(r"[^A-Z0-9]+", "-", str(trigger.get("scope") or "ALL").upper()).strip("-")
    metric = re.sub(r"[^A-Z0-9]+", "-", str(trigger.get("metric") or "METRIC").upper()).strip("-")
    return f"{row.get('key', 'APP')}-{scope}-{metric}"


def apply_overview_context(report, history=None):
    """Add counts, changes, coverage and alert lifecycle to joined health."""
    health = report.get("health") or {}
    rows = health.get("rows") or []
    history = history or []
    previous_rows = {r.get("key"): r for r in (((history[0].get("health") or {}).get("rows"))
                                                if history else [])}

    current_alerts = {}
    for row in rows:
        triggers = row.get("overview_triggers") or []
        for trigger in triggers:
            trigger["alert_id"] = _alert_id(row, trigger)
            trigger.pop("headline", None)
            trigger.pop("action", None)
            current_alerts[trigger["alert_id"]] = {"row": row, "trigger": trigger}
        triggers.sort(key=lambda t: (SEVERITY_RANK.get(t.get("status"), 9),
                                     -(t.get("impact_dau") or 0)))
        row["primary_trigger"] = triggers[0] if triggers else None
        previous = previous_rows.get(row.get("key")) or {}
        row["previous_overview_status"] = previous.get("overview_status")

    previous_alert_ids = set()
    if history:
        for row in (history[0].get("health") or {}).get("rows", []):
            for trigger in row.get("overview_triggers") or []:
                previous_alert_ids.add(trigger.get("alert_id") or _alert_id(row, trigger))
    for alert_id, item in current_alerts.items():
        consecutive = 1
        for prior in history:
            prior_ids = {
                trigger.get("alert_id") or _alert_id(row, trigger)
                for row in (prior.get("health") or {}).get("rows", [])
                for trigger in row.get("overview_triggers") or []
            }
            if alert_id not in prior_ids:
                break
            consecutive += 1
        item["trigger"]["lifecycle"] = "continuing" if alert_id in previous_alert_ids else "new"
        item["trigger"]["consecutive_reports"] = consecutive

    no_data_rows = [r for r in rows if r.get("data_state") == "no_data"]
    critical_rows = [r for r in rows if r.get("data_state") != "no_data"
                     and r.get("overview_status") == "degraded"]
    watch_rows = [r for r in rows if r.get("data_state") != "no_data"
                  and r.get("overview_status") == "watch"]
    stable_rows = [r for r in rows if r.get("data_state") != "no_data"
                   and r.get("overview_status") not in ("degraded", "watch")]
    health["overview_counts"] = {
        "critical": len(critical_rows), "watch": len(watch_rows),
        "stable": len(stable_rows), "no_data": len(no_data_rows),
    }

    health.pop("decisions", None)

    changes = {"new_critical": [], "new_watch": [], "recovered": [], "escalated": []}
    if previous_rows:
        for row in rows:
            current = row.get("overview_status")
            previous = (previous_rows.get(row.get("key")) or {}).get("overview_status")
            if current == "degraded" and previous == "watch":
                changes["escalated"].append(row["name"])
            elif current == "degraded" and previous != "degraded":
                changes["new_critical"].append(row["name"])
            elif current == "watch" and previous not in ("watch", "degraded"):
                changes["new_watch"].append(row["name"])
            elif previous in ("degraded", "watch") and current not in ("degraded", "watch"):
                changes["recovered"].append(row["name"])
    changes["new_alerts"] = sorted(set(current_alerts) - previous_alert_ids)
    changes["resolved_alerts"] = sorted(previous_alert_ids - set(current_alerts))
    changes["comparable"] = bool(previous_rows)
    health["changes"] = changes

    def measured_flow(row, key):
        return any(m.get("key") == key and m.get("availability") == "measured"
                   for m in row.get("secondary_metrics", []))

    coverage = {
        "logs": sum(bool(r.get("in_logs")) for r in rows),
        "ios_dau": sum((r.get("ios_dau") or 0) > 0 for r in rows),
        "android_dau": sum((r.get("android_dau") or 0) > 0 for r in rows),
        "crash_anr": sum(any(p.get("crash_rate") is not None or p.get("anr_rate") is not None
                             for p in (r.get("platform_overview") or {}).values()) for r in rows),
        "loading": sum(measured_flow(r, "loading") for r in rows),
        "rewarded": sum(measured_flow(r, "reward_complete") for r in rows),
        "withdrawal": sum(measured_flow(r, "withdrawal") for r in rows),
        "total": len(rows), "no_data": len(no_data_rows),
        "data_quality": sum(bool(r.get("data_quality")) for r in rows),
    }
    health["coverage"] = coverage

    systemic = []
    rollout_by_platform = Counter(
        trigger.get("scope") for row in rows for trigger in row.get("overview_triggers", [])
        if trigger.get("metric") == "rollout")
    for platform, count in rollout_by_platform.most_common():
        if count >= 2:
            systemic.append(f"{platform} release regressions in {count} projects")
    if coverage["crash_anr"] < coverage["total"]:
        systemic.append(f"crash/ANR coverage {coverage['crash_anr']}/{coverage['total']}")
    if coverage["data_quality"]:
        systemic.append(f"funnel telemetry mismatch in {coverage['data_quality']} project(s)")
    if coverage["no_data"]:
        systemic.append(f"{coverage['no_data']} projects have no production telemetry")
    health["systemic_signals"] = systemic[:4]
    return report


# ------------------------------------------------------------------ query

def project_funnel_stage(fn, st, project_key=None):
    """Map one project's raw telemetry onto a canonical funnel stage.

    Separate applications/repositories often emit different phrases for the same
    business event.  The report schema remains stable (for example ``rv_show`` /
    ``rv_finish`` / ``rv_reward``), while ``stage_overrides_by_app`` changes only
    the source matcher used for that project.
    """
    override = ((fn.get("stage_overrides_by_app") or {}).get(project_key) or {}).get(st["key"])
    if override is False or (isinstance(override, dict) and override.get("disabled")):
        return None
    return {**st, **(override or {})}


def day_query(cfg, app_id=None, day=None, win=None, project_key=None):
    F = cfg["fields"]
    U = F["user"]
    filt = server_filter(cfg) + (time_bounds_filter(cfg, win["lo"], win["hi"]) if win else time_filter(cfg, day))
    if app_id:
        filt.append({"term": {F["app_id"]: app_id}})

    def level_agg(level_value):
        return {"filter": {"term": {F["level"]: level_value}},
                "aggs": {"affected": {"cardinality": {"field": U}},
                         "top": {"terms": {"field": F["message_keyword"], "size": 12},
                                 "aggs": {"u": {"cardinality": {"field": U}},
                                          "cat": {"terms": {"field": F["category"], "size": 1}},
                                          "plat": {"terms": {"field": F["platform"], "size": 3}},
                                          "ver": {"terms": {"field": F["version"], "size": 1}}}},
                         "by_cat": {"terms": {"field": F["category"], "size": 10}}}}

    aggs = {
        "dau": {"cardinality": {"field": U}},
        "errors": level_agg(cfg["levels"]["error"]),
        "warns": level_agg(cfg["levels"]["warn"]),
        "versions": {"terms": {"field": F["version"], "size": 14},
                     "aggs": {
                         "users": {"cardinality": {"field": U}},
                         "err": {"filter": {"term": {F["level"]: cfg["levels"]["error"]}},
                                 "aggs": {"u": {"cardinality": {"field": U}}}},
                         # A version may be live on both platforms. The old aggregation kept
                         # one dominant platform label and attached the version's all-platform
                         # DAU to it, which made rollout comparisons false. Preserve a real
                         # cohort per (version, platform), including its own users/errors.
                         "plat": {"terms": {"field": F["platform"], "size": 4},
                                  "aggs": {
                                      "users": {"cardinality": {"field": U}},
                                      "err": {"filter": {"term": {F["level"]: cfg["levels"]["error"]}},
                                              "aggs": {"u": {"cardinality": {"field": U}}}},
                                  }},
                     }},
        "by_platform": {"terms": {"field": F["platform"], "size": 6},
                        "aggs": {"users": {"cardinality": {"field": U}}}},
    }
    tag_f = F.get("tags")
    fresh_tag = cfg.get("fresh_launch_tag")
    if tag_f and fresh_tag:
        aggs["fresh"] = {"filter": {"term": {tag_f: fresh_tag}},
                         "aggs": {"u": {"cardinality": {"field": U}}}}
        aggs["nonfresh"] = {"filter": {"bool": {"must_not": [{"term": {tag_f: fresh_tag}}]}},
                            "aggs": {"u": {"cardinality": {"field": U}}}}
    if cfg["signals"]:
        aggs["signals"] = {"filters": {"filters": {
            k: {"match_phrase": {F["message_text"]: s["phrase"]}} for k, s in cfg["signals"].items()}},
            "aggs": {"u": {"cardinality": {"field": U}}}}
    if cfg["funnels"]:
        funnel_stages = [(fn, mapped) for fn in cfg["funnels"] for st in fn["stages"]
                          for mapped in [project_funnel_stage(fn, st, project_key)] if mapped]
        aggs["funnels"] = {"filters": {"filters": {
            f'{fn["key"]}::{st["key"]}': stage_filter(F, st) for fn, st in funnel_stages}},
            "aggs": {"u": {"cardinality": {"field": U}},
                     "by_platform": {"terms": {"field": F["platform"], "size": 6},
                                     "aggs": {"u": {"cardinality": {"field": U}}}}}}
        breakdown_stages = [(fn, st) for fn, st in funnel_stages if st.get("breakdown")]
        if breakdown_stages:
            aggs["funnel_breakdowns"] = {"filters": {"filters": {
                f'{fn["key"]}::{st["key"]}': stage_filter(F, st) for fn, st in breakdown_stages}},
                "aggs": {"reasons": {"terms": {"field": F["message_keyword"], "size": 15},
                                     "aggs": {"u": {"cardinality": {"field": U}}}}}}
        if tag_f and fresh_tag:
            split_stages = [(fn, st) for fn, st in funnel_stages if fn.get("split_by_tag")]
            if split_stages:
                aggs["funnels_split"] = {"filters": {"filters": {
                    f'{fn["key"]}::{st["key"]}': stage_filter(F, st) for fn, st in split_stages}},
                    "aggs": {"fresh": {"filter": {"term": {tag_f: fresh_tag}},
                                       "aggs": {"u": {"cardinality": {"field": U}}}},
                             "nonfresh": {"filter": {"bool": {"must_not": [{"term": {tag_f: fresh_tag}}]}},
                                          "aggs": {"u": {"cardinality": {"field": U}}}}}}
    return {"size": 0, "track_total_hits": False,
            "query": {"bool": {"filter": filt}} if filt else {"match_all": {}}, "aggs": aggs}


def stage_filter(F, st):
    """A funnel-stage matcher: a Message phrase, optionally scoped to a category/level."""
    phrases = st.get("phrases") or st.get("phrase")
    phrases = phrases if isinstance(phrases, list) else [phrases]
    if not all(isinstance(phrase, str) and phrase for phrase in phrases):
        raise ValueError(f"funnel stage {st.get('key')} must declare phrase or phrases")
    if len(phrases) == 1:
        message_match = {"match_phrase": {F["message_text"]: phrases[0]}}
    else:
        message_match = {"bool": {"should": [
            {"match_phrase": {F["message_text"]: phrase}} for phrase in phrases
        ], "minimum_should_match": 1}}
    must = [message_match]
    if st.get("category"):
        must.append({"term": {F["category"]: st["category"]}})
    if st.get("level"):
        must.append({"term": {F["level"]: st["level"]}})
    return {"bool": {"must": must}}


# ------------------------------------------------------------------ operational endpoint health

OP_CLASS_LABELS = {
    "transport_timeout": "Transport timeout",
    "transport_failure": "Transport failure",
    "http_failure": "HTTP 4xx/5xx",
    "server_business": "Server/business rejection",
    "unknown": "Unclassified",
}


def operation_scope_filter(F, flow):
    """Config-driven scope for a provider/endpoint flow.

    `Message` and `Attributes` are both supported because provider identity is often
    written only into the opaque Attributes envelope.
    """
    scope = flow.get("scope", {})
    must = []
    if scope.get("message_phrase"):
        must.append({"match_phrase": {F["message_text"]: scope["message_phrase"]}})
    if scope.get("attributes_phrase"):
        must.append({"match_phrase": {F["attributes"]: scope["attributes_phrase"]}})
    if scope.get("category"):
        must.append({"term": {F["category"]: scope["category"]}})
    return must


def operation_outcome_filter(F, flow, outcome):
    must = operation_scope_filter(F, flow)
    phrases = flow.get(outcome)
    if not phrases:
        return None
    if not isinstance(phrases, list):
        phrases = [phrases]
    matchers = [{"match_phrase": {F["message_text"]: phrase}} for phrase in phrases]
    if len(matchers) == 1:
        must.append(matchers[0])
    else:
        must.append({"bool": {"should": matchers, "minimum_should_match": 1}})
    return {"bool": {"must": must}}


def classify_http_attributes(attributes):
    """Classify a standard log Attributes envelope without rendering raw content."""
    text = (attributes or "").lower()
    m = re.search(r'["\']?httpcode["\']?\s*[:=]\s*["\']?(\d+)', text)
    http_code = int(m.group(1)) if m else None
    timeout = "timeout" in text or "timed out" in text
    transport = "transport" in text or "apperror" in text or "network" in text
    server = "responsecode" in text and "error" in text
    if http_code == 0:
        return "transport_timeout" if timeout else "transport_failure"
    if http_code is not None and http_code >= 400:
        return "http_failure"
    if server or (http_code == 200 and ("server error" in text or "rejection" in text)):
        return "server_business"
    if timeout and transport:
        return "transport_timeout"
    if transport:
        return "transport_failure"
    return "unknown"


def operation_reason(attributes, flow):
    """Return the first configured, safe reason bucket; no raw response is retained."""
    text = (attributes or "").lower()
    for bucket in flow.get("reason_buckets", []):
        if any(needle.lower() in text for needle in bucket.get("contains", [])):
            return bucket.get("label", bucket.get("key", "Other"))
    return flow.get("default_reason", "Other")


def operation_attention(flow, failure_rate, retry_reach):
    th = flow.get("thresholds", {})
    return ((failure_rate is not None and failure_rate >= th.get("terminal_failure_watch_pct", float("inf"))) or
            (retry_reach is not None and retry_reach >= th.get("retry_reach_watch_pct_dau", float("inf"))))


def operation_status(flow, failure_rate, retry_reach):
    th = flow.get("thresholds", {})
    alert = ((failure_rate is not None and failure_rate >= th.get("terminal_failure_alert_pct", float("inf"))) or
             (retry_reach is not None and retry_reach >= th.get("retry_reach_alert_pct_dau", float("inf"))))
    return "alert" if alert else ("watch" if operation_attention(flow, failure_rate, retry_reach) else "healthy")


def collect_operation_flow(client, cfg, prefix, app_id, day, profile, flow, dau=None, include_detail=True, win=None):
    """Collect terminal/retry reliability plus safe class buckets for one configured flow."""
    F = cfg["fields"]
    base = server_filter(cfg) + (time_bounds_filter(cfg, win["lo"], win["hi"]) if win else time_filter(cfg, day))
    index = win["index"] if win else prefix + day
    if app_id:
        base.append({"term": {F["app_id"]: app_id}})
    scope = operation_scope_filter(F, flow)
    outcomes = {}
    for name in ("start", "success", "failure", "retry"):
        matcher = operation_outcome_filter(F, flow, name)
        if matcher:
            outcomes[name] = matcher
    outcome_body = {
        "size": 0, "track_total_hits": False,
        "query": {"bool": {"filter": base + scope}},
        "aggs": {"dau": {"cardinality": {"field": F["user"]}},
                 "outcomes": {"filters": {"filters": outcomes},
                              "aggs": {"users": {"cardinality": {"field": F["user"]}}}}},
    }
    aggs = client.search(index, outcome_body)["aggregations"]
    agg = aggs["outcomes"]["buckets"]
    effective_dau = dau if dau is not None else aggs["dau"]["value"]
    result = {name: {"events": val["doc_count"], "users": val.get("users", {}).get("value", 0)}
              for name, val in agg.items()}
    result.setdefault("start", {"events": 0, "users": 0})
    result.setdefault("success", {"events": 0, "users": 0})
    result.setdefault("failure", {"events": 0, "users": 0})
    result.setdefault("retry", {"events": 0, "users": 0})
    terminal = result["success"]["events"] + result["failure"]["events"]
    failure_rate = round(result["failure"]["events"] / terminal * 100, 3) if terminal else None
    retry_reach = round(result["retry"]["users"] / effective_dau * 100, 3) if effective_dau else 0.0

    # Only final failures and retries are fetched. Success volume can be large and is
    # represented by exact aggregations above. No raw record or identifier is rendered.
    non_success = [operation_outcome_filter(F, flow, name) for name in ("failure", "retry")
                   if operation_outcome_filter(F, flow, name)]
    classes, reasons = Counter(), Counter()
    drilldown = None
    truncated = False
    if non_success and include_detail:
        # OpenSearch defaults to index.max_result_window=10k.  Counts remain exact
        # through aggregations; only the optional attribute-class scan can be capped.
        limit = min(10000, int(flow.get("max_classification_records", 10000)))
        detail_body = {
            "size": limit, "track_total_hits": True,
            "_source": [F["message_text"], F["attributes"]],
            "query": {"bool": {"filter": base + scope, "should": non_success, "minimum_should_match": 1}},
            "aggs": {
                "hours": {"date_histogram": {"field": F["time"], "fixed_interval": "1h", "min_doc_count": 1}},
                "versions": {"terms": {"field": F["version"], "size": 4}, "aggs": {"users": {"cardinality": {"field": F["user"]}}}},
                "platforms": {"terms": {"field": F["platform"], "size": 4}, "aggs": {"users": {"cardinality": {"field": F["user"]}}}},
            },
        }
        detail = client.search(index, detail_body)
        total = detail["hits"]["total"]["value"]
        truncated = total > limit
        retry_phrase = (flow.get("retry") or "").lower()
        for hit in detail["hits"].get("hits", []):
            src = hit.get("_source", {})
            bucket = "retry" if retry_phrase and retry_phrase in str(src.get(F["message_text"], "")).lower() else "failure"
            label = classify_http_attributes(str(src.get(F["attributes"], "") or ""))
            classes[(bucket, label)] += 1
            if bucket == "failure" and flow.get("reason_buckets"):
                reasons[operation_reason(str(src.get(F["attributes"], "") or ""), flow)] += 1
        if operation_attention(flow, failure_rate, retry_reach):
            aggs = detail["aggregations"]
            drilldown = {
                "hours": [{"hour": b.get("key_as_string", str(b["key"])), "events": b["doc_count"]}
                          for b in sorted(aggs["hours"]["buckets"], key=lambda b: -b["doc_count"])[:3]],
                "versions": [{"value": b["key"], "events": b["doc_count"], "users": b["users"]["value"]}
                             for b in aggs["versions"]["buckets"]],
                "platforms": [{"value": plat_label(b["key"]), "events": b["doc_count"], "users": b["users"]["value"]}
                              for b in aggs["platforms"]["buckets"]],
            }
    return {
        "key": flow["key"], "label": flow.get("label", flow["key"]),
        "start": result["start"], "success": result["success"],
        "failure": result["failure"], "retry": result["retry"],
        "terminal_failure_rate_pct": failure_rate, "retry_reach_pct_dau": retry_reach,
        "retry_events_per_user": round(result["retry"]["events"] / result["retry"]["users"], 2) if result["retry"]["users"] else 0.0,
        "classes": {bucket: {label: count for (kind, label), count in classes.items() if kind == bucket}
                    for bucket in ("failure", "retry")},
        "reasons": dict(reasons), "status": operation_status(flow, failure_rate, retry_reach),
        "thresholds": dict(flow.get("thresholds") or {}),
        "drilldown": drilldown, "classification_truncated": truncated,
    }


def collect_session_window_flow(client, cfg, prefix, app_id, day, profile, flow, dau=None, include_detail=True, win=None):
    """Session-scoped variant of collect_operation_flow: a 'session' is [marker_i, marker_i+1)
    per user, bounded by a configured session-start marker (e.g. a launch/boot log line), not
    a per-event cardinality. A session 'has a problem' if any configured problem signal falls
    inside its window. Denominator is the marker's raw EVENT count (sessions), not cardinality(user);
    the marker-timestamp fetch is scoped only to the (small, by construction) set of affected users,
    not the whole cohort, so this stays cheap even though the marker itself fires at high volume.

    Returns the same shape as collect_operation_flow so it renders through the same HTML/Slack/MD
    paths unchanged: terminal_failure_rate_pct here means '% of sessions with >=1 problem signal'.
    """
    F = cfg["fields"]
    # F["user"] etc. are multi-field query/sort/agg targets (e.g. "UUID.keyword"); _source
    # filtering and dict reads need the real top-level source key ("UUID") instead.
    user_src = F["user"].split(".")[0]
    base = server_filter(cfg) + (time_bounds_filter(cfg, win["lo"], win["hi"]) if win else time_filter(cfg, day))
    index = win["index"] if win else prefix + day
    if app_id:
        base.append({"term": {F["app_id"]: app_id}})

    marker = flow["session_marker"]
    marker_must = [{"match_phrase": {F["message_text"]: marker["message_phrase"]}}]
    if marker.get("category"):
        marker_must.append({"term": {F["category"]: marker["category"]}})

    # The marker's own log Category can independently be put behind a client-side
    # SessionRolloutPercentage (TheBestLogger `LogTargetCategory`), which silently drops the
    # marker for excluded sessions with no fallback. That would make total_sessions a silent
    # undercount. Track the marker's user-reach so a future rollout change is visible instead
    # of quietly corrupting this metric's denominator.
    total_body = {
        "size": 0, "track_total_hits": True,
        "query": {"bool": {"filter": base, "must": marker_must}},
        "aggs": {"marker_users": {"cardinality": {"field": F["user"]}}},
    }
    total_result = client.search(index, total_body)
    total_sessions = total_result["hits"]["total"]["value"]
    marker_users = total_result["aggregations"]["marker_users"]["value"]

    signals = flow.get("problem_signals", [])
    signal_filters = [{"match_phrase": {F["message_text"]: s["message_phrase"]}} for s in signals]
    # OpenSearch index.max_result_window caps from+size at 10000 on this cluster; this is a
    # single-shot query (no search_after pagination), so it must stay at or under that ceiling.
    limit = min(10000, int(flow.get("max_problem_records", 10000)))
    problem_body = {
        "size": limit, "track_total_hits": True,
        "_source": [user_src, "TimeUTC"],
        "query": {"bool": {"filter": base, "should": signal_filters, "minimum_should_match": 1}},
        "sort": [{"TimeUTC": "asc"}],
        "aggs": {"users": {"cardinality": {"field": F["user"]}},
                 "by_signal": {"terms": {"field": F["message_keyword"], "size": len(signal_filters) + 5}}},
    }
    problem = client.search(index, problem_body)
    problem_hits = problem["hits"]["hits"]
    problem_total = problem["hits"]["total"]["value"]
    users_affected = problem["aggregations"]["users"]["value"]
    truncated = problem_total > limit
    by_signal_raw = {b["key"]: b["doc_count"] for b in problem["aggregations"]["by_signal"]["buckets"]}
    classes_failure = {}
    for bucket_key, count in by_signal_raw.items():
        label = next((s.get("label", s["message_phrase"]) for s in signals if s["message_phrase"] in bucket_key), bucket_key)
        classes_failure[label] = classes_failure.get(label, 0) + count

    sessions_with_problem = 0
    if problem_hits:
        affected_uuids = sorted({h["_source"][user_src] for h in problem_hits if h["_source"].get(user_src)})
        marker_body = {
            "size": 10000, "track_total_hits": True,
            "_source": [user_src, "TimeUTC"],
            "query": {"bool": {"filter": base + [{"terms": {F["user"]: affected_uuids}}], "must": marker_must}},
            "sort": [{F["user"]: "asc"}, {"TimeUTC": "asc"}],
        }
        marker_hits = client.search(index, marker_body)["hits"]["hits"]
        starts_by_user = {}
        for h in marker_hits:
            src = h["_source"]
            u = src.get(user_src)
            if u:
                starts_by_user.setdefault(u, []).append(src["TimeUTC"])

        sessions_seen = set()
        for h in problem_hits:
            src = h["_source"]
            u = src.get(user_src)
            ts = src.get("TimeUTC")
            if not u or not ts:
                continue
            starts = starts_by_user.get(u, [])
            # Session index = count of markers at/before ts, 0-based; a problem that precedes this
            # day's first marker (a trailing request from a session that started the prior day)
            # still counts, bucketed into session 0 rather than dropped.
            session_idx = max(sum(1 for s in starts if s <= ts) - 1, 0)
            sessions_seen.add((u, session_idx))
        sessions_with_problem = len(sessions_seen)

    clean_sessions = max(total_sessions - sessions_with_problem, 0)
    failure_rate = round(sessions_with_problem / total_sessions * 100, 4) if total_sessions else None
    effective_dau = dau if dau is not None else None
    problem_pct_dau = round(users_affected / effective_dau * 100, 4) if effective_dau else 0.0
    marker_reach_pct_dau = round(marker_users / effective_dau * 100, 3) if effective_dau else None

    # Self-defense against a future client-side rollout cut on the marker's category (see note
    # above): if the marker's own DAU reach drops below this floor, total_sessions is likely no
    # longer a full session count, so force attention regardless of how healthy the raw ratio looks.
    min_marker_reach_pct_dau = flow.get("min_marker_reach_pct_dau", 90)
    coverage_ok = marker_reach_pct_dau is None or marker_reach_pct_dau >= min_marker_reach_pct_dau
    status = operation_status(flow, failure_rate, 0.0)
    reasons = {}
    if not coverage_ok:
        status = "watch" if status == "healthy" else status
        reasons[f"Session-marker reach dropped to {marker_reach_pct_dau:.1f}% DAU "
                f"(floor {min_marker_reach_pct_dau}%) — total_sessions likely undercounts true sessions; "
                f"check the marker category's SessionRolloutPercentage"] = marker_users

    return {
        "key": flow["key"], "label": flow.get("label", flow["key"]),
        "success": {"events": clean_sessions, "users": 0},
        "failure": {"events": sessions_with_problem, "users": users_affected},
        "retry": {"events": 0, "users": 0},
        "terminal_failure_rate_pct": failure_rate, "retry_reach_pct_dau": 0.0,
        "retry_events_per_user": 0.0,
        "classes": {"failure": classes_failure, "retry": {}},
        "reasons": reasons, "status": status,
        "thresholds": dict(flow.get("thresholds") or {}),
        "drilldown": None, "classification_truncated": truncated,
        "total_sessions": total_sessions, "sessions_with_problem": sessions_with_problem,
        "users_affected": users_affected, "dau": effective_dau, "problem_pct_dau": problem_pct_dau,
        "marker_reach_pct_dau": marker_reach_pct_dau,
    }


def collect_operations(client, cfg, key, prefix, app_id, day, dau, win=None):
    out = []
    for profile in cfg.get("operations", []):
        if profile.get("apps") and key not in profile["apps"] and app_id not in profile["apps"]:
            continue
        flows = []
        for flow in profile.get("flows", []):
            collect_fn = collect_session_window_flow if flow.get("type") == "session_window" else collect_operation_flow
            flows.append(collect_fn(client, cfg, prefix, app_id, day, profile, flow, dau, win=win))
        if flows:
            out.append({"key": profile["key"], "label": profile.get("label", profile["key"]), "flows": flows})
    return out


def prior_operation_flow(project, profile_key, flow_key):
    for profile in project.get("operations", []):
        if profile.get("key") != profile_key:
            continue
        for flow in profile.get("flows", []):
            if flow.get("key") == flow_key:
                return flow
    return None


def attach_operation_baselines(client, cfg, key, prefix, app_id, operations, prior_by_date,
                               disk_dates_desc, operation_base_dates):
    """Attach a per-flow baseline, preferring saved daily operation blocks.

    Before seven operation-enabled Pulse reports accumulate, the fallback asks OpenSearch
    for the preceding complete days, but only for the small terminal/retry aggregations.
    """
    profiles_cfg = {p.get("key"): p for p in cfg.get("operations", [])}
    default_days = int(cfg.get("operation_baseline_days", 7))
    for profile in operations:
        profile_cfg = profiles_cfg.get(profile.get("key"), {})
        flows_cfg = {f.get("key"): f for f in profile_cfg.get("flows", [])}
        for flow in profile.get("flows", []):
            flow_cfg = flows_cfg.get(flow.get("key"), {})
            n = int(flow_cfg.get("baseline_days", default_days))
            saved = []
            for day in disk_dates_desc:
                prior = prior_by_date.get(day, {}).get(key)
                prior_flow = prior_operation_flow(prior, profile.get("key"), flow.get("key")) if prior else None
                if prior_flow:
                    saved.append(prior_flow)
                if len(saved) >= n:
                    break
            if len(saved) >= n:
                snapshots, source = saved[:n], "saved reports"
            else:
                dates = operation_base_dates[-n:]
                collect_fn = collect_session_window_flow if flow_cfg.get("type") == "session_window" else collect_operation_flow
                snapshots = [collect_fn(client, cfg, prefix, app_id, day, profile_cfg, flow_cfg,
                                        dau=None, include_detail=False)
                             for day in dates]
                source = "OpenSearch" if snapshots else "none"
            failure_rates = [s.get("terminal_failure_rate_pct") for s in snapshots
                             if s.get("terminal_failure_rate_pct") is not None]
            retry_reaches = [s.get("retry_reach_pct_dau") for s in snapshots]
            base_failure = round(mean(failure_rates), 3) if failure_rates else None
            base_retry = round(mean(retry_reaches), 3) if retry_reaches else None
            flow["baseline"] = {
                "days": len(snapshots), "source": source,
                "terminal_failure_rate_pct": base_failure, "retry_reach_pct_dau": base_retry,
            }
            flow["terminal_failure_delta_pct"] = delta_pct(flow.get("terminal_failure_rate_pct"), base_failure)
            flow["retry_reach_delta_pct"] = delta_pct(flow.get("retry_reach_pct_dau"), base_retry)
    return operations


def attach_operation_baselines_windows(client, cfg, prefix, app_id, operations, base_windows):
    """Rolling variant of attach_operation_baselines: per-flow baseline = the same clock
    window on each of the prior days, always live from OpenSearch (small aggs only)."""
    profiles_cfg = {p.get("key"): p for p in cfg.get("operations", [])}
    for profile in operations:
        profile_cfg = profiles_cfg.get(profile.get("key"), {})
        flows_cfg = {f.get("key"): f for f in profile_cfg.get("flows", [])}
        for flow in profile.get("flows", []):
            flow_cfg = flows_cfg.get(flow.get("key"), {})
            collect_fn = collect_session_window_flow if flow_cfg.get("type") == "session_window" else collect_operation_flow
            snapshots = [collect_fn(client, cfg, prefix, app_id, None, profile_cfg, flow_cfg,
                                    dau=None, include_detail=False, win=w)
                         for w in base_windows]
            failure_rates = [s.get("terminal_failure_rate_pct") for s in snapshots
                             if s.get("terminal_failure_rate_pct") is not None]
            retry_reaches = [s.get("retry_reach_pct_dau") for s in snapshots]
            base_failure = round(mean(failure_rates), 3) if failure_rates else None
            base_retry = round(mean(retry_reaches), 3) if retry_reaches else None
            flow["baseline"] = {
                "days": len(snapshots), "source": "prior windows",
                "terminal_failure_rate_pct": base_failure, "retry_reach_pct_dau": base_retry,
            }
            flow["terminal_failure_delta_pct"] = delta_pct(flow.get("terminal_failure_rate_pct"), base_failure)
            flow["retry_reach_delta_pct"] = delta_pct(flow.get("retry_reach_pct_dau"), base_retry)
    return operations


def baseline_query(cfg, app_id=None, base_dates=None):
    """Light per-day agg for the OpenSearch baseline fallback."""
    F = cfg["fields"]
    filt = server_filter(cfg) + time_range_filter(cfg, base_dates)
    if app_id:
        filt.append({"term": {F["app_id"]: app_id}})
    return {"size": 0, "track_total_hits": False,
            "query": {"bool": {"filter": filt}} if filt else {"match_all": {}},
            "aggs": {"per_day": {"terms": {"field": "_index", "size": 60},
                                 "aggs": {"users": {"cardinality": {"field": F["user"]}},
                                          "errors": {"filter": {"term": {F["level"]: cfg["levels"]["error"]}}},
                                          "warns": {"filter": {"term": {F["level"]: cfg["levels"]["warn"]}}}}},
                     "by_version": {"terms": {"field": F["version"], "size": 20}}}}


# ------------------------------------------------------------------ collect

def top_list(agg, dau):
    out = []
    for b in agg.get("buckets", []):
        users = b.get("u", {}).get("value", 0)
        cat_b = b.get("cat", {}).get("buckets", [])
        plat_b = b.get("plat", {}).get("buckets", [])
        ver_b = b.get("ver", {}).get("buckets", [])
        total = b["doc_count"]
        out.append({"msg": norm_msg(b["key"]), "total": total, "users": users,
                    "pct": round(min(100.0, users / dau * 100.0), 2) if dau else 0.0,
                    "per_user": round(total / users, 1) if users else 0.0,
                    "cat": cat_b[0]["key"] if cat_b else "",
                    "plats": [pb["key"] for pb in plat_b],
                    "ver": ver_b[0]["key"] if ver_b else ""})
    return out


def cat_list(agg):
    return [{"cat": b["key"], "total": b["doc_count"]} for b in agg.get("buckets", [])]


def collect_day(client, cfg, prefix, app_id, day, win=None, project_key=None):
    index = win["index"] if win else prefix + day
    a = client.search(index, day_query(cfg, app_id, day, win, project_key))["aggregations"]
    dau = a["dau"]["value"]
    versions_detail = []
    for b in a["versions"]["buckets"]:
        platform_buckets = b.get("plat", {}).get("buckets", [])
        rich_platform_buckets = [pb for pb in platform_buckets if "users" in pb]
        if rich_platform_buckets:
            for pb in rich_platform_buckets:
                perr = pb.get("err") or {}
                versions_detail.append({
                    "ver": b["key"], "docs": pb["doc_count"],
                    "dau": (pb.get("users") or {}).get("value", 0),
                    "err_total": perr.get("doc_count", 0),
                    "err_users": (perr.get("u") or {}).get("value", 0),
                    "plat": pb["key"],
                })
        else:
            # Backward-compatible with cached/fake aggregation fixtures that predate the
            # platform-cohort fix. Live responses always take the branch above.
            plat = platform_buckets[0]["key"] if platform_buckets else ""
            versions_detail.append({
                "ver": b["key"], "docs": b["doc_count"], "dau": b["users"]["value"],
                "err_total": b["err"]["doc_count"], "err_users": b["err"]["u"]["value"],
                "plat": plat,
            })
    return {
        "dau": dau,
        "err_total": a["errors"]["doc_count"], "err_users": a["errors"]["affected"]["value"],
        "warn_total": a["warns"]["doc_count"], "warn_users": a["warns"]["affected"]["value"],
        "top_errors": top_list(a["errors"]["top"], dau)[:10],
        "top_warns": top_list(a["warns"]["top"], dau)[:10],
        "errors_by_cat": cat_list(a["errors"]["by_cat"])[:8],
        "warns_by_cat": cat_list(a["warns"]["by_cat"])[:8],
        "versions": [(v["ver"], v["docs"]) for v in versions_detail],
        "versions_detail": versions_detail,
        "platforms": [(b["key"], b["doc_count"]) for b in a["by_platform"]["buckets"]],
        "platform_users": {plat_label(b["key"]): b.get("users", {}).get("value", 0)
                           for b in a["by_platform"]["buckets"]},
        "signals": {k: {"total": v["doc_count"], "users": v.get("u", {}).get("value", 0)}
                    for k, v in a.get("signals", {}).get("buckets", {}).items()},
        "funnels_raw": {k: {"total": v["doc_count"], "users": v.get("u", {}).get("value", 0)}
                        for k, v in a.get("funnels", {}).get("buckets", {}).items()},
        "funnels_platform_raw": {
            k: {plat_label(pb["key"]): {"total": pb["doc_count"],
                                         "users": pb.get("u", {}).get("value", 0)}
                for pb in v.get("by_platform", {}).get("buckets", [])}
            for k, v in a.get("funnels", {}).get("buckets", {}).items()},
        "funnel_breakdowns": {k: [{"msg": bb["key"], "total": bb["doc_count"],
                                   "users": bb.get("u", {}).get("value", 0)}
                                  for bb in v.get("reasons", {}).get("buckets", [])]
                              for k, v in a.get("funnel_breakdowns", {}).get("buckets", {}).items()},
        "fresh_users": a.get("fresh", {}).get("u", {}).get("value", 0),
        "nonfresh_users": a.get("nonfresh", {}).get("u", {}).get("value", 0),
        "funnels_split": {k: {"fresh": v.get("fresh", {}).get("u", {}).get("value", 0),
                              "nonfresh": v.get("nonfresh", {}).get("u", {}).get("value", 0)}
                          for k, v in a.get("funnels_split", {}).get("buckets", {}).items()},
    }


def collect_baseline_os(client, cfg, prefix, app_id, base_dates):
    idx = ",".join(prefix + d for d in base_dates)
    a = client.search(idx, baseline_query(cfg, app_id, base_dates))["aggregations"]
    per_day_err, per_day_warn, daus = [], [], []
    for b in a["per_day"]["buckets"]:
        u = b["users"]["value"] or 0
        daus.append(u)
        if u:
            per_day_err.append(b["errors"]["doc_count"] / u)
            per_day_warn.append(b["warns"]["doc_count"] / u)
    return {"err_per_user": mean(per_day_err), "warn_per_user": mean(per_day_warn),
            "dau": mean(daus), "versions": {b["key"] for b in a["by_version"]["buckets"]},
            "source": "OpenSearch"}


def collect_baseline_windows(client, cfg, prefix, app_id, base_windows, project_key=None):
    """Baseline for the rolling report = the same clock window on each of the prior N days,
    pulled live from OpenSearch (never from disk, so intermediate runs don't touch the daily
    baseline history). Returns averaged per-user rates + DAU and the prior top signatures."""
    errs, warns, daus, versions = [], [], [], set()
    err_sigs, warn_sigs = set(), set()
    err_sig_pcts, warn_sig_pcts = {}, {}
    recent_err_top, recent_warn_top = [], []
    funnel_rate_samples = {}
    for i, w in enumerate(base_windows):
        d = collect_day(client, cfg, prefix, app_id, None, win=w, project_key=project_key)
        if d["dau"]:
            daus.append(d["dau"])
            errs.append(d["err_total"] / d["dau"])
            warns.append(d["warn_total"] / d["dau"])
        for t in d["top_errors"]:
            err_sigs.add(t["msg"])
            err_sig_pcts.setdefault(t["msg"], []).append(t.get("pct", 0))
        for t in d["top_warns"]:
            warn_sigs.add(t["msg"])
            warn_sig_pcts.setdefault(t["msg"], []).append(t.get("pct", 0))
        for v in d["versions"]:
            versions.add(v[0] if isinstance(v, (list, tuple)) else v)
        for rate_key, value in _funnel_rate_values(
                assemble_funnels(cfg, d, d["dau"], project_key)).items():
            funnel_rate_samples.setdefault(rate_key, []).append(value)
        if i == 0:  # most-recent prior window drives "resolved since" comparison
            recent_err_top, recent_warn_top = d["top_errors"], d["top_warns"]
    return {"err_per_user": mean(errs), "warn_per_user": mean(warns), "dau": mean(daus),
            "versions": versions, "err_sigs": err_sigs, "warn_sigs": warn_sigs,
            "err_sig_pcts": {k: mean(v) for k, v in err_sig_pcts.items()},
            "warn_sig_pcts": {k: mean(v) for k, v in warn_sig_pcts.items()},
            "recent_err_top": recent_err_top, "recent_warn_top": recent_warn_top,
            "funnel_rate_baselines": {k: mean(v) for k, v in funnel_rate_samples.items()}}


def fetch_samples(client, cfg, prefix, app_id, day, limit=6):
    """Distinct error messages with a sample stacktrace (for the MD fix report)."""
    F = cfg["fields"]
    filt = server_filter(cfg) + time_filter(cfg, day) + [{"term": {F["level"]: cfg["levels"]["error"]}},
                                 {"exists": {"field": F["stacktrace"]}}]
    if app_id:
        filt.append({"term": {F["app_id"]: app_id}})
    src = [F["message_text"], F["category"], F["version"], F["platform"], F["device"], F["stacktrace"]]
    if F.get("attributes"):
        src.append(F["attributes"])
    q = {"size": limit, "collapse": {"field": F["message_keyword"]},
         "_source": src,
         "query": {"bool": {"filter": filt}}}
    try:
        hits = client.search(prefix + day, q)["hits"]["hits"]
    except Exception:
        return []
    out = []
    for h in hits:
        s = h["_source"]
        stack = redact(str(s.get(F["stacktrace"], ""))[:800])
        rec = {"msg": norm_msg(s.get(F["message_text"], "")), "cat": s.get(F["category"], ""),
               "ver": s.get(F["version"], ""), "plat": plat_label(s.get(F["platform"], "")),
               "device": s.get(F["device"], ""), "stack": stack}
        if F.get("attributes"):
            rec["attrs"] = redact(str(s.get(F["attributes"], "") or "")[:400])
        out.append(rec)
    return out


# ------------------------------------------------------------------ metrics

def per_user(count, dau):
    return count / dau if dau else 0.0


def delta_pct(cur, base):
    return None if cur is None or base is None or base <= 0 else (cur - base) / base * 100.0


def release_error_delta(current, previous):
    """Return absolute and relative error deltas for two release cohorts."""
    if not previous:
        return None, None
    absolute = round(current["err_per_user"] - previous["err_per_user"], 2)
    relative = delta_pct(current["err_per_user"], previous["err_per_user"])
    return absolute, None if relative is None else round(relative, 1)


def numeric_version_key(version):
    """Return a comparable key for dotted numeric production versions."""
    value = str(version or "").strip()
    if value[:1].lower() == "v":
        value = value[1:]
    if not re.fullmatch(r"\d+(?:\.\d+)*", value):
        return None
    return tuple(int(part) for part in value.split("."))


def select_observed_release_cohort(cohorts, min_cohort_dau=0, min_rollout_pct=0.0):
    """Select the two newest sufficiently sampled numeric versions.

    Major, minor and patch versions follow the same rule: a version is comparable only after
    it passes the DAU and rollout gates. Tiny test/patch cohorts remain visible as
    excluded_newer_versions but cannot become the focus, baseline or regression trigger.
    """
    cohorts = list(cohorts or [])
    ranked = [(numeric_version_key(row.get("ver")), row) for row in cohorts]
    ranked = [(key, row) for key, row in ranked if key is not None]
    if ranked:
        ranked.sort(key=lambda item: item[0], reverse=True)
        eligible = [(key, row) for key, row in ranked
                    if (row.get("dau") or 0) >= min_cohort_dau
                    and ((row.get("rollout_pct") is None and min_rollout_pct <= 0)
                         or (row.get("rollout_pct") is not None
                             and row.get("rollout_pct") >= min_rollout_pct))]
        if eligible:
            current_key, current = eligible[0]
            previous = eligible[1][1] if len(eligible) > 1 else None
            excluded_newer = [row for key, row in ranked if key > current_key]
            selection = "newest sufficiently sampled versions"
        else:
            current_key, current = ranked[0]
            previous = None
            excluded_newer = []
            selection = "no sufficiently sampled version"
    else:
        current = max(cohorts, key=lambda row: row.get("dau") or 0, default={})
        previous = None
        excluded_newer = []
        selection = "release order unknown"
    absolute, relative = release_error_delta(current, previous)
    return {
        "current": current,
        "previous": previous,
        "err_per_user_delta": absolute,
        "err_per_user_delta_pct": relative,
        "selection": selection,
        "excluded_newer_versions": excluded_newer,
    }


def classify(err_delta, th):
    if err_delta is None:
        return "watch"
    if err_delta >= th["degraded_pct"]:
        return "degraded"
    if err_delta >= th["watch_pct"]:
        return "watch"
    return "healthy"


# --- issue rule table: shared by log-hygiene (item 2) and the impact bar (item 4) ---
# A rule matches a signature when ALL present conditions hold; first match wins.
# The engine is generic; the rules (verdict/ux/business/owner/action text) live in config.

def match_rule(rule, sig, level):
    m = rule.get("match", {})
    if m.get("empty_message") and sig["msg"] != EMPTY_MSG:
        return False
    if "level" in m and m["level"] != level:
        return False
    if "category" in m:
        cats = m["category"] if isinstance(m["category"], list) else [m["category"]]
        if sig.get("cat", "") not in cats:
            return False
    if "phrase" in m:
        phrases = m["phrase"] if isinstance(m["phrase"], list) else [m["phrase"]]
        if not any(p.lower() in sig["msg"].lower() for p in phrases):
            return False
    if "regex" in m and not re.search(m["regex"], sig["msg"], re.I):
        return False
    return True


def classify_sig(sig, level, hygiene):
    """Attach a verdict + impact fields to a signature from the config rule table."""
    for rule in hygiene.get("rules", []):
        if match_rule(rule, sig, level):
            r = {k: rule.get(k) for k in ("verdict", "ux", "business", "owner", "action", "reason")
                 if rule.get(k) is not None}
            r.setdefault("verdict", "review")
            return r
    return dict(hygiene.get("default", {"verdict": "review"}))


def build_hygiene(sigs):
    """Bucket classified signatures by verdict (mute / fix / ux-assess / review)."""
    buckets = {}
    for s in sigs:
        v = (s.get("hygiene") or {}).get("verdict", "review")
        buckets.setdefault(v, []).append(s)
    out = {}
    for v, items in buckets.items():
        items.sort(key=lambda x: -x.get("pct", 0))
        out[v] = {"count": len(items),
                  "events": sum(i["total"] for i in items),
                  "worst_pct": items[0]["pct"] if items else 0.0,
                  "items": items[:6]}
    return out


def _funnel_rates(fn, su, dau, se=None):
    """Config-defined conversion rates using unique users or explicit event counts."""
    se = se or {}
    rates = []
    for rt in fn.get("rates", []):
        count_unit = rt.get("count", "users")
        counts = se if count_unit == "events" and se else su
        num = counts.get(rt["num"], 0)
        d = rt.get("den")
        if d == "dau":
            den = dau
        elif isinstance(d, list):        # sum of stages, e.g. success/(success+failed)
            den = sum(counts.get(k, 0) for k in d)
        else:
            den = counts.get(d, 0)
        pct = round(num / den * 100.0, 1) if den else None
        quality = ("numerator_exceeds_denominator" if pct is not None and pct > 100.0 else
                   "denominator_missing" if den == 0 and num > 0 else None)
        rates.append({"label": rt["label"], "num": num, "den": den,
                      "num_stage": rt["num"], "den_stage": d,
                      "count_unit": count_unit if counts is se else "users",
                      "pct": pct, "data_quality": quality,
                      "good": rt.get("good", "high"), "business": rt.get("business"),
                      "good_at": rt.get("good_at"), "bad_at": rt.get("bad_at")})
    return rates


def assemble_funnels(cfg, today, dau, key):
    """Reassemble per-funnel stage users/%DAU + config-defined conversion rates."""
    funnels_raw = today["funnels_raw"]
    funnel_breakdowns = today.get("funnel_breakdowns", {})
    funnels_split = today.get("funnels_split", {})
    funnels_platform_raw = today.get("funnels_platform_raw", {})
    fresh_dau = today.get("fresh_users", 0)
    nonfresh_dau = today.get("nonfresh_users", 0)
    out = []
    for fn in cfg["funnels"]:
        apps = fn.get("apps")
        if apps and key not in apps:
            continue
        stages = []
        breakdowns = []
        for st in fn["stages"]:
            r = funnels_raw.get(f'{fn["key"]}::{st["key"]}', {})
            u = r.get("users", 0)
            stages.append({"key": st["key"], "label": st["label"], "users": u,
                           "total": r.get("total", 0),
                           "pct": round(min(100.0, u / dau * 100.0), 1) if dau else 0.0})
            bd = st.get("breakdown")
            if bd:
                rows = funnel_breakdowns.get(f'{fn["key"]}::{st["key"]}', [])
                strip = bd.get("strip_prefix", "")
                reasons = []
                for row in rows:
                    msg = redact(row["msg"])
                    if strip and msg.startswith(strip):
                        msg = msg[len(strip):].strip() or "(no reason logged)"
                    ru = row["users"]
                    reasons.append({"reason": msg, "users": ru, "total": row["total"],
                                    "pct": round(ru / dau * 100.0, 1) if dau else 0.0})
                reasons.sort(key=lambda x: -x["users"])
                breakdowns.append({"stage": st["key"], "label": bd.get("breakdown_label", st["label"]),
                                   "reasons": reasons[:bd.get("top", 5)]})
        if not any(s["users"] for s in stages):
            continue  # funnel not applicable to this app
        su = {s["key"]: s["users"] for s in stages}
        se = {s["key"]: s["total"] for s in stages}
        rates = _funnel_rates(fn, su, dau, se)
        platforms = {}
        for platform in ("iOS", "Android"):
            platform_dau = (today.get("platform_users") or {}).get(platform) or 0
            platform_stages = []
            for st in fn["stages"]:
                raw = (funnels_platform_raw.get(f'{fn["key"]}::{st["key"]}', {})
                       .get(platform, {}))
                platform_stages.append({
                    "key": st["key"], "label": st["label"],
                    "users": raw.get("users", 0), "total": raw.get("total", 0),
                    "pct": (round(min(100.0, raw.get("users", 0) / platform_dau * 100.0), 1)
                            if platform_dau else None),
                })
            psu = {s["key"]: s["users"] for s in platform_stages}
            pse = {s["key"]: s["total"] for s in platform_stages}
            platforms[platform] = {
                "dau": platform_dau, "stages": platform_stages,
                "has_events": any(s["total"] for s in platform_stages),
                "rates": _funnel_rates(fn, psu, platform_dau, pse),
            }
        splits = []
        if fn.get("split_by_tag"):
            for cohort, cdau in (("Fresh launch", fresh_dau), ("Returning (warm)", nonfresh_dau)):
                field = "fresh" if cohort == "Fresh launch" else "nonfresh"
                cstages = [{"key": st["key"], "label": st["label"],
                            "users": funnels_split.get(f'{fn["key"]}::{st["key"]}', {}).get(field, 0)}
                           for st in fn["stages"]]
                for s in cstages:
                    s["pct"] = round(min(100.0, s["users"] / cdau * 100.0), 1) if cdau else 0.0
                csu = {s["key"]: s["users"] for s in cstages}
                splits.append({"cohort": cohort, "dau": cdau, "stages": cstages,
                               "rates": _funnel_rates(fn, csu, cdau)})
        out.append({"key": fn["key"], "label": fn["label"], "stages": stages,
                    "rates": rates, "note": fn.get("note"), "breakdowns": breakdowns,
                    "splits": splits, "platforms": platforms})
    return out


def _funnel_rate_key(funnel, platform, rate):
    return "\x1f".join((str(funnel), str(platform), str(rate).casefold()))


def _funnel_rate_values(funnels):
    """Flatten measured platform funnel rates for baseline averaging."""
    values = {}
    for funnel in funnels:
        for platform, platform_data in (funnel.get("platforms") or {}).items():
            for rate in platform_data.get("rates", []):
                if rate.get("pct") is not None and not rate.get("data_quality"):
                    values[_funnel_rate_key(funnel.get("key"), platform,
                                            rate.get("label"))] = rate["pct"]
    return values


def attach_funnel_baselines(funnels, baseline_values, baseline_periods, source):
    """Attach average prior conversion and an absolute percentage-point delta."""
    for funnel in funnels:
        for platform, platform_data in (funnel.get("platforms") or {}).items():
            for rate in platform_data.get("rates", []):
                base = baseline_values.get(_funnel_rate_key(
                    funnel.get("key"), platform, rate.get("label")))
                rate["baseline_pct"] = None if base is None else round(base, 1)
                rate["delta_pp"] = (None if base is None or rate.get("pct") is None else
                                    round(rate["pct"] - base, 1))
                rate["baseline_periods"] = baseline_periods
                rate["baseline_source"] = source
    return funnels


def build_impact(top_errors, top_warns, limit=5):
    """The business-impact bar: the highest-reach actionable (fix/ux-assess) issues."""
    pool = [{**t, "kind": "error"} for t in top_errors] + [{**t, "kind": "warn"} for t in top_warns]
    issues = [p for p in pool if (p.get("hygiene") or {}).get("verdict") in ("fix", "ux-assess")]
    issues.sort(key=lambda x: -x.get("pct", 0))
    out = []
    for p in issues[:limit]:
        h = p.get("hygiene") or {}
        out.append({"issue": p["msg"], "kind": p["kind"], "verdict": h.get("verdict"),
                    "cat": p.get("cat", ""), "users": p["users"], "pct": p["pct"],
                    "events": p["total"], "per_user": p.get("per_user", 0),
                    "plats": [plat_label(x) for x in p.get("plats", [])], "ver": p.get("ver", ""),
                    "ux": h.get("ux"), "business": h.get("business"),
                    "action": h.get("action"), "owner": h.get("owner")})
    return out


def build_project(client, cfg, key, name, prefix, app_id, report_day, os_base_dates,
                  operation_base_dates, prior_by_date, disk_dates_desc, n,
                  win=None, base_windows=None):
    today = collect_day(client, cfg, prefix, app_id, report_day, win=win, project_key=key)
    th = cfg["thresholds"]
    err_pu = per_user(today["err_total"], today["dau"])
    warn_pu = per_user(today["warn_total"], today["dau"])

    # baseline: prefer the most recent N prior reports on disk that include this project
    # (even weeks old); else fall back to OpenSearch over the immediate window.
    prior_days = [d for d in disk_dates_desc if key in prior_by_date.get(d, {})][:n]
    prior_err_sigs, prior_warn_sigs, prior_versions = set(), set(), set()
    recent_err_top, recent_warn_top = [], []
    funnel_rate_baselines = {}
    funnel_baseline_periods = 0
    funnel_baseline_source = "none"
    if win is not None:
        # rolling-window report: baseline = same clock window on the prior N days (live from OS)
        bw = collect_baseline_windows(client, cfg, prefix, app_id, base_windows or [], key)
        base_source = f"prior {win['hours']}h windows"
        base_err_pu, base_warn_pu, base_dau = bw["err_per_user"], bw["warn_per_user"], bw["dau"]
        prior_err_sigs, prior_warn_sigs, prior_versions = bw["err_sigs"], bw["warn_sigs"], bw["versions"]
        recent_err_top, recent_warn_top = bw["recent_err_top"], bw["recent_warn_top"]
        funnel_rate_baselines = bw.get("funnel_rate_baselines") or {}
        funnel_baseline_periods = len(base_windows or [])
        funnel_baseline_source = "prior windows"
        prior_status = None
        base_dates_used = [w["label"] for w in (base_windows or [])]
    elif prior_days:
        base_source = "saved reports"
        base_err_pu = mean([prior_by_date[d][key].get("err_per_user") for d in prior_days])
        base_warn_pu = mean([prior_by_date[d][key].get("warn_per_user") for d in prior_days])
        base_dau = mean([prior_by_date[d][key].get("dau") for d in prior_days])
        for d in prior_days:
            for t in prior_by_date[d][key].get("top_errors", []):
                prior_err_sigs.add(t["msg"])
            for t in prior_by_date[d][key].get("top_warns", []):
                prior_warn_sigs.add(t["msg"])
            for v in prior_by_date[d][key].get("versions", []):
                prior_versions.add(v[0] if isinstance(v, (list, tuple)) else v)
        recent = max(prior_days)
        recent_err_top = prior_by_date[recent][key].get("top_errors", [])
        recent_warn_top = prior_by_date[recent][key].get("top_warns", [])
        prior_status = prior_by_date[recent][key].get("status")
        base_dates_used = prior_days
        funnel_samples = {}
        for d in prior_days:
            for rate_key, value in _funnel_rate_values(
                    prior_by_date[d][key].get("funnels") or []).items():
                funnel_samples.setdefault(rate_key, []).append(value)
        funnel_rate_baselines = {k: mean(v) for k, v in funnel_samples.items()}
        funnel_baseline_periods = len(prior_days)
        funnel_baseline_source = "saved reports"
    else:
        ob = collect_baseline_os(client, cfg, prefix, app_id, os_base_dates) if os_base_dates else \
            {"err_per_user": 0.0, "warn_per_user": 0.0, "dau": 0.0, "versions": set()}
        base_source = "OpenSearch" if os_base_dates else "none"
        base_err_pu, base_warn_pu, base_dau = ob["err_per_user"], ob["warn_per_user"], ob["dau"]
        prior_versions = ob["versions"]
        prior_status = None
        base_dates_used = os_base_dates

    err_d = delta_pct(err_pu, base_err_pu)
    warn_d = delta_pct(warn_pu, base_warn_pu)
    low_data = today["dau"] < cfg["min_dau"]
    trend_status = "nodata" if (low_data or err_d is None) else classify(err_d, th)
    absolute_status = ("degraded" if err_pu >= th.get("absolute_err_per_user_degraded", 10.0) else
                       "watch" if err_pu >= th.get("absolute_err_per_user_watch", 5.0) else "healthy")
    dau_drop_pct = (max(0.0, (base_dau - today["dau"]) / base_dau * 100.0)
                    if base_dau > 0 else None)
    traffic_status = ("degraded" if dau_drop_pct is not None and
                      dau_drop_pct >= th.get("dau_drop_degraded_pct", 70.0) else
                      "watch" if dau_drop_pct is not None and
                      dau_drop_pct >= th.get("dau_drop_watch_pct", 40.0) else "healthy")
    measured_statuses = ([trend_status] if trend_status != "nodata" else [])
    measured_statuses += [s for s in (absolute_status, traffic_status)
                          if s in ("watch", "degraded")]
    status = min(measured_statuses, key=lambda v: SEVERITY_RANK.get(v, 9)) \
        if measured_statuses else "nodata"
    if today["dau"] == 0:
        status = "degraded" if base_dau > 0 else "nodata"

    today_err_msgs = {t["msg"] for t in today["top_errors"]}
    today_warn_msgs = {t["msg"] for t in today["top_warns"]}
    appeared = [t for t in today["top_errors"] if prior_err_sigs and t["msg"] not in prior_err_sigs]
    disappeared = [t for t in recent_err_top if t.get("msg") not in today_err_msgs]
    appeared_warns = [t for t in today["top_warns"] if prior_warn_sigs and t["msg"] not in prior_warn_sigs]
    disappeared_warns = [t for t in recent_warn_top if t.get("msg") not in today_warn_msgs]
    total_docs = sum(c for _, c in today["versions"]) or 1
    new_releases = [v for v, c in today["versions"]
                    if v not in prior_versions and c / total_docs >= th["new_release_min_share"]] if prior_versions else []
    worst = max(today["top_errors"], key=lambda t: t["pct"], default=None)
    worst_warn = max(today["top_warns"], key=lambda t: t["pct"], default=None)

    # per-signature baseline %DAU (avg across baseline days where the signature appears)
    def base_sig_map(field):
        m = {}
        for d in prior_days:
            for t in prior_by_date[d][key].get(field, []):
                m.setdefault(t["msg"], []).append(t.get("pct", 0))
        return {k2: mean(v) for k2, v in m.items()}

    def with_base(items, base_map):
        out = []
        for t in items:
            base = base_map.get(t["msg"])
            base = round(base, 2) if base is not None else None
            rel = round((t["pct"] - base) / base * 100) if base and base > 0 else None
            out.append({**t, "base_pct": base, "pct_delta": rel})
        return out

    base_err_map = bw["err_sig_pcts"] if win is not None else base_sig_map("top_errors")
    base_warn_map = bw["warn_sig_pcts"] if win is not None else base_sig_map("top_warns")
    top_errors = with_base(today["top_errors"], base_err_map)
    top_warns = with_base(today["top_warns"], base_warn_map)

    # log-hygiene classification (item 2) + impact fields (item 4), from the config rule table
    hygiene = cfg["hygiene"]
    for t in top_errors:
        t["hygiene"] = classify_sig(t, "error", hygiene)
    for t in top_warns:
        t["hygiene"] = classify_sig(t, "warn", hygiene)
    hygiene_buckets = build_hygiene(top_errors + top_warns)
    funnels = attach_funnel_baselines(
        assemble_funnels(cfg, today, today["dau"], key), funnel_rate_baselines,
        funnel_baseline_periods, funnel_baseline_source)
    impact = build_impact(top_errors, top_warns)
    if win is not None:
        operations = collect_operations(client, cfg, key, prefix, app_id, None, today["dau"], win=win)
        operations = attach_operation_baselines_windows(client, cfg, prefix, app_id, operations,
                                                        base_windows or [])
    else:
        operations = collect_operations(client, cfg, key, prefix, app_id, report_day, today["dau"])
        operations = attach_operation_baselines(client, cfg, key, prefix, app_id, operations,
                                                 prior_by_date, disk_dates_desc, operation_base_dates)

    # Per-release rollout share inside its own platform + error rate. This used to divide
    # a dominant-platform label by portfolio DAU, so a shared iOS/Android version looked
    # like one cohort. Rollout is a platform question and now has a platform denominator.
    versions_detail = []
    for v in today["versions_detail"]:
        vdau = v["dau"] or 0
        platform = plat_label(v["plat"])
        platform_dau = (today.get("platform_users") or {}).get(platform) or 0
        versions_detail.append({
            "ver": v["ver"], "plat": platform, "dau": vdau,
            "platform_dau": platform_dau,
            "rollout_pct": round(min(100.0, vdau / platform_dau * 100), 1)
                           if platform_dau else None,
            "err_per_user": round(v["err_total"] / vdau, 2) if vdau else 0.0,
            "err_pct_users": round(min(100.0, v["err_users"] / vdau * 100), 1) if vdau else 0.0,
            "err_total": v["err_total"],
        })
    versions_detail.sort(key=lambda x: -x["dau"])
    versions_detail = versions_detail[:12]

    release_cohorts = {}
    for platform in ("iOS", "Android"):
        cohorts = [v for v in versions_detail if v["plat"] == platform]
        if not cohorts:
            continue
        overview_cfg = cfg.get("overview") or {}
        release_cohorts[platform] = select_observed_release_cohort(
            cohorts,
            min_cohort_dau=overview_cfg.get("rollout_min_cohort_dau", 100),
            min_rollout_pct=overview_cfg.get("rollout_min_pct", 1.0))

    return {
        "key": key, "name": name, "prefix": prefix, "app_id": app_id,
        "status": status, "prior_status": prior_status, "low_data": low_data,
        "report_day": win["label"] if win else report_day,
        "baseline_dates_used": sorted(base_dates_used),
        "baseline_source": base_source,
        "dau": today["dau"],
        "err_total": today["err_total"], "err_users": today["err_users"],
        "err_pct_users": round(min(100.0, per_user(today["err_users"], today["dau"]) * 100), 1),
        "warn_total": today["warn_total"], "warn_users": today["warn_users"],
        "err_per_user": round(err_pu, 2), "err_per_user_base": round(base_err_pu, 2),
        "warn_per_user": round(warn_pu, 2), "warn_per_user_base": round(base_warn_pu, 2),
        "err_per_user_delta_pct": None if (low_data or err_d is None) else round(err_d, 1),
        "warn_per_user_delta_pct": None if (low_data or warn_d is None) else round(warn_d, 1),
        "base_dau": round(base_dau),
        "dau_drop_pct": None if dau_drop_pct is None else round(dau_drop_pct, 1),
        "status_components": {"trend": trend_status, "absolute_errors": absolute_status,
                              "traffic": traffic_status},
        "fresh_users": today.get("fresh_users", 0),
        "nonfresh_users": today.get("nonfresh_users", 0),
        "fresh_pct": round(today.get("fresh_users", 0) / today["dau"] * 100, 1) if today["dau"] else 0.0,
        "top_errors": top_errors, "top_warns": top_warns,
        "top_error_reach": round(worst["pct"], 1) if worst else 0.0,
        "top_error_reach_msg": worst["msg"] if worst else "",
        "top_warn_reach": round(worst_warn["pct"], 1) if worst_warn else 0.0,
        "top_warn_reach_msg": worst_warn["msg"] if worst_warn else "",
        "errors_by_cat": today["errors_by_cat"], "warns_by_cat": today["warns_by_cat"],
        "versions": today["versions"][:8], "versions_detail": versions_detail,
        "release_cohorts": release_cohorts,
        "platforms": today["platforms"],
        "platform_users": today.get("platform_users") or {},
        "signals": today["signals"],
        "appeared_errors": appeared[:6], "disappeared_errors": disappeared[:6],
        "appeared_warnings": appeared_warns[:6], "disappeared_warnings": disappeared_warns[:6],
        "new_releases": new_releases,
        "hygiene": hygiene_buckets, "funnels": funnels,
        "funnel_applicability": {
            fn["key"]: (not fn.get("apps") or key in fn.get("apps", []))
            for fn in cfg.get("funnels", [])
        },
        "funnel_telemetry_notes": {
            fn["key"]: (fn.get("telemetry_notes_by_app") or {}).get(key)
            for fn in cfg.get("funnels", [])
            if (fn.get("telemetry_notes_by_app") or {}).get(key)
        },
        "impact": impact, "operations": operations,
    }


FNAME_DATE_RE = re.compile(r"_(\d{4}-\d{2}-\d{2})\.json$")


def load_prior_reports(out_dir, slug, report_day, max_candidates=21, return_meta=False):
    """Scan out_dir for prior day-model reports (any date < report_day, even weeks old).

    Returns (by_date, dates_desc). A prior report is usable only if it is a day-model
    report (has 'report_day') with per-project rate fields — 'structurally sufficient'
    to serve as a baseline. Most-recent-first; capped to bound I/O.
    """
    cands = []
    for path in glob.glob(os.path.join(out_dir, f"{slug}_*.json")):
        m = FNAME_DATE_RE.search(os.path.basename(path))
        if m and m.group(1) < report_day:
            cands.append((m.group(1), path))
    cands.sort(reverse=True)
    by_date, corrupt = {}, []
    for d, path in cands[:max_candidates]:
        try:
            with open(path) as handle:
                rep = json.load(handle)
        except (OSError, ValueError) as exc:
            corrupt.append({"file": os.path.basename(path), "error": type(exc).__name__})
            continue
        if not rep.get("report_day") or "projects" not in rep:
            continue  # not a day-model report -> not structurally sufficient
        usable = {p["key"]: p for p in rep["projects"]
                  if all(k in p for k in ("err_per_user", "warn_per_user", "dau"))}
        if usable:
            by_date[d] = usable
    result = (by_date, sorted(by_date, reverse=True))
    return result + ({"corrupt_candidates": corrupt},) if return_meta else result


def build_report(client, cfg, report_day, out_dir, slug):
    idx = discover_indices(client)
    n = cfg["baseline_days"]
    # prior day-model reports on disk (any dates < report_day, most-recent first)
    prior_by_date, disk_dates_desc, baseline_meta = load_prior_reports(
        out_dir, slug, report_day, return_meta=True)
    operation_baseline_days = max([int(f.get("baseline_days", cfg.get("operation_baseline_days", 7)))
                                   for p in cfg.get("operations", []) for f in p.get("flows", [])] or [0])
    jobs = []
    for src in cfg["sources"]:
        prefix = src["index_prefix"]
        app_names = src.get("app_names", {})
        if prefix not in idx or report_day not in idx[prefix]:
            if src.get("split_by_app_id") and app_names:
                for app_id, name in app_names.items():
                    jobs.append((app_id, name, prefix, app_id, [], []))
            else:
                key = src.get("key") or prefix.rstrip("-")
                jobs.append((key, src.get("name") or key, prefix, None, [], []))
            continue
        before = [d for d in idx[prefix] if d < report_day]
        os_base_dates = before[-n:]  # OpenSearch fallback window (immediate N index days)
        operation_base_dates = before[-operation_baseline_days:] if operation_baseline_days else []
        if src.get("split_by_app_id"):
            discovered = set(discover_app_ids(client, cfg, prefix, report_day))
            for app_id in sorted(discovered | set(app_names)):
                jobs.append((app_id, app_names.get(app_id, app_id), prefix, app_id, os_base_dates, operation_base_dates))
        else:
            key = src.get("key") or prefix.rstrip("-")
            jobs.append((key, src.get("name") or key, prefix, None, os_base_dates, operation_base_dates))

    def run(job):
        key, name, prefix, app_id, os_base_dates, operation_base_dates = job
        try:
            if prefix not in idx or report_day not in idx.get(prefix, []):
                raise PartialSearchError(f"required source index missing for {report_day}: {prefix}*")
            return build_project(client, cfg, key, name, prefix, app_id, report_day,
                                 os_base_dates, operation_base_dates, prior_by_date, disk_dates_desc, n)
        except Exception as e:
            return {"key": key, "name": name, "error": safe_error(e)}

    with ThreadPoolExecutor(max_workers=cfg["max_workers"]) as ex:
        projects = [p for p in ex.map(run, jobs) if p]
    ok = [p for p in projects if "error" not in p]
    ok.sort(key=lambda p: (1 if p["status"] == "nodata" else 0, -p["dau"]))
    # funnels: app-specific funnels (those with an `apps` scope) are bounded to the top-N
    # DAU projects; universal funnels (no `apps` scope, e.g. the cross-project loading
    # funnel) are kept for every project.
    top_n = cfg.get("funnel_top_dau")
    if top_n:
        universal = {fn["key"] for fn in cfg["funnels"] if not fn.get("apps")}
        keep = {p["key"] for p in sorted(ok, key=lambda p: -p["dau"])[:top_n]}
        for p in ok:
            if p["key"] not in keep:
                p["funnels"] = [fn for fn in p["funnels"] if fn["key"] in universal]
    errors = [p for p in projects if "error" in p]
    overall = "degraded" if errors or baseline_meta["corrupt_candidates"] else "healthy"
    for p in ok:
        if SEVERITY_RANK.get(p["status"], 9) < SEVERITY_RANK.get(overall, 9):
            overall = p["status"]
    used_dates = sorted({d for p in ok for d in p.get("baseline_dates_used", [])})
    from_disk = any(p["baseline_source"] == "saved reports" for p in ok)
    return {
        "schema": 3,
        "generated_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "report_day": report_day, "baseline_dates": used_dates, "baseline_days": n,
        "window_utc": window_label(report_day),
        "is_last_complete": report_day == (dt.datetime.now(dt.timezone.utc).date() - dt.timedelta(days=1)).isoformat(),
        "baseline_source": "saved reports" if from_disk else ("OpenSearch" if used_dates else "none"),
        "overall_status": overall, "brand": cfg["brand"],
        "thresholds": cfg.get("thresholds") or {},
        "overview": cfg.get("overview") or {},
        "fresh_tag": cfg.get("fresh_launch_tag") or "",
        "funnels_note": cfg["funnels_summary_note"], "md_observations": cfg["md_observations"],
        "signals_meta": {k: v.get("label", k) for k, v in cfg["signals"].items()},
        "projects": ok, "source": client.base.split("//")[-1].split(".")[0],
        "errors": errors,
        "trust": {"complete": not errors and not baseline_meta["corrupt_candidates"],
                  "expected_projects": len(jobs), "successful_projects": len(ok),
                  "failed_projects": len(errors), **baseline_meta},
    }


def build_report_window(client, cfg, hours, now_dt):
    """Rolling-window (intermediate) report over [now - hours, now], baseline = the same
    clock window on each of the prior N days. Never reads/writes the daily baseline history."""
    idx = discover_indices(client)
    n = cfg["baseline_days"]
    hi_dt = now_dt.replace(second=0, microsecond=0)
    lo_dt = hi_dt - dt.timedelta(hours=hours)
    jobs = []
    for src in cfg["sources"]:
        prefix = src["index_prefix"]
        win = make_window(cfg, prefix, idx, lo_dt, hi_dt)
        app_names = src.get("app_names", {})
        if not win:
            if src.get("split_by_app_id") and app_names:
                jobs.extend((app_id, name, prefix, app_id, None, [])
                            for app_id, name in app_names.items())
            else:
                key = src.get("key") or prefix.rstrip("-")
                jobs.append((key, src.get("name") or key, prefix, None, None, []))
            continue
        base_windows = [w for w in (make_window(cfg, prefix, idx, lo_dt - dt.timedelta(days=k),
                                                 hi_dt - dt.timedelta(days=k)) for k in range(1, n + 1)) if w]
        if src.get("split_by_app_id"):
            # discover over the whole window (all indices it touches, bounded to [lo, hi]) so an
            # app active only in the older half of a cross-midnight window is not missed.
            discovered = discover_app_ids(client, cfg, prefix, None, index=win["index"],
                                          extra_filter=time_bounds_filter(cfg, win["lo"], win["hi"]))
            for app_id in sorted(set(discovered) | set(app_names)):
                jobs.append((app_id, app_names.get(app_id, app_id), prefix, app_id, win, base_windows))
        else:
            key = src.get("key") or prefix.rstrip("-")
            jobs.append((key, src.get("name") or key, prefix, None, win, base_windows))

    def run(job):
        key, name, prefix, app_id, win, base_windows = job
        try:
            if win is None:
                raise PartialSearchError(f"required source has no index coverage: {prefix}*")
            return build_project(client, cfg, key, name, prefix, app_id, None, [], [], {}, [], n,
                                 win=win, base_windows=base_windows)
        except Exception as e:
            return {"key": key, "name": name, "error": safe_error(e)}

    with ThreadPoolExecutor(max_workers=cfg["max_workers"]) as ex:
        projects = [p for p in ex.map(run, jobs) if p]
    ok = [p for p in projects if "error" not in p]
    ok.sort(key=lambda p: (1 if p["status"] == "nodata" else 0, -p["dau"]))
    universal = {fn["key"] for fn in cfg["funnels"] if not fn.get("apps")}
    top_n = cfg.get("funnel_top_dau")
    if top_n:
        keep = {p["key"] for p in sorted(ok, key=lambda p: -p["dau"])[:top_n]}
        for p in ok:
            if p["key"] not in keep:
                p["funnels"] = [fn for fn in p["funnels"] if fn["key"] in universal]
    errors = [p for p in projects if "error" in p]
    overall = "degraded" if errors else "healthy"
    for p in ok:
        if SEVERITY_RANK.get(p["status"], 9) < SEVERITY_RANK.get(overall, 9):
            overall = p["status"]
    label = f"{lo_dt.strftime('%Y-%m-%d %H:%M')} → {hi_dt.strftime('%Y-%m-%d %H:%M')} UTC"
    return {
        "schema": 3, "kind": "rolling", "window_hours": hours,
        "generated_utc": now_dt.strftime("%Y-%m-%d %H:%M UTC"),
        "report_day": hi_dt.strftime("%Y-%m-%dT%H%MZ"),
        "window_label": f"last {hours}h", "baseline_dates": [], "baseline_days": n,
        "window_utc": label, "is_last_complete": False,
        "baseline_source": f"prior {n}×{hours}h windows",
        "overall_status": overall, "brand": cfg["brand"],
        "thresholds": cfg.get("thresholds") or {},
        "overview": cfg.get("overview") or {},
        "fresh_tag": cfg.get("fresh_launch_tag") or "",
        "funnels_note": cfg["funnels_summary_note"], "md_observations": cfg["md_observations"],
        "signals_meta": {k: v.get("label", k) for k, v in cfg["signals"].items()},
        "projects": ok, "source": client.base.split("//")[-1].split(".")[0],
        "errors": errors,
        "trust": {"complete": not errors, "expected_projects": len(jobs),
                  "successful_projects": len(ok), "failed_projects": len(errors)},
    }


# ------------------------------------------------------------------ render

STATUS_LABEL = {"healthy": "Healthy", "watch": "Watch", "degraded": "Degraded", "nodata": "Low data"}
SEVERITY_RANK = {"degraded": 0, "watch": 1, "healthy": 2, "nodata": 3}


def day_label(report):
    """Headline label: the report day for the daily report, or 'last Nh' for the rolling one."""
    return report.get("window_label") or report["report_day"]


def scope_word(report):
    """Time-scope word for 'new/resolved' sections: 'today' (daily) or 'in the last Nh' (rolling)."""
    return f"in the last {report.get('window_hours')}h" if report.get("kind") == "rolling" else "today"


def build_attention(report):
    """Everything that needs attention, portfolio-wide, in one scannable list.

    Sources: failed project queries, degraded/watch project status (with the top actionable
    impact item), operation flows at watch/alert, and funnel rates in their configured 'bad'
    zone. Severity: 'degraded' (red) before 'watch' (yellow); projects keep DAU order."""
    items = []
    for e in report.get("errors", []):
        items.append({"sev": "degraded", "proj": e["name"],
                      "text": f"query failed — project missing from this report ({e['error'][:60]})"})
    for p in report["projects"]:
        st = p["status"]
        if st in ("degraded", "watch"):
            d = p.get("err_per_user_delta_pct")
            dtxt = "" if d is None else f" ({d:+.0f}% vs baseline)"
            worst = (f"; worst: {p['top_error_reach_msg'][:60]} ({p['top_error_reach']:.1f}% DAU)"
                     if p.get("top_error_reach_msg") else "")
            imp = (p.get("impact") or [None])[0]
            act = f" → {imp['action'][:90].rstrip()}" if imp and imp.get("action") else ""
            items.append({"sev": st, "proj": p["name"],
                          "text": f"errors {p['err_per_user']:.1f}/user{dtxt}{worst}{act}"})
        for profile in p.get("operations", []):
            for flow in profile.get("flows", []):
                fst = flow.get("status")
                if fst in ("watch", "alert"):
                    fr = flow.get("terminal_failure_rate_pct")
                    frt = "n/a" if fr is None else f"{fr:.2f}%"
                    items.append({"sev": "degraded" if fst == "alert" else "watch", "proj": p["name"],
                                  "text": (f"{profile.get('label', profile.get('key', ''))} / "
                                           f"{flow.get('label', flow.get('key', ''))} — terminal failure {frt}, "
                                           f"retry {flow.get('retry_reach_pct_dau', 0):.2f}% DAU [{fst.upper()}]")})
        for fn in p.get("funnels", []):
            for r in fn.get("rates", []):
                if rate_tone(r) == "bad":
                    lim = f"limit ≤{r['bad_at']}%" if r.get("good") == "low" else f"target ≥{r['good_at']}%"
                    items.append({"sev": "watch", "proj": p["name"],
                                  "text": f"{fn['label']}: {r['label']} {r['pct']:.0f}% ({lim})"})
            for sp in fn.get("splits", []):
                if not sp.get("dau"):
                    continue
                for r in sp["rates"]:
                    if rate_tone(r) == "bad":
                        lim = f"limit ≤{r['bad_at']}%" if r.get("good") == "low" else f"target ≥{r['good_at']}%"
                        items.append({"sev": "watch", "proj": p["name"],
                                      "text": f"{fn['label']} · {sp['cohort']}: {r['label']} {r['pct']:.0f}% ({lim})"})
    return sorted(items, key=lambda a: 0 if a["sev"] == "degraded" else 1)


def attention_section(report):
    att = build_attention(report)
    if not att:
        return ('<section class="card att"><h2 class="ov-title">Needs attention</h2>'
                '<p class="empty">nothing — all projects healthy vs baseline</p></section>')
    rows = "".join(
        f'<div class="att-row"><span class="status-dot {a["sev"]}"></span>'
        f'<span class="att-text"><b>{html.escape(a["proj"])}</b> — {html.escape(a["text"])}</span></div>'
        for a in att)
    return f'<section class="card att"><h2 class="ov-title">⚠ Needs attention ({len(att)})</h2>{rows}</section>'


def fmt_int(n):
    # a store-only row has no DAU and no error counts; an absent number is "—", not a crash
    if n is None:
        return "—"
    return f"{int(n):,}"


def fmt_delta(pct_val, higher_is_bad=True):
    if pct_val is None:
        return '<span class="delta flat">—</span>'
    arrow = "▲" if pct_val > 0 else ("▼" if pct_val < 0 else "–")
    bad = (pct_val > 0) if higher_is_bad else (pct_val < 0)
    cls = "up-bad" if bad and abs(pct_val) >= 1 else ("down-good" if (not bad) and abs(pct_val) >= 1 else "flat")
    return f'<span class="delta {cls}">{arrow} {abs(pct_val):.0f}%</span>'


def rate_tone(r):
    """good/bad/watch colour for a funnel rate, only when config gives defensible
    thresholds (good_at/bad_at, interpreted per the rate's `good` direction). No
    thresholds -> neutral, so reach/volume/normal-waterfall rates aren't mislabelled."""
    p = r.get("pct")
    if p is not None and p > 100:
        return "watch"  # numerator users exceed denominator users — instrumentation skew
    ga, ba = r.get("good_at"), r.get("bad_at")
    if p is None or ga is None or ba is None:
        return ""
    if r.get("good") == "low":                 # lower is better
        return "good" if p <= ga else ("bad" if p >= ba else "watch")
    return "good" if p >= ga else ("bad" if p <= ba else "watch")


def sig_delta_html(it):
    """Per-signature %DAU change vs baseline (down is good for errors)."""
    if it.get("base_pct") is None:
        return ' <span class="sdelta new">new</span>' if "base_pct" in it else ""
    d = it.get("pct_delta")
    if d is None:
        return ""
    arrow = "▼" if d < 0 else ("▲" if d > 0 else "–")
    cls = "down-good" if d < 0 else ("up-bad" if d > 0 else "flat")
    return f' <span class="sdelta {cls}" title="baseline {it["base_pct"]:.1f}% of DAU">{arrow}{abs(d)}%</span>'


def sig_bars(items, tone):
    if not items:
        return '<p class="empty">none</p>'
    mx = max(it["total"] for it in items) or 1
    rows = []
    for it in items:
        w = max(2.0, it["total"] / mx * 100.0)
        rows.append(
            f'<div class="bar-row"><div class="bar-label" title="{html.escape(it["msg"])}">'
            f'{html.escape(it["msg"][:120])}</div>'
            f'<div class="bar-track"><div class="bar-fill {tone}" style="width:{w:.1f}%"></div></div>'
            f'<div class="bar-val">{fmt_int(it["total"])}<span class="bar-sub">{fmt_int(it["users"])}u · {it["pct"]:.1f}%{sig_delta_html(it)}</span></div></div>')
    return "\n".join(rows)


def cat_bars(items, tone):
    if not items:
        return '<p class="empty">none</p>'
    mx = max(it["total"] for it in items) or 1
    rows = []
    for it in items:
        w = max(2.0, it["total"] / mx * 100.0)
        rows.append(
            f'<div class="bar-row"><div class="bar-label">{html.escape(str(it["cat"]))}</div>'
            f'<div class="bar-track"><div class="bar-fill {tone}" style="width:{w:.1f}%"></div></div>'
            f'<div class="bar-val">{fmt_int(it["total"])}</div></div>')
    return "\n".join(rows)


def version_table(vd):
    if not vd:
        return '<p class="empty">none</p>'
    rows = "".join(
        f'<tr><td>{html.escape(str(v["ver"]))}</td><td>{html.escape(v["plat"])}</td>'
        f'<td class="num">{fmt_int(v["dau"])}</td>'
        f'<td class="num">{v["rollout_pct"]:.1f}%</td>'
        f'<td class="num">{v["err_per_user"]:.1f}</td>'
        f'<td class="num">{v["err_pct_users"]:.0f}%</td></tr>'
        for v in vd
    )
    return ('<div class="table-scroll"><table class="ver">'
            '<thead><tr><th>Version</th><th>Plat</th><th class="num">DAU</th>'
            '<th class="num">rollout %</th><th class="num">err/user</th><th class="num">% users</th></tr></thead>'
            f'<tbody>{rows}</tbody></table></div>')


def _sig_tu(v):
    """Signal value is now {total,users}; tolerate the legacy int shape from old reports."""
    if isinstance(v, dict):
        return v.get("total", 0), v.get("users")
    return v, None


def signal_grid(sig, labels):
    cells = []
    for key in labels:
        if key not in sig:
            continue
        total, users = _sig_tu(sig[key])
        sub = f'<div class="sig-sub">{fmt_int(users)} users</div>' if users else ""
        cells.append(f'<div class="sig"><div class="sig-val">{fmt_int(total)}</div>'
                     f'<div class="sig-lbl">{html.escape(labels.get(key, key))}</div>{sub}</div>')
    return '<div class="sig-grid">' + "".join(cells) + "</div>" if cells else ""


def _health_cells(row):
    """The store/technical half of an overview row; empty cells when there is no snapshot."""
    if not row:
        return '<td class="num">—</td>' * 3
    def cell(value, text, title=""):
        t = f' title="{html.escape(title)}"' if title else ""
        return (f'<td class="num" data-sort="{value if value is not None else -1}"{t}>'
                f'{text}</td>')
    share = row.get("ios_share_pct")
    rating = row.get("rating")
    rate = row.get("crash_per_1k_sessions")
    return "".join([
        cell(share, "—" if share is None else (f"{share:.0f}%" if share >= 10
                                               else f"{share:.1f}%"),
             "share of DAU on iOS — the denominator for the Apple-only columns"),
        cell(rating, "—" if rating is None else f"{rating:.2f}"
             + (f' <span class="dim">{row["rating_delta"]:+.2f}</span>'
                if row.get("rating_delta") else "")),
        cell(rate, "—" if rate is None else f"{rate:.2f}"
             + (f' <span class="dim">{row["crash_per_1k_delta"]:+.2f}</span>'
                if row.get("crash_per_1k_delta") else ""),
             row.get("analytics_pending") or "iOS crashes per 1,000 iOS sessions"),
    ])


def overview_row(p, health_row=None):
    st = p["status"]
    rel = ' <span class="rel-flag">NEW</span>' if p["new_releases"] else ""
    return (
        f'<tr class="{st}">'
        f'<td data-sort="{html.escape(p["name"].lower())}"><span class="status-dot {st}"></span>{html.escape(p["name"])}{rel}</td>'
        f'<td class="num" data-sort="{p["dau"]}">{fmt_int(p["dau"])}</td>'
        f'<td class="num" data-sort="{p.get("fresh_pct", 0)}" title="{fmt_int(p.get("fresh_users", 0))} users with a cold/fresh-start launch tag">{p.get("fresh_pct", 0):.0f}%</td>'
        f'<td class="num" data-sort="{p["err_total"]}">{fmt_int(p["err_total"])}</td>'
        f'<td class="num" data-sort="{p["err_per_user"]}">{p["err_per_user"]:.1f} {fmt_delta(p["err_per_user_delta_pct"])}</td>'
        f'<td class="num" data-sort="{p["top_error_reach"]}" title="{html.escape(p["top_error_reach_msg"])}">{p["top_error_reach"]:.1f}%</td>'
        f'<td class="num" data-sort="{p["warn_total"]}">{fmt_int(p["warn_total"])}</td>'
        f'<td class="num" data-sort="{p["warn_per_user"]}">{p["warn_per_user"]:.1f} {fmt_delta(p["warn_per_user_delta_pct"])}</td>'
        f'<td class="num" data-sort="{p["top_warn_reach"]}" title="{html.escape(p["top_warn_reach_msg"])}">{p["top_warn_reach"]:.1f}%</td>'
        + _health_cells(health_row)
        + f'<td data-sort="{SEVERITY_RANK.get(st, 4)}"><span class="status-chip {st}">{STATUS_LABEL[st]}</span></td></tr>')


def overview_table(report):
    health = {r["key"]: r for r in ((report.get("health") or {}).get("rows") or [])}
    rows = "\n".join(overview_row(p, health.get(p["key"])) for p in report["projects"])
    base = report["baseline_dates"]
    base_lbl = f'{base[0]} → {base[-1]}' if base else 'n/a'
    ft = report.get("fresh_tag")
    fresh_note = (f"<b>Fresh %</b> = share of that day's DAU whose session carried a <code>{html.escape(ft)}</code> tag "
                  "(a cold/fresh process start rather than a warm resume). ") if ft else ""
    h = report.get("health") or {}
    store_note = (f"Rating, crash rate and device metrics come from the store snapshot of "
                  f"<b>{h['store_day']}</b>; crash rate is per 1,000 <b>iOS</b> sessions. "
                  if h.get("store_day") else
                  (f"No store data in this report — {html.escape(str(h.get('store_unavailable')))}. "
                   if h.get("store_unavailable") else ""))
    return f"""
<section class="card overview">
  <h2 class="ov-title">All projects — {day_label(report)}</h2>
  <div class="table-scroll"><table class="ov">
    <thead><tr><th>Project</th><th class="num">DAU</th><th class="num">Fresh %</th><th class="num">Errors</th>
      <th class="num">err/user</th><th class="num">worst err %</th>
      <th class="num">Warns</th><th class="num">warn/user</th><th class="num">worst warn %</th>
      <th class="num">iOS %</th><th class="num">Rating</th><th class="num">crash /1k sess</th>
      <th>Status</th></tr></thead>
    <tbody>{rows}</tbody>
  </table></div>
  <p class="ov-note">{store_note}All log figures are for <b>{day_label(report)}</b>. {fresh_note}err/user & warn/user show the <b>diff vs the {report['baseline_days']}-day baseline</b> ({base_lbl}, from {report['baseline_source']}). Worst error/warn % = the single signature at that level touching the largest share of that day's DAU. <b>Click a column header to sort</b> (again to reverse).</p>
</section>
"""


def funnels_summary(report):
    """Portfolio-level business-funnel rates in the main summary (per project that has them)."""
    projs = [p for p in report["projects"] if p.get("funnels")]
    if not projs:
        return ""
    blocks = []
    for p in projs:
        fns = []
        for fn in p["funnels"]:
            rates = [r for r in fn["rates"] if r["pct"] is not None]
            if not rates:
                continue
            chips = "".join(
                '<span class="fs-rate %s" title="%s"><b>%.0f%%</b> %s</span>'
                % (rate_tone(r), html.escape(r.get("business") or ""), r["pct"], html.escape(r["label"]))
                for r in rates)
            bd_html = ""
            for bd in fn.get("breakdowns", []):
                if not bd["reasons"]:
                    continue
                items = "".join(
                    '<li><span class="fs-bd-r">%s</span>'
                    '<span class="fs-bd-v"><b>%s</b>u · %.1f%% DAU</span></li>'
                    % (html.escape(rz["reason"][:90]), fmt_int(rz["users"]), rz["pct"])
                    for rz in bd["reasons"])
                bd_html += ('<div class="fs-bd"><span class="fs-bd-h">Top %s reasons</span>'
                            '<ul class="fs-bd-list">%s</ul></div>'
                            % (html.escape(bd["label"]), items))
            split_html = ""
            for sp in fn.get("splits", []):
                if not sp["dau"]:
                    continue
                schips = "".join(
                    '<span class="fs-rate %s"><b>%.0f%%</b> %s</span>'
                    % (rate_tone(r), r["pct"], html.escape(r["label"]))
                    for r in sp["rates"] if r["pct"] is not None)
                split_html += ('<div class="fs-split"><span class="fs-split-c">%s <b>%s</b>u</span>'
                               '<div class="fs-rates">%s</div></div>'
                               % (html.escape(sp["cohort"]), fmt_int(sp["dau"]), schips))
            fns.append('<div class="fs-fn"><span class="fs-fn-name">%s</span>'
                       '<div class="fs-rates">%s</div>%s%s</div>'
                       % (html.escape(fn["label"]), chips, split_html, bd_html))
        if fns:
            blocks.append('<div class="fs-proj"><div class="fs-proj-name">'
                          '<span class="status-dot %s"></span>%s</div>%s</div>'
                          % (p["status"], html.escape(p["name"]), "".join(fns)))
    if not blocks:
        return ""
    note = report.get("funnels_note") or ""
    note_html = f'<p class="ov-note">{note}</p>' if note else ""
    return ('<section class="card fsum"><h2 class="ov-title">Business funnels — key conversion rates</h2>'
            + note_html + "".join(blocks) + "</section>")


def chg_list(items, cls, render):
    if not items:
        return ""
    return f'<ul class="chg {cls}">' + "".join(f"<li>{render(x)}</li>" for x in items) + "</ul>"


VERDICT_META = {
    "fix": ("Fix", "err", "real defect"),
    "ux-assess": ("UX review", "warn", "user-facing"),
    "mute": ("Mute", "mute", "noise / down-level"),
    "review": ("Review", "muted", "unclassified"),
}


def _imp_line(label, val):
    if not val:
        return ""
    return '<div class="imp-line"><span class="imp-k">%s</span> %s</div>' % (label, html.escape(str(val)))


def impact_section(p):
    """Business-impact bar (item 4): who · how much · UX · business · what to do, per issue."""
    items = p.get("impact") or []
    if not items:
        return ""
    rows = []
    for i in items:
        tag, tone, _ = VERDICT_META.get(i.get("verdict"), (i.get("verdict") or "review", "muted", ""))
        plats = "/".join(i.get("plats") or []) or "—"
        action = i.get("action") or ""
        if i.get("owner"):
            action = (action + " · " if action else "") + "owner: " + i["owner"]
        rows.append(
            '<div class="imp-row %s">'
            '<div class="imp-head"><span class="hy-tag %s">%s</span>'
            '<span class="imp-issue" title="%s">%s</span></div>'
            '<div class="imp-metrics">%s users · <b>%.1f%% of DAU</b> · %s events · %s/user · %s · %s</div>'
            '<div class="imp-lines">%s%s%s</div></div>'
            % (tone, tone, tag, html.escape(i["issue"]), html.escape(i["issue"][:100]),
               fmt_int(i["users"]), i["pct"], fmt_int(i["events"]), i.get("per_user", 0),
               plats, html.escape(i.get("ver") or "—"),
               _imp_line("UX", i.get("ux")), _imp_line("Business", i.get("business")),
               _imp_line("Action", action)))
    return ('<h3 class="sub">Issues — business impact <span class="sub-hint">who · how much · UX · business · what to do</span></h3>'
            '<div class="imp">' + "".join(rows) + "</div>")


def funnels_section(p):
    """Business funnels (item 3): users reaching each stage + config-defined conversion rates."""
    fns = p.get("funnels") or []
    if not fns:
        return ""
    blocks = []
    for fn in fns:
        mx = max((s["pct"] for s in fn["stages"]), default=0) or 100.0
        rows = []
        for s in fn["stages"]:
            w = s["pct"] / mx * 100.0 if mx else 0.0
            rows.append(
                '<div class="fn-row"><div class="fn-lbl" title="%s">%s</div>'
                '<div class="fn-track"><div class="fn-fill" style="width:%.1f%%"></div></div>'
                '<div class="fn-val">%su<span class="fn-sub">%.1f%% DAU</span></div></div>'
                % (html.escape(s["label"]), html.escape(s["label"]), w, fmt_int(s["users"]), s["pct"]))
        chips = []
        for r in fn.get("rates", []):
            val = "n/a" if r["pct"] is None else ("%.0f%%" % r["pct"])
            chips.append('<span class="fn-rate %s" title="%s"><b>%s</b> %s</span>'
                         % (rate_tone(r), html.escape(r.get("business") or ""), val, html.escape(r["label"])))
        note = ('<div class="fn-note">%s</div>' % html.escape(fn["note"])) if fn.get("note") else ""
        rate_html = ('<div class="fn-rates">' + "".join(chips) + "</div>") if chips else ""
        split_html = ""
        for sp in fn.get("splits", []):
            if not sp["dau"]:
                continue
            schips = "".join(
                '<span class="fn-rate %s"><b>%s</b> %s</span>'
                % (rate_tone(r), "n/a" if r["pct"] is None else ("%.0f%%" % r["pct"]), html.escape(r["label"]))
                for r in sp["rates"])
            split_html += ('<div class="fn-split"><span class="fn-split-c">%s · <b>%su</b></span>'
                           '<div class="fn-rates">%s</div></div>'
                           % (html.escape(sp["cohort"]), fmt_int(sp["dau"]), schips))
        blocks.append('<div class="fn-card"><div class="fn-title">%s</div>%s%s%s%s</div>'
                      % (html.escape(fn["label"]), "".join(rows), rate_html, split_html, note))
    return ('<h3 class="sub">Business funnels <span class="sub-hint">users reaching each stage · % of DAU</span></h3>'
            '<div class="fn-grid">' + "".join(blocks) + "</div>")


def hygiene_section(p):
    """Log-sanitation (item 2): high-volume signatures bucketed to mute / fix / UX-review."""
    hy = p.get("hygiene") or {}
    cols = []
    for v in ("fix", "ux-assess", "mute", "review"):
        b = hy.get(v)
        if not b or not b.get("items"):
            continue
        tag, tone, _ = VERDICT_META.get(v, (v, "muted", ""))
        items = "".join(
            '<li title="%s">%s <span class="muted">%s · %su · %.1f%%</span></li>'
            % (html.escape(i["msg"]), html.escape(i["msg"][:64]), fmt_int(i["total"]),
               fmt_int(i["users"]), i["pct"])
            for i in b["items"])
        cols.append(
            '<div class="hy-col"><div class="hy-head"><span class="hy-tag %s">%s</span>'
            '<span class="hy-meta">%d sig · %s ev · worst %.1f%% DAU</span></div>'
            '<ul class="hy-list">%s</ul></div>'
            % (tone, tag, b["count"], fmt_int(b["events"]), b["worst_pct"], items))
    if not cols:
        return ""
    return ('<h3 class="sub">Log hygiene <span class="sub-hint">what to mute / fix / send to UX-review</span></h3>'
            '<div class="hy-grid">' + "".join(cols) + "</div>")


def operation_delta(flow, key):
    """Compact higher-is-worse delta label against the flow's saved/OpenSearch baseline."""
    delta = flow.get(key)
    baseline = flow.get("baseline") or {}
    days = baseline.get("days", 0)
    if delta is None or not days:
        return ""
    arrow = "▲" if delta > 0 else ("▼" if delta < 0 else "–")
    return f" {arrow}{abs(delta):.0f}% vs {days}d"


def operation_section(p):
    """Endpoint/provider health: terminal outcome, retry friction, ownership, drilldown."""
    cards = []
    for profile in p.get("operations", []):
        for flow in profile.get("flows", []):
            failure_rate = flow.get("terminal_failure_rate_pct")
            failure_text = "n/a" if failure_rate is None else f"{failure_rate:.3f}%{operation_delta(flow, 'terminal_failure_delta_pct')}"
            retry = flow.get("retry") or {}
            retry_text = ""
            if retry.get("events") or retry.get("users"):
                retry_text = (f'<br>Retry: <b>{flow.get("retry_reach_pct_dau", 0):.3f}% DAU{operation_delta(flow, "retry_reach_delta_pct")}</b> '
                              f'· {fmt_int(retry.get("events", 0))} events · {flow.get("retry_events_per_user", 0):.2f}/affected user')
            if flow.get("users_affected") is not None:
                retry_text += (f'<br>Reach: <b>{fmt_int(flow["users_affected"])}u ({flow.get("problem_pct_dau", 0):.3f}% DAU)</b> '
                              f'· sessions {fmt_int(flow.get("sessions_with_problem", 0))}/{fmt_int(flow.get("total_sessions", 0))}')
            classes = []
            for bucket, prefix in (("failure", "final"), ("retry", "retry")):
                for kind, count in (flow.get("classes", {}).get(bucket, {}) or {}).items():
                    classes.append(f'{prefix} {OP_CLASS_LABELS.get(kind, kind)} {fmt_int(count)}')
            reasons = [f'{label} {fmt_int(count)}' for label, count in (flow.get("reasons") or {}).items()]
            drill = flow.get("drilldown")
            extra = []
            if classes:
                extra.append("Classes: " + "; ".join(classes))
            if reasons:
                extra.append("Failure reasons: " + "; ".join(reasons))
            if drill:
                peaks = ", ".join(f'{x["hour"]}: {fmt_int(x["events"])}' for x in drill.get("hours", []))
                versions = ", ".join(f'{x["value"]} {fmt_int(x["events"])}ev/{fmt_int(x["users"])}u' for x in drill.get("versions", []))
                platforms = ", ".join(f'{x["value"]} {fmt_int(x["events"])}ev/{fmt_int(x["users"])}u' for x in drill.get("platforms", []))
                if peaks: extra.append("Top non-success hours: " + peaks)
                if versions: extra.append("Version split: " + versions)
                if platforms: extra.append("Platform split: " + platforms)
            if flow.get("classification_truncated"):
                extra.append("Class scan capped; aggregate outcomes remain exact")
            cards.append(
                '<div class="op-card %s"><div class="op-title">%s <span class="op-status">%s</span></div>'
                '<div class="op-metrics">Terminal: <b>%s failed</b> · %s success · %s failure%s</div>'
                '%s</div>'
                % (flow.get("status", "healthy"), html.escape(profile.get("label", "Operation") + " — " + flow.get("label", flow.get("key", ""))),
                   html.escape(flow.get("status", "healthy")), failure_text,
                   fmt_int(flow.get("success", {}).get("events", 0)), fmt_int(flow.get("failure", {}).get("events", 0)),
                   retry_text, ('<div class="op-detail">' + "<br>".join(html.escape(x) for x in extra) + "</div>") if extra else ""))
    if not cards:
        return ""
    return ('<h3 class="sub">Provider / endpoint health <span class="sub-hint">terminal outcome · retry friction · failure ownership</span></h3>'
            '<div class="op-grid">' + "".join(cards) + "</div>")


def project_card_image(p):
    """Slim card for the PNG render: status + core tiles + funnel infographics only.
    Text-heavy sections (business impact, top errors/warnings, hygiene, stacktraces,
    categories, signals, releases) live in the .md and full .html, not the image."""
    st = p["status"]
    rel = ('<div class="release">New release: '
           + ", ".join(html.escape(v) for v in p["new_releases"]) + "</div>") if p["new_releases"] else ""
    return f"""
<section class="card">
  <header class="card-head">
    <div class="card-title"><span class="status-dot {st}"></span><h2>{html.escape(p['name'])}</h2>
      <span class="status-chip {st}">{STATUS_LABEL[st]}</span></div>
    <div class="card-window">{p['report_day']} &middot; baseline {p['baseline_source']}</div>
  </header>
  {rel}
  <div class="tiles">
    <div class="tile"><div class="tile-val">{fmt_int(p['dau'])}</div>
      <div class="tile-lbl">DAU (unique users)<br><span class="tile-sub">baseline ~{fmt_int(p['base_dau'])}/day</span></div></div>
    <div class="tile"><div class="tile-val">{p.get('fresh_pct', 0):.0f}<span class="unit">%</span></div>
      <div class="tile-lbl">fresh launches &middot; % of DAU<br><span class="tile-sub">{fmt_int(p.get('fresh_users', 0))} cold/fresh</span></div></div>
    <div class="tile"><div class="tile-val">{p['err_per_user']:.1f}<span class="unit">/user</span></div>
      <div class="tile-lbl">errors per user {fmt_delta(p['err_per_user_delta_pct'])}<br><span class="tile-sub">baseline {p['err_per_user_base']:.1f}</span></div></div>
    <div class="tile"><div class="tile-val">{p['top_error_reach']:.1f}<span class="unit">%</span></div>
      <div class="tile-lbl">worst error &middot; % of DAU<br><span class="tile-sub" title="{html.escape(p['top_error_reach_msg'])}">{html.escape(p['top_error_reach_msg'][:32]) or '—'}</span></div></div>
    <div class="tile"><div class="tile-val">{p['warn_per_user']:.1f}<span class="unit">/user</span></div>
      <div class="tile-lbl">warnings per user {fmt_delta(p['warn_per_user_delta_pct'])}<br><span class="tile-sub">baseline {p['warn_per_user_base']:.1f}</span></div></div>
    <div class="tile"><div class="tile-val">{fmt_int(p['err_total'])}</div>
      <div class="tile-lbl">errors (day)<br><span class="tile-sub">{fmt_int(p['warn_total'])} warnings</span></div></div>
  </div>
  {funnels_section(p)}
</section>
"""


def project_card(p, signals_meta):
    st = p["status"]
    rel = ('<div class="release">New release: '
           + ", ".join(html.escape(v) for v in p["new_releases"]) + "</div>") if p["new_releases"] else ""
    appeared = chg_list(p["appeared_errors"], "app",
                        lambda t: f'🆕 {html.escape(t["msg"][:90])} <span class="muted">({fmt_int(t["total"])} · {t["pct"]:.1f}% DAU)</span>')
    disappeared = chg_list(p["disappeared_errors"], "gone",
                        lambda t: f'✅ {html.escape(t["msg"][:90])} <span class="muted">(was {fmt_int(t["total"])} · {t.get("pct", 0):.1f}% DAU)</span>')
    churn = ""
    if appeared or disappeared:
        churn = (f'<div class="cols"><div class="col"><h3 class="sub">New errors today</h3>{appeared or "<p class=empty>none</p>"}</div>'
                 f'<div class="col"><h3 class="sub">Gone since baseline</h3>{disappeared or "<p class=empty>none</p>"}</div></div>')
    appeared_warns = chg_list(p["appeared_warnings"], "app",
                              lambda t: f'🆕 {html.escape(t["msg"][:90])} <span class="muted">({fmt_int(t["total"])} · {t["pct"]:.1f}% DAU)</span>')
    disappeared_warns = chg_list(p["disappeared_warnings"], "gone",
                                 lambda t: f'✅ {html.escape(t["msg"][:90])} <span class="muted">(was {fmt_int(t["total"])} · {t.get("pct", 0):.1f}% DAU)</span>')
    warn_churn = ""
    if appeared_warns or disappeared_warns:
        warn_churn = (f'<div class="cols"><div class="col"><h3 class="sub">New warning signatures today</h3>{appeared_warns or "<p class=empty>none</p>"}</div>'
                      f'<div class="col"><h3 class="sub">Warnings gone since baseline</h3>{disappeared_warns or "<p class=empty>none</p>"}</div></div>')
    return f"""
<section class="card">
  <header class="card-head">
    <div class="card-title"><span class="status-dot {st}"></span><h2>{html.escape(p['name'])}</h2>
      <span class="status-chip {st}">{STATUS_LABEL[st]}</span></div>
    <div class="card-window">{p['report_day']} &middot; baseline {p['baseline_source']}</div>
  </header>
  {rel}
  <div class="tiles">
    <div class="tile"><div class="tile-val">{fmt_int(p['dau'])}</div>
      <div class="tile-lbl">DAU (unique users)<br><span class="tile-sub">baseline ~{fmt_int(p['base_dau'])}/day</span></div></div>
    <div class="tile"><div class="tile-val">{p['err_per_user']:.1f}<span class="unit">/user</span></div>
      <div class="tile-lbl">errors per user {fmt_delta(p['err_per_user_delta_pct'])}<br><span class="tile-sub">baseline {p['err_per_user_base']:.1f}</span></div></div>
    <div class="tile"><div class="tile-val">{p['top_error_reach']:.1f}<span class="unit">%</span></div>
      <div class="tile-lbl">worst error &middot; % of DAU<br><span class="tile-sub" title="{html.escape(p['top_error_reach_msg'])}">{html.escape(p['top_error_reach_msg'][:32]) or '—'}</span></div></div>
    <div class="tile"><div class="tile-val">{p['warn_per_user']:.1f}<span class="unit">/user</span></div>
      <div class="tile-lbl">warnings per user {fmt_delta(p['warn_per_user_delta_pct'])}<br><span class="tile-sub">baseline {p['warn_per_user_base']:.1f}</span></div></div>
    <div class="tile"><div class="tile-val">{p['top_warn_reach']:.1f}<span class="unit">%</span></div>
      <div class="tile-lbl">worst warning &middot; % of DAU<br><span class="tile-sub" title="{html.escape(p['top_warn_reach_msg'])}">{html.escape(p['top_warn_reach_msg'][:32]) or '—'}</span></div></div>
    <div class="tile"><div class="tile-val">{fmt_int(p['err_total'])}</div>
      <div class="tile-lbl">errors (day)<br><span class="tile-sub">{fmt_int(p['warn_total'])} warnings</span></div></div>
  </div>
  {impact_section(p)}
  <div class="cols">
    <div class="col"><h3 class="sub">Top 10 errors <span class="sub-hint">total · users · % of DAU</span></h3>{sig_bars(p['top_errors'], 'err')}</div>
    <div class="col"><h3 class="sub">Top 10 warnings <span class="sub-hint">total · users · % of DAU</span></h3>{sig_bars(p['top_warns'], 'warn')}</div>
  </div>
  {churn}
  {warn_churn}
  {funnels_section(p)}
  {operation_section(p)}
  {hygiene_section(p)}
  <div class="cols">
    <div class="col"><h3 class="sub">Errors by category</h3>{cat_bars(p['errors_by_cat'], 'err')}</div>
    <div class="col"><h3 class="sub">Warnings by category</h3>{cat_bars(p['warns_by_cat'], 'warn')}</div>
  </div>
  {'<h3 class="sub">Network / server signals</h3>' + signal_grid(p['signals'], signals_meta) if p['signals'] else ''}
  <h3 class="sub">Releases in prod — rollout % of DAU & error rate <span class="sub-hint">compare new vs old version</span></h3>{version_table(p['versions_detail'])}
</section>
"""


def render_inner(report, image=False):
    ov = report["overall_status"]
    counts = {"healthy": 0, "watch": 0, "degraded": 0, "nodata": 0}
    for p in report["projects"]:
        counts[p["status"]] = counts.get(p["status"], 0) + 1
    summary = f'{counts["degraded"]} degraded &middot; {counts["watch"]} watch &middot; {counts["healthy"]} healthy'
    if counts["nodata"]:
        summary += f' &middot; {counts["nodata"]} low-data'
    b = report["brand"]
    detail = "\n".join(project_card_image(p) if image else project_card(p, report["signals_meta"])
                       for p in report["projects"])
    detail_note = ('<p class="detail-sub muted">Core infographic per project — status, DAU/fresh-launch %, error rates and loading funnels. '
                   'Full top-errors, business-impact, log-hygiene and stacktraces are in the accompanying <b>.md</b> report.</p>'
                   if image else "")
    foot = "" if image else f"""
  <footer class="foot">
    <p>Every figure is for the report day <b>{day_label(report)}</b>. Rates (errors/warnings per unique user) and the worst-error reach use that day's DAU as denominator. <b>diff %</b> compares the report day to the average of the {report['baseline_days']} days before it ({report['baseline_source']}). Each signature shows <b>total events · unique users · % of DAU</b>. Message groups are exact signatures; secrets redacted.</p>
  </footer>"""
    return CSS + f"""
<div class="wrap">
  <header class="page-head">
    <div class="brand"><div class="pulse-mark {ov}"></div>
      <div><div class="eyebrow">{html.escape(b['org'])} &middot; {html.escape(b['product'])}</div>
        <h1>Prod health, {day_label(report)}</h1>
        <div class="daywin">{report['window_utc']}{' &middot; last complete UTC day' if report.get('is_last_complete') else ''}</div></div></div>
    <div class="head-meta"><span class="status-chip {ov} big">{STATUS_LABEL[ov]}</span>
      <div class="meta-line">{len(report['projects'])} projects &middot; {summary}</div>
      <div class="meta-line muted">generated {report['generated_utc']} &middot; baseline from {report['baseline_source']}</div></div>
  </header>
  {attention_section(report)}
  {overview_table(report)}
  {funnels_summary(report)}
  <h2 class="detail-head">Per-project detail — {day_label(report)}</h2>
  {detail_note}
  {detail}{foot}
</div>
""" + ("" if image else SORT_SCRIPT)


SORT_SCRIPT = """<script>
(function(){
  var table=document.querySelector('table.ov'); if(!table) return;
  var ths=table.querySelectorAll('thead th'); var tbody=table.querySelector('tbody');
  var state={col:-1,asc:true};
  function val(row,i){var td=row.children[i]; if(!td) return '';
    var d=td.getAttribute('data-sort'); if(d===null) d=td.textContent.trim();
    var n=parseFloat(String(d).replace(/,/g,'')); return isNaN(n)?String(d).toLowerCase():n;}
  ths.forEach(function(th,i){th.addEventListener('click',function(){
    state.asc = state.col===i ? !state.asc : true; state.col=i;
    var rows=Array.prototype.slice.call(tbody.querySelectorAll('tr'));
    rows.sort(function(a,b){var x=val(a,i),y=val(b,i);
      if(x<y) return state.asc?-1:1; if(x>y) return state.asc?1:-1; return 0;});
    rows.forEach(function(r){tbody.appendChild(r);});
    ths.forEach(function(t){t.removeAttribute('data-arrow');});
    th.setAttribute('data-arrow', state.asc?' \\u25B2':' \\u25BC');});});
})();
</script>"""


CSS = """<style>
:root{--bg:#f6f8fb;--surface:#ffffff;--surface-2:#f1f4f8;--ink:#131a24;--ink-2:#455163;--muted:#8593a4;--line:#e4e9f0;--accent:#2f6df6;
--good:#158a55;--good-bg:#e3f4ec;--good-line:#bfe6d2;--watch:#b0791a;--watch-bg:#fbf0d8;--watch-line:#f0d9a6;--bad:#cf3138;--bad-bg:#fbe3e4;--bad-line:#f2c2c4;
--bar-err:#e2655d;--bar-warn:#d7a13c;--shadow:0 1px 2px rgba(19,26,36,.06),0 4px 16px rgba(19,26,36,.05);}
@media (prefers-color-scheme:dark){:root{--bg:#0c1016;--surface:#151b24;--surface-2:#1b232e;--ink:#e9eef5;--ink-2:#aab7c6;--muted:#6d7c8d;--line:#232d3a;--accent:#6f9dff;
--good:#42bd88;--good-bg:#11291f;--good-line:#1e4634;--watch:#e0b45c;--watch-bg:#2b2312;--watch-line:#4a3c18;--bad:#f2726f;--bad-bg:#301a1b;--bad-line:#54282a;
--bar-err:#f2726f;--bar-warn:#e0b45c;--shadow:0 1px 2px rgba(0,0,0,.4),0 6px 20px rgba(0,0,0,.35);}}
:root[data-theme="light"]{--bg:#f6f8fb;--surface:#ffffff;--surface-2:#f1f4f8;--ink:#131a24;--ink-2:#455163;--muted:#8593a4;--line:#e4e9f0;--accent:#2f6df6;
--good:#158a55;--good-bg:#e3f4ec;--good-line:#bfe6d2;--watch:#b0791a;--watch-bg:#fbf0d8;--watch-line:#f0d9a6;--bad:#cf3138;--bad-bg:#fbe3e4;--bad-line:#f2c2c4;
--bar-err:#e2655d;--bar-warn:#d7a13c;--shadow:0 1px 2px rgba(19,26,36,.06),0 4px 16px rgba(19,26,36,.05);}
:root[data-theme="dark"]{--bg:#0c1016;--surface:#151b24;--surface-2:#1b232e;--ink:#e9eef5;--ink-2:#aab7c6;--muted:#6d7c8d;--line:#232d3a;--accent:#6f9dff;
--good:#42bd88;--good-bg:#11291f;--good-line:#1e4634;--watch:#e0b45c;--watch-bg:#2b2312;--watch-line:#4a3c18;--bad:#f2726f;--bad-bg:#301a1b;--bad-line:#54282a;
--bar-err:#f2726f;--bar-warn:#e0b45c;--shadow:0 1px 2px rgba(0,0,0,.4),0 6px 20px rgba(0,0,0,.35);}
*{box-sizing:border-box}
.wrap{font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;color:var(--ink);background:var(--bg);max-width:1240px;margin:0 auto;padding:28px 22px 48px;line-height:1.5}
.tile-val,.bar-val,.delta,.sig-val,.chip b,.card-window,.num{font-family:ui-monospace,"SF Mono",Menlo,monospace;font-variant-numeric:tabular-nums}
h1{font-size:26px;margin:2px 0 0;letter-spacing:-.02em}
h2{font-size:18px;margin:0;letter-spacing:-.01em}
.eyebrow{font-size:11px;text-transform:uppercase;letter-spacing:.13em;color:var(--muted);font-weight:600}
.daywin{font-size:12px;color:var(--muted);margin-top:4px;font-family:ui-monospace,"SF Mono",Menlo,monospace;font-variant-numeric:tabular-nums}
.page-head{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap;padding-bottom:18px;border-bottom:1px solid var(--line);margin-bottom:20px}
.brand{display:flex;gap:14px;align-items:center}
.pulse-mark{width:34px;height:34px;border-radius:9px;flex:none;position:relative;background:var(--surface-2);border:1px solid var(--line)}
.pulse-mark::after{content:"";position:absolute;inset:0;margin:auto;width:14px;height:14px;border-radius:50%}
.pulse-mark.healthy::after{background:var(--good);box-shadow:0 0 0 4px var(--good-bg)}
.pulse-mark.watch::after{background:var(--watch);box-shadow:0 0 0 4px var(--watch-bg)}
.pulse-mark.degraded::after{background:var(--bad);box-shadow:0 0 0 4px var(--bad-bg)}
.head-meta{text-align:right}.meta-line{font-size:12.5px;color:var(--ink-2);margin-top:5px}.meta-line.muted{color:var(--muted)}
.status-chip{display:inline-block;padding:3px 11px;border-radius:999px;font-size:12px;font-weight:700;border:1px solid transparent}
.status-chip.big{font-size:13px;padding:5px 14px}
.status-chip.healthy{color:var(--good);background:var(--good-bg);border-color:var(--good-line)}
.status-chip.watch{color:var(--watch);background:var(--watch-bg);border-color:var(--watch-line)}
.status-chip.degraded{color:var(--bad);background:var(--bad-bg);border-color:var(--bad-line)}
.status-chip.nodata{color:var(--muted);background:var(--surface-2);border-color:var(--line)}
.card{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:20px;margin-bottom:20px;box-shadow:var(--shadow)}
.overview{padding-bottom:14px}.ov-title{margin-bottom:12px}
.detail-head{font-size:14px;text-transform:uppercase;letter-spacing:.1em;color:var(--muted);margin:26px 4px 14px}
.table-scroll{overflow-x:auto}
table.ov{width:100%;border-collapse:collapse;font-size:13px;min-width:640px}
table.ov th{text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);padding:6px 10px;border-bottom:1px solid var(--line);font-weight:600;cursor:pointer;user-select:none;white-space:nowrap}
table.ov th:hover{color:var(--ink-2)}
table.ov th[data-arrow]::after{content:attr(data-arrow);color:var(--accent);font-weight:700}
table.ov td{padding:8px 10px;border-bottom:1px solid var(--line)}
table.ov td.num,table.ov th.num{text-align:right}
table.ov tbody tr:hover{background:var(--surface-2)}
.ov-note{font-size:11px;color:var(--muted);margin-top:10px}
.att .ov-title{margin-bottom:8px}
.att-row{display:flex;align-items:baseline;gap:4px;font-size:12.5px;color:var(--ink-2);padding:5px 0;border-bottom:1px dotted var(--line)}
.att-row:last-child{border-bottom:none}
.att-text{min-width:0}.att-text b{color:var(--ink)}
.rel-flag{font-size:11px}
.card-head{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}
.card-title{display:flex;align-items:center;gap:10px}
.status-dot{width:9px;height:9px;border-radius:50%;flex:none;display:inline-block;margin-right:7px}
.status-dot.healthy{background:var(--good)}.status-dot.watch{background:var(--watch)}.status-dot.degraded{background:var(--bad)}.status-dot.nodata{background:var(--muted)}
.card-window{font-size:12px;color:var(--muted)}
.release{margin-top:12px;padding:8px 12px;border-radius:8px;background:var(--surface-2);border:1px solid var(--line);font-size:13px;font-weight:600}
.tiles{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:16px 0 6px}
.tile{background:var(--surface-2);border:1px solid var(--line);border-radius:11px;padding:13px 14px}
.tile-val{font-size:23px;font-weight:700;letter-spacing:-.02em}
.tile-val .unit{font-size:12px;color:var(--muted);font-weight:600;margin-left:2px}
.tile-lbl{font-size:11.5px;color:var(--ink-2);margin-top:3px;line-height:1.35}.tile-sub{color:var(--muted);font-size:11px}
.delta{font-size:11px;font-weight:700;padding:1px 5px;border-radius:5px;white-space:nowrap}
.delta.up-bad{color:var(--bad);background:var(--bad-bg)}.delta.down-good{color:var(--good);background:var(--good-bg)}.delta.flat{color:var(--muted)}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:22px;margin-top:14px}.col{min-width:0}
.sub{font-size:11px;text-transform:uppercase;letter-spacing:.1em;color:var(--muted);margin:12px 0 9px;font-weight:700}
.sub-hint{text-transform:none;letter-spacing:0;font-weight:500;color:var(--muted);opacity:.8}
.bar-row{display:grid;grid-template-columns:1fr 70px auto;align-items:center;gap:9px;margin-bottom:6px}
.bar-label{font-size:12px;color:var(--ink-2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.bar-track{background:var(--surface-2);border-radius:4px;height:9px;overflow:hidden}
.bar-fill{height:100%;border-radius:4px}.bar-fill.err{background:var(--bar-err)}.bar-fill.warn{background:var(--bar-warn)}
.bar-val{font-size:12px;color:var(--ink);text-align:right;min-width:92px;display:flex;flex-direction:column;line-height:1.2}
.bar-sub{font-size:10px;color:var(--muted)}
.sdelta{font-size:10px;font-weight:700;padding:0 3px;border-radius:4px}
.sdelta.down-good{color:var(--good)}.sdelta.up-bad{color:var(--bad)}.sdelta.flat{color:var(--muted)}.sdelta.new{color:var(--accent)}
table.ver{width:100%;border-collapse:collapse;font-size:12px;min-width:440px}
table.ver th{text-align:left;font-size:10px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);padding:4px 8px;border-bottom:1px solid var(--line);font-weight:600;white-space:nowrap}
table.ver td{padding:5px 8px;border-bottom:1px solid var(--line)}
table.ver td.num,table.ver th.num{text-align:right}
table.ver tbody tr:hover{background:var(--surface-2)}
.chg{margin:0;padding-left:18px;font-size:12.5px;line-height:1.6}.chg .muted{color:var(--muted)}
.chg.gone li{color:var(--good)}
.sig-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px}
.sig{background:var(--surface-2);border:1px solid var(--line);border-radius:9px;padding:10px 12px}
.sig-val{font-size:18px;font-weight:700}.sig-lbl{font-size:11px;color:var(--muted);margin-top:2px}
.pv-row{display:flex;gap:10px;align-items:baseline;margin-bottom:7px}
.pv-plat{font-size:11px;font-weight:700;color:var(--ink-2);min-width:58px}
.chips{display:flex;flex-wrap:wrap;gap:7px}
.chip{font-size:12px;color:var(--ink-2);background:var(--surface-2);border:1px solid var(--line);border-radius:7px;padding:4px 9px}
.chip b{margin-left:7px;color:var(--ink);font-weight:700}
.empty{color:var(--muted);font-size:12px;font-style:italic}
.sig-sub{font-size:10px;color:var(--muted);margin-top:2px;font-family:ui-monospace,"SF Mono",Menlo,monospace}
.hy-tag{display:inline-block;font-size:10px;font-weight:700;padding:1px 7px;border-radius:999px;text-transform:uppercase;letter-spacing:.04em;white-space:nowrap}
.hy-tag.err{color:var(--bad);background:var(--bad-bg);border:1px solid var(--bad-line)}
.hy-tag.warn{color:var(--watch);background:var(--watch-bg);border:1px solid var(--watch-line)}
.hy-tag.mute,.hy-tag.muted{color:var(--muted);background:var(--surface-2);border:1px solid var(--line)}
.imp{display:flex;flex-direction:column;gap:10px;margin-bottom:4px}
.imp-row{background:var(--surface-2);border:1px solid var(--line);border-left:3px solid var(--muted);border-radius:9px;padding:11px 13px}
.imp-row.err{border-left-color:var(--bad)}.imp-row.warn{border-left-color:var(--watch)}
.imp-head{display:flex;align-items:center;gap:9px;margin-bottom:5px;min-width:0}
.imp-issue{font-size:13px;font-weight:600;color:var(--ink);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.imp-metrics{font-size:11.5px;color:var(--ink-2);font-family:ui-monospace,"SF Mono",Menlo,monospace;font-variant-numeric:tabular-nums;margin-bottom:6px}
.imp-lines{display:flex;flex-direction:column;gap:3px}
.imp-line{font-size:12px;color:var(--ink-2);line-height:1.4}
.imp-k{display:inline-block;min-width:66px;font-size:10px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);font-weight:700}
.fn-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.fn-card{background:var(--surface-2);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.fn-title{font-size:12.5px;font-weight:700;color:var(--ink);margin-bottom:9px}
.fn-row{display:grid;grid-template-columns:1fr 88px auto;gap:8px;align-items:center;margin-bottom:5px}
.fn-lbl{font-size:11.5px;color:var(--ink-2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.fn-track{background:var(--surface);border:1px solid var(--line);border-radius:4px;height:8px;overflow:hidden}
.fn-fill{height:100%;background:var(--accent);border-radius:4px}
.fn-val{font-size:11px;color:var(--ink);text-align:right;display:flex;flex-direction:column;line-height:1.15;font-family:ui-monospace,"SF Mono",Menlo,monospace;font-variant-numeric:tabular-nums}
.fn-sub{font-size:9.5px;color:var(--muted)}
.fn-rates{display:flex;flex-wrap:wrap;gap:6px;margin-top:9px;padding-top:9px;border-top:1px solid var(--line)}
.fn-rate{font-size:11px;color:var(--ink-2);background:var(--surface);border:1px solid var(--line);border-radius:6px;padding:2px 8px}
.fn-rate b{color:var(--accent);font-variant-numeric:tabular-nums}
.fn-split{display:flex;gap:8px;align-items:baseline;margin-top:7px;flex-wrap:wrap}
.fn-split-c{font-size:10.5px;color:var(--muted);min-width:130px;font-variant-numeric:tabular-nums}
.fn-split-c b{color:var(--ink-2)}
.fn-split .fn-rates{margin-top:0;padding-top:0;border-top:none;gap:5px}
.fn-note{font-size:11px;color:var(--muted);margin-top:8px;font-style:italic}
.fsum .ov-title{margin-bottom:6px}
.fs-proj{padding:11px 0;border-bottom:1px solid var(--line)}
.fs-proj:last-child{border-bottom:none;padding-bottom:2px}
.fs-proj-name{font-size:13px;font-weight:700;color:var(--ink);margin-bottom:8px;display:flex;align-items:center}
.fs-fn{display:flex;gap:10px;align-items:baseline;margin-bottom:6px;flex-wrap:wrap}
.fs-fn-name{font-size:11.5px;color:var(--ink-2);min-width:190px;font-weight:600}
.fs-rates{display:flex;flex-wrap:wrap;gap:6px}
.fs-rate{font-size:11px;color:var(--ink-2);background:var(--surface-2);border:1px solid var(--line);border-radius:6px;padding:2px 8px}
.fs-rate b{color:var(--accent);font-variant-numeric:tabular-nums;margin-right:3px}
.fs-rate.good,.fn-rate.good{background:var(--good-bg);border-color:var(--good-line)}
.fs-rate.good b,.fn-rate.good b{color:var(--good)}
.fs-rate.watch,.fn-rate.watch{background:var(--watch-bg);border-color:var(--watch-line)}
.fs-rate.watch b,.fn-rate.watch b{color:var(--watch)}
.fs-rate.bad,.fn-rate.bad{background:var(--bad-bg);border-color:var(--bad-line)}
.fs-rate.bad b,.fn-rate.bad b{color:var(--bad)}
.fs-bd{flex-basis:100%;margin:5px 0 3px 190px}
.fs-bd-h{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.03em;color:var(--muted)}
.fs-bd-list{margin:3px 0 0;padding:0;list-style:none}
.fs-bd-list li{display:flex;justify-content:space-between;gap:12px;font-size:11px;color:var(--ink-2);padding:1.5px 0;border-bottom:1px dotted var(--line)}
.fs-bd-list li:last-child{border-bottom:none}
.fs-bd-r{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.fs-bd-v{white-space:nowrap;color:var(--muted);font-variant-numeric:tabular-nums}
.fs-bd-v b{color:var(--ink);margin-right:2px}
.fs-split{flex-basis:100%;display:flex;gap:10px;align-items:baseline;margin:4px 0 0 190px}
.fs-split-c{font-size:10.5px;color:var(--muted);min-width:150px;font-variant-numeric:tabular-nums}
.fs-split-c b{color:var(--ink-2);margin:0 1px}
.hy-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}
.hy-col{background:var(--surface-2);border:1px solid var(--line);border-radius:10px;padding:11px 12px}
.hy-head{display:flex;align-items:center;gap:8px;margin-bottom:7px;flex-wrap:wrap}
.hy-meta{font-size:10px;color:var(--muted);font-family:ui-monospace,"SF Mono",Menlo,monospace}
.hy-list{margin:0;padding-left:15px;font-size:11.5px;line-height:1.55;color:var(--ink-2)}
.hy-list .muted{font-size:10px;font-family:ui-monospace,"SF Mono",Menlo,monospace}
.op-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(310px,1fr));gap:12px}
.op-card{background:var(--surface-2);border:1px solid var(--line);border-radius:10px;padding:12px}
.op-card.watch{border-color:var(--watch-line)}.op-card.alert{border-color:var(--bad-line)}
.op-title{font-weight:750;font-size:13px;margin-bottom:8px}.op-status{font-size:10px;margin-left:6px;text-transform:uppercase;color:var(--muted)}
.op-metrics{font-size:12px;line-height:1.6;color:var(--ink-2)}.op-metrics b{color:var(--ink)}
.op-detail{font-size:11px;line-height:1.55;color:var(--muted);margin-top:7px}
.foot{margin-top:8px;padding-top:16px;border-top:1px solid var(--line);color:var(--muted);font-size:11.5px}
@media (max-width:720px){.tiles{grid-template-columns:repeat(2,1fr)}.cols{grid-template-columns:1fr;gap:8px}.fn-grid{grid-template-columns:1fr}.fs-fn{flex-direction:column;gap:3px}.fs-fn-name{min-width:0}.page-head{flex-direction:column}.head-meta{text-align:left}}
</style>"""

SKELETON_HEAD = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
                 '<meta name="viewport" content="width=device-width,initial-scale=1">'
                 "<title>{title}</title><style>body{{margin:0}}</style></head><body>")
SKELETON_TAIL = "</body></html>"


def fmt_metric(value):
    """Device metrics span 0.02 to 3000, so the precision follows the magnitude."""
    if value is None:
        return "—"
    if abs(value) >= 100:
        return f"{value:,.0f}"
    return f"{value:.1f}" if abs(value) >= 10 else f"{value:.2f}"


def _health_move(delta, unit="", digits=2):
    """Nothing at all when the move rounds to zero: '▼0.00' claims a direction it cannot see."""
    if delta is None or abs(delta) < 0.5 / (10 ** digits):
        return ""
    return f" {'▲' if delta > 0 else '▼'}{abs(delta):.{digits}f}{unit}"


def render_health_slack(report):
    """One line per project: is this project healthy, and on what evidence.

    Deliberately the first block of the message — the log detail below answers "why", this
    answers "which projects should I even look at". Every number carries its unit, and the
    iOS-only ones are marked, because a crash rate over all-platform DAU is not a fact.
    """
    icon = {"healthy": "\U0001f7e2", "watch": "\U0001f7e1", "degraded": "\U0001f534",
            "nodata": "⚪"}
    health = report.get("health") or {}
    rows = health.get("rows") or []
    if not rows:
        return []
    out = ["", "*Per-project metrics (client logs + stores):*"]
    age = health.get("store_age_days")
    when = ("" if not age else
            f", {age}d older than the log window" if age > 0 else
            f", read {-age}d after the log window")
    store_note = (f"store data {health['store_day']}{when}" if health.get("store_day")
                  else f"no store data ({health.get('store_unavailable')})")
    # One shared caveat said once beats the same words on every row.
    pendings = {r["analytics_pending"] for r in rows if r.get("analytics_pending")}
    with_store = [r for r in rows if r.get("in_store_report")]
    shared_pending = (pendings.pop() if len(pendings) == 1
                      and len([r for r in with_store if r.get("analytics_pending")])
                      == len(with_store) else None)
    out.append(f"_DAU + errors from client logs · rating, crash rate and device metrics from the "
               f"stores ({store_note}) · iOS-only figures marked_"
               + (f"\n_iOS crashes and sessions: {shared_pending} for every app._"
                  if shared_pending else ""))
    detailed = [r for r in rows if r["status"] in ("degraded", "watch")]
    brief = [r for r in rows if r["status"] == "healthy"]
    for r in detailed:
        bits = []
        if r.get("dau") is not None:
            bits.append(f"{fmt_int(r['dau'])} DAU")
        elif r.get("coverage_note"):
            bits.append(r["coverage_note"])
        share = r.get("ios_share_pct")
        if share is not None:
            bits.append(f"iOS {share:.0f}%" if share >= 10 else f"iOS {share:.1f}%")
        if r.get("err_per_user") is not None:
            bits.append(f"err {r['err_per_user']:.1f}/u"
                        + (f" ({r['err_per_user_delta_pct']:+.0f}%)"
                           if r.get("err_per_user_delta_pct") is not None else ""))
        if r.get("err_pct_users") is not None:
            bits.append(f"{r['err_pct_users']:.0f}% users hit an error")
        if r.get("rating") is not None:
            bits.append(f"{r['rating']:.2f}★" + _health_move(r.get("rating_delta")))
        if r.get("crash_per_1k_sessions") is not None:
            bits.append(f"iOS crash {r['crash_per_1k_sessions']:.2f}/1k sess"
                        + _health_move(r.get("crash_per_1k_delta")))
        elif r.get("analytics_pending") and not shared_pending:
            bits.append("iOS crash pending")
        if r.get("sessions_per_ios_dau") is not None:
            bits.append(f"{r['sessions_per_ios_dau']:.1f} sess/iOS user")
        if r.get("crashes_per_1k_ios_dau") is not None:
            bits.append(f"{r['crashes_per_1k_ios_dau']:.2f} crashes/1k iOS users")
        wd = r.get("worst_device_metric")
        if wd:
            bits.append(f"{wd['label'].lower()} {fmt_metric(wd['value'])} {wd['unit']}")
        if r.get("startup"):
            bits.append(f"{r['startup']['label']} {r['startup']['pct']:.0f}%")
        out.append(f"{icon.get(r['status'], '⚪')} *{r['name']}* — "
                   + (" · ".join(bits) or "nothing measured"))
    if brief:
        # a healthy project needs its numbers on record, not a line of its own
        compact = []
        for r in brief:
            seg = [r["name"]]
            if r.get("dau") is not None:
                seg.append(f"{fmt_int(r['dau'])} DAU")
            if r.get("err_per_user") is not None:
                seg.append(f"{r['err_per_user']:.1f} err/u")
            if r.get("crash_per_1k_sessions") is not None:
                seg.append(f"{r['crash_per_1k_sessions']:.2f}/1k")
            if r.get("rating") is not None:
                seg.append(f"{r['rating']:.2f}★")
            compact.append(" ".join(seg[:1]) + " (" + " · ".join(seg[1:]) + ")"
                           if len(seg) > 1 else seg[0])
        out.append(f"🟢 *Healthy ({len(brief)}):* " + " | ".join(compact))
    quiet = [r for r in rows if r["status"] == "nodata"]
    if quiet:
        out.append(f"⚪ *No data ({len(quiet)}):* " + ", ".join(r["name"] for r in quiet))
    missing = [r["name"] for r in rows if not r["in_store_report"]]
    if missing:
        out.append(f"_Not in the store report (no listing or not configured there): "
                   f"{', '.join(missing)}._")
    return out


def render_health_md(report):
    """The same health row set as a table, in the attached triage file."""
    health = report.get("health") or {}
    rows = health.get("rows") or []
    if not rows:
        return []
    def num(v, fmt="{:.2f}"):
        return "—" if v is None else fmt.format(v)
    source = (f"store snapshot **{health['store_day']}**"
              + (f" ({health['store_age_days']}d older than this report)"
                 if health.get("store_age_days") else "")
              if health.get("store_day")
              else f"**no store snapshot** — {health.get('store_unavailable')}")
    L = ["## Portfolio health — logs joined with the stores", "",
         f"- Log metrics: this report. Store metrics: {source}.",
         "- `DAU` counts every platform; Apple's crashes and sessions are **iOS-only**, so every "
         "ratio between them uses the project's iOS DAU and says so. Where the iOS DAU is unknown "
         "the ratio is left empty rather than mixed across platforms.", "",
         "| Project | Status | DAU | iOS % | err/user | Δ% | users w/ error | Rating | "
         "iOS crash /1k sess | Δ | sess / iOS user | crashes /1k iOS users | Worst device metric | "
         "Startup |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        wd = r.get("worst_device_metric")
        worst = "—" if not wd else f"{wd['label']} {fmt_metric(wd['value'])} {wd['unit']}"
        startup = "—" if not r.get("startup") else f"{r['startup']['label']} {r['startup']['pct']:.0f}%"
        L.append(f"| {r['name']} | {STATUS_LABEL[r['status']]} | {fmt_int(r['dau'])} "
                 f"| {num(r.get('ios_share_pct'), '{:.1f}')} "
                 f"| {num(r.get('err_per_user'), '{:.2f}')} "
                 f"| {num(r.get('err_per_user_delta_pct'), '{:+.0f}')} "
                 f"| {num(r.get('err_pct_users'), '{:.0f}')} "
                 f"| {num(r.get('rating'))} "
                 f"| {num(r.get('crash_per_1k_sessions'))} "
                 f"| {num(r.get('crash_per_1k_delta'), '{:+.2f}')} "
                 f"| {num(r.get('sessions_per_ios_dau'), '{:.2f}')} "
                 f"| {num(r.get('crashes_per_1k_ios_dau'))} | {worst} | {startup} |")
    L.append("")
    pending = sorted({r["analytics_pending"] for r in rows if r.get("analytics_pending")})
    for text in pending:
        L.append(f"- iOS crash/session columns: {text}.")
    missing = [r["name"] for r in rows if not r["in_store_report"]]
    if missing:
        L.append(f"- Not present in the store report (no listing, or not configured there): "
                 f"{', '.join(missing)}.")
    between = [(r["name"], r["between_versions"]) for r in rows if r.get("between_versions")]
    if between:
        L += ["", "**iOS crash rate between releases**", "",
              "| Project | New version | /1k | Previous | /1k | Δ |", "|---|---|---|---|---|---|"]
        for name, b in between:
            L.append(f"| {name} | {b['version']} | {b['rate']:.2f} | {b['prev_version']} "
                     f"| {b['prev_rate']:.2f} | {b['delta']:+.2f} |")
    L.append("")
    return L


ICON = {"healthy": "\U0001f7e2", "watch": "\U0001f7e1", "degraded": "\U0001f534", "nodata": "⚪"}

SLACK_ONE_MESSAGE_BUDGET = 3500


def slack_len(text):
    """Length in the unit the Slack poster splits on: UTF-16 code units."""
    return sum(2 if ord(ch) > 0xFFFF else 1 for ch in text)


def _fit(lines, limit=SLACK_ONE_MESSAGE_BUDGET, tail_note=None):
    """Drop lines from the end until the message fits, and say what was dropped."""
    out = list(lines)
    dropped = 0
    while slack_len("\n".join(out)) > limit and len(out) > 3:
        out.pop()
        dropped += 1
    if dropped and tail_note:
        out.append(tail_note.format(n=dropped))
    return "\n".join(out) + "\n"


def _status_reason_line(row, limit=2, width=110):
    """Why this app is not green, in its own words, from whichever side found it.

    Capped and truncated on purpose: this is a board to scan, and a finding's full text —
    including the suggested action — is in the technical or experience report below.
    """
    seen, texts = set(), []
    for reason in row.get("reasons", []):
        text = reason["text"].split(" → ")[0].strip()
        if text in seen:
            continue
        seen.add(text)
        texts.append(text if len(text) <= width else text[:width - 1].rstrip() + "…")
        if len(texts) >= limit:
            break
    extra = len(seen) - len(texts) + max(0, len(row.get("reasons", [])) - len(seen))
    line = " · ".join(texts)
    return line + (f" · _+{extra} more_" if extra > 0 else "")


def _short_number(value):
    if value is None:
        return "✕"
    value = float(value)
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.1f}m"
    if abs(value) >= 1_000:
        return f"{value / 1_000:.1f}k"
    return str(int(value)) if value.is_integer() else f"{value:.1f}"


def _delta_text(value):
    return "✕" if value is None else f"{value:+.0f}%"


def _trigger_value(text, status, threshold=None, comparator=">"):
    if status not in ("degraded", "watch"):
        return text
    suffix = f"{comparator}{threshold:g}" if threshold is not None else ""
    marked = f"{text}{suffix}"
    return f"*{marked}*" if status == "degraded" else f"_{marked}_"


def _overview_value(text, status="healthy"):
    """Highlight the value that owns a row status without exposing threshold syntax.

    The overview is a reading surface, not a query language.  Thresholds remain in the
    evidence attachment; Slack needs the value and a small severity marker at the exact
    metric that caused the project badge.
    """
    if status == "degraded":
        return f"*{text} 🔴*"
    if status == "watch":
        return f"*{text}*"
    if status == "improved":
        return f"*{text} 🟢*"
    return text


def _directional_delta(value, positive, negative, status="healthy",
                       improvement_direction=None, meaningful_pct=None):
    if value is None:
        text = "—"
    elif value > 0:
        text = f"{positive}{abs(value):.0f}%"
    elif value < 0:
        text = f"{negative}{abs(value):.0f}%"
    else:
        text = "0%"
    if status not in ("degraded", "watch") and meaningful_pct is not None:
        improved = ((improvement_direction == "positive" and value is not None
                     and value >= meaningful_pct)
                    or (improvement_direction == "negative" and value is not None
                        and value <= -meaningful_pct))
        if improved:
            status = "improved"
    return _overview_value(text, status)


def _volume_delta(value, status="healthy", meaningful_pct=None):
    """DAU direction; arrows describe volume and do not imply good or bad."""
    return _directional_delta(value, "▲", "▼", status,
                              improvement_direction="positive",
                              meaningful_pct=meaningful_pct)


def _error_delta(value, status="healthy", meaningful_pct=None):
    """Error direction; up is worse and down is better."""
    return _directional_delta(value, "↑", "↓", status,
                              improvement_direction="negative",
                              meaningful_pct=meaningful_pct)


def _overview_number(value):
    return "—" if value is None else _short_number(value)


def _flow_cell(metric):
    label = metric.get("label") or metric.get("key") or "flow"
    if not metric.get("available"):
        return f"{label} ✕"
    value = metric.get("value")
    if metric.get("kind") == "operation":
        retry = metric.get("retry_pct_dau")
        statuses = metric.get("component_status") or {}
        thresholds = metric.get("thresholds") or {}
        fail_text = "✕" if value is None else f"{value:.2f}%f"
        retry_text = "✕" if retry is None else f"{retry:.2f}%r"
        fail_status = statuses.get("failure")
        retry_status = statuses.get("retry")
        fail_bar = (thresholds.get("terminal_failure_alert_pct") if fail_status == "degraded"
                    else thresholds.get("terminal_failure_watch_pct") if fail_status == "watch"
                    else None)
        retry_bar = (thresholds.get("retry_reach_alert_pct_dau") if retry_status == "degraded"
                     else thresholds.get("retry_reach_watch_pct_dau") if retry_status == "watch"
                     else None)
        return (f"{label} {_trigger_value(fail_text, fail_status, fail_bar)}/"
                f"{_trigger_value(retry_text, retry_status, retry_bar)}")
    raw = "✕" if value is None else f"{value:.0f}%"
    target = metric.get("target") or {}
    status = metric.get("status")
    if target.get("good") == "low":
        threshold = target.get("bad_at") if status == "degraded" else target.get("good_at")
        comparator = ">"
    else:
        threshold = target.get("bad_at") if status == "degraded" else target.get("good_at")
        comparator = "<"
    return f"{label} {_trigger_value(raw, status, threshold, comparator)}"


def _platform_cell(label, data):
    statuses = data.get("metric_status") or {}
    thresholds = data.get("metric_thresholds") or {}
    version = data.get("version") or "✕"
    rollout = data.get("rollout_pct")
    rollout_text = f"v{version}@{rollout:.0f}%" if rollout is not None else f"v{version}@✕"
    rollout_status = statuses.get("rollout")
    rollout_bars = thresholds.get("rollout") or {}
    rollout_bar = (rollout_bars.get("alert") if rollout_status == "degraded"
                   else rollout_bars.get("watch") if rollout_status == "watch" else None)
    version_delta = _trigger_value(_delta_text(data.get("version_err_delta_pct")),
                                   rollout_status, rollout_bar)
    crash = data.get("crash_rate")
    crash_text = "✕" if crash is None else f"{crash:.2f}{'%' if data.get('crash_rate_unit') == '% users' else '/1k'}"
    crash_status = statuses.get("crash")
    crash_bars = thresholds.get("crash") or {}
    crash_bar = (crash_bars.get("alert") if crash_status == "degraded"
                 else crash_bars.get("watch") if crash_status == "watch" else None)
    crash_text = _trigger_value(crash_text, crash_status, crash_bar)
    anr = data.get("anr_rate")
    anr_text = "✕" if anr is None else f"{anr:.2f}%"
    anr_status = statuses.get("anr")
    anr_bars = thresholds.get("anr") or {}
    anr_bar = (anr_bars.get("alert") if anr_status == "degraded"
               else anr_bars.get("watch") if anr_status == "watch" else None)
    anr_text = _trigger_value(anr_text, anr_status, anr_bar)
    return (f"{label} {_short_number(data.get('dau'))}dau/{_short_number(data.get('sessions'))}sess "
            f"{rollout_text} Δv{version_delta} cr{crash_text} anr{anr_text}")


def _metric_availability_text(metric, label, compact=False, decimals=0):
    if metric.get("status") == "data_quality":
        return f"{label} telemetry mismatch" if not compact else f"{label} DQ"
    if not metric.get("available"):
        if metric.get("availability") == "not_applicable":
            return None
        return f"{label} —"
    value = metric.get("value")
    raw = "—" if value is None else f"{value:.{decimals}f}%"
    value_status = metric.get("absolute_status") or metric.get("status")
    return f"{label} {_overview_value(raw, value_status)} {_flow_delta_text(metric)}"


def _flow_delta_text(metric):
    """Compact time delta for conversion rates; the report legend owns the `pp` unit."""
    delta = metric.get("delta_pp")
    if delta is None:
        return "Δ—"
    if abs(delta) < 0.05:
        return "±0"
    arrow = "▲" if delta > 0 else ("▼" if delta < 0 else "–")
    magnitude = f"{abs(delta):.1f}".rstrip("0").rstrip(".")
    raw = f"{arrow}{magnitude}"
    return _overview_value(raw, metric.get("delta_status"))


def _platform_flows(data, compact=False):
    by_key = {m.get("key"): m for m in data.get("flows", [])}
    lines = []
    loading = by_key.get("loading")
    start_game_events = data.get("start_game_events")
    start_game_cell = ("StartGame —" if start_game_events is None else
                       f"StartGame {_overview_number(start_game_events)} events (100% ref)")
    if loading:
        cell = _metric_availability_text(
            loading, loading.get("display_label") or "Login reached", compact, decimals=1)
        loading_cells = [start_game_cell]
        if cell:
            loading_cells.append(cell)
            for key, fallback in (("home_ready", "Home ready"),
                                  ("popups_settled", "Popups settled")):
                metric = by_key.get(key)
                if metric:
                    extra = _metric_availability_text(
                        metric, metric.get("display_label") or fallback, compact, decimals=1)
                    if extra:
                        loading_cells.append(extra)
        lines.append("Loading: " + " · ".join(loading_cells))
    completed, granted = by_key.get("reward_complete"), by_key.get("reward_grant")
    end_metric = by_key.get("reward_end_to_end")
    if any(m and m.get("status") == "data_quality" for m in (completed, granted)):
        lines.append("RV DQ" if compact else "Rewarded telemetry incomplete")
    elif (completed and granted and completed.get("available") and granted.get("available")
          and completed.get("value") is not None and granted.get("value") is not None):
        completion = _overview_value(
            f"{completed['value']:.0f}%", completed.get("absolute_status") or completed.get("status"))
        grant = _overview_value(
            f"{granted['value']:.0f}%", granted.get("absolute_status") or granted.get("status"))
        started_raw = completed.get("denominator")
        granted_raw = granted.get("numerator")
        started = _overview_number(started_raw)
        finished = _overview_number(completed.get("numerator"))
        granted_count = _overview_number(granted_raw)
        end_to_end = (end_metric.get("value") if end_metric and end_metric.get("available") else
                      granted_raw / started_raw * 100.0
                      if started_raw not in (None, 0) and granted_raw is not None else None)
        end_text = "—" if end_to_end is None else f"{end_to_end:.0f}%"
        end_delta = _flow_delta_text(end_metric or {})
        lines.append(f"Rewarded: {started} started → {finished} completed "
                     f"({completion} {_flow_delta_text(completed)}) → {granted_count} rewarded "
                     f"({grant} {_flow_delta_text(granted)}) · End-to-end: {end_text} {end_delta}")
    elif completed or granted:
        availability = (completed or granted).get("availability")
        if availability != "not_applicable":
            lines.append("RV —" if compact else "Rewarded —")
    return "\n    " + "\n    ".join(lines) if lines else ""


def _stability_metric_text(metric, fallback_value=None, fallback_status="nodata",
                           compact=False):
    """A rate with release provenance; historical fallback is never presented as current."""
    if not metric:
        if fallback_value is None:
            return "—"
        return _overview_value(f"{fallback_value:.2f}% all versions", fallback_status)
    value = metric.get("value_pct")
    if value is None:
        return "—"
    value_text = _overview_value(f"{value:.2f}%", metric.get("absolute_status"))
    version = metric.get("version")
    scope = metric.get("scope")
    if version:
        version_label = (f"build {version}" if metric.get("version_kind") == "build"
                         else f"v{version}")
        value_text += f" @ {version_label}"
    elif scope == "all_versions":
        value_text += " all versions"
    focus = metric.get("focus_version")
    if (scope == "latest_measured" and focus and version
            and _clean_version(focus) != _clean_version(version)):
        value_text += f" (v{focus} pending)"
    baseline = metric.get("baseline_pct")
    if baseline is not None:
        previous_count = len(metric.get("baseline_versions") or [])
        baseline_label = ("previous avg" if compact or previous_count < 2 else
                          f"previous {previous_count}-version avg")
        delta = _error_delta(
            metric.get("delta_pct"), metric.get("delta_status"),
            meaningful_pct=None)
        value_text += f" vs {baseline:.2f}% {baseline_label} ({delta})"
    return value_text


def _readable_platform_line(label, data, compact=False):
    """Platform DAU, release comparison, health and platform-owned funnels."""
    statuses = data.get("metric_status") or {}
    thresholds = data.get("metric_thresholds") or {}
    version = data.get("version") or "—"
    flows = _platform_flows(data, compact=compact)
    rollout = data.get("rollout_pct")
    rollout_text = "—" if rollout is None else f"{rollout:.0f}%"
    previous_version = data.get("previous_version") or "—"
    current_err = data.get("version_err_per_user")
    previous_err = data.get("previous_version_err_per_user")
    delta_value = data.get("version_err_delta_pct") if data.get("version_sample_sufficient") else None
    version_watch = abs(((thresholds.get("rollout") or {}).get("watch") or 0)) or None
    version_delta = _error_delta(delta_value, statuses.get("rollout"), version_watch)
    if current_err is not None and previous_err is not None and data.get("version_sample_sufficient"):
        error_text = (version_delta if compact else
                      f"{previous_err:.2f}→{current_err:.2f} ({version_delta})")
    elif current_err is not None:
        error_text = "low sample" if compact else f"{current_err:.2f} (not enough data)"
    else:
        error_text = "—"
    crash_text = _stability_metric_text(
        data.get("crash_stability"), data.get("crash_rate_pct"), statuses.get("crash"),
        compact=compact)
    anr_text = _stability_metric_text(
        data.get("anr_stability"), data.get("anr_rate_pct"), statuses.get("anr"),
        compact=compact)
    dau = _overview_number(data.get("dau"))
    store_text = f"{data.get('store_name') or 'Store'}: {data.get('store_state') or '—'}"
    if data.get("store_version"):
        store_text += f" v{data['store_version']}"
    if data.get("store_phased"):
        store_text += f" · {data['store_phased']}"
    rating = data.get("store_rating")
    rating_text = "—" if rating is None else f"{rating:.2f}★"
    if rating is not None and data.get("store_rating_count") is not None:
        rating_text += f" ({_overview_number(data['store_rating_count'])})"
    store_text += f" · Rating {rating_text}"
    if compact:
        version_compare = (f"v{version} {rollout_text} ← {previous_version}"
                           if previous_version != "—" else f"v{version} {rollout_text}")
        line = (f"  *{label}* · DAU {dau} · {store_text} · "
                f"{version_compare} · "
                f"err {error_text}")
    else:
        line = (f"  *{label}* · DAU {dau} · {store_text} · "
                f"v{version} rollout {rollout_text} ← v{previous_version} · "
                f"version errors/user {error_text}")
    line += f"\n    Stability: Crash rate {crash_text} · ANR rate {anr_text}"
    if flows:
        line += flows
    excluded_newer = data.get("excluded_newer_versions") or []
    if excluded_newer:
        sample = excluded_newer[0]
        sample_text = f"v{sample.get('ver') or '—'} {_overview_number(sample.get('dau'))} DAU"
        if len(excluded_newer) > 1:
            sample_text += f" +{len(excluded_newer) - 1}"
        line += f" · newer sample {sample_text}"
    return line


def _readable_flow_cell(metric):
    labels = {
        "loading": "Loading",
        "reward_complete": "Rewarded completion",
        "reward_grant": "Reward granted",
        "withdrawal": "Withdrawal",
    }
    label = labels.get(metric.get("key"), metric.get("label") or metric.get("key") or "Flow")
    if not metric.get("available"):
        return f"{label} —"
    value = metric.get("value")
    if metric.get("kind") == "operation":
        if metric.get("key") == "withdrawal":
            statuses = metric.get("component_status") or {}
            start = _overview_number(metric.get("start_events"))
            success = _overview_number(metric.get("success_events"))
            failed = _overview_number(metric.get("failure_events"))
            fail_rate = "—" if value is None else f"{value:.2f}% fail"
            return (f"Withdrawal: {start} requested → {success} success / {failed} failed "
                    f"({_overview_value(fail_rate, statuses.get('failure'))})")
        retry = metric.get("retry_pct_dau")
        statuses = metric.get("component_status") or {}
        failure_text = "—" if value is None else f"{value:.2f}%"
        retry_text = "—" if retry is None else f"{retry:.2f}%"
        return (f"{label} fail {_overview_value(failure_text, statuses.get('failure'))}, "
                f"retry {_overview_value(retry_text, statuses.get('retry'))}")
    raw = "—" if value is None else f"{value:.0f}%"
    return f"{label} {_overview_value(raw, metric.get('status'))}"


def _readable_flows(metrics):
    by_key = {m.get("key"): m for m in metrics}
    cells = []
    loading = by_key.pop("loading", None)
    if loading:
        cells.append(_readable_flow_cell(loading))

    completed = by_key.pop("reward_complete", None)
    granted = by_key.pop("reward_grant", None)
    if completed and granted and completed.get("available") and granted.get("available"):
        shown = _overview_number(completed.get("denominator"))
        finished = _overview_number(completed.get("numerator"))
        granted_count = _overview_number(granted.get("numerator"))
        completion_rate = _overview_value(f"{completed['value']:.1f}%",
                                          completed.get("status"))
        grant_rate = _overview_value(f"{granted['value']:.1f}%", granted.get("status"))
        cells.append(f"Rewarded ads: {shown} shown → {finished} completed ({completion_rate}) "
                     f"→ {granted_count} granted ({grant_rate})")
    elif completed or granted:
        if (completed and completed.get("available")) or (granted and granted.get("available")):
            cells += [_readable_flow_cell(m) for m in (completed, granted) if m]
        else:
            cells.append("Rewarded flow —")

    withdrawal = by_key.pop("withdrawal", None)
    if withdrawal:
        cells.append(_readable_flow_cell(withdrawal))
    cells += [_readable_flow_cell(m) for m in by_key.values()]
    return " · ".join(cells) or "all —"


def _overview_row(row, compact=False):
    status = row.get("overview_status", "nodata")
    name = row["name"]
    platforms = row.get("platform_overview") or {}
    no_data = row.get("data_state") == "no_data"
    lead = f"🔴 *{name}*" if status == "degraded" else (
        f"◻ *{name}*" if no_data else f"• *{name}*")
    if no_data:
        store_cells = []
        for platform in ("iOS", "Android"):
            pdata = platforms.get(platform) or {}
            store_name = pdata.get("store_name") or (
                "App Store" if platform == "iOS" else "Google Play")
            state = pdata.get("store_state") or "—"
            cell = f"{store_name}: {state}"
            if pdata.get("store_version"):
                cell += f" v{pdata['store_version']}"
            store_cells.append(cell)
        return f"{lead} · No production data · " + " · ".join(store_cells)
    time_delta = row.get("time_delta") or {}
    time_status = row.get("time_metric_status") or {}
    time_thresholds = row.get("time_metric_thresholds") or {}
    dau_status = time_status.get("dau")
    dau_watch = abs(((time_thresholds.get("dau") or {}).get("watch") or 0)) or None
    dau_delta = _volume_delta(time_delta.get("dau_pct"), dau_status, dau_watch)
    err_status = time_status.get("errors")
    err_watch = abs(((time_thresholds.get("errors") or {}).get("watch") or 0)) or None
    err_delta = _error_delta(time_delta.get("err_per_user_pct"), err_status, err_watch)
    ios = _readable_platform_line(
        "iOS", platforms.get("iOS") or {}, compact=compact)
    android = _readable_platform_line(
        "Android", platforms.get("Android") or {}, compact=compact)
    absolute_status = time_status.get("absolute_errors")
    err_value = _overview_value(
        "—" if row.get("err_per_user") is None else f"{row['err_per_user']:.2f}",
        absolute_status)
    total_line = (f"  DAU {_overview_number(row.get('dau'))} {dau_delta} · "
                  f"err/user {err_value} {err_delta}" if compact else
                  f"  DAU {_overview_number(row.get('dau'))} ({dau_delta}) · "
                  f"errors/user {err_value} ({err_delta})")
    withdrawal = next((m for m in row.get("secondary_metrics", [])
                       if m.get("key") == "withdrawal" and m.get("available")), None)
    if withdrawal:
        if compact:
            requested = _overview_number(withdrawal.get("start_events"))
            failed = _overview_number(withdrawal.get("failure_events"))
            rate = "—" if withdrawal.get("value") is None else f"{withdrawal['value']:.2f}%"
            total_line += f" · Withdrawal {failed}/{requested} failed ({rate})"
        else:
            total_line += " · " + _readable_flow_cell(withdrawal)
    if compact:
        return "\n".join((f"{lead} · {total_line.strip()}", ios, android))
    return "\n".join((lead, total_line, ios, android))


def render_status_slack_parts(report):
    """Render one or more Slack-safe messages without splitting a project card."""
    health = report.get("health") or {}
    rows = health.get("rows") or []
    if not rows:
        return []
    if not health.get("overview_counts"):
        apply_overview_context(report, [])
        health = report.get("health") or {}
        rows = health.get("rows") or []
    counts = health.get("overview_counts") or {}
    critical, watch = counts.get("critical", 0), counts.get("watch", 0)
    stable, no_data = counts.get("stable", 0), counts.get("no_data", 0)
    portfolio_name = ((report.get("overview") or {}).get("portfolio_name")
                      or f"{report['brand']['org']} Portfolio")
    baseline = (f"avg {report.get('baseline_days')} prior {report.get('window_hours')}h"
                if report.get("kind") == "rolling" else
                f"avg {report.get('baseline_days') or 0} prior days")
    coverage = health.get("coverage") or {}
    head = [
        f"*{portfolio_name} · {report['report_day']}*",
        f"_🔴{critical} critical · {watch} watch · {stable} stable · "
        f"{no_data} no data · logs {coverage.get('logs', 0)}/{len(rows)}_",
        f"_Δ vs {baseline} · flow Δ pp · v←prior · err ↑worse/↓better_",
        "_🟢 better · 🔴 critical · DQ_",
    ]

    def pack_cards(cards, show_family=False):
        """Greedily fill the fewest ordered parts while keeping every card atomic."""
        def assemble_part(part_cards, part_number, part_total):
            lines = list(head) + ["", f"*Projects · part {part_number}/{part_total}*"]
            previous_family = object()
            for index, (family, card, _) in enumerate(part_cards):
                if index:
                    lines += ["", "────────────────────────", ""]
                if show_family and family != previous_family:
                    lines.append(f"*{family}*")
                lines.append(card)
                previous_family = family
            return "\n".join(lines) + "\n"

        packed = []
        current = []
        # Two-digit placeholder makes the final part labels no longer than the sizing pass.
        for card in cards:
            candidate = current + [card]
            if current and slack_len(assemble_part(candidate, 99, 99)) > SLACK_ONE_MESSAGE_BUDGET:
                packed.append(current)
                current = [card]
            else:
                current = candidate
            if slack_len(assemble_part(current, 99, 99)) > SLACK_ONE_MESSAGE_BUDGET:
                raise ValueError(
                    f"project card cannot fit one Slack message: {card[1].splitlines()[0]}")
        if current:
            packed.append(current)
        total = len(packed)

        # Greedy sizing finds the minimum part count, then a tiny ordered partition search
        # balances the number of projects per message. A grouped no-data card carries the
        # number of project names it represents, so 15 apps split approximately 7/8 instead
        # of leaving a nearly empty continuation message.
        ideal_weight = sum(card[2] for card in cards) / total
        cache = {}

        def balanced(start, parts_left):
            key = (start, parts_left)
            if key in cache:
                return cache[key]
            if parts_left == 1:
                tail = cards[start:]
                part_number = total
                if (not tail or slack_len(assemble_part(tail, part_number, total)) >
                        SLACK_ONE_MESSAGE_BUDGET):
                    cache[key] = None
                else:
                    weight = sum(card[2] for card in tail)
                    cache[key] = (abs(weight - ideal_weight), [tail])
                return cache[key]
            best = None
            part_number = total - parts_left + 1
            last_end = len(cards) - parts_left + 1
            for end in range(start + 1, last_end + 1):
                chunk = cards[start:end]
                if slack_len(assemble_part(chunk, part_number, total)) > SLACK_ONE_MESSAGE_BUDGET:
                    break
                remainder = balanced(end, parts_left - 1)
                if remainder is None:
                    continue
                weight = sum(card[2] for card in chunk)
                score = abs(weight - ideal_weight) + remainder[0]
                candidate = (score, [chunk] + remainder[1])
                if best is None or candidate[0] < best[0]:
                    best = candidate
            cache[key] = best
            return best

        partition = balanced(0, total)
        packed = partition[1] if partition is not None else packed
        return [assemble_part(cards_in_part, index, total)
                for index, cards_in_part in enumerate(packed, 1)]

    # Compatibility for old saved reports and the scale contract: those rows predate the
    # fixed overview schema. Keep every project visible without pretending absent cells were
    # collected; regenerated reports always take the structured path below.
    if not any("primary_flow" in row for row in rows):
        legacy = list(head) + [""]
        legacy_cards = []
        for index, row in enumerate(rows):
            marker = "🔴" if row.get("status") == "degraded" else "•"
            card = (f"{marker} *{row['name']}* — metrics unavailable · "
                    f"{_overview_number(row.get('dau'))} DAU")
            if index:
                legacy += ["", "────────────────────────", ""]
            legacy.append(card)
            legacy_cards.append((None, card, 1))
        legacy_text = "\n".join(legacy) + "\n"
        return ([legacy_text] if slack_len(legacy_text) <= SLACK_ONE_MESSAGE_BUDGET
                else pack_cards(legacy_cards))
    families = []
    for row in rows:
        if row.get("family") not in families:
            families.append(row.get("family"))
    changes = health.get("changes") or {}
    systemic = health.get("systemic_signals") or []

    def context_lines(compact=False, include_changes=True):
        lines = []
        if include_changes and changes.get("comparable"):
            change_parts = []
            for key, label in (("new_critical", "new critical"), ("escalated", "escalated"),
                               ("new_watch", "new watch"), ("recovered", "recovered")):
                if changes.get(key):
                    change_parts.append(f"{label}: {', '.join(changes[key])}")
            if compact:
                change_parts = change_parts[:2]
            if change_parts:
                lines += ["", "*Changed* — " + " · ".join(change_parts)]
        if systemic:
            if compact:
                pass  # Each compact project row already owns the same signals without repetition.
            else:
                lines += ["", "*Portfolio signals* — " + " · ".join(systemic)]
        return lines

    def assemble(compact=False, include_changes=True):
        lines = list(head) + context_lines(compact=compact, include_changes=include_changes)
        lines += ["", "*Projects*"]
        first_card = True
        for family in families:
            family_rows = sorted(
                (r for r in rows if r.get("family") == family),
                key=lambda r: (r.get("data_state") == "no_data",
                               -(r.get("dau") or 0),
                               r.get("name") or ""))
            for index, row in enumerate(family_rows):
                if not first_card:
                    lines += ["", "────────────────────────", ""]
                if index == 0 and (len(families) > 1 or family != portfolio_name):
                    lines.append(f"*{family} · {len(family_rows)} projects*")
                lines.append(_overview_row(row, compact=compact))
                first_card = False
        return "\n".join(lines) + "\n"

    text = assemble(compact=False)
    if slack_len(text) > SLACK_ONE_MESSAGE_BUDGET:
        text = assemble(compact=True)
    if slack_len(text) > SLACK_ONE_MESSAGE_BUDGET:
        text = assemble(compact=True, include_changes=False)
    if slack_len(text) <= SLACK_ONE_MESSAGE_BUDGET:
        return [text]

    cards = []
    for family in families:
        family_rows = sorted(
            (r for r in rows if r.get("family") == family),
            key=lambda r: (r.get("data_state") == "no_data",
                           -(r.get("dau") or 0),
                           r.get("name") or ""))
        cards.extend((family, _overview_row(row, compact=True), 1)
                     for row in family_rows)
    return pack_cards(cards, show_family=(len(families) > 1 or families[0] != portfolio_name))


def render_status_slack(report):
    """Compatibility helper for callers whose fixture is known to fit one Slack message."""
    parts = render_status_slack_parts(report)
    if len(parts) > 1:
        raise ValueError("portfolio overview has multiple Slack parts; use render_status_slack_parts")
    return parts[0] if parts else ""


class Block(list):
    """A message block that remembers how many items it stands for.

    The blocks are pre-capped when built (five signatures out of forty), so the length of the
    list is not the number of facts. Without the real total a trim note says "+5 more" for a
    section whose header already said 11 — an error the reader has no way to detect.
    """

    def __init__(self, lines=(), total=None):
        super().__init__(lines)
        self.total = len(self) - 2 if total is None else total


def render_technical_slack(report):
    """The client-log side of the technical report, budgeted to one Slack message.

    The old digest printed every funnel stage of every project and therefore split into
    several messages, which is most of why the channel read as noise. Here the message keeps
    what is off target and the numbers behind each project; the stage-by-stage funnels, every
    signature and the stacktraces live in the attached markdown, which is where a reader who
    has decided to dig actually goes.
    """
    b = report["brand"]
    errs = report.get("errors", [])
    total = len(report["projects"]) + len(errs)
    proj_count = (f"{len(report['projects'])}/{total} projects ({len(errs)} failed)"
                  if errs else f"{len(report['projects'])} projects")
    base_desc = (f"vs {report['baseline_source']}" if report.get("kind") == "rolling"
                 else f"day vs {report['baseline_days']}-day baseline ({report['baseline_source']})")
    st = report["overall_status"]
    head = [f"*{b['org']} — technical report, {day_label(report)}*  "
            f"{ICON[st]} *{STATUS_LABEL[st]}*",
            f"_covers {report['window_utc']} · {proj_count} · {base_desc}_",
            "_Client logs and funnels, plus crashes and device metrics from the stores. "
            "Ratings, reviews and releases are in the store & experience report._"]
    if errs:
        head.append(f"⚠️ *{len(errs)} projects not reported (query failed):* "
                    + ", ".join(f"{e['name']} ({e['error'][:40]})" for e in errs))

    metrics = render_health_slack(report)

    att = build_attention(report)
    att_block = [""]
    if att:
        att_block.append(f"*⚠️ Off target ({len(att)}):*")
        for a in att:
            ic = ICON["degraded"] if a["sev"] == "degraded" else ICON["watch"]
            att_block.append(f"{ic} *{a['proj']}* — {a['text']}")
    else:
        att_block.append("*✅ Nothing off target: errors, funnels and operations all inside "
                         "their baselines.*")

    appeared = [(p["name"], t) for p in report["projects"] for t in p.get("appeared_errors", [])]
    resolved = [(p["name"], t) for p in report["projects"] for t in p.get("disappeared_errors", [])]
    new_block, gone_block = [], []
    if appeared:
        new_block += ["", f"*🆕 New error signatures ({len(appeared)}):*"]
        for name, t in appeared[:5]:
            new_block.append(f"• {name}: {t['msg'][:70]} — {fmt_int(t['total'])} "
                             f"({t['pct']:.1f}% DAU)")
    if resolved:
        gone_block += ["", f"*✅ No longer detected ({len(resolved)}):*"]
        for name, t in resolved[:4]:
            gone_block.append(f"• {name}: {t['msg'][:70]} — was {fmt_int(t['total'])}")
    # the true totals, so a trim note counts what the reader is missing rather than what
    # happened to be in the block when the trimming started
    if len(appeared) > 5:
        new_block.append(f"  _+{len(appeared) - 5} more in the attached report._")
    if len(resolved) > 4:
        gone_block.append(f"  _+{len(resolved) - 4} more in the attached report._")
    new_block = Block(new_block, total=len(appeared))
    gone_block = Block(gone_block, total=len(resolved))

    foot = ["", "_Stage-by-stage funnels, every signature and representative stacktraces: the "
                "attached markdown report._"]
    return head, metrics, att_block, new_block, gone_block, foot


def compose_technical_message(report, store_section=None,
                              limit=SLACK_ONE_MESSAGE_BUDGET):
    """Assemble the technical message from the log side and the store side.

    Trimming order is the reverse of decision value: signatures first, then the metric rows
    of healthy projects, then the off-target list — never the header or the pointer to the
    attachment.
    """
    head, metrics, att, new_sig, gone_sig, foot = render_technical_slack(report)
    store_section = list(store_section or [])
    blocks = [head, metrics, att, new_sig, gone_sig, store_section, foot]
    original = [len(blk) for blk in blocks]

    def text():
        return "\n".join(l for blk in blocks for l in blk)

    def cap(index, keep, noun):
        blk = blocks[index]
        # a build-time shortfall note is not an item; drop it before counting
        items = [l for l in blk[2:] if not l.startswith("  _")]
        blk = Block(blk[:2] + items, total=getattr(blk, "total", None))
        blocks[index] = blk
        if len(blk) <= keep + 2:
            return
        total = getattr(blk, "total", original[index] - 2)
        dropped = max(0, total - keep)
        note = (f"  _all {total} {noun} are in the attached report._" if keep == 0
                else f"  _+{dropped} {noun} in the attached report._")
        blocks[index] = Block(blk[:2 + keep] + ([note] if dropped else []), total=total)

    # Trim value-last: signatures, then the softer store lines, then findings. The metric rows
    # and the store crash/device lines are the technical report's reason to exist.
    for index, keep, noun in ((4, 2, "resolved signatures"), (3, 3, "new signatures"),
                              (4, 0, "resolved signatures"), (5, 14, "store lines"),
                              (2, 8, "findings"), (1, 8, "projects"),
                              (3, 0, "new signatures"), (5, 10, "store lines"),
                              (2, 5, "findings"), (1, 5, "projects")):
        if slack_len(text()) <= limit:
            break
        cap(index, keep, noun)
    # A ladder can run out of steps, and going over the limit is not a cosmetic failure: the
    # poster splits the message and the three-message structure silently becomes four. So the
    # last word belongs to a backstop that cannot fail to fit.
    if slack_len(text()) > limit:
        trimmed = 0
        for index in (5, 1, 2, 3, 4):
            while slack_len(text()) > limit and len(blocks[index]) > 2:
                blocks[index].pop()
                trimmed += 1
            if slack_len(text()) <= limit:
                break
        if trimmed:
            blocks[-1] = ([f"  _+{trimmed} more lines than fit one message — all of it is in "
                           f"the attached report._"] + blocks[-1])
        while slack_len(text()) > limit and len(blocks[1]) > 2:
            blocks[1].pop()
    return text() + "\n"


def render_slack(report):
    icon = {"healthy": "\U0001f7e2", "watch": "\U0001f7e1", "degraded": "\U0001f534", "nodata": "⚪"}
    b = report["brand"]
    lc = " (last complete UTC day)" if report.get("is_last_complete") else ""
    errs = report.get("errors", [])
    total = len(report["projects"]) + len(errs)
    proj_count = f"{len(report['projects'])}/{total} projects ({len(errs)} failed)" if errs else f"{len(report['projects'])} projects"
    base_desc = f"vs {report['baseline_source']}" if report.get("kind") == "rolling" else f"day vs {report['baseline_days']}-day baseline ({report['baseline_source']})"
    lines = [f"*{b['org']} — technical report, {day_label(report)}*{lc}  "
             f"{icon[report['overall_status']]} *{STATUS_LABEL[report['overall_status']]}*",
             f"_covers {report['window_utc']}_",
             f"_{proj_count} · {base_desc} · generated {report['generated_utc']}_",
             "_Client logs, funnels and signatures, plus crashes and device metrics from the "
             "stores. Ratings, reviews and releases are in the store & experience report._"]
    if errs:
        lines.append("")
        lines.append(f"⚠️ *{len(errs)} projects not reported (query failed):* "
                     + ", ".join(f"{e['name']} ({e['error'][:40]})" for e in errs))
    lines += render_health_slack(report)
    # everything needing attention, portfolio-wide, before anything else
    att = build_attention(report)
    lines.append("")
    if att:
        lines.append(f"*⚠️ Needs attention ({len(att)}):*")
        for a in att[:12]:
            ic = icon["degraded"] if a["sev"] == "degraded" else icon["watch"]
            lines.append(f"{ic} *{a['proj']}* — {a['text']}")
        if len(att) > 12:
            lines.append(f"  +{len(att) - 12} more")
    else:
        lines.append("✅ *Nothing needs attention — all projects healthy vs baseline.*")
    # status transitions
    trans = [f"{p['name']} {STATUS_LABEL[p['prior_status']]}→{STATUS_LABEL[p['status']]}"
             for p in report["projects"] if p.get("prior_status") and p["prior_status"] != p["status"]]
    rel = [f"{p['name']} {'/'.join(p['new_releases'])} (new build)" for p in report["projects"] if p["new_releases"]]
    if trans or rel:
        lines.append("")
        lines.append("*Changes:* " + "; ".join(trans + rel))
    lines.append("")
    lines.append("*All projects (by DAU):*")
    for p in report["projects"]:
        ed = "" if p["err_per_user_delta_pct"] is None else f" ({p['err_per_user_delta_pct']:+.0f}%)"
        wd = "" if p["warn_per_user_delta_pct"] is None else f" ({p['warn_per_user_delta_pct']:+.0f}%)"
        relm = " (new build)" if p["new_releases"] else ""
        lines.append(f"{icon[p['status']]} *{p['name']}*{relm} — {fmt_int(p['dau'])} DAU "
                     f"(fresh {p.get('fresh_pct', 0):.0f}%) · "
                     f"{fmt_int(p['err_total'])} err ({p['err_per_user']:.1f}/user{ed}, worst {p['top_error_reach']:.1f}% DAU) · "
                     f"{fmt_int(p['warn_total'])} warn ({p['warn_per_user']:.1f}/user{wd}, worst {p['top_warn_reach']:.1f}% DAU)")
        for fn in p.get("funnels", []):
            rates = [r for r in fn["rates"] if r["pct"] is not None]
            if rates:
                rl = ", ".join(f"{r['label']} {r['pct']:.0f}%" for r in rates[:3])
                lines.append(f"    ↳ _{fn['label']}_ — {rl}")
            for sp in fn.get("splits", []):
                if not sp["dau"]:
                    continue
                srl = ", ".join(f"{r['label']} {r['pct']:.0f}%" for r in sp["rates"] if r["pct"] is not None)
                lines.append(f"        · {sp['cohort']} ({fmt_int(sp['dau'])}u): {srl}")
            for bd in fn.get("breakdowns", []):
                for rz in bd["reasons"][:5]:
                    lines.append(f"        · {rz['reason'][:100]} — {fmt_int(rz['users'])}u ({rz['pct']:.1f}%)")
        for profile in p.get("operations", []):
            for flow in profile.get("flows", []):
                fr = flow.get("terminal_failure_rate_pct")
                terminal = "n/a" if fr is None else f"{fr:.3f}% terminal fail{operation_delta(flow, 'terminal_failure_delta_pct')}"
                retry = flow.get("retry") or {}
                retry_text = (f" · retry {flow.get('retry_reach_pct_dau', 0):.3f}% DAU{operation_delta(flow, 'retry_reach_delta_pct')} "
                              f"({flow.get('retry_events_per_user', 0):.2f}/u)") if retry.get("events") else ""
                if flow.get("users_affected") is not None:
                    retry_text += (f" · {fmt_int(flow['users_affected'])}u ({flow.get('problem_pct_dau', 0):.3f}% DAU) "
                                  f"· {fmt_int(flow.get('sessions_with_problem', 0))}/{fmt_int(flow.get('total_sessions', 0))} sessions")
                lines.append(f"    ↳ _{profile['label']} / {flow['label']}_ — {terminal}{retry_text} [{flow.get('status', 'healthy').upper()}]")
        lines.append("")   # blank line between projects
    # Both sides of the diff, equal weight: what appeared vs what is no longer detected.
    appeared_all = [(p["name"], t) for p in report["projects"] for t in p.get("appeared_errors", [])]
    resolved_all = [(p["name"], t) for p in report["projects"] for t in p.get("disappeared_errors", [])]
    if appeared_all:
        lines.append("")
        lines.append(f"*🆕 New errors {scope_word(report)}:*")
        for name, t in appeared_all[:8]:
            lines.append(f"• {name}: {t['msg'][:70]} — {fmt_int(t['total'])} ({t['pct']:.1f}% DAU)")
        if len(appeared_all) > 8:
            lines.append(f"  +{len(appeared_all) - 8} more")
    if resolved_all:
        lines.append("")
        lines.append("*✅ Resolved / no longer detected (vs baseline) — potentially fixed:*")
        for name, t in resolved_all[:8]:
            lines.append(f"• {name}: {t['msg'][:70]} — was {fmt_int(t['total'])} ({t.get('pct', 0):.1f}% DAU)")
        if len(resolved_all) > 8:
            lines.append(f"  +{len(resolved_all) - 8} more")

    appeared_warn_all = [(p["name"], t) for p in report["projects"] for t in p.get("appeared_warnings", [])]
    resolved_warn_all = [(p["name"], t) for p in report["projects"] for t in p.get("disappeared_warnings", [])]
    if appeared_warn_all:
        lines.append("")
        lines.append(f"*🆕 New warning signatures {scope_word(report)}:*")
        for name, t in appeared_warn_all[:8]:
            lines.append(f"• {name}: {t['msg'][:70]} — {fmt_int(t['total'])} ({t['pct']:.1f}% DAU)")
        if len(appeared_warn_all) > 8:
            lines.append(f"  +{len(appeared_warn_all) - 8} more")
    if resolved_warn_all:
        lines.append("")
        lines.append("*✅ Warning signatures gone since baseline:*")
        for name, t in resolved_warn_all[:8]:
            lines.append(f"• {name}: {t['msg'][:70]} — was {fmt_int(t['total'])} ({t.get('pct', 0):.1f}% DAU)")
        if len(resolved_warn_all) > 8:
            lines.append(f"  +{len(resolved_warn_all) - 8} more")

    lines.append("")
    lines.append("Full dashboard + structured .md attached. Reply to turn any signal into a backlog task.")
    return "\n".join(lines)


def render_status_md(report):
    """Work-ready companion to the single Slack grid, with no duplicated project lists."""
    b = report["brand"]
    L = [f"# {b['org']} — portfolio overview {report['report_day']}", "",
         f"- Generated: {report['generated_utc']}",
         f"- `Trend`: report day versus the average of {report.get('baseline_days') or 0} prior complete days.",
         "- `Errors vs prior version`: released/live cohort versus the previous production cohort on the same platform; store release order is used when available.",
         "- `StartGame`: emitted canonical StartGame activity events in the window. It is not DAU or server sessions; distinct-user reach is reported separately.",
         "- `Loading`: unique-user reach from the technical boot marker. `Login reached` is available portfolio-wide; Blingz additionally reports `Home ready` (`APP_READY`) and `Popups settled` (`APP_POPUPS_SETTLED`). These are reach proxies, not correlated launch conversions or TTI.",
         "- `—`: the cell is part of the contract, but data or instrumentation is absent. It is never hidden.",
         "- Red overview status is possible only when a metric printed in the overview crosses its alert "
         "threshold. Ratings, reviews and release workflow are context in the experience report.", "",
         "## Evidence package", "",
         "- `*.overview.md` — this metric surface and exact trigger ownership.",
         "- `*.md` — client logs, stage-by-stage funnels, signatures and representative stacktraces.",
         "- `store_pulse_*.technical.md` — crashes, ANRs, sessions, device metrics and version comparisons.",
         "- `store_pulse_*.experience.md` — ratings, reviews, listings and release workflow.", ""]
    rows = (report.get("health") or {}).get("rows") or []
    families = []
    for row in rows:
        if row.get("family") not in families:
            families.append(row.get("family"))
    for family in families:
        family_rows = sorted(
            (r for r in rows if r.get("family") == family),
            key=lambda r: (r.get("data_state") == "no_data",
                           -(r.get("dau") or 0),
                           r.get("name") or ""))
        L += [f"## {family}", ""]
        for r in family_rows:
            status = STATUS_LABEL.get(r.get("overview_status"), "Low data")
            L += [f"### {r['name']} — {status}", ""]
            triggers = r.get("overview_triggers") or []
            L.append("- Overview triggers: " + ("; ".join(
                f"{t['scope']} / {t['metric']} ({t['status']})" for t in triggers) or "none"))
            td = r.get("time_delta") or {}
            L.append(f"- Time delta: DAU {_delta_text(td.get('dau_pct'))}; "
                     f"errors/user {_delta_text(td.get('err_per_user_pct'))}.")
            L += ["", "| Platform | Store state | Store version | Rating | DAU | StartGame events | StartGame users | Sessions | "
                        "Observed version | Rollout | Previous | Δv errors/user | "
                        "Crash rate | ANR rate | Cohort source |",
                  "|---|---|---|---:|---:|---:|---:|---:|---|---:|---|---:|---:|---:|---|"]
            for platform in ("iOS", "Android"):
                p = (r.get("platform_overview") or {}).get(platform) or {}
                crash_text = _stability_metric_text(
                    p.get("crash_stability"), p.get("crash_rate_pct"),
                    (p.get("metric_status") or {}).get("crash"), compact=False)
                anr_text = _stability_metric_text(
                    p.get("anr_stability"), p.get("anr_rate_pct"),
                    (p.get("metric_status") or {}).get("anr"), compact=False)
                rollout_text = ("✕" if p.get("rollout_pct") is None
                                else f"{p['rollout_pct']:.1f}%")
                store_state = p.get("store_state") or "—"
                if p.get("store_phased"):
                    store_state += f" ({p['store_phased']})"
                rating = p.get("store_rating")
                rating_text = "—" if rating is None else f"{rating:.2f}★"
                if rating is not None and p.get("store_rating_count") is not None:
                    rating_text += f" ({fmt_int(p['store_rating_count'])})"
                L.append(f"| {platform} | {store_state} | {p.get('store_version') or '—'} "
                         f"| {rating_text} "
                         f"| {fmt_int(p.get('dau'))} "
                         f"| {fmt_int(p.get('start_game_events'))} "
                         f"| {fmt_int(p.get('start_game_users'))} "
                         f"| {fmt_int(p.get('sessions'))} "
                         f"| {p.get('version') or '✕'} | "
                         f"{rollout_text} "
                         f"| {p.get('previous_version') or '✕'} "
                         f"| {_delta_text(p.get('version_err_delta_pct'))} | {crash_text} "
                         f"| {anr_text} | {p.get('cohort_selection') or '✕'} |")
            for platform in ("iOS", "Android"):
                p = (r.get("platform_overview") or {}).get(platform) or {}
                by_key = {m.get("key"): m for m in p.get("flows", [])}
                loading = by_key.get("loading")
                if loading and loading.get("available"):
                    L.append(f"- {platform} Loading denominator: **{fmt_int(loading.get('denominator'))} boot users**.")
                else:
                    L.append(f"- {platform} Loading denominator: **—**.")
                for key, label, event_name in (
                        ("loading", "Login reached", "api/core/Login SUCCEEDED"),
                        ("home_ready", "Home ready", "APP_READY"),
                        ("popups_settled", "Popups settled", "APP_POPUPS_SETTLED")):
                    metric = by_key.get(key)
                    if metric and metric.get("available"):
                        delta = metric.get("delta_pp")
                        baseline = metric.get("baseline_value")
                        comparison = (" · baseline unavailable" if delta is None else
                                      f" · Δ {delta:+.1f} pp vs {baseline:.1f}% baseline")
                        L.append(f"  - {label}: **{fmt_int(metric.get('numerator'))} users** "
                                 f"({metric.get('value'):.1f}%)"
                                 f"{comparison} · source `{event_name}`.")
                    elif key == "loading" or (metric and metric.get("availability") != "not_applicable"):
                        L.append(f"  - {label}: **—** · source `{event_name}`.")
                completed = by_key.get("reward_complete")
                granted = by_key.get("reward_grant")
                end_to_end = by_key.get("reward_end_to_end")
                if (completed and granted and completed.get("available") and
                        granted.get("available")):
                    def rate_detail(metric):
                        value = metric.get("value")
                        delta = metric.get("delta_pp")
                        baseline = metric.get("baseline_value")
                        value_text = "—" if value is None else f"{value:.1f}%"
                        if delta is None:
                            return f"{value_text}; baseline unavailable"
                        return f"{value_text}; Δ {delta:+.1f} pp vs {baseline:.1f}% baseline"

                    L.append(
                        f"- {platform} Rewarded: **{fmt_int(completed.get('denominator'))} started** "
                        f"→ **{fmt_int(completed.get('numerator'))} completed** "
                        f"({rate_detail(completed)}) → **{fmt_int(granted.get('numerator'))} rewarded** "
                        f"({rate_detail(granted)}) · End-to-end: "
                        f"{rate_detail(end_to_end or {})}.")
                elif any(m and m.get("availability") != "not_applicable"
                         for m in (completed, granted, end_to_end)):
                    L.append(f"- {platform} Rewarded: **—**.")
            metrics = [_flow_cell(m).replace("*", "").replace("_", "")
                       for m in r.get("secondary_metrics", [])]
            L += ["", "- Secondary flow cells: " + ("; ".join(metrics) or "none configured") + "."]
            missing = []
            missing += [m.get("label") for m in r.get("secondary_metrics", [])
                        if not m.get("available")]
            for platform, pdata in (r.get("platform_overview") or {}).items():
                for field, label in (("sessions", "sessions"), ("crash_rate", "crash"),
                                     ("anr_rate", "ANR"), ("version", "rollout")):
                    if pdata.get(field) is None:
                        missing.append(f"{platform} {label}")
            L.append("- Coverage gaps: " + (", ".join(x for x in missing if x) or "none") + ".")
            if r.get("reasons"):
                L += ["", "Additional evidence (full detail in the technical/experience reports):"]
                for reason in r["reasons"]:
                    L.append(f"- `{reason['side']}` {reason['text']}")
            L.append("")
    return "\n".join(L) + "\n"


def render_md(report, samples):
    b = report["brand"]
    lc = " (last complete UTC day)" if report.get("is_last_complete") else ""
    errs = report.get("errors", [])
    total = len(report["projects"]) + len(errs)
    proj_line = (f"{len(report['projects'])}/{total} projects ({len(errs)} failed to report)"
                 if errs else f"{len(report['projects'])} projects")
    rolling = report.get("kind") == "rolling"
    base_line = (f"- Baseline: **{report['baseline_source']}** (same clock window on the prior {report['baseline_days']} days)"
                 if rolling else
                 f"- Baseline: {report['baseline_days']} days before, from **{report['baseline_source']}** ({', '.join(report['baseline_dates']) or 'n/a'})")
    metric_line = ("- All metrics are for the rolling window; `diff%` = this window vs the same clock window on prior days; `%DAU` = unique affected users ÷ window users."
                   if rolling else
                   "- All metrics are for the report day; `diff%` = report day vs baseline daily average; `%DAU` = unique affected users ÷ that day's DAU.")
    L = [f"# {b['org']} {b['product']} — {day_label(report)}{lc}", "",
         f"- Window: **{report['window_utc']}**",
         f"- Overall: **{STATUS_LABEL[report['overall_status']]}**  ·  {proj_line}",
         base_line,
         f"- Generated: {report['generated_utc']}  ·  source: {report['source']}",
         metric_line,
         "", "> Structured for AI/engineer triage: each project lists its top signatures with affected-user % and, for projects needing attention, representative stacktraces with version/platform.", ""]
    if errs:
        L.append(f"> ⚠️ **{len(errs)} projects are missing from this report** — their queries failed and no data was collected: "
                 + "; ".join(f"{e['name']} (`{e['error']}`)" for e in errs) + ". Portfolio totals and Overall status below EXCLUDE these projects.")
        L.append("")
    att = build_attention(report)
    if att:
        L.append("## ⚠ Needs attention — portfolio-wide")
        for a in att:
            L.append(f"- **{a['proj']}** ({a['sev']}): {a['text']}")
        L.append("")
    for p in report["projects"]:
        L.append(f"## {p['name']} — {STATUS_LABEL[p['status']]}")
        d = p["err_per_user_delta_pct"]
        wd = p["warn_per_user_delta_pct"]
        L.append(f"- DAU {fmt_int(p['dau'])} (baseline ~{fmt_int(p['base_dau'])}/day) · errors {fmt_int(p['err_total'])} "
                 f"({p['err_per_user']:.1f}/user{'' if d is None else f', {d:+.0f}% vs baseline'}, worst {p['top_error_reach']:.1f}% DAU) · "
                 f"warnings {fmt_int(p['warn_total'])} ({p['warn_per_user']:.1f}/user{'' if wd is None else f', {wd:+.0f}% vs baseline'}, worst {p['top_warn_reach']:.1f}% DAU)")
        nonfresh = p.get("nonfresh_users") or (p["dau"] - p.get("fresh_users", 0))
        L.append(f"- Fresh launches: **{p.get('fresh_pct', 0):.1f}% of DAU** ({fmt_int(p.get('fresh_users', 0))}u cold/fresh vs {fmt_int(nonfresh)}u returning/warm; a user with both session kinds counts in both cohorts)")
        if p["new_releases"]:
            L.append(f"- New release: {', '.join(p['new_releases'])}")
        vd = p.get("versions_detail", [])
        if vd:
            L.append("- Releases (version · platform · rollout % of DAU · err/user): "
                     + "; ".join(f"{v['ver']}({v['plat']}) {v['rollout_pct']:.0f}% · {v['err_per_user']:.1f}" for v in vd[:5]))
        if p["signals"]:
            sg = []
            for k, v in p["signals"].items():
                total, users = _sig_tu(v)
                sg.append(f"{report['signals_meta'].get(k, k)}={fmt_int(total)}" + (f"/{fmt_int(users)}u" if users else ""))
            L.append("- Signals: " + ", ".join(sg))
        for profile in p.get("operations", []):
            L.append("")
            L.append(f"### {profile['label']} — daily endpoint health")
            for flow in profile.get("flows", []):
                fr = flow.get("terminal_failure_rate_pct")
                terminal = "n/a" if fr is None else f"{fr:.3f}%{operation_delta(flow, 'terminal_failure_delta_pct')}"
                retry = flow.get("retry") or {}
                terminal_total = flow["success"]["events"] + flow["failure"]["events"]
                if flow.get("users_affected") is not None:
                    reach_clause = (f"reach **{fmt_int(flow['users_affected'])}u ({flow.get('problem_pct_dau', 0):.3f}% DAU)**; "
                                    f"sessions **{fmt_int(flow.get('sessions_with_problem', 0))}/{fmt_int(flow.get('total_sessions', 0))}**; ")
                else:
                    reach_clause = (f"retry reach **{flow.get('retry_reach_pct_dau', 0):.3f}% DAU{operation_delta(flow, 'retry_reach_delta_pct')}** "
                                    f"({fmt_int(retry.get('events', 0))} events; {flow.get('retry_events_per_user', 0):.2f}/affected user); ")
                L.append(f"- **{flow['label']}** — terminal failure **{terminal}** "
                         f"({fmt_int(flow['failure']['events'])} failed / {fmt_int(terminal_total)} terminal); "
                         f"{reach_clause}"
                         f"status **{flow.get('status', 'healthy').upper()}**.")
                class_text = []
                for bucket, prefix in (("failure", "final"), ("retry", "retry")):
                    class_text += [f"{prefix} {OP_CLASS_LABELS.get(kind, kind)} {fmt_int(count)}"
                                   for kind, count in (flow.get("classes", {}).get(bucket, {}) or {}).items()]
                if class_text:
                    L.append("  - Failure classes: " + "; ".join(class_text))
                if flow.get("reasons"):
                    L.append("  - Failure reasons: " + "; ".join(f"{k} {fmt_int(v)}" for k, v in flow["reasons"].items()))
                if flow.get("drilldown"):
                    dr = flow["drilldown"]
                    if dr.get("hours"):
                        L.append("  - Top non-success hours: " + ", ".join(f"{x['hour']} ({fmt_int(x['events'])})" for x in dr["hours"]))
                    if dr.get("versions"):
                        L.append("  - Version split: " + ", ".join(f"{x['value']} {fmt_int(x['events'])}ev/{fmt_int(x['users'])}u" for x in dr["versions"]))
                    if dr.get("platforms"):
                        L.append("  - Platform split: " + ", ".join(f"{x['value']} {fmt_int(x['events'])}ev/{fmt_int(x['users'])}u" for x in dr["platforms"]))
        L.append("")
        L.append("| Top error | total | users | %DAU | vs base |")
        L.append("|---|--:|--:|--:|--:|")
        for t in p["top_errors"][:8]:
            m = t["msg"][:90].replace("|", "\\|")
            vb = "new" if t.get("base_pct") is None else (f"{t['pct_delta']:+d}%" if t.get("pct_delta") is not None else "—")
            L.append(f"| {m} | {fmt_int(t['total'])} | {fmt_int(t['users'])} | {t['pct']:.1f}% | {vb} |")
        L.append("")
        L.append("| Top warning | total | users | %DAU | vs base |")
        L.append("|---|--:|--:|--:|--:|")
        for t in p["top_warns"][:8]:
            m = t["msg"][:90].replace("|", "\\|")
            vb = "new" if t.get("base_pct") is None else (f"{t['pct_delta']:+d}%" if t.get("pct_delta") is not None else "—")
            L.append(f"| {m} | {fmt_int(t['total'])} | {fmt_int(t['users'])} | {t['pct']:.1f}% | {vb} |")
        # business-impact bar (item 4): who · how much · UX · business · action
        if p.get("impact"):
            L.append("")
            L.append("**Business impact — top actionable issues:**")
            for i in p["impact"]:
                tag = (i.get("verdict") or "review").upper()
                plats = "/".join(i.get("plats") or []) or "—"
                L.append(f"- **[{tag}] {i['issue'][:90]}** — {fmt_int(i['users'])} users · {i['pct']:.1f}% DAU · "
                         f"{fmt_int(i['events'])} events · {i.get('per_user', 0)}/user · {plats} · {i.get('ver') or '—'}")
                if i.get("ux"):
                    L.append(f"  - UX: {i['ux']}")
                if i.get("business"):
                    L.append(f"  - Business: {i['business']}")
                act = i.get("action") or ""
                if i.get("owner"):
                    act = (act + " · " if act else "") + f"owner: {i['owner']}"
                if act:
                    L.append(f"  - Action: {act}")
        # business funnels (item 3)
        if p.get("funnels"):
            L.append("")
            for fn in p["funnels"]:
                stages = " → ".join(f"{s['label']} {fmt_int(s['users'])}u ({s['pct']:.1f}%)" for s in fn["stages"])
                L.append(f"**Funnel — {fn['label']}:** {stages}")
                for r in fn.get("rates", []):
                    val = "n/a" if r["pct"] is None else f"{r['pct']:.0f}%"
                    bm = f" — {r['business']}" if r.get("business") else ""
                    L.append(f"  - {r['label']}: **{val}**{bm}")
                for sp in fn.get("splits", []):
                    if not sp["dau"]:
                        continue
                    st = " → ".join(f"{s['label']} {fmt_int(s['users'])}u ({s['pct']:.1f}%)" for s in sp["stages"])
                    rl = ", ".join(f"{r['label']} {r['pct']:.0f}%" for r in sp["rates"] if r["pct"] is not None)
                    L.append(f"  - _{sp['cohort']}_ ({fmt_int(sp['dau'])}u): {st}  →  {rl}")
                for bd in fn.get("breakdowns", []):
                    if not bd["reasons"]:
                        continue
                    L.append(f"  - _Top {bd['label']} reasons:_")
                    for rz in bd["reasons"]:
                        L.append(f"    - {rz['reason'][:100]} — {fmt_int(rz['users'])}u ({rz['pct']:.1f}% DAU), {fmt_int(rz['total'])} ev")
        # log hygiene (item 2)
        hy = p.get("hygiene") or {}
        hy_line = [f"{v}: {b['count']} sig / {fmt_int(b['events'])} ev"
                   for v in ("fix", "ux-assess", "mute", "review") for b in [hy.get(v)] if b]
        if hy_line:
            L.append("")
            L.append("**Log hygiene:** " + " · ".join(hy_line))
        if p["appeared_errors"]:
            L.append("")
            L.append(f"**New errors {scope_word(report)}:** " + "; ".join(f"{t['msg'][:70]} ({t['pct']:.1f}%DAU)" for t in p["appeared_errors"]))
        if p["disappeared_errors"]:
            L.append("**Resolved / no longer detected:** " + "; ".join(f"{t['msg'][:70]} (was {t.get('pct', 0):.1f}%DAU)" for t in p["disappeared_errors"]))
        if p["appeared_warnings"]:
            L.append("")
            L.append(f"**New warning signatures {scope_word(report)}:** " + "; ".join(f"{t['msg'][:70]} ({t['pct']:.1f}%DAU)" for t in p["appeared_warnings"]))
        if p["disappeared_warnings"]:
            L.append("**Warnings gone since baseline:** " + "; ".join(f"{t['msg'][:70]} (was {t.get('pct', 0):.1f}%DAU)" for t in p["disappeared_warnings"]))
        if p["key"] in samples and samples[p["key"]]:
            L.append("")
            L.append("<details><summary>Representative error stacktraces (fix context)</summary>")
            L.append("")
            for s in samples[p["key"]][:5]:
                L.append(f"- **{s['msg'][:90]}** · {s['cat']} · {s['ver']} · {s['plat']} · {s['device']}")
                if s.get("attrs"):
                    L.append(f"  - attributes: `{s['attrs'][:200]}`")
                L.append("  ```")
                for ln in s["stack"].splitlines()[:6]:
                    L.append("  " + ln.strip())
                L.append("  ```")
            L.append("</details>")
        L.append("")
    obs = report.get("md_observations") or []
    if obs:
        L.append("## Log-system / infra observations")
        for o in obs:
            L.append(f"- {o}")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--out", default=".")
    ap.add_argument("--day", "--today", dest="day",
                    default=(dt.datetime.now(dt.timezone.utc).date() - dt.timedelta(days=1)).isoformat(),
                    help="report day (the completed day to analyze); default = yesterday UTC")
    ap.add_argument("--baseline-days", "--window", dest="baseline_days", type=int, default=None)
    ap.add_argument("--slug", default="prod_pulse")
    ap.add_argument("--dashboard", action="store_true",
                    help="also write the HTML dashboard files. Off by default: the report is "
                         "read as the Slack message plus the markdown attachment.")
    ap.add_argument("--store-snapshot", default=None,
                    help="path to the store report JSON to join, pinning it instead of "
                         "searching the configured directory by date. The orchestrator passes "
                         "the file it just generated.")
    ap.add_argument("--hours", type=int, default=None,
                    help="rolling-window (intermediate) report over the last N hours instead of a full day")
    ap.add_argument("--history-through", default=None,
                    help="only compare lifecycle/changes with reports at or before this report id; "
                         "use 'none' when no delivered report exists")
    args = ap.parse_args()

    cfg = load_config(args.config)
    if args.baseline_days:
        cfg["baseline_days"] = args.baseline_days
    client = Client(resolve_base_url(cfg), resolve_headers(cfg),
                    timeout=cfg["http_timeout"], retries=cfg["http_retries"],
                    deadline=time.monotonic() + cfg["run_timeout"])

    rolling = args.hours is not None
    if rolling:
        if not cfg.get("time_field"):
            ap.error("--hours requires cfg['time_field'] (e.g. \"TimeUTC\"); without it the rolling "
                     "window has no timestamp bound and would silently query whole-day indices.")
        now_dt = dt.datetime.now(dt.timezone.utc)
        report = build_report_window(client, cfg, args.hours, now_dt)
        samples = {}  # no stacktrace samples on the intermediate report
    else:
        report = build_report(client, cfg, args.day, args.out, args.slug)
        # sample stacktraces for attention projects (bounded), for the MD report
        samples = {}
        attention = [p for p in report["projects"] if p["status"] in ("degraded", "watch")][:6]
        with ThreadPoolExecutor(max_workers=cfg["max_workers"]) as ex:
            futs = {p["key"]: ex.submit(fetch_samples, client, cfg, p["prefix"], p["app_id"], report["report_day"])
                    for p in attention}
            for k, f in futs.items():
                try:
                    samples[k] = f.result()
                except Exception:
                    samples[k] = []

    history = load_health_history(args.out, args.slug, report["report_day"],
                                  kind=report.get("kind"), through=args.history_through)
    snapshot, why = load_store_snapshot(cfg, os.path.dirname(os.path.abspath(args.config)),
                                        report["report_day"], args.store_snapshot)
    report["health"] = build_health(report, snapshot)
    apply_overview_context(report, history)
    report["health"]["store_unavailable"] = why
    health_status = min([row["status"] for row in report["health"]["rows"]
                         if row["status"] != "nodata"] or ["nodata"],
                        key=lambda value: SEVERITY_RANK.get(value, 9))
    if SEVERITY_RANK.get(health_status, 9) < SEVERITY_RANK.get(report["overall_status"], 9):
        report["overall_status"] = health_status
    store_trust = ((snapshot or {}).get("report") or {}).get("trust") or {}
    trust = report.setdefault("trust", {})
    trust["store_snapshot_available"] = snapshot is not None
    trust["store_complete"] = bool(snapshot) and store_trust.get("complete", True)
    trust["store_delivery_safe"] = bool(snapshot) and store_trust.get(
        "delivery_safe", store_trust.get("complete", True))
    trust["complete"] = bool(trust.get("complete", True)
                             and trust["store_delivery_safe"])
    store_section = (snapshot or {}).get("technical_section") or []

    os.makedirs(args.out, exist_ok=True)
    base_path = os.path.join(args.out, f"{args.slug}_{report['report_day']}" if rolling
                             else f"{args.slug}_{args.day}")
    # Serialize once through the final redaction choke point. Collectors already redact
    # untrusted strings; this second boundary protects future fields and renderer drift.
    atomic_write_json(base_path + ".json", report, indent=2, default=list)
    if args.dashboard:
        title = html.escape(f"{cfg['brand']['org']} {cfg['brand']['product']}")
        inner = render_inner(report)
        atomic_write_text(base_path + ".inner.html", safety_redact(inner))
        atomic_write_text(base_path + ".html", safety_redact(
            SKELETON_HEAD.format(title=title) + inner + SKELETON_TAIL))
        atomic_write_text(base_path + ".render.html", safety_redact(
            SKELETON_HEAD.format(title=title) + render_inner(report, image=True) + SKELETON_TAIL))
    atomic_write_text(base_path + ".slack.txt", safety_redact(render_slack(report)))
    atomic_write_text(base_path + ".md", safety_redact(render_md(report, samples)))
    atomic_write_text(base_path + ".technical.slack.txt",
                      safety_redact(compose_technical_message(report, store_section)))
    overview_parts = render_status_slack_parts(report)
    if overview_parts:
        part_files = []
        for index, overview_text in enumerate(overview_parts, 1):
            part_path = (base_path + ".overview.slack.txt" if index == 1 else
                         base_path + f".overview.part-{index:02d}.slack.txt")
            atomic_write_text(part_path, safety_redact(overview_text))
            part_files.append(os.path.basename(part_path))
        atomic_write_text(base_path + ".overview.parts", "\n".join(part_files) + "\n")
        atomic_write_text(base_path + ".overview.md", safety_redact(render_status_md(report)))

    print(f"report_day: {report['report_day']}  overall: {report['overall_status']}  "
          f"projects: {len(report['projects'])}  baseline: {report['baseline_source']}")
    for p in report["projects"]:
        print(f"  {p['status']:9} {p['name']:16} dau={fmt_int(p['dau']):>7} err={fmt_int(p['err_total']):>8} "
              f"err/user={p['err_per_user']:>5} d={p['err_per_user_delta_pct']} worst={p['top_error_reach']}%")
    health = report.get("health") or {}
    print(f"  store join: {health.get('store_day') or 'none'}"
          + (f" ({health['store_unavailable']})" if health.get("store_unavailable") else ""))
    if report["errors"]:
        print("  ERRORS:", [(e["name"], e["error"][:60]) for e in report["errors"]])
    print(f"overview_messages: {len(overview_parts)}")
    print(f"store_technical_section: {len(store_section)} lines")
    print(f"written: {base_path}.{{json,slack.txt,md,technical.slack.txt,overview.slack.txt,overview.parts,overview.md"
          + (",html,inner.html,render.html}}" if args.dashboard else "}}"))


if __name__ == "__main__":
    main()
