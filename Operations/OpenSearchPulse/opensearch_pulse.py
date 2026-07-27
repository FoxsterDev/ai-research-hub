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
import glob
import html
import json
import os
import re
import time
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

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
    cfg.setdefault("min_dau", 100)
    cfg.setdefault("signals", {})
    cfg.setdefault("operations", [])  # config-driven endpoint/provider health sections
    cfg.setdefault("funnels", [])          # business-metric funnels (phrase-counted stages)
    cfg.setdefault("funnel_top_dau", None)  # if set, only the top-N DAU projects render funnels
    cfg.setdefault("funnels_summary_note", "")  # HTML note under the funnels summary (org copy lives in config)
    cfg.setdefault("md_observations", [])       # trailing md bullets (org-specific observations live in config)
    hy = cfg.setdefault("hygiene", {})     # shared issue rule table (log-sanitation + impact bar)
    hy.setdefault("rules", [])
    hy.setdefault("default", {"verdict": "review"})
    cfg.setdefault("levels", {"error": "Error", "warn": "Warn"})
    cfg.setdefault("sources", [])
    th = cfg.setdefault("thresholds", {})
    th.setdefault("degraded_pct", 40)
    th.setdefault("watch_pct", 15)
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

class Client:
    def __init__(self, base, headers, timeout=120, retries=3, backoff=2.0):
        self.base = base.rstrip("/")
        self.headers = headers
        self.timeout = timeout
        self.retries = max(1, int(retries))
        self.backoff = backoff

    def _req(self, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        last = None
        for attempt in range(self.retries):
            req = urllib.request.Request(self.base + path, data=data,
                                         method="POST" if body is not None else "GET", headers=self.headers)
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    return json.loads(resp.read().decode())
            except Exception as e:
                last = e
                msg = str(e).lower()
                transient = ("timed out" in msg or "timeout" in msg or "reset" in msg or "temporarily" in msg
                             or "429" in msg or "503" in msg or "unavailable" in msg)
                if not transient or attempt == self.retries - 1:
                    raise
                time.sleep(self.backoff * (2 ** attempt))
        raise last

    def cat_indices(self):
        return self._req("/_cat/indices?h=index&format=json")

    def search(self, index_list, body):
        return self._req(f"/{index_list}/_search", body)


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

SECRET_PATTERNS = [
    (re.compile(r"(://[^:/\s]+:)([^@/\s]+)(@)"), r"\1***REDACTED***\3"),
    (re.compile(r"((?:password|passwd|pwd)\s*[:=]\s*)([^\s,;&]+)", re.I), r"\1***REDACTED***"),
    (re.compile(r"(bearer\s+)([A-Za-z0-9._\-]{8,})", re.I), r"\1***REDACTED***"),
    (re.compile(r"((?:api[_-]?key|apikey|access[_-]?token|auth[_-]?token|secret|token)\s*[:=]\s*)([^\s,;&]+)", re.I), r"\1***REDACTED***"),
]


def redact(s):
    for pat, repl in SECRET_PATTERNS:
        s = pat.sub(repl, s)
    return s


EMPTY_MSG = "⟨no message — exception / stack-only⟩"


def norm_msg(s):
    if not s or not s.strip():
        return EMPTY_MSG
    return redact(re.sub(r"\s+", " ", s).strip())


# ------------------------------------------------------------------ query

def day_query(cfg, app_id=None, day=None, win=None):
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
                         "plat": {"terms": {"field": F["platform"], "size": 2}},
                     }},
        "by_platform": {"terms": {"field": F["platform"], "size": 6}},
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
        aggs["funnels"] = {"filters": {"filters": {
            f'{fn["key"]}::{st["key"]}': stage_filter(F, st) for fn in cfg["funnels"] for st in fn["stages"]}},
            "aggs": {"u": {"cardinality": {"field": U}}}}
        breakdown_stages = [(fn, st) for fn in cfg["funnels"] for st in fn["stages"] if st.get("breakdown")]
        if breakdown_stages:
            aggs["funnel_breakdowns"] = {"filters": {"filters": {
                f'{fn["key"]}::{st["key"]}': stage_filter(F, st) for fn, st in breakdown_stages}},
                "aggs": {"reasons": {"terms": {"field": F["message_keyword"], "size": 15},
                                     "aggs": {"u": {"cardinality": {"field": U}}}}}}
        if tag_f and fresh_tag:
            split_stages = [(fn, st) for fn in cfg["funnels"] if fn.get("split_by_tag")
                            for st in fn["stages"]]
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
    must = [{"match_phrase": {F["message_text"]: st["phrase"]}}]
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
    phrase = flow.get(outcome)
    if not phrase:
        return None
    must.append({"match_phrase": {F["message_text"]: phrase}})
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
    for name in ("success", "failure", "retry"):
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
        "key": flow["key"], "label": flow.get("label", flow["key"]), "success": result["success"],
        "failure": result["failure"], "retry": result["retry"],
        "terminal_failure_rate_pct": failure_rate, "retry_reach_pct_dau": retry_reach,
        "retry_events_per_user": round(result["retry"]["events"] / result["retry"]["users"], 2) if result["retry"]["users"] else 0.0,
        "classes": {bucket: {label: count for (kind, label), count in classes.items() if kind == bucket}
                    for bucket in ("failure", "retry")},
        "reasons": dict(reasons), "status": operation_status(flow, failure_rate, retry_reach),
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


def collect_day(client, cfg, prefix, app_id, day, win=None):
    index = win["index"] if win else prefix + day
    a = client.search(index, day_query(cfg, app_id, day, win))["aggregations"]
    dau = a["dau"]["value"]
    versions_detail = []
    for b in a["versions"]["buckets"]:
        plat = b["plat"]["buckets"][0]["key"] if b["plat"]["buckets"] else ""
        versions_detail.append({
            "ver": b["key"], "docs": b["doc_count"], "dau": b["users"]["value"],
            "err_total": b["err"]["doc_count"], "err_users": b["err"]["u"]["value"], "plat": plat,
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
        "signals": {k: {"total": v["doc_count"], "users": v.get("u", {}).get("value", 0)}
                    for k, v in a.get("signals", {}).get("buckets", {}).items()},
        "funnels_raw": {k: {"total": v["doc_count"], "users": v.get("u", {}).get("value", 0)}
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


def collect_baseline_windows(client, cfg, prefix, app_id, base_windows):
    """Baseline for the rolling report = the same clock window on each of the prior N days,
    pulled live from OpenSearch (never from disk, so intermediate runs don't touch the daily
    baseline history). Returns averaged per-user rates + DAU and the prior top signatures."""
    errs, warns, daus, versions = [], [], [], set()
    err_sigs, warn_sigs = set(), set()
    err_sig_pcts, warn_sig_pcts = {}, {}
    recent_err_top, recent_warn_top = [], []
    for i, w in enumerate(base_windows):
        d = collect_day(client, cfg, prefix, app_id, None, win=w)
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
        if i == 0:  # most-recent prior window drives "resolved since" comparison
            recent_err_top, recent_warn_top = d["top_errors"], d["top_warns"]
    return {"err_per_user": mean(errs), "warn_per_user": mean(warns), "dau": mean(daus),
            "versions": versions, "err_sigs": err_sigs, "warn_sigs": warn_sigs,
            "err_sig_pcts": {k: mean(v) for k, v in err_sig_pcts.items()},
            "warn_sig_pcts": {k: mean(v) for k, v in warn_sig_pcts.items()},
            "recent_err_top": recent_err_top, "recent_warn_top": recent_warn_top}


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


def _funnel_rates(fn, su, dau):
    """Config-defined conversion rates for a stage-users map `su` against cohort `dau`."""
    rates = []
    for rt in fn.get("rates", []):
        num = su.get(rt["num"], 0)
        d = rt.get("den")
        if d == "dau":
            den = dau
        elif isinstance(d, list):        # sum of stages, e.g. success/(success+failed)
            den = sum(su.get(k, 0) for k in d)
        else:
            den = su.get(d, 0)
        rates.append({"label": rt["label"], "num": num, "den": den,
                      "pct": round(num / den * 100.0, 1) if den else None,
                      "good": rt.get("good", "high"), "business": rt.get("business"),
                      "good_at": rt.get("good_at"), "bad_at": rt.get("bad_at")})
    return rates


def assemble_funnels(cfg, today, dau, key):
    """Reassemble per-funnel stage users/%DAU + config-defined conversion rates."""
    funnels_raw = today["funnels_raw"]
    funnel_breakdowns = today.get("funnel_breakdowns", {})
    funnels_split = today.get("funnels_split", {})
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
                    msg = row["msg"]
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
        rates = _funnel_rates(fn, su, dau)
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
                    "splits": splits})
    return out


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
    today = collect_day(client, cfg, prefix, app_id, report_day, win=win)
    if today["dau"] == 0:
        return None
    th = cfg["thresholds"]
    err_pu = per_user(today["err_total"], today["dau"])
    warn_pu = per_user(today["warn_total"], today["dau"])

    # baseline: prefer the most recent N prior reports on disk that include this project
    # (even weeks old); else fall back to OpenSearch over the immediate window.
    prior_days = [d for d in disk_dates_desc if key in prior_by_date.get(d, {})][:n]
    prior_err_sigs, prior_warn_sigs, prior_versions = set(), set(), set()
    recent_err_top, recent_warn_top = [], []
    if win is not None:
        # rolling-window report: baseline = same clock window on the prior N days (live from OS)
        bw = collect_baseline_windows(client, cfg, prefix, app_id, base_windows or [])
        base_source = f"prior {win['hours']}h windows"
        base_err_pu, base_warn_pu, base_dau = bw["err_per_user"], bw["warn_per_user"], bw["dau"]
        prior_err_sigs, prior_warn_sigs, prior_versions = bw["err_sigs"], bw["warn_sigs"], bw["versions"]
        recent_err_top, recent_warn_top = bw["recent_err_top"], bw["recent_warn_top"]
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
    # No usable baseline (err_d is None <=> base_err_pu <= 0) means we cannot judge a trend —
    # report it as nodata (unknown), not watch, so a baseline-less app never false-alarms.
    status = "nodata" if (low_data or err_d is None) else classify(err_d, th)

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
    funnels = assemble_funnels(cfg, today, today["dau"], key)
    impact = build_impact(top_errors, top_warns)
    if win is not None:
        operations = collect_operations(client, cfg, key, prefix, app_id, None, today["dau"], win=win)
        operations = attach_operation_baselines_windows(client, cfg, prefix, app_id, operations,
                                                        base_windows or [])
    else:
        operations = collect_operations(client, cfg, key, prefix, app_id, report_day, today["dau"])
        operations = attach_operation_baselines(client, cfg, key, prefix, app_id, operations,
                                                 prior_by_date, disk_dates_desc, operation_base_dates)

    # per-release rollout share of DAU + error rate (compare old vs new version)
    versions_detail = []
    for v in today["versions_detail"]:
        vdau = v["dau"] or 0
        versions_detail.append({
            "ver": v["ver"], "plat": plat_label(v["plat"]), "dau": vdau,
            "rollout_pct": round(min(100.0, vdau / today["dau"] * 100), 1) if today["dau"] else 0.0,
            "err_per_user": round(v["err_total"] / vdau, 2) if vdau else 0.0,
            "err_pct_users": round(min(100.0, v["err_users"] / vdau * 100), 1) if vdau else 0.0,
            "err_total": v["err_total"],
        })
    versions_detail.sort(key=lambda x: -x["dau"])
    versions_detail = versions_detail[:8]

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
        "platforms": today["platforms"], "signals": today["signals"],
        "appeared_errors": appeared[:6], "disappeared_errors": disappeared[:6],
        "appeared_warnings": appeared_warns[:6], "disappeared_warnings": disappeared_warns[:6],
        "new_releases": new_releases,
        "hygiene": hygiene_buckets, "funnels": funnels, "impact": impact, "operations": operations,
    }


FNAME_DATE_RE = re.compile(r"_(\d{4}-\d{2}-\d{2})\.json$")


def load_prior_reports(out_dir, slug, report_day, max_candidates=21):
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
    by_date = {}
    for d, path in cands[:max_candidates]:
        try:
            rep = json.load(open(path))
        except Exception:
            continue
        if not rep.get("report_day") or "projects" not in rep:
            continue  # not a day-model report -> not structurally sufficient
        usable = {p["key"]: p for p in rep["projects"]
                  if all(k in p for k in ("err_per_user", "warn_per_user", "dau"))}
        if usable:
            by_date[d] = usable
    return by_date, sorted(by_date, reverse=True)


def build_report(client, cfg, report_day, out_dir, slug):
    idx = discover_indices(client)
    n = cfg["baseline_days"]
    # prior day-model reports on disk (any dates < report_day, most-recent first)
    prior_by_date, disk_dates_desc = load_prior_reports(out_dir, slug, report_day)
    operation_baseline_days = max([int(f.get("baseline_days", cfg.get("operation_baseline_days", 7)))
                                   for p in cfg.get("operations", []) for f in p.get("flows", [])] or [0])
    jobs = []
    for src in cfg["sources"]:
        prefix = src["index_prefix"]
        if prefix not in idx or report_day not in idx[prefix]:
            continue
        before = [d for d in idx[prefix] if d < report_day]
        os_base_dates = before[-n:]  # OpenSearch fallback window (immediate N index days)
        operation_base_dates = before[-operation_baseline_days:] if operation_baseline_days else []
        if src.get("split_by_app_id"):
            app_names = src.get("app_names", {})
            for app_id in discover_app_ids(client, cfg, prefix, report_day):
                jobs.append((app_id, app_names.get(app_id, app_id), prefix, app_id, os_base_dates, operation_base_dates))
        else:
            key = src.get("key") or prefix.rstrip("-")
            jobs.append((key, src.get("name") or key, prefix, None, os_base_dates, operation_base_dates))

    def run(job):
        key, name, prefix, app_id, os_base_dates, operation_base_dates = job
        try:
            return build_project(client, cfg, key, name, prefix, app_id, report_day,
                                 os_base_dates, operation_base_dates, prior_by_date, disk_dates_desc, n)
        except Exception as e:
            return {"key": key, "name": name, "error": str(e)}

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
    overall = "healthy"
    for p in ok:
        if p["status"] == "degraded":
            overall = "degraded"; break
        if p["status"] == "watch":
            overall = "watch"
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
        "fresh_tag": cfg.get("fresh_launch_tag") or "",
        "funnels_note": cfg["funnels_summary_note"], "md_observations": cfg["md_observations"],
        "signals_meta": {k: v.get("label", k) for k, v in cfg["signals"].items()},
        "projects": ok, "source": client.base.split("//")[-1].split(".")[0],
        "errors": [p for p in projects if "error" in p],
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
        if not win:
            continue
        base_windows = [w for w in (make_window(cfg, prefix, idx, lo_dt - dt.timedelta(days=k),
                                                 hi_dt - dt.timedelta(days=k)) for k in range(1, n + 1)) if w]
        if src.get("split_by_app_id"):
            app_names = src.get("app_names", {})
            # discover over the whole window (all indices it touches, bounded to [lo, hi]) so an
            # app active only in the older half of a cross-midnight window is not missed.
            for app_id in discover_app_ids(client, cfg, prefix, None, index=win["index"],
                                           extra_filter=time_bounds_filter(cfg, win["lo"], win["hi"])):
                jobs.append((app_id, app_names.get(app_id, app_id), prefix, app_id, win, base_windows))
        else:
            key = src.get("key") or prefix.rstrip("-")
            jobs.append((key, src.get("name") or key, prefix, None, win, base_windows))

    def run(job):
        key, name, prefix, app_id, win, base_windows = job
        try:
            return build_project(client, cfg, key, name, prefix, app_id, None, [], [], {}, [], n,
                                 win=win, base_windows=base_windows)
        except Exception as e:
            return {"key": key, "name": name, "error": str(e)}

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
    overall = "healthy"
    for p in ok:
        if p["status"] == "degraded":
            overall = "degraded"; break
        if p["status"] == "watch":
            overall = "watch"
    label = f"{lo_dt.strftime('%Y-%m-%d %H:%M')} → {hi_dt.strftime('%Y-%m-%d %H:%M')} UTC"
    return {
        "schema": 3, "kind": "rolling", "window_hours": hours,
        "generated_utc": now_dt.strftime("%Y-%m-%d %H:%M UTC"),
        "report_day": hi_dt.strftime("%Y-%m-%dT%H%MZ"),
        "window_label": f"last {hours}h", "baseline_dates": [], "baseline_days": n,
        "window_utc": label, "is_last_complete": False,
        "baseline_source": f"prior {n}×{hours}h windows",
        "overall_status": overall, "brand": cfg["brand"],
        "fresh_tag": cfg.get("fresh_launch_tag") or "",
        "funnels_note": cfg["funnels_summary_note"], "md_observations": cfg["md_observations"],
        "signals_meta": {k: v.get("label", k) for k, v in cfg["signals"].items()},
        "projects": ok, "source": client.base.split("//")[-1].split(".")[0],
        "errors": [p for p in projects if "error" in p],
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
            act = f" → {imp['action'][:90]}" if imp and imp.get("action") else ""
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


def overview_row(p):
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
        f'<td data-sort="{SEVERITY_RANK.get(st, 4)}"><span class="status-chip {st}">{STATUS_LABEL[st]}</span></td></tr>')


def overview_table(report):
    rows = "\n".join(overview_row(p) for p in report["projects"])
    base = report["baseline_dates"]
    base_lbl = f'{base[0]} → {base[-1]}' if base else 'n/a'
    ft = report.get("fresh_tag")
    fresh_note = (f"<b>Fresh %</b> = share of that day's DAU whose session carried a <code>{html.escape(ft)}</code> tag "
                  "(a cold/fresh process start rather than a warm resume). ") if ft else ""
    return f"""
<section class="card overview">
  <h2 class="ov-title">All projects — {day_label(report)}</h2>
  <div class="table-scroll"><table class="ov">
    <thead><tr><th>Project</th><th class="num">DAU</th><th class="num">Fresh %</th><th class="num">Errors</th>
      <th class="num">err/user</th><th class="num">worst err %</th>
      <th class="num">Warns</th><th class="num">warn/user</th><th class="num">worst warn %</th><th>Status</th></tr></thead>
    <tbody>{rows}</tbody>
  </table></div>
  <p class="ov-note">All figures are for <b>{day_label(report)}</b>. {fresh_note}err/user & warn/user show the <b>diff vs the {report['baseline_days']}-day baseline</b> ({base_lbl}, from {report['baseline_source']}). Worst error/warn % = the single signature at that level touching the largest share of that day's DAU. <b>Click a column header to sort</b> (again to reverse).</p>
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
.wrap{font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;color:var(--ink);background:var(--bg);max-width:1120px;margin:0 auto;padding:28px 22px 48px;line-height:1.5}
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


def render_slack(report):
    icon = {"healthy": "\U0001f7e2", "watch": "\U0001f7e1", "degraded": "\U0001f534", "nodata": "⚪"}
    b = report["brand"]
    lc = " (last complete UTC day)" if report.get("is_last_complete") else ""
    errs = report.get("errors", [])
    total = len(report["projects"]) + len(errs)
    proj_count = f"{len(report['projects'])}/{total} projects ({len(errs)} failed)" if errs else f"{len(report['projects'])} projects"
    base_desc = f"vs {report['baseline_source']}" if report.get("kind") == "rolling" else f"day vs {report['baseline_days']}-day baseline ({report['baseline_source']})"
    lines = [f"*{b['org']} {b['product']} — {day_label(report)}*{lc}  {icon[report['overall_status']]} *{STATUS_LABEL[report['overall_status']]}*",
             f"_covers {report['window_utc']}_",
             f"_{proj_count} · {base_desc} · generated {report['generated_utc']}_"]
    if errs:
        lines.append("")
        lines.append(f"⚠️ *{len(errs)} projects not reported (query failed):* "
                     + ", ".join(f"{e['name']} ({e['error'][:40]})" for e in errs))
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
    ap.add_argument("--hours", type=int, default=None,
                    help="rolling-window (intermediate) report over the last N hours instead of a full day")
    args = ap.parse_args()

    cfg = load_config(args.config)
    if args.baseline_days:
        cfg["baseline_days"] = args.baseline_days
    client = Client(resolve_base_url(cfg), resolve_headers(cfg),
                    timeout=cfg["http_timeout"], retries=cfg["http_retries"])

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

    os.makedirs(args.out, exist_ok=True)
    base_path = os.path.join(args.out, f"{args.slug}_{report['report_day']}" if rolling
                             else f"{args.slug}_{args.day}")
    with open(base_path + ".json", "w") as f:
        json.dump(report, f, indent=2, default=list)
    title = html.escape(f"{cfg['brand']['org']} {cfg['brand']['product']}")
    inner = render_inner(report)
    with open(base_path + ".inner.html", "w") as f:
        f.write(inner)
    with open(base_path + ".html", "w") as f:
        f.write(SKELETON_HEAD.format(title=title) + inner + SKELETON_TAIL)
    with open(base_path + ".render.html", "w") as f:
        f.write(SKELETON_HEAD.format(title=title) + render_inner(report, image=True) + SKELETON_TAIL)
    with open(base_path + ".slack.txt", "w") as f:
        f.write(render_slack(report))
    with open(base_path + ".md", "w") as f:
        f.write(render_md(report, samples))

    print(f"report_day: {report['report_day']}  overall: {report['overall_status']}  "
          f"projects: {len(report['projects'])}  baseline: {report['baseline_source']}")
    for p in report["projects"]:
        print(f"  {p['status']:9} {p['name']:16} dau={fmt_int(p['dau']):>7} err={fmt_int(p['err_total']):>8} "
              f"err/user={p['err_per_user']:>5} d={p['err_per_user_delta_pct']} worst={p['top_error_reach']}%")
    if report["errors"]:
        print("  ERRORS:", [(e["name"], e["error"][:60]) for e in report["errors"]])
    print(f"written: {base_path}.{{json,html,inner.html,render.html,slack.txt,md}}")


if __name__ == "__main__":
    main()
