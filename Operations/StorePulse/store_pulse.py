#!/usr/bin/env python3
"""Store Pulse — a config-driven daily store-health reporter for mobile portfolios.

Reads Google Play (Play Developer Reporting API, Android Publisher reviews, the
Play Console bulk-report bucket) and Apple (App Store Connect API plus the public
iTunes lookup endpoint) for every app in a config table, and writes a snapshot,
a dashboard, a Slack digest, a compact digest block for an existing report, and a
triage markdown file.

The tool is free of any app, org or credential data: everything target-specific
lives in the JSON config the caller supplies, and every secret is read from a
path named by an environment variable. That keeps this directory publishable.

Delivery (Slack, e-mail) is deliberately not part of this tool.
"""

import argparse
import datetime as dt
import glob
import html
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import store_sources as src
from store_auth import AppleAuth, AuthError, GoogleAuth, HttpError, Transport
from report_safety import atomic_write_json, atomic_write_text, redact as safety_redact, safe_error as shared_safe_error

STATUS_ORDER = {"healthy": 0, "nodata": 1, "watch": 2, "degraded": 3}
STATUS_LABEL = {"healthy": "Healthy", "watch": "Watch", "degraded": "Degraded", "nodata": "Low data"}
ICON = {"healthy": "\U0001f7e2", "watch": "\U0001f7e1", "degraded": "\U0001f534", "nodata": "⚪"}

SLICE_NEEDS = {
    "ios_rating": (),
    "ios_reviews": ("apple",),
    "ios_release": ("apple",),
    "ios_analytics": ("apple",),
    "ios_perf": ("apple",),
    "play_vitals": ("google",),
    "play_issues": ("google",),
    "play_anomalies": ("google",),
    "play_reviews": ("google",),
    "play_rating": ("google", "bucket"),
    "play_store_perf": ("google", "bucket"),
    "play_installs": ("google", "bucket"),
}

DEFAULTS = {
    "storefronts": ["us"],
    "review_excerpt_chars": 240,
    "review_sample": 3,
    "max_workers": 6,
    "http_timeout": 60,
    "http_retries": 3,
    "run_timeout": 900,
    "vitals_trail_days": 7,
    "vitals_rate_is_fraction": "auto",
    "slices": {k: True for k in SLICE_NEEDS},
    "thresholds": {
        "play_crash_alert_pct": 1.09,
        "play_anr_alert_pct": 0.47,
        "play_device_alert_pct": 8.0,
        "watch_fraction": 0.6,
        "rating_drop_watch": 0.02,
        "rating_drop_alert": 0.05,
        "rating_drop_7d_watch": 0.07,
        "rating_drop_7d_alert": 0.15,
        "rating_floor_watch": 3.5,
        "rating_floor_alert": 3.0,
        "rating_floor_min_count": 5,
        "neg_share_watch_pct": 40.0,
        "neg_share_alert_pct": 60.0,
        "neg_min_count": 5,
        "unanswered_backlog_watch": 25,
        "conversion_drop_watch_pct": 10.0,
        "conversion_drop_alert_pct": 25.0,
        "min_vitals_users": 100,
        "ios_crash_per_1k_watch": 2.0,
        "ios_crash_per_1k_alert": 5.0,
        "ios_crash_min_sessions": 500,
        "perf_regression_watch_pct": 25.0,
        "perf_regression_alert_pct": 50.0,
        "perf_findings_per_app": 2,
    },
    "review_topics": [],
    "modes": {
        "daily": {"review_window_days": 1, "review_pages": 1},
        "weekly": {"review_window_days": 7, "review_pages": 1},
        "monthly": {"review_window_days": 30, "review_pages": 3}
    },
    "play_vitals_sets": [
        {"key": "crash", "metric_set": "crashRateMetricSet",
         "metrics": ["crashRate", "userPerceivedCrashRate", "distinctUsers"],
         "dimensions": ["versionCode"]},
        {"key": "anr", "metric_set": "anrRateMetricSet",
         "metrics": ["anrRate", "userPerceivedAnrRate", "distinctUsers"],
         "dimensions": ["versionCode"]},
    ],
    "play_reports": {},
    "ios_perf_device": "all_iphones",
    "ios_perf_baseline_versions": 4,
    "ios_perf_metrics": [
        {"key": "termination", "label": "Foreground terminations", "category": "TERMINATION",
         "metric": "onScreen", "percentile": "p90", "watch": 0.5, "alert": 1.0,
         "min_for_regression": 0.5},
        {"key": "hang", "label": "Hang rate", "category": "HANG", "metric": "hangRate",
         "percentile": "p90", "watch": 10.0, "alert": 20.0, "min_for_regression": 2.0},
        {"key": "launch", "label": "Launch time", "category": "LAUNCH", "metric": "launchTime",
         "percentile": "p90", "watch": 2000.0, "alert": 3000.0, "min_for_regression": 500.0},
        {"key": "memory", "label": "Peak memory", "category": "MEMORY", "metric": "peakMemory",
         "percentile": "p90", "min_for_regression": 100.0},
        {"key": "disk", "label": "Disk writes", "category": "DISK", "metric": "diskWrites",
         "percentile": "p90", "min_for_regression": 50.0},
        {"key": "battery", "label": "Battery drain", "category": "BATTERY", "metric": "batteryUsage",
         "percentile": "p90", "min_for_regression": 1.0},
        {"key": "glitch", "label": "Animation glitches", "category": "ANIMATION",
         "metric": "animationGlitchRate", "percentile": "p90", "min_for_regression": 1.0},
    ],
    "ios_analytics_granularity": "DAILY",
    "ios_analytics_max_segments": 100,
    "ios_analytics_max_rows": 200000,
    "ios_analytics_metrics": [
        {"key": "crashes", "label": "Crashes", "report": "App Crashes", "category": "APP_USAGE",
         "value_cols": ["Crashes", "Crash Count", "Count"],
         "dim_cols": ["App Version", "Device", "Platform Version"]},
        {"key": "sessions", "label": "Sessions", "report": "App Sessions Standard",
         "category": "APP_USAGE", "value_cols": ["Sessions", "Session Count", "Count"],
         "dim_cols": ["App Version"]},
        {"key": "installs", "label": "Installs",
         "report": "App Store Installation and Deletion Standard", "category": "APP_USAGE",
         "value_cols": ["Counts", "Installations", "Install Count", "Count"],
         "row_filter": {"Event": ["install"]}, "dim_cols": ["App Version"]},
        {"key": "deletions", "label": "Deletions",
         "report": "App Store Installation and Deletion Standard", "category": "APP_USAGE",
         "value_cols": ["Counts", "Deletions", "Delete Count", "Count"],
         "row_filter": {"Event": ["delete"]}, "dim_cols": ["App Version"]},
    ],
    "credentials": {
        "google_service_account_env": "STORE_PULSE_GOOGLE_SA_JSON",
        "play_reports_bucket_env": "STORE_PULSE_PLAY_BUCKET",
        "apple_key_path_env": "STORE_PULSE_ASC_KEY_P8",
        "apple_key_id_env": "STORE_PULSE_ASC_KEY_ID",
        "apple_issuer_id_env": "STORE_PULSE_ASC_ISSUER_ID",
    },
    "brand": {"org": "", "product": "Store Pulse"},
}


# ------------------------------------------------------------------ config

def _merge(base, over):
    out = dict(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(path):
    with open(path) as fh:
        cfg = json.load(fh)
    cfg = _merge(DEFAULTS, cfg)
    if not cfg.get("apps"):
        raise SystemExit("config error: 'apps' is empty — nothing to report on")
    keys = [app.get("key") for app in cfg["apps"]]
    if None in keys or len(set(keys)) != len(keys):
        raise SystemExit("config error: app keys must be present and unique")
    unknown_slices = set(cfg.get("slices", {})) - set(SLICE_NEEDS)
    if unknown_slices:
        raise SystemExit("config error: unknown slice(s): " + ", ".join(sorted(unknown_slices)))
    for field in ("max_workers", "http_timeout", "http_retries", "run_timeout",
                  "ios_analytics_max_segments", "ios_analytics_max_rows"):
        if float(cfg.get(field, 0)) <= 0:
            raise SystemExit(f"config error: {field} must be positive")
    th = cfg["thresholds"]
    for watch, alert in (("rating_drop_watch", "rating_drop_alert"),
                         ("rating_drop_7d_watch", "rating_drop_7d_alert"),
                         ("neg_share_watch_pct", "neg_share_alert_pct"),
                         ("conversion_drop_watch_pct", "conversion_drop_alert_pct"),
                         ("ios_crash_per_1k_watch", "ios_crash_per_1k_alert"),
                         ("perf_regression_watch_pct", "perf_regression_alert_pct")):
        if th[alert] < th[watch]:
            raise SystemExit(f"config error: {alert} must be >= {watch}")
    for app in cfg["apps"]:
        if not app.get("key"):
            raise SystemExit("config error: every app needs a 'key'")
        app.setdefault("name", app["key"])
        app.setdefault("android", None)
        app.setdefault("ios", None)
        app.setdefault("ios_app_id", None)
        app.setdefault("family", cfg.get("default_family"))
        app.setdefault("slices", {})
    return cfg


class Creds:
    """Resolves credentials from env-named paths; records why a slice is unavailable."""

    def __init__(self, cfg, transport):
        c = cfg["credentials"]
        self.transport = transport
        self.reasons = {}
        sa_path = os.environ.get(c["google_service_account_env"], "")
        self.google = None
        if not sa_path:
            self.reasons["google"] = f"${c['google_service_account_env']} is not set"
        elif not os.path.exists(sa_path):
            self.reasons["google"] = f"${c['google_service_account_env']} points at a missing file"
        else:
            self.google = GoogleAuth(sa_path, transport)
        self.bucket = os.environ.get(c["play_reports_bucket_env"], "").replace("gs://", "").strip("/")
        if not self.bucket:
            self.reasons["bucket"] = f"${c['play_reports_bucket_env']} is not set"
        key = os.environ.get(c["apple_key_path_env"], "")
        kid = os.environ.get(c["apple_key_id_env"], "")
        iss = os.environ.get(c["apple_issuer_id_env"], "")
        self.apple = None
        if not (key and kid and iss):
            missing = [n for n, v in ((c["apple_key_path_env"], key), (c["apple_key_id_env"], kid),
                                      (c["apple_issuer_id_env"], iss)) if not v]
            self.reasons["apple"] = "missing $" + ", $".join(missing)
        elif not os.path.exists(key):
            self.reasons["apple"] = f"${c['apple_key_path_env']} points at a missing file"
        else:
            self.apple = AppleAuth(key, kid, iss)

    def has(self, need):
        return {"google": self.google is not None, "apple": self.apple is not None,
                "bucket": bool(self.bucket)}.get(need, False)

    def missing_for(self, slice_name):
        return [n for n in SLICE_NEEDS[slice_name] if not self.has(n)]

    def google_headers(self):
        return self.google.headers()

    def apple_headers(self):
        return self.apple.headers()


# ------------------------------------------------------------------ helpers

def apply_mode(cfg, mode):
    """Resolve read depth. An explicit `--mode` is a deliberate override; without one the
    config is the truth — the engine must never silently narrow a review window a host
    declared on purpose (this portfolio runs 7 days because volume is low)."""
    if mode:
        cfg.update((cfg.get("modes") or {}).get(mode, {}))
    cfg["mode"] = mode or "config"
    return cfg


_URL_RE = re.compile(r"(https?://)([^/\s]+)(/[^\s]*)?")


def safe_error(exc, limit=220):
    """Report-safe error text. Secrets are redacted, and a URL keeps only scheme+host:
    a GCS object URL carries the bulk-report bucket id, which lives in the environment
    on purpose and must never land in a committed report or a Slack message."""
    text = str(exc) if isinstance(exc, (HttpError, AuthError)) else shared_safe_error(exc, limit=1000)
    text = _URL_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}/…" if m.group(3) else m.group(0),
                       safety_redact(text))
    return text[:limit]


def slice_enabled(cfg, app, name):
    if name in app.get("slices", {}):
        return bool(app["slices"][name])
    return bool(cfg["slices"].get(name, False))


def rate_to_pct(value, mode="auto"):
    """Play vitals rates are ratios; be explicit but tolerate a percent-shaped API."""
    if value is None:
        return None
    if mode is True or mode == "fraction":
        return value * 100.0
    if mode is False or mode == "percent":
        return value
    return value * 100.0 if value <= 1.0 else value


def month_token(day):
    return f"{day.year:04d}{day.month:02d}"


def newest_series_day(series, not_after=None):
    days = sorted(d for d in series if re.match(r"^\d{4}-\d{2}-\d{2}$", d))
    if not_after:
        days = [d for d in days if d <= not_after]
    return days[-1] if days else None


def match_topics(text, topics):
    """Every topic a review touches, in config order (a review is rarely about one thing)."""
    low = (text or "").lower()
    hits = []
    for t in topics:
        if any(phrase.lower() in low for phrase in t.get("phrases", [])):
            hits.append(t)
    return hits


def topic_of(text, topics):
    hits = match_topics(text, topics)
    return hits[0]["key"] if hits else None


def _tier(stars):
    return "negative" if stars <= 2 else "neutral" if stars == 3 else "positive"


def review_digest(items, cfg, source):
    """Star split, negative share, unanswered backlog and topic buckets."""
    topics = cfg.get("review_topics", [])
    stars = [r["stars"] for r in items if r.get("stars")]
    neg = [r for r in items if r.get("stars") and r["stars"] <= 2]
    buckets = {}
    for r in neg:
        key = topic_of((r.get("title", "") + " " + r.get("text", "")), topics) or "other"
        buckets[key] = buckets.get(key, 0) + 1
    worst = sorted(neg, key=lambda r: (r["stars"], -(r.get("thumbs_up") or 0)))
    sample = [{k: v for k, v in r.items() if k in ("stars", "text", "title", "app_version",
                                                   "territory", "device", "at", "answered")}
              for r in worst[:cfg["review_sample"]]]
    return {
        "source": source,
        "count": len(items),
        "avg": round(sum(stars) / len(stars), 2) if stars else None,
        "split": {str(s): sum(1 for x in stars if x == s) for s in range(1, 6)},
        "neg_count": len(neg),
        "neg_share_pct": round(100.0 * len(neg) / len(items), 1) if items else None,
        "unanswered": sum(1 for r in items if not r.get("answered")),
        "topics": dict(sorted(buckets.items(), key=lambda kv: -kv[1])),
        "sample": sample,
    }


# ------------------------------------------------------------------ collect

def collect_ios_rating(ctx, app):
    fronts = app.get("storefronts") or ctx["cfg"]["storefronts"]
    data = src.itunes_lookup(ctx["transport"], app["ios"], fronts)
    primary = fronts[0]
    front = data["storefronts"].get(primary, {})
    if app.get("ios_app_id") is None and data.get("track_id"):
        app["ios_app_id"] = str(data["track_id"])
    app["_current_release"] = front.get("released")
    return {"as_of": ctx["now"][:10], "primary_storefront": primary,
            "avg": front.get("avg"), "count": front.get("count"),
            "avg_current": front.get("avg_current"), "version": front.get("version"),
            "released": front.get("released"), "listed": front.get("listed", False),
            "track_id": data.get("track_id"), "store_name": data.get("name"),
            "by_storefront": data["storefronts"]}


def _ios_app_id(ctx, app):
    if app.get("ios_app_id"):
        return app["ios_app_id"]
    found = src.asc_app_by_bundle(ctx["transport"], ctx["creds"].apple_headers(), app["ios"])
    if not found:
        raise RuntimeError(f"bundle id not found in the App Store Connect account")
    app["ios_app_id"] = found["id"]
    return app["ios_app_id"]


def collect_ios_reviews(ctx, app):
    app_id = _ios_app_id(ctx, app)
    cfg = ctx["cfg"]
    items = src.asc_customer_reviews(ctx["transport"], ctx["creds"].apple_headers(), app_id,
                                     max_pages=cfg.get("review_pages", 1))
    cutoff = ctx["window_start"]
    fresh = [r for r in items if (r.get("at") or "") >= cutoff]
    out = review_digest(fresh, cfg, "ios")
    out["backlog_unanswered"] = sum(1 for r in items if not r.get("answered"))
    out["scanned"] = len(items)
    out["window_start"] = cutoff
    return out


def collect_ios_release(ctx, app):
    app_id = _ios_app_id(ctx, app)
    headers = ctx["creds"].apple_headers()
    versions = src.asc_versions(ctx["transport"], headers, app_id)
    current = versions[0] if versions else None
    phased = src.asc_phased_release(ctx["transport"], headers, current["id"]) if current else None
    out = {"versions": versions, "phased": phased, "current": current,
           "submissions": [], "rejection": None, "submission_notes": None}
    state = ((current or {}).get("state") or "").upper()
    if any(bad in state for bad in ("REJECT", "INVALID", "REMOVED")):
        # A rejection is only actionable with its timeline: how it was submitted, when, and
        # how long it has sat. The reviewer's message itself is Resolution-Center-only.
        subs = src.asc_review_submissions(ctx["transport"], headers, app_id)
        out["submissions"] = subs[:5]
        last = subs[0] if subs else None
        if last:
            age = None
            try:
                submitted = dt.date.fromisoformat(last["submitted"][:10])
                age = (ctx["day"] - submitted).days
            except (TypeError, ValueError):
                pass
            out["rejection"] = {"state": state, "version": (current or {}).get("version"),
                                "submission_state": last["state"], "submitted": last["submitted"][:10],
                                "days_unresolved": age,
                                "version_created": (current or {}).get("created")}
        else:
            out["rejection"] = {"state": state, "version": (current or {}).get("version"),
                                "submission_state": None, "submitted": None,
                                "days_unresolved": None,
                                "version_created": (current or {}).get("created")}
        out["submission_notes"] = src.asc_review_detail(ctx["transport"], headers, current["id"])
    return out


def _analytics_report_index(ctx, requests):
    """Report name -> ordered candidates, preferring ONGOING but retaining snapshot fallback.

    An app can carry both an ONGOING request (a fresh instance per day) and a
    ONE_TIME_SNAPSHOT (the trailing year, once). They expose the same report catalogue
    under different ids, so the daily read prefers ONGOING and falls back to the
    snapshot while ONGOING has not delivered its first instance yet.
    """
    cfg, index, errors = ctx["cfg"], {}, []
    order = sorted(requests, key=lambda r: 0 if r["access_type"] == "ONGOING" else 1)
    for req in order:
        try:
            reports = src.asc_analytics_reports(
                ctx["transport"], ctx["creds"].apple_headers(), req["id"],
                categories=cfg.get("ios_analytics_categories", []),
                name_filter=cfg.get("ios_analytics_reports", []))
        except HttpError as exc:
            errors.append(f"{req['access_type']}: {safe_error(exc)}")
            continue
        for rep in reports:
            candidate = dict(rep, request=req["id"], access_type=req["access_type"])
            if rep["name"] not in index:
                index[rep["name"]] = candidate
            else:
                index[rep["name"]].setdefault("fallbacks", []).append(candidate)
    return index, errors


def _analytics_instance(ctx, report_id, granularity):
    """Newest instance whose data day is not after the report day."""
    inst = src.asc_report_instance(ctx["transport"], ctx["creds"].apple_headers(),
                                   report_id, granularity=granularity, limit=50)
    limit = ctx["day"].isoformat()
    usable = [i for i in inst if (i.get("processing_date") or "") <= limit]
    return usable[-1] if usable else None


def _latest_analytics_instance(ctx, report_id, granularity):
    """Newest snapshot instance regardless of processing date; its rows are date-filtered."""
    instances = src.asc_report_instance(ctx["transport"], ctx["creds"].apple_headers(),
                                        report_id, granularity=granularity, limit=50)
    return instances[-1] if instances else None


def _analytics_rows(ctx, instance_id):
    cfg = ctx["cfg"]
    segments = src.asc_instance_segments(ctx["transport"], ctx["creds"].apple_headers(),
                                         instance_id)
    max_rows = cfg["ios_analytics_max_rows"]
    header, rows, read_segments = [], [], 0
    complete = len(segments) <= cfg["ios_analytics_max_segments"]
    for seg in segments[:cfg["ios_analytics_max_segments"]]:
        if not seg.get("url"):
            complete = False
            continue
        seg_header, seg_rows = src.asc_segment_rows(ctx["transport"], seg["url"])
        header = header or seg_header
        read_segments += 1
        if len(rows) + len(seg_rows) > max_rows:
            complete = False
            rows.extend(seg_rows[:max(0, max_rows - len(rows))])
            break
        rows.extend(seg_rows)
    return header, rows, {"segments": len(segments), "segments_read": read_segments,
                          "rows_read": len(rows), "complete": complete}


def _row_matches(row, row_filter):
    for column, allowed in (row_filter or {}).items():
        value = (row.get(column) or "").strip().lower()
        if not any(a.lower() in value for a in allowed):
            return False
    return True


def _rows_for_day(header, rows, day):
    """Select one data day from a ONE_TIME_SNAPSHOT; daily reports remain unchanged."""
    idx = src.pick_col(header, ["Date"])
    if idx is None:
        return rows
    column = header[idx]
    wanted = day.isoformat()
    return [row for row in rows if str(row.get(column) or "")[:10] == wanted]


def _aggregate_rows(header, rows, spec):
    """Sum one value column over an instance, plus the top slices of its dimensions."""
    idx = src.pick_col(header, spec["value_cols"])
    if idx is None:
        return {"value": None, "unmapped": spec["value_cols"], "header": header[:12]}
    missing = [c for c in (spec.get("row_filter") or {}) if src.pick_col(header, [c]) is None]
    if missing:
        return {"value": None, "unmapped": missing, "header": header[:12]}
    column = header[idx]
    total, matched, by_dim = 0.0, 0, {}
    dim_names = [header[i] for i in
                 (src.pick_col(header, [d]) for d in spec.get("dim_cols") or []) if i is not None]
    for row in rows:
        if not _row_matches(row, spec.get("row_filter")):
            continue
        value = src.parse_num(row.get(column))
        if value is None:
            continue
        total += value
        matched += 1
        for dim in dim_names:
            key = (row.get(dim) or "").strip() or "—"
            bucket = by_dim.setdefault(dim, {})
            bucket[key] = bucket.get(key, 0.0) + value
    out = {"value": total if matched else None, "column": column, "rows": matched}
    out["breakdown"] = {dim: [{"key": k, "value": v} for k, v in
                              sorted(vals.items(), key=lambda kv: -kv[1])[:5]]
                        for dim, vals in by_dim.items()}
    return out


def collect_ios_analytics(ctx, app):
    """App Analytics: crash, session and install/deletion counts for the report day.

    Apple serves these only through a registered report request (`bootstrap` creates
    them) and starts delivering instances 24-48h after registration, so "registered but
    no instance yet" is a normal state that must be reported, not treated as a failure.
    """
    cfg = ctx["cfg"]
    app_id = _ios_app_id(ctx, app)
    requests = src.asc_analytics_requests(ctx["transport"], ctx["creds"].apple_headers(), app_id)
    live = [r for r in requests if not r.get("stopped")]
    out = {"requests": requests,
           "ongoing": sum(1 for r in live if r["access_type"] == "ONGOING"),
           "snapshot": sum(1 for r in live if r["access_type"] == "ONE_TIME_SNAPSHOT"),
           "stopped": sum(1 for r in requests if r.get("stopped")),
           "reports": [], "metrics": {}, "derived": {}, "as_of": None, "pending": None}
    if not live:
        out["pending"] = ("no analytics report request registered — "
                          "run `bootstrap` with an Admin-role key")
        return out
    index, listing_errors = _analytics_report_index(ctx, live)
    out["reports"] = sorted(index)
    if listing_errors:
        out["listing_errors"] = listing_errors
    if not index:
        out["pending"] = ("could not list the request's reports — " + "; ".join(listing_errors)
                          if listing_errors else
                          "the request is registered but Apple lists no reports for it yet")
        return out
    granularity = cfg["ios_analytics_granularity"]
    cache = {}
    for spec in cfg.get("ios_analytics_metrics", []):
        rep = index.get(spec["report"])
        if not rep:
            out["metrics"][spec["key"]] = {"label": spec["label"], "value": None,
                                           "missing_report": spec["report"]}
            continue
        selected = None
        for candidate in [rep] + (rep.get("fallbacks") or []):
            cache_key = candidate["id"]
            if cache_key not in cache:
                inst = (_latest_analytics_instance(ctx, cache_key, granularity)
                        if candidate.get("access_type") == "ONE_TIME_SNAPSHOT"
                        else _analytics_instance(ctx, cache_key, granularity))
                cache[cache_key] = (candidate, inst, *_analytics_rows(ctx, inst["id"])) \
                    if inst else (candidate, None, [], [], {
                        "segments": 0, "segments_read": 0, "rows_read": 0, "complete": True})
            if cache[cache_key][1]:
                selected = cache[cache_key]
                break
        if selected:
            selected_rep, inst, header, rows, coverage = selected
            if selected_rep.get("access_type") == "ONE_TIME_SNAPSHOT":
                rows = _rows_for_day(header, rows, ctx["day"])
        else:
            selected_rep, inst, header, rows, coverage = rep, None, [], [], {
                "segments": 0, "segments_read": 0, "rows_read": 0, "complete": True}
        if not inst:
            out["metrics"][spec["key"]] = {"label": spec["label"], "value": None,
                                           "no_instance": True}
            continue
        agg = _aggregate_rows(header, rows, spec)
        if not coverage["complete"]:
            agg.update({"value": None, "incomplete": True})
        agg.update({"label": spec["label"], "report": spec["report"],
                    "as_of": (ctx["day"].isoformat()
                              if selected_rep.get("access_type") == "ONE_TIME_SNAPSHOT"
                              else inst["processing_date"]),
                    "instance_processing_date": inst["processing_date"],
                    "granularity": inst["granularity"],
                    **coverage, "access_type": selected_rep["access_type"]})
        out["metrics"][spec["key"]] = agg
        if not out["as_of"] or (agg["as_of"] or "") > out["as_of"]:
            out["as_of"] = agg["as_of"]
    got = {k: m for k, m in out["metrics"].items() if m.get("value") is not None}
    crashes, sessions = (got.get("crashes") or {}).get("value"), (got.get("sessions") or {}).get("value")
    crash_day = (got.get("crashes") or {}).get("as_of")
    session_day = (got.get("sessions") or {}).get("as_of")
    if crashes is not None and sessions and crash_day == session_day:
        out["derived"]["crashes_per_1k_sessions"] = crashes / sessions * 1000.0
        out["derived"]["crash_rate_as_of"] = crash_day
    elif crashes is not None or sessions is not None:
        out["derived"]["crash_rate_incomplete"] = "crashes and sessions do not share an instance date"
    installs, deletions = (got.get("installs") or {}).get("value"), (got.get("deletions") or {}).get("value")
    install_day = (got.get("installs") or {}).get("as_of")
    deletion_day = (got.get("deletions") or {}).get("as_of")
    if deletions is not None and installs and install_day == deletion_day:
        out["derived"]["deletion_ratio_pct"] = deletions / installs * 100.0
        out["derived"]["deletion_ratio_as_of"] = install_day
    elif deletions is not None or installs is not None:
        out["derived"]["deletion_ratio_incomplete"] = \
            "installs and deletions do not share an instance date"
    if not got:
        pending = [m for m in out["metrics"].values() if m.get("no_instance")]
        out["pending"] = ("registered, waiting for Apple's first report instance"
                          if pending else "no report instance carried a usable value column")
    return out


def collect_ios_perf(ctx, app):
    """Xcode-Organizer device metrics: hangs, launch, memory, disk, battery, terminations.

    Apple keys these by app version rather than by day, so the reading is "the current
    release against the releases before it", and a value only exists once enough opted-in
    devices have reported for that version.
    """
    cfg = ctx["cfg"]
    app_id = _ios_app_id(ctx, app)
    raw = src.asc_perf_power(ctx["transport"], ctx["creds"].apple_headers(), app_id)
    device = cfg["ios_perf_device"]
    series = src.asc_perf_series(raw, device)
    depth = cfg["ios_perf_baseline_versions"]
    metrics = {}
    for spec in cfg.get("ios_perf_metrics", []):
        entry = series.get((spec["category"], spec["metric"]))
        if not entry:
            continue
        pct = spec.get("percentile", "p90")
        points = entry["percentiles"].get(pct) or []
        if not points:
            continue
        latest = points[-1]
        prior = [p["value"] for p in points[-1 - depth:-1]]
        baseline = sum(prior) / len(prior) if prior else None
        devices = sorted(entry["devices"].get(pct) or [], key=lambda d: -(d["value"] or 0))
        metrics[spec["key"]] = {
            "label": spec.get("label", spec["key"]),
            "category": spec["category"], "metric": spec["metric"], "percentile": pct,
            "unit": entry["unit_label"] or entry["unit"],
            "value": latest["value"], "version": latest["version"],
            "baseline": baseline, "baseline_versions": [p["version"] for p in points[-1 - depth:-1]],
            "delta_pct": (None if not baseline
                          else (latest["value"] - baseline) / baseline * 100.0),
            "trail": [{"version": p["version"], "value": p["value"]} for p in points[-6:]],
            "worst_device": devices[0] if devices else None,
            "watch": spec.get("watch"), "alert": spec.get("alert"),
            "min_for_regression": spec.get("min_for_regression"),
        }
    seen = {}
    for m in metrics.values():
        if m.get("version"):
            seen[m["version"]] = seen.get(m["version"], 0) + 1
    version = max(seen.items(), key=lambda kv: kv[1])[0] if seen else None
    insights = src.asc_perf_insights(raw)
    return {"version": version, "device": device,
            "platform": (raw.get("productData") or [{}])[0].get("platform"),
            "metrics": metrics, "insights": insights,
            "regression_count": sum(1 for i in insights if i["direction"] == "regressions")}


def collect_play_vitals(ctx, app):
    cfg = ctx["cfg"]
    data = src.play_vitals(ctx["transport"], ctx["creds"].google_headers(), app["android"],
                           ctx["day"], cfg["play_vitals_sets"], cfg["vitals_trail_days"])
    mode = cfg["vitals_rate_is_fraction"]
    out = {"as_of": data["as_of"], "errors": data["errors"], "metrics": {}, "sets": {}, "worst_device": None}
    for key, block in data["sets"].items():
        pcts = {m: rate_to_pct(v, mode) for m, v in (block["overall"] or {}).items()
                if m != "distinctUsers"}
        users = (block["overall"] or {}).get("distinctUsers")
        trail = {}
        for day, metrics in (block["trail"] or {}).items():
            trail[day] = {m: rate_to_pct(v, mode) for m, v in metrics.items() if m != "distinctUsers"}
        breakdown = []
        for row in block["breakdown"] or []:
            raw_metrics = row.get("metrics") or {}
            metrics_pct = {
                m: (v if m == "distinctUsers" else rate_to_pct(v, mode))
                for m, v in raw_metrics.items()
            }
            breakdown.append({**row, "metrics_pct": metrics_pct})
        out["sets"][key] = {"as_of": block["as_of"], "pct": pcts, "users": users, "trail": trail,
                            "breakdown": breakdown, "freshness": block["freshness"]}
        for m, v in pcts.items():
            out["metrics"][m] = v
        if users:
            out.setdefault("users", 0)
            out["users"] = max(out["users"], int(users))
    return out


def collect_play_issues(ctx, app):
    return src.play_error_issues(ctx["transport"], ctx["creds"].google_headers(), app["android"],
                                 ctx["day"], trail_days=ctx["cfg"].get("issues_trail_days", 1),
                                 limit=ctx["cfg"].get("issues_limit", 8))


def collect_play_anomalies(ctx, app):
    return src.play_anomalies(ctx["transport"], ctx["creds"].google_headers(), app["android"],
                              limit=ctx["cfg"].get("anomalies_limit", 10))


def collect_play_reviews(ctx, app):
    items = src.play_reviews(ctx["transport"], ctx["creds"].google_headers(), app["android"],
                             max_results=ctx["cfg"].get("play_reviews_max", 100),
                             translation=ctx["cfg"].get("play_reviews_translation"))
    cutoff = ctx["window_start"]
    fresh = [r for r in items if (r.get("at") or "") >= cutoff]
    out = review_digest(fresh, ctx["cfg"], "play")
    out["backlog_unanswered"] = sum(1 for r in items if not r.get("answered"))
    out["scanned"] = len(items)
    out["window_start"] = cutoff
    return out


def _play_report_series(ctx, app, report_key):
    """Read one Play bulk CSV family into a {date: {key: value}} series.

    The current month plus the previous one are read (older first, so newer rows
    win) because a run early in a month still needs the 7-day baseline that lives
    in the previous month's file.
    """
    spec = (ctx["cfg"].get("play_reports") or {}).get(report_key)
    if not spec:
        raise RuntimeError(f"no play_reports['{report_key}'] spec in config")
    headers = ctx["creds"].google_headers()
    bucket = ctx["creds"].bucket
    day = ctx["day"]
    months = [month_token(day.replace(day=1) - dt.timedelta(days=1)), month_token(day)]
    listing = src.gcs_list(ctx["transport"], headers, bucket,
                           spec["dir"].format(package=app["android"]), limit=500)
    series, header, read = {}, [], []
    for month in months:
        name = spec["prefix_template"].format(package=app["android"], month=month)
        obj = next((i for i in listing if i["name"] == name), None)
        if obj is None:
            obj = src.report_object(listing, name.rsplit("_", 1)[0], month)
        if obj is None:
            continue
        text = src.gcs_get_text(ctx["transport"], headers, bucket, obj["name"])
        part, header = src.play_csv_series(text, spec.get("date_cols", ["Date"]), spec["values"])
        series.update(part)
        read.append(obj["name"].rsplit("/", 1)[-1])
    if not read:
        raise RuntimeError(f"no {report_key} report object found for {app['android']} "
                           f"in {'/'.join(months)}")
    return series, header


def collect_play_rating(ctx, app):
    series, _ = _play_report_series(ctx, app, "ratings")
    as_of = newest_series_day(series, ctx["day"].isoformat())
    latest = series.get(as_of, {}) if as_of else {}
    week_day = newest_series_day(series, (ctx["day"] - dt.timedelta(days=7)).isoformat())
    week = series.get(week_day, {}) if week_day else {}
    return {"as_of": as_of, "daily_avg": latest.get("daily_avg"), "total_avg": latest.get("total_avg"),
            "count": latest.get("count"), "week_ago_day": week_day,
            "week_ago_total_avg": week.get("total_avg"), "series": series}


def collect_play_store_perf(ctx, app):
    series, _ = _play_report_series(ctx, app, "store_performance")
    as_of = newest_series_day(series, ctx["day"].isoformat())
    cur = series.get(as_of, {}) if as_of else {}
    prior = [series[d] for d in sorted(series) if as_of and d < as_of][-7:]
    def conv(block):
        vis, acq = block.get("visitors"), block.get("acquisitions")
        return round(100.0 * acq / vis, 2) if vis and acq is not None else None
    base = [conv(b) for b in prior]
    base = [b for b in base if b is not None]
    return {"as_of": as_of, "visitors": cur.get("visitors"), "acquisitions": cur.get("acquisitions"),
            "conversion_pct": conv(cur),
            "baseline_conversion_pct": round(sum(base) / len(base), 2) if base else None}


def collect_play_installs(ctx, app):
    series, _ = _play_report_series(ctx, app, "installs")
    as_of = newest_series_day(series, ctx["day"].isoformat())
    cur = series.get(as_of, {}) if as_of else {}
    inst, uninst = cur.get("installs"), cur.get("uninstalls")
    return {"as_of": as_of, "installs": inst, "uninstalls": uninst,
            "active": cur.get("active"),
            "uninstall_ratio_pct": round(100.0 * uninst / inst, 1) if inst and uninst is not None else None}


COLLECTORS = {
    "ios_rating": collect_ios_rating,
    "ios_reviews": collect_ios_reviews,
    "ios_release": collect_ios_release,
    "ios_analytics": collect_ios_analytics,
    "ios_perf": collect_ios_perf,
    "play_vitals": collect_play_vitals,
    "play_issues": collect_play_issues,
    "play_anomalies": collect_play_anomalies,
    "play_reviews": collect_play_reviews,
    "play_rating": collect_play_rating,
    "play_store_perf": collect_play_store_perf,
    "play_installs": collect_play_installs,
}

PLATFORM_FIELD = {"ios": "ios", "play": "android"}


def collect_app(ctx, app, only=None):
    out = {"key": app["key"], "name": app["name"], "android": app.get("android"),
           "ios": app.get("ios"), "family": app.get("family"),
           "errors": {}, "skipped": {}, "slices": {}}
    for name, fn in COLLECTORS.items():
        if only and name not in only:
            continue
        if not slice_enabled(ctx["cfg"], app, name):
            continue
        platform = name.split("_")[0]
        if not app.get(PLATFORM_FIELD[platform]):
            out["skipped"][name] = f"no {platform} identifier configured"
            continue
        missing = ctx["creds"].missing_for(name)
        if missing:
            out["skipped"][name] = "; ".join(ctx["creds"].reasons.get(m, m) for m in missing)
            continue
        try:
            out["slices"][name] = fn(ctx, app)
        except (HttpError, AuthError) as exc:
            out["errors"][name] = safe_error(exc)
        except Exception as exc:  # a broken slice must not take the report down
            out["errors"][name] = safe_error(exc)
    out["ios_app_id"] = app.get("ios_app_id")
    return out


# ------------------------------------------------------------------ metrics

def _delta(cur, prev):
    if cur is None or prev is None:
        return None
    return round(cur - prev, 3)


def prior_reports(out_dir, slug, day, max_files=30, return_meta=False):
    """Disk-first history: every earlier run of this slug is a baseline candidate."""
    found, corrupt = [], []
    for path in sorted(glob.glob(os.path.join(out_dir, f"{slug}_*.json")), reverse=True):
        stamp = os.path.basename(path)[len(slug) + 1:-5]
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", stamp) or stamp >= day.isoformat():
            continue
        try:
            with open(path) as fh:
                found.append((stamp, json.load(fh)))
        except (OSError, ValueError) as exc:
            corrupt.append({"file": os.path.basename(path), "error": type(exc).__name__})
            continue
        if len(found) >= max_files:
            break
    return (found, {"corrupt_candidates": corrupt}) if return_meta else found


def _prior_app(history, key):
    for stamp, report in history:
        for app in report.get("apps", []):
            if app["key"] == key:
                return stamp, app
    return None, None


def _prior_app_at_or_before(history, key, limit_day):
    for stamp, report in history:
        if stamp > limit_day:
            continue
        for app in report.get("apps", []):
            if app["key"] == key:
                return stamp, app
    return None, None


def _rating_of(app_block, platform):
    s = (app_block or {}).get("slices", {})
    if platform == "ios":
        r = s.get("ios_rating") or {}
        return r.get("avg"), r.get("count")
    r = s.get("play_rating") or {}
    return r.get("total_avg"), r.get("count")


def attach_deltas(app_out, history, day):
    prev_stamp, prev = _prior_app(history, app_out["key"])
    week_limit = (day - dt.timedelta(days=6)).isoformat()
    w_stamp, week = _prior_app_at_or_before(history, app_out["key"], week_limit)
    app_out["baseline"] = {"prev_day": prev_stamp, "week": w_stamp}
    for platform in ("ios", "play"):
        cur_avg, cur_count = _rating_of(app_out, platform)
        p_avg, p_count = _rating_of(prev, platform)
        w_avg, _ = _rating_of(week, platform)
        app_out.setdefault("rating", {})[platform] = {
            "avg": cur_avg, "count": cur_count,
            "d_avg": _delta(cur_avg, p_avg), "d_count": _delta(cur_count, p_count),
            "d_avg_7d": _delta(cur_avg, w_avg),
        }
    attach_crash_deltas(app_out, prev, week)
    if not (app_out.get("crash_delta") or {}).get("versions"):
        for stamp, report in history:
            historical = next((a for a in report.get("apps", [])
                               if a.get("key") == app_out.get("key")
                               and (a.get("crash_delta") or {}).get("versions")), None)
            if historical:
                old = historical["crash_delta"]
                app_out["crash_delta"]["versions"] = old["versions"]
                app_out["crash_delta"]["between_versions"] = old.get("between_versions")
                app_out["crash_delta"]["versions_as_of"] = stamp
                break
    app_out["prior_status"] = (prev or {}).get("status")
    app_out["prior_status_by_store"] = (prev or {}).get("status_by_store") or {}
    return app_out


def _crash_rate_of(app_block, min_sessions):
    """Crash rate only when the sample behind it is large enough to compare."""
    an = ((app_block or {}).get("slices") or {}).get("ios_analytics") or {}
    sessions = ((an.get("metrics") or {}).get("sessions") or {}).get("value") or 0
    rate = (an.get("derived") or {}).get("crashes_per_1k_sessions")
    if rate is None or sessions < min_sessions:
        return None, sessions
    return rate, sessions


def _version_rates(app_block, order, min_sessions):
    """Per-version crash rate, newest release first, thin versions dropped.

    `order` is the App Store version list (newest first), which is the only reliable
    release ordering — version strings in this portfolio are not sortable ("01.14.53"
    against "15.54.30"), so they are ranked by Apple's own list, not parsed.
    """
    an = ((app_block or {}).get("slices") or {}).get("ios_analytics") or {}
    rank = {v: i for i, v in enumerate(order) if v}
    out = []
    for row in _analytics_version_rows(an):
        if row.get("crashes_per_1k") is None or (row.get("sessions") or 0) < min_sessions:
            continue
        # Without App Store release order, crash-volume order is not chronology. Suppress
        # the comparison rather than reversing "new" and "previous".
        if row["version"] not in rank:
            continue
        out.append({"version": row["version"], "rate": row["crashes_per_1k"],
                    "sessions": row["sessions"], "crashes": row.get("crashes"),
                    "rank": rank.get(row["version"])})
    out.sort(key=lambda r: (r["rank"] if r["rank"] is not None else 10**6))
    return out


def attach_crash_deltas(app_out, prev, week, min_sessions=None):
    """Attach the two crash-rate comparisons a reader actually asks for.

    Over time: today against the previous snapshot and against the ~week-old one, from the
    same disk baseline the ratings use. Between releases: the newest version against the one
    before it, inside today's instance. Both are omitted rather than guessed when either side
    is below the session floor — a rate over 40 sessions is noise, and a delta of noise is
    worse than no delta.
    """
    if min_sessions is None:
        min_sessions = (app_out.get("_min_sessions")
                        or DEFAULTS["thresholds"]["ios_crash_min_sessions"])
    cur, cur_sessions = _crash_rate_of(app_out, min_sessions)
    prev_rate, _ = _crash_rate_of(prev, min_sessions)
    week_rate, _ = _crash_rate_of(week, min_sessions)
    order = [v.get("version") for v in
             (((app_out.get("slices") or {}).get("ios_release") or {}).get("versions") or [])]
    versions = _version_rates(app_out, order, min_sessions)
    between = None
    if len(versions) >= 2:
        new, old = versions[0], versions[1]
        between = {"version": new["version"], "rate": new["rate"],
                   "prev_version": old["version"], "prev_rate": old["rate"],
                   "delta": new["rate"] - old["rate"],
                   "delta_pct": ((new["rate"] - old["rate"]) / old["rate"] * 100.0
                                 if old["rate"] else None)}
    app_out["crash_delta"] = {
        "rate": cur, "sessions": cur_sessions,
        "prev_rate": prev_rate, "d": _delta(cur, prev_rate),
        "week_rate": week_rate, "d_7d": _delta(cur, week_rate),
        "min_sessions": min_sessions,
        "versions": versions, "between_versions": between,
    }
    return app_out


def _worse(current, candidate):
    return candidate if STATUS_ORDER[candidate] > STATUS_ORDER[current] else current


STORE_LABEL = {"ios": "App Store", "play": "Google Play"}

# Every finding belongs to one of two reports: what the build does on devices, or what the
# user sees and says. The split is a property of the finding kind, declared once here, so a
# new kind cannot quietly land in both reports or in neither.
FINDING_NATURE = {
    "vitals": "technical", "issue": "technical", "anomaly": "technical",
    "perf": "technical", "perf_regression": "technical", "crash": "technical",
    "rating": "experience", "rating_floor": "experience", "reviews": "experience",
    "reviews_backlog": "experience", "conversion": "experience", "release": "experience",
}


def finding_nature(kind):
    return FINDING_NATURE.get(kind, "technical")


def _has_measured_value(block):
    """True only when a slice carried at least one real number.

    `ios_analytics` fills a metric entry per configured metric even while Apple has no
    instance yet, so the presence of the dict says nothing about whether data arrived.
    """
    return any(m.get("value") is not None
               for m in ((block or {}).get("metrics") or {}).values())


def _store_has_data(app_out, store):
    s = app_out["slices"]
    if store == "ios":
        return any([(app_out.get("rating", {}).get("ios") or {}).get("avg") is not None,
                    (s.get("ios_reviews") or {}).get("count"),
                    (s.get("ios_reviews") or {}).get("backlog_unanswered"),
                    _has_measured_value(s.get("ios_perf")),
                    _has_measured_value(s.get("ios_analytics"))])
    return any([(app_out.get("rating", {}).get("play") or {}).get("avg") is not None,
                (s.get("play_vitals") or {}).get("metrics"),
                (s.get("play_reviews") or {}).get("count"),
                (s.get("play_reviews") or {}).get("backlog_unanswered"),
                (s.get("play_store_perf") or {}).get("conversion_pct") is not None,
                (s.get("play_installs") or {}).get("installs") is not None,
                s.get("play_issues"), s.get("play_anomalies")])


def _nature_has_data(app_out, nature):
    """Did this app measure anything of that nature at all?

    Without this an app with no device metrics and no crash instance would read as
    technically healthy, which is a claim the data does not support.
    """
    s = app_out["slices"]
    if nature == "technical":
        return any([_has_measured_value(s.get("ios_perf")),
                    _has_measured_value(s.get("ios_analytics")),
                    (s.get("play_vitals") or {}).get("metrics"),
                    s.get("play_issues"), s.get("play_anomalies")])
    return any([(app_out.get("rating", {}).get("ios") or {}).get("avg") is not None,
                (app_out.get("rating", {}).get("play") or {}).get("avg") is not None,
                (s.get("ios_reviews") or {}).get("count"),
                (s.get("ios_reviews") or {}).get("backlog_unanswered"),
                (s.get("play_reviews") or {}).get("count"),
                (s.get("play_store_perf") or {}).get("conversion_pct") is not None])


def score_app(app_out, cfg):
    """Attach findings, a per-store status, and the app-wide worst-of status.

    Every finding carries the store it belongs to, because the report is delivered as one
    message per store: a Play crash rate must not colour the App Store verdict.
    """
    th = cfg["thresholds"]
    att = []
    s = app_out["slices"]

    for store in ("ios", "play"):
        r = app_out.get("rating", {}).get(store) or {}
        d1, d7, avg = r.get("d_avg"), r.get("d_avg_7d"), r.get("avg")
        if avg is None:
            continue
        sev = None
        if d1 is not None and d1 <= -th["rating_drop_alert"]:
            sev = "degraded"
        elif d7 is not None and d7 <= -th["rating_drop_7d_alert"]:
            sev = "degraded"
        elif (d1 is not None and d1 <= -th["rating_drop_watch"]) or \
             (d7 is not None and d7 <= -th["rating_drop_7d_watch"]):
            sev = "watch"
        if sev:
            moves = []
            if d1 is not None:
                moves.append(f"{d1:+.2f} d/d")
            if d7 is not None:
                moves.append(f"{d7:+.2f} 7d")
            att.append({"sev": sev, "kind": "rating", "store": store,
                        "text": f"rating {avg:.2f}★ — {', '.join(moves)}"})
        count = r.get("count") or 0
        if count >= th["rating_floor_min_count"]:
            floor_sev = ("degraded" if avg < th["rating_floor_alert"]
                         else "watch" if avg < th["rating_floor_watch"] else None)
            if floor_sev:
                bar = th["rating_floor_watch" if floor_sev == "watch" else "rating_floor_alert"]
                att.append({"sev": floor_sev, "kind": "rating_floor", "store": store,
                            "text": f"rating is {avg:.2f}★ over {fmt_int(count)} ratings"
                                    f" (below the {bar:.1f}★ floor)"})
        elif count and avg < th["rating_floor_watch"]:
            att.append({"sev": "watch", "kind": "rating_floor", "store": store,
                        "text": f"rating {avg:.2f}★ on only {count} ratings"
                                " — low sample, but nothing better is on the listing"})

    vit = s.get("play_vitals") or {}
    users = vit.get("users") or 0
    for metric, bar_key, name in (("userPerceivedCrashRate", "play_crash_alert_pct", "user-perceived crash rate"),
                                  ("userPerceivedAnrRate", "play_anr_alert_pct", "user-perceived ANR rate")):
        pct = (vit.get("metrics") or {}).get(metric)
        if pct is None:
            continue
        bar = th[bar_key]
        if users and users < th["min_vitals_users"]:
            # Too few Android users for the rate to mean anything. That makes the vitals
            # slice low-data — it must not drag an app whose other signals are fine.
            app_out.setdefault("low_data", [])
            if "play_vitals" not in app_out["low_data"]:
                app_out["low_data"].append("play_vitals")
            continue
        if pct >= bar:
            att.append({"sev": "degraded", "kind": "vitals", "store": "play",
                        "text": f"{name} {pct:.2f}% ≥ {bar:.2f}% Google bad-behaviour bar"})
        elif pct >= bar * th["watch_fraction"]:
            att.append({"sev": "watch", "kind": "vitals", "store": "play",
                        "text": f"{name} {pct:.2f}% ({pct / bar * 100:.0f}% of the {bar:.2f}% bar)"})

    for set_key, metric in (("crash", "userPerceivedCrashRate"), ("anr", "userPerceivedAnrRate")):
        for row in ((vit.get("sets") or {}).get(set_key) or {}).get("breakdown", []) or []:
            pct = rate_to_pct((row.get("metrics") or {}).get(metric), cfg["vitals_rate_is_fraction"])
            if pct is not None and pct >= th["play_device_alert_pct"]:
                dim = ", ".join(f"{k}={v}" for k, v in (row.get("dims") or {}).items())
                att.append({"sev": "degraded", "kind": "vitals", "store": "play",
                            "text": f"{metric} {pct:.1f}% on {dim} "
                                    f"(≥{th['play_device_alert_pct']:.0f}% single-slice bar)"})

    for key, store in (("ios_reviews", "ios"), ("play_reviews", "play")):
        rv = s.get(key) or {}
        share, count = rv.get("neg_share_pct"), rv.get("neg_count") or 0
        if share is not None and count >= th["neg_min_count"]:
            sev = ("degraded" if share >= th["neg_share_alert_pct"]
                   else "watch" if share >= th["neg_share_watch_pct"] else None)
            if sev:
                topics = ", ".join(list(rv.get("topics", {}))[:3])
                att.append({"sev": sev, "kind": "reviews", "store": store,
                            "text": f"{count}/{rv['count']} fresh reviews ≤2★ ({share:.0f}%)"
                                    + (f" — {topics}" if topics else "")})
        backlog = rv.get("backlog_unanswered") or 0
        if backlog >= th["unanswered_backlog_watch"]:
            scanned = rv.get("scanned") or 0
            # only claim a scan window when the page cap was actually hit — otherwise the
            # number is the whole review history the API returned.
            qualifier = (f" of the {scanned} most recent" if scanned >= 200
                         else " — every review it has" if scanned and backlog == scanned else "")
            att.append({"sev": "watch", "kind": "reviews_backlog", "store": store,
                        "text": f"{backlog} unanswered reviews{qualifier}"})

    perf = s.get("play_store_perf") or {}
    cur, base = perf.get("conversion_pct"), perf.get("baseline_conversion_pct")
    if cur is not None and base:
        drop = (base - cur) / base * 100.0
        sev = ("degraded" if drop >= th["conversion_drop_alert_pct"]
               else "watch" if drop >= th["conversion_drop_watch_pct"] else None)
        if sev:
            att.append({"sev": sev, "kind": "conversion", "store": "play",
                        "text": f"store conversion {cur:.1f}% vs {base:.1f}% baseline ({drop:.0f}% down)"})

    an = s.get("ios_analytics") or {}
    per_1k = (an.get("derived") or {}).get("crashes_per_1k_sessions")
    sessions = ((an.get("metrics") or {}).get("sessions") or {}).get("value") or 0
    if per_1k is not None and sessions >= th["ios_crash_min_sessions"]:
        sev = ("degraded" if per_1k >= th["ios_crash_per_1k_alert"]
               else "watch" if per_1k >= th["ios_crash_per_1k_watch"] else None)
        if sev:
            bar = th["ios_crash_per_1k_alert" if sev == "degraded" else "ios_crash_per_1k_watch"]
            att.append({"sev": sev, "kind": "crash", "store": "ios",
                        "text": f"{per_1k:.2f} crashes per 1k sessions on {an.get('as_of')}"
                                f" (bar {bar:.2f}) — {fmt_int(sessions)} sessions"})
    elif per_1k is not None:
        app_out.setdefault("low_data", [])
        if "ios_analytics" not in app_out["low_data"]:
            app_out["low_data"].append("ios_analytics")

    perf = s.get("ios_perf") or {}
    regressed, over_bar = [], []
    for m in (perf.get("metrics") or {}).values():
        value, watch, alert = m.get("value"), m.get("watch"), m.get("alert")
        if value is None:
            continue
        sev = ("degraded" if alert is not None and value >= alert
               else "watch" if watch is not None and value >= watch else None)
        if sev:
            bar = alert if sev == "degraded" else watch
            over_bar.append((value / bar, sev, bar, m))
            continue
        # A regression is a finding on its own: peak memory has no absolute bar, but a
        # release that moved it 50% against the previous versions still needs an owner.
        delta, floor = m.get("delta_pct"), m.get("min_for_regression")
        if delta is None or (floor is not None and value < floor):
            continue
        if delta >= th["perf_regression_watch_pct"]:
            regressed.append((delta, m))
    # One unhealthy build can breach five bars at once. The attention list is a portfolio
    # view, so keep the two worst per app and let the device table carry the rest.
    over_bar.sort(reverse=True, key=lambda o: (STATUS_ORDER[o[1]], o[0]))
    keep = th.get("perf_findings_per_app", 2)
    for i, (_, sev, bar, m) in enumerate(over_bar[:keep]):
        extra = ""
        if i == keep - 1 and len(over_bar) > keep:
            extra = f" (+{len(over_bar) - keep} more over bar)"
        att.append({"sev": sev, "kind": "perf", "store": "ios",
                    "text": f"{m['label']} {fmt_perf(m['value'], m['unit'])} on v{m['version']}"
                            f" ({m['percentile']}, bar {fmt_perf(bar, m['unit'])}){extra}"})
    if regressed:
        regressed.sort(reverse=True, key=lambda r: r[0])
        by_version = {}
        for delta, m in regressed:
            by_version.setdefault(m.get("version"), []).append((delta, m))
        for version, group in by_version.items():
            worst = group[0][0]
            sev = "degraded" if worst >= th["perf_regression_alert_pct"] else "watch"
            detail = ", ".join(f"{m['label']} {fmt_perf(m['value'], m['unit'])} ({d:+.0f}%)"
                               for d, m in group[:3])
            depth = len(group[0][1].get("baseline_versions") or [])
            att.append({"sev": sev, "kind": "perf_regression", "store": "ios",
                        "text": f"v{version} regressed against the previous {depth} "
                                f"version{'s' if depth != 1 else ''} — {detail}"})

    rel = s.get("ios_release") or {}
    state = ((rel.get("current") or {}).get("state") or "").upper()
    if any(bad in state for bad in ("REJECT", "INVALID", "REMOVED")):
        att.append({"sev": "degraded", "kind": "release", "store": "ios",
                    "text": f"version {(rel.get('current') or {}).get('version')} is {state}"})
    elif rel.get("phased") and (rel["phased"].get("state") or "").upper() in ("ACTIVE", "PAUSED"):
        ph = rel["phased"]
        att.append({"sev": "watch", "kind": "release", "store": "ios",
                    "text": f"phased release {ph.get('state','').lower()} day {ph.get('day')}"})

    for an in (s.get("play_anomalies") or [])[:3]:
        att.append({"sev": "watch", "kind": "anomaly", "store": "play",
                    "text": f"Google flagged an anomaly in {an.get('metric') or an.get('metric_set')}"
                            + (f" ({an['day']})" if an.get("day") else "")})

    top = sorted((s.get("play_issues") or []), key=lambda i: -(i.get("users_pct") or 0))
    if top and (top[0].get("users_pct") or 0) > 0:
        it = top[0]
        app_out["top_issue"] = it
        if it.get("users_pct", 0) >= th.get("issue_reach_watch_pct", 1.0):
            att.append({"sev": "watch", "kind": "issue", "store": "play",
                        "text": f"{it.get('type','issue')} {it.get('cause') or it.get('location') or ''}"
                                f" — {it['users_pct']:.2f}% of users"})

    by_store = {}
    for store in ("ios", "play"):
        status = "healthy"
        for a in att:
            if a["store"] == store:
                status = _worse(status, a["sev"])
        # "no measurable signal" is a fallback, never an override: an app with no ratings can
        # still have a finding worth the top of the digest — a rejected release, for instance.
        if status == "healthy" and not _store_has_data(app_out, store):
            status = "nodata"
        by_store[store] = status

    by_nature = {}
    for nature in ("technical", "experience"):
        status = "healthy"
        measured = False
        for a in att:
            if a.get("nature", finding_nature(a["kind"])) == nature:
                status = _worse(status, a["sev"])
                measured = True
        if status == "healthy" and not measured and not _nature_has_data(app_out, nature):
            status = "nodata"
        by_nature[nature] = status
    app_out["status_by_nature"] = by_nature
    app_out["status_by_store"] = by_store
    app_out["status"] = ("nodata" if all(v == "nodata" for v in by_store.values())
                         else max((v for v in by_store.values() if v != "nodata"),
                                  key=lambda v: STATUS_ORDER[v]))
    for a in att:
        a.setdefault("nature", finding_nature(a["kind"]))
    app_out["attention"] = sorted(att, key=lambda a: STATUS_ORDER[a["sev"]], reverse=True)
    return app_out


def _median(xs):
    xs = sorted(xs)
    if not xs:
        return None
    mid = len(xs) // 2
    return xs[mid] if len(xs) % 2 else (xs[mid - 1] + xs[mid]) / 2


def build_tech_summary(apps, thresholds=None):
    """Portfolio roll-up of the iOS technical slices (device metrics + App Analytics).

    Kept separate from the store roll-up because it answers a different question: not
    "how does the listing look" but "what are our builds doing on real devices".
    """
    thresholds = thresholds or DEFAULTS["thresholds"]
    regression_watch = thresholds["perf_regression_watch_pct"]
    worst, regressions, crash_1k = {}, [], []
    perf_apps = analytics_apps = 0
    pending, unmapped = [], []
    versions = {}
    for a in apps:
        perf = a["slices"].get("ios_perf") or {}
        metrics = perf.get("metrics") or {}
        if metrics:
            perf_apps += 1
            versions[a["name"]] = perf.get("version")
        for key, m in metrics.items():
            if m.get("value") is None:
                continue
            cur = worst.get(key)
            if not cur or m["value"] > cur["value"]:
                worst[key] = {"value": m["value"], "unit": m["unit"], "label": m["label"],
                              "app": a["name"], "version": m.get("version"),
                              "percentile": m.get("percentile"),
                              "watch": m.get("watch"), "alert": m.get("alert")}
            delta, floor = m.get("delta_pct"), m.get("min_for_regression")
            if delta is not None and delta >= regression_watch and not (
                    floor is not None and m["value"] < floor):
                regressions.append({"app": a["name"], "label": m["label"], "delta_pct": delta,
                                    "value": m["value"], "unit": m["unit"],
                                    "version": m.get("version")})
        an = a["slices"].get("ios_analytics") or {}
        if (an.get("metrics") or {}) and any(m.get("value") is not None
                                             for m in an["metrics"].values()):
            analytics_apps += 1
        per_1k = (an.get("derived") or {}).get("crashes_per_1k_sessions")
        if per_1k is not None:
            crash_1k.append({"app": a["name"], "value": per_1k, "as_of": an.get("as_of")})
        if an.get("pending"):
            pending.append({"app": a["name"], "text": an["pending"]})
        for key, m in (an.get("metrics") or {}).items():
            if m.get("unmapped"):
                unmapped.append({"app": a["name"], "metric": key,
                                 "looked_for": m["unmapped"], "header": m.get("header")})
    regressions.sort(key=lambda r: -r["delta_pct"])
    crash_1k.sort(key=lambda c: -c["value"])
    return {"perf_apps": perf_apps, "analytics_apps": analytics_apps,
            "worst": worst, "regressions": regressions, "crash_1k": crash_1k,
            "crash_1k_median": _median([c["value"] for c in crash_1k]),
            "pending": pending, "unmapped": unmapped[:5], "versions": versions,
            **build_core_metrics(apps)}


CORE_KEYS = ("crashes", "sessions", "installs", "deletions")


def build_core_metrics(apps):
    """Portfolio totals and the per-version rows behind them.

    This is the panel a reader looks at first — how many crashes, over how many sessions,
    on which build — so it is computed once here and rendered into every output.
    """
    totals, measured, dates = dict.fromkeys(CORE_KEYS, 0.0), set(), set()
    crash_components, install_components = [], []
    version_rows = []
    for a in apps:
        an = a["slices"].get("ios_analytics") or {}
        metrics = an.get("metrics") or {}
        for key in CORE_KEYS:
            metric = metrics.get(key) or {}
            value = metric.get("value")
            if value is not None:
                totals[key] += value
                measured.add(key)
                metric_day = metric.get("as_of") or an.get("as_of")
                if metric_day:
                    dates.add(metric_day)
        crashes, sessions = metrics.get("crashes") or {}, metrics.get("sessions") or {}
        crash_day = crashes.get("as_of") or an.get("as_of")
        session_day = sessions.get("as_of") or an.get("as_of")
        if (crashes.get("value") is not None and sessions.get("value") is not None
                and crash_day and crash_day == session_day):
            crash_components.append({"app": a["name"], "as_of": crash_day,
                                     "crashes": crashes["value"],
                                     "sessions": sessions["value"]})
        installs, deletions = metrics.get("installs") or {}, metrics.get("deletions") or {}
        install_day = installs.get("as_of") or an.get("as_of")
        deletion_day = deletions.get("as_of") or an.get("as_of")
        if (installs.get("value") is not None and deletions.get("value") is not None
                and install_day and install_day == deletion_day):
            install_components.append({"app": a["name"], "as_of": install_day,
                                       "installs": installs["value"],
                                       "deletions": deletions["value"]})
        delta = a.get("crash_delta") or {}
        between = delta.get("between_versions") or {}
        for row in _analytics_version_rows(an):
            enriched = dict(row, app=a["name"])
            if row["version"] == between.get("version"):
                enriched.update(prev_version=between["prev_version"],
                                delta=between["delta"], delta_pct=between.get("delta_pct"))
            if row["version"] == (a["slices"].get("ios_perf") or {}).get("version") or \
                    row["version"] == ((a["slices"].get("ios_release") or {}).get("current")
                                       or {}).get("version"):
                enriched.update(d_crashes_per_1k=delta.get("d"),
                                d_crashes_per_1k_7d=delta.get("d_7d"))
            version_rows.append(enriched)
    crash_day = max((c["as_of"] for c in crash_components), default=None)
    install_day = max((c["as_of"] for c in install_components), default=None)
    crash_apps = [c for c in crash_components if c["as_of"] == crash_day]
    install_apps = [c for c in install_components if c["as_of"] == install_day]
    crash_numerator = sum(c["crashes"] for c in crash_apps)
    crash_denominator = sum(c["sessions"] for c in crash_apps)
    install_numerator = sum(c["installs"] for c in install_apps)
    install_denominator = sum(c["deletions"] for c in install_apps)
    raw_totals = {k: (totals[k] if k in measured else None) for k in CORE_KEYS}
    # The headline is a coherent population, not four independently available totals.
    core = {"crashes": crash_numerator if crash_apps else None,
            "sessions": crash_denominator if crash_apps else None,
            "installs": install_numerator if install_apps else None,
            "deletions": install_denominator if install_apps else None,
            "raw_component_totals": raw_totals}
    core["crashes_per_1k"] = (crash_numerator / crash_denominator * 1000.0
                              if crash_denominator else None)
    core["net_installs"] = (install_numerator - install_denominator
                            if install_apps else None)
    core["as_of"] = next(iter(dates)) if len(dates) == 1 else None
    core["date_range"] = ([min(dates), max(dates)] if dates else [])
    core["crash_rate_population"] = {"apps": len(crash_apps),
                                     "expected_apps": len(apps),
                                     "components": crash_apps,
                                     "as_of": crash_day,
                                     "excluded_other_dates": len(crash_components) - len(crash_apps),
                                     "crashes": crash_numerator,
                                     "sessions": crash_denominator}
    core["net_installs_population"] = {"apps": len(install_apps),
                                       "expected_apps": len(apps),
                                       "components": install_apps,
                                       "as_of": install_day,
                                       "excluded_other_dates": len(install_components) - len(install_apps),
                                       "installs": install_numerator,
                                       "deletions": install_denominator}
    version_rows.sort(key=lambda r: -(r.get("crashes") or r.get("sessions") or 0))
    return {"core": core, "version_rows": version_rows}


def attach_core_deltas(tech, history, day):
    """Portfolio crash-rate movement, read from the earlier snapshots' own totals.

    Summing per-app rates would be wrong (a rate is not additive), so the comparison uses
    the stored portfolio totals of the previous run and of the newest run at least a week
    old — the same disk baseline the ratings use.
    """
    core = tech.get("core") or {}
    week_limit = (day - dt.timedelta(days=6)).isoformat()

    def rate_at(report):
        return ((report.get("tech_summary") or {}).get("core") or {}).get("crashes_per_1k")

    prev = next(((stamp, rate_at(r)) for stamp, r in history if rate_at(r) is not None),
                (None, None))
    week = next(((stamp, rate_at(r)) for stamp, r in history
                 if stamp <= week_limit and rate_at(r) is not None), (None, None))
    core["prev_crashes_per_1k"], core["prev_day"] = prev[1], prev[0]
    core["week_crashes_per_1k"], core["week_day"] = week[1], week[0]
    core["d_crashes_per_1k"] = _delta(core.get("crashes_per_1k"), prev[1])
    core["d_crashes_per_1k_7d"] = _delta(core.get("crashes_per_1k"), week[1])
    return tech


def build_store_summary(apps, store):
    """Portfolio roll-up for one store: what a reader needs before the per-app list."""
    rated, ratings_total, movers = [], 0, []
    reviews_new = reviews_neg = backlog = 0
    topics, backlog_by_app, states = {}, [], {}
    crash, anr, conv, installs, uninstalls = [], [], [], 0, 0
    review_key = "ios_reviews" if store == "ios" else "play_reviews"
    for a in apps:
        r = (a.get("rating") or {}).get(store) or {}
        if r.get("avg") is not None:
            rated.append((r["avg"], a["name"], r.get("count") or 0))
            ratings_total += r.get("count") or 0
            if r.get("d_avg"):
                movers.append((abs(r["d_avg"]), f"{a['name']} {r['d_avg']:+.2f}"))
        rv = a["slices"].get(review_key) or {}
        reviews_new += rv.get("count") or 0
        reviews_neg += rv.get("neg_count") or 0
        if rv.get("backlog_unanswered"):
            backlog += rv["backlog_unanswered"]
            backlog_by_app.append((rv["backlog_unanswered"], a["name"]))
        for k, v in (rv.get("topics") or {}).items():
            topics[k] = topics.get(k, 0) + v
        if store == "ios":
            cur = ((a["slices"].get("ios_release") or {}).get("current")) or {}
            st = (cur.get("state") or "").upper()
            if st:
                bucket = ("rejected" if any(b in st for b in ("REJECT", "INVALID", "REMOVED"))
                          else "live" if "READY" in st or "AVAILABLE" in st else "pre-release")
                states[bucket] = states.get(bucket, 0) + 1
        else:
            m = (a["slices"].get("play_vitals") or {}).get("metrics") or {}
            if m.get("userPerceivedCrashRate") is not None:
                crash.append((m["userPerceivedCrashRate"], a["name"]))
            if m.get("userPerceivedAnrRate") is not None:
                anr.append((m["userPerceivedAnrRate"], a["name"]))
            perf = a["slices"].get("play_store_perf") or {}
            if perf.get("conversion_pct") is not None:
                conv.append((perf["conversion_pct"], a["name"]))
            inst = a["slices"].get("play_installs") or {}
            installs += inst.get("installs") or 0
            uninstalls += inst.get("uninstalls") or 0
    movers.sort(reverse=True)
    backlog_by_app.sort(reverse=True)
    return {
        "store": store,
        "apps_total": len(apps),
        "apps_rated": len(rated),
        "ratings_total": ratings_total,
        "rating_min": min(rated)[0] if rated else None,
        "rating_max": max(rated)[0] if rated else None,
        "rating_median": _median([r[0] for r in rated]),
        "worst_app": min(rated)[1] if rated else None,
        "movers": [m[1] for m in movers[:5]],
        "reviews_new": reviews_new,
        "reviews_neg": reviews_neg,
        "topics": dict(sorted(topics.items(), key=lambda kv: -kv[1])),
        "backlog": backlog,
        "backlog_by_app": [f"{n} {c}" for c, n in backlog_by_app[:5]],
        "release_states": states,
        "worst_crash": max(crash)[0] if crash else None,
        "worst_crash_app": max(crash)[1] if crash else None,
        "worst_anr": max(anr)[0] if anr else None,
        "worst_anr_app": max(anr)[1] if anr else None,
        "conversion_median": _median([c[0] for c in conv]),
        "installs": installs or None,
        "uninstalls": uninstalls or None,
    }


def slice_state_delivery_safe(slice_state, corrupt_candidates=None):
    return (not (corrupt_candidates or []) and all(
        state["failed"] == 0
        and state["ok"] + state.get("skipped_count", 0) == state["expected"]
        for state in slice_state.values()))


def build_report(cfg, creds, transport, day, out_dir, slug, only=None, app_filter=None):
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    apps_cfg = [a for a in cfg["apps"] if not app_filter or a["key"] in app_filter]
    window_days = cfg.get("review_window_days", 1)
    ctx = {"cfg": cfg, "creds": creds, "transport": transport, "day": day, "now": now,
           "window_start": (day - dt.timedelta(days=window_days)).isoformat(),
           "prev_window_start": (day - dt.timedelta(days=window_days * 2)).isoformat()}
    history, baseline_meta = prior_reports(out_dir, slug, day, return_meta=True)
    results = {}
    with ThreadPoolExecutor(max_workers=cfg["max_workers"]) as ex:
        futs = {a["key"]: ex.submit(collect_app, ctx, a, only) for a in apps_cfg}
        for key, fut in futs.items():
            try:
                results[key] = fut.result()
            except Exception as exc:
                results[key] = {"key": key, "name": key, "slices": {}, "skipped": {},
                                "errors": {"*": f"{type(exc).__name__}: {str(exc)[:180]}"}}
    apps = []
    for a in apps_cfg:
        block = results[a["key"]]
        block["_min_sessions"] = cfg["thresholds"]["ios_crash_min_sessions"]
        attach_deltas(block, history, day)
        block.pop("_min_sessions", None)
        score_app(block, cfg)
        apps.append(block)

    PRE_RELEASE = ("PREPARE_FOR_SUBMISSION", "WAITING_FOR_REVIEW", "IN_REVIEW",
                   "PENDING_DEVELOPER_RELEASE", "PROCESSING_FOR_DISTRIBUTION",
                   "READY_FOR_REVIEW", "WAITING_FOR_EXPORT_COMPLIANCE")
    coverage = []
    for a in apps:
        ios = a["slices"].get("ios_rating") or {}
        if not (a.get("ios") and ios and not ios.get("listed")):
            continue
        cur = ((a["slices"].get("ios_release") or {}).get("current")) or {}
        state = (cur.get("state") or "").upper()
        if any(bad in state for bad in ("REJECT", "INVALID", "REMOVED")):
            why = f"listing is down — version {cur.get('version')} is {state}"
        elif state in PRE_RELEASE:
            why = f"not on the store yet — version {cur.get('version')} is {state}"
        elif state:
            why = f"no listing on this storefront while the version reads {state}"
        else:
            why = "configured bundle id is not on the App Store"
        coverage.append({"app": a["name"], "store": "App Store", "id": a["ios"],
                         "state": state or None, "text": why})
    order = {"degraded": 0, "watch": 1, "healthy": 2, "nodata": 3}
    apps.sort(key=lambda a: (order[a["status"]], -((a.get("rating", {}).get("ios") or {}).get("count") or 0)))
    scored = [a for a in apps if a["status"] != "nodata"]
    overall = "healthy"
    for a in scored:
        overall = _worse(overall, a["status"])
    overall_by_nature = {}
    for nature in ("technical", "experience"):
        worst, seen = "healthy", False
        for a in apps:
            st = (a.get("status_by_nature") or {}).get(nature, "nodata")
            if st == "nodata":
                continue
            seen = True
            worst = _worse(worst, st)
        overall_by_nature[nature] = worst if seen else "nodata"
    overall_by_store = {}
    for store in ("ios", "play"):
        worst = "healthy"
        seen = False
        for a in apps:
            st = (a.get("status_by_store") or {}).get(store, "nodata")
            if st == "nodata":
                continue
            seen = True
            worst = _worse(worst, st)
        overall_by_store[store] = worst if seen else "nodata"
    store_summaries = {st: build_store_summary(apps, st) for st in ("ios", "play")}
    tech_summary = attach_core_deltas(build_tech_summary(apps, cfg["thresholds"]), history, day)
    slice_state = {}
    for name in SLICE_NEEDS:
        ok = sum(1 for a in apps if name in a["slices"])
        failed = sum(1 for a in apps if name in a["errors"])
        skipped = {a["skipped"][name] for a in apps if name in a["skipped"]}
        skipped_count = sum(1 for a in apps if name in a["skipped"])
        expected = sum(1 for app in apps_cfg if slice_enabled(cfg, app, name))
        if expected or ok or failed or skipped:
            slice_state[name] = {"ok": ok, "failed": failed,
                                 "skipped": sorted(skipped)[:1][0] if skipped else None,
                                 "skipped_count": skipped_count, "expected": expected,
                                 "complete": ok == expected}
    experience_slices = {"ios_rating", "ios_reviews", "ios_release", "play_reviews",
                         "play_rating", "play_store_perf", "play_installs"}
    for name, state in slice_state.items():
        if state["complete"]:
            continue
        nature = "experience" if name in experience_slices else "technical"
        coverage_status = "degraded" if state["failed"] else "watch"
        overall_by_nature[nature] = _worse(overall_by_nature[nature], coverage_status)
        overall = _worse(overall, coverage_status)
        store = "ios" if name.startswith("ios") else "play"
        overall_by_store[store] = _worse(overall_by_store[store], coverage_status)
    trust_complete = (not baseline_meta["corrupt_candidates"]
                      and all(state["complete"] for state in slice_state.values()))
    # A configured source that is explicitly unavailable (no credential or no platform id)
    # is an honest coverage gap, not a failed measurement. It may be delivered as an explicit
    # `✕`; provider/query failures and unaccounted rows remain unsafe and block publication.
    delivery_safe = slice_state_delivery_safe(
        slice_state, baseline_meta["corrupt_candidates"])
    if baseline_meta["corrupt_candidates"]:
        overall = _worse(overall, "watch")
        for nature in overall_by_nature:
            overall_by_nature[nature] = _worse(overall_by_nature[nature], "watch")
    return {
        "kind": "store",
        "mode": cfg.get("mode", "daily"),
        "review_window_days": window_days,
        "slug": slug,
        "brand": cfg["brand"],
        "report_day": day.isoformat(),
        "generated_utc": now,
        "overall_status": overall,
        "apps": apps,
        "attention": [dict(a, app=app["name"]) for app in apps for a in app["attention"]],
        "slice_state": slice_state,
        "coverage_gaps": coverage,
        "overall_by_store": overall_by_store,
        "overall_by_nature": overall_by_nature,
        "store_summaries": store_summaries,
        "tech_summary": tech_summary,
        "baseline_reports": [h[0] for h in history[:3]],
        "credential_state": {k: (True if creds.has(k) else creds.reasons.get(k, "unavailable"))
                             for k in ("google", "apple", "bucket")},
        "trust": {"complete": trust_complete, "delivery_safe": delivery_safe,
                  "expected_apps": len(apps_cfg),
                  "collected_apps": len(apps), **baseline_meta},
    }


# ------------------------------------------------------------------ render

def fmt_int(n):
    if n is None:
        return "—"
    n = int(n)
    return f"{n/1_000_000:.1f}M" if n >= 1_000_000 else (f"{n/1_000:.0f}k" if n >= 10_000 else f"{n:,}")


def fmt_perf(value, unit=None):
    """Device metrics arrive with Apple's own unit, and range from 0.02 to 3000."""
    if value is None:
        return "—"
    if abs(value) >= 100:
        out = f"{value:,.0f}"
    elif abs(value) >= 10:
        out = f"{value:.1f}"
    else:
        out = f"{value:.2f}"
    return f"{out} {unit}" if unit else out


def star(avg, delta=None, d7=None):
    if avg is None:
        return "—"
    out = f"{avg:.2f}★"
    if delta:
        out += f" ({delta:+.2f})"
    elif d7:
        out += f" ({d7:+.2f} 7d)"
    return out


def _rating_line(app):
    parts = []
    for platform, label in (("ios", "iOS"), ("play", "Play")):
        r = (app.get("rating") or {}).get(platform) or {}
        if r.get("avg") is None:
            continue
        seg = f"{label} {star(r['avg'], r.get('d_avg'), r.get('d_avg_7d'))}"
        if r.get("count") is not None:
            seg += f" · {fmt_int(r['count'])} ratings"
            if r.get("d_count"):
                seg += f" ({r['d_count']:+.0f})"
        parts.append(seg)
    return " | ".join(parts)


def _vitals_line(app):
    vit = app["slices"].get("play_vitals") or {}
    m = vit.get("metrics") or {}
    bits = []
    if m.get("userPerceivedCrashRate") is not None:
        bits.append(f"crash {m['userPerceivedCrashRate']:.2f}%")
    if m.get("userPerceivedAnrRate") is not None:
        bits.append(f"ANR {m['userPerceivedAnrRate']:.2f}%")
    if vit.get("users"):
        bits.append(f"{fmt_int(vit['users'])} users")
    if vit.get("as_of"):
        bits.append(f"as of {vit['as_of']}")
    return " · ".join(bits)


def _reviews_line(app):
    bits = []
    for key, label in (("ios_reviews", "iOS"), ("play_reviews", "Play")):
        rv = app["slices"].get(key) or {}
        if not rv:
            continue
        if not rv.get("count") and not rv.get("backlog_unanswered"):
            continue
        seg = f"{label} {rv.get('count', 0)} new"
        if rv.get("neg_count"):
            seg += f", {rv['neg_count']}≤2★"
        if rv.get("backlog_unanswered"):
            seg += f", {rv['backlog_unanswered']} unanswered"
        bits.append(seg)
    return " | ".join(bits)


def split_skips(app, report):
    """Separate app-specific skips from the global credential gap already in the header."""
    pending = {v for v in report["credential_state"].values() if v is not True}
    cred, local = [], []
    for name, reason in (app.get("skipped") or {}).items():
        (cred if any(reason.startswith(pv[:30]) for pv in pending) else local).append((name, reason))
    return cred, local


def render_slack(report):
    b = report["brand"]
    lines = [f"*{b['org']} {b['product']} — stores, {report['report_day']}*  "
             f"{ICON[report['overall_status']]} *{STATUS_LABEL[report['overall_status']]}*",
             f"_{len(report['apps'])} apps · generated {report['generated_utc']}_"]
    unavailable = [f"{k} ({v})" for k, v in report["credential_state"].items() if v is not True]
    if unavailable:
        lines.append(f"_credentials pending: {'; '.join(unavailable)}_")
    att = report["attention"]
    lines.append("")
    if att:
        lines.append(f"*⚠️ Needs attention ({len(att)}):*")
        for a in att[:12]:
            lines.append(f"{ICON['degraded'] if a['sev'] == 'degraded' else ICON['watch']} "
                         f"*{a['app']}* — {a['text']}")
        if len(att) > 12:
            lines.append(f"  +{len(att) - 12} more")
    else:
        lines.append("✅ *Nothing needs attention — ratings, vitals and reviews all inside thresholds.*")
    trans = [f"{a['name']} {STATUS_LABEL[a['prior_status']]}→{STATUS_LABEL[a['status']]}"
             for a in report["apps"] if a.get("prior_status") and a["prior_status"] != a["status"]]
    if trans:
        lines.append("")
        lines.append("*Changes:* " + "; ".join(trans))
    lines.append("")
    lines.append("*All apps:*")
    for a in report["apps"]:
        head = f"{ICON[a['status']]} *{a['name']}* — {_rating_line(a) or 'no rating data'}"
        lines.append(head)
        for extra in (_vitals_line(a), _reviews_line(a)):
            if extra:
                lines.append(f"    ↳ _{extra}_")
    gaps = report.get("coverage_gaps") or []
    if gaps:
        lines.append("")
        lines.append("*Not on the store:*")
        for g in gaps:
            lines.append(f"⚪ {g['app']} — {g['text']}")
    return "\n".join(lines) + "\n"


def _app_store_line(a, store):
    """One-line per-app summary inside a store-scoped report."""
    r = (a.get("rating") or {}).get(store) or {}
    bits = []
    if r.get("avg") is not None:
        seg = f"{r['avg']:.2f}★"
        if r.get("count") is not None:
            seg += f" ({fmt_int(r['count'])})"
        if r.get("d_avg"):
            seg += f" {r['d_avg']:+.2f}"
        bits.append(seg)
    rv = a["slices"].get("ios_reviews" if store == "ios" else "play_reviews") or {}
    if rv:
        seg = f"{rv.get('count', 0)} new"
        if rv.get("neg_count"):
            seg += f", {rv['neg_count']}≤2★"
        if rv.get("backlog_unanswered"):
            seg += f", {rv['backlog_unanswered']} unanswered"
        bits.append(seg)
    if store == "ios":
        cur = ((a["slices"].get("ios_release") or {}).get("current")) or {}
        if cur.get("version"):
            state = (cur.get("state") or "").upper()
            short = ("live" if "READY" in state or "AVAILABLE" in state
                     else state.replace("_", " ").lower())
            bits.append(f"v{cur['version']} {short}")
        ph = (a["slices"].get("ios_release") or {}).get("phased") or {}
        if ph.get("state"):
            bits.append(f"phased {ph['state'].lower()} d{ph.get('day')}")
        bits.extend(_ios_tech_bits(a))
    else:
        m = (a["slices"].get("play_vitals") or {}).get("metrics") or {}
        if m.get("userPerceivedCrashRate") is not None:
            bits.append(f"crash {m['userPerceivedCrashRate']:.2f}%")
        if m.get("userPerceivedAnrRate") is not None:
            bits.append(f"ANR {m['userPerceivedAnrRate']:.2f}%")
        perf = a["slices"].get("play_store_perf") or {}
        if perf.get("conversion_pct") is not None:
            bits.append(f"conv {perf['conversion_pct']:.1f}%")
        inst = a["slices"].get("play_installs") or {}
        if inst.get("uninstall_ratio_pct") is not None:
            bits.append(f"uninst {inst['uninstall_ratio_pct']:.0f}%")
    return " · ".join(bits)


def _ios_tech_bits(a, limit=2):
    """The technical reading, compressed: what is over a bar, then what moved."""
    out = []
    per_1k = ((a["slices"].get("ios_analytics") or {}).get("derived") or {}).get("crashes_per_1k_sessions")
    if per_1k is not None:
        out.append(f"{per_1k:.2f} crashes/1k sess")
    metrics = (a["slices"].get("ios_perf") or {}).get("metrics") or {}
    over = [m for m in metrics.values()
            if m.get("value") is not None and m.get("watch") is not None
            and m["value"] >= m["watch"]]
    over.sort(key=lambda m: -(m["value"] / m["watch"]))
    for m in over[:limit]:
        out.append(f"{m['label'].lower()} {fmt_perf(m['value'], m['unit'])}")
    if not over:
        moved = [m for m in metrics.values()
                 if (m.get("delta_pct") or 0) >= 25.0
                 and not (m.get("min_for_regression") is not None
                          and (m.get("value") or 0) < m["min_for_regression"])]
        moved.sort(key=lambda m: -(m["delta_pct"] or 0))
        for m in moved[:limit]:
            out.append(f"{m['label'].lower()} {m['delta_pct']:+.0f}% vs prev")
    return out


def fmt_move(delta, unit="", scale=1.0):
    """A signed movement with an arrow, or nothing when there is no baseline to compare."""
    if delta in (None, 0):
        return ""
    arrow = "▲" if delta > 0 else "▼"
    return f" {arrow}{abs(delta) * scale:.2f}{unit}"


def _core_bits(row):
    bits = []
    if row.get("crashes") is not None:
        bits.append(f"{fmt_int(row['crashes'])} crashes")
    if row.get("sessions"):
        bits.append(f"{fmt_int(row['sessions'])} sessions")
    per_1k = row.get("crashes_per_1k")
    if per_1k is not None:
        moves = fmt_move(row.get("d_crashes_per_1k")) + \
            (f" {'▲' if (row.get('d_crashes_per_1k_7d') or 0) > 0 else '▼'}"
             f"{abs(row['d_crashes_per_1k_7d']):.2f} 7d"
             if row.get("d_crashes_per_1k_7d") else "")
        bits.append(f"{per_1k:.2f}/1k{moves}")
    if row.get("installs") is not None:
        bits.append(f"{fmt_int(row['installs'])} installs")
    if row.get("deletions") is not None:
        bits.append(f"{fmt_int(row['deletions'])} deletions")
    return bits


CORE_SLACK_VERSION_ROWS = 6


def render_core_slack(report):
    """The core-metrics panel: crashes, sessions and installs, and the versions behind them."""
    tech = report.get("tech_summary") or {}
    core = tech.get("core") or {}
    rows = tech.get("version_rows") or []
    has_totals = any(core.get(k) is not None for k in CORE_KEYS)
    if not has_totals and not tech.get("pending") and not tech.get("unmapped"):
        return []
    block = ["", "*Core metrics — crashes · sessions · installs (App Analytics):*"]
    if has_totals:
        bits = _core_bits(core)
        if core.get("net_installs") is not None:
            bits.append(f"net {core['net_installs']:+,.0f}")
        block.append(f"• *Portfolio* {' · '.join(bits)}"
                     + (f" · data for {core['as_of']}" if core.get("as_of") else ""))
        crash_pop = core.get("crash_rate_population") or {}
        install_pop = core.get("net_installs_population") or {}
        coverage = []
        if crash_pop.get("expected_apps"):
            coverage.append(f"crash/session {crash_pop.get('apps', 0)}/{crash_pop['expected_apps']} apps")
        if install_pop.get("expected_apps"):
            coverage.append(f"install/delete {install_pop.get('apps', 0)}/{install_pop['expected_apps']} apps")
        if coverage:
            date_range = core.get("date_range") or []
            block.append("  _Matched coverage: " + " · ".join(coverage)
                         + (f" · dates {date_range[0]}…{date_range[-1]}" if date_range else "") + "._")
        for row in rows[:CORE_SLACK_VERSION_ROWS]:
            line = f"• *{row['app']}* v{row['version']} — " + " · ".join(_core_bits(row))
            block.append(line + (f" · vs v{row['prev_version']} "
                                 f"{row['delta']:+.2f}/1k" if row.get("prev_version") else ""))
        if len(rows) > CORE_SLACK_VERSION_ROWS:
            block.append(f"  _+{len(rows) - CORE_SLACK_VERSION_ROWS} more app versions in the "
                         f"attached report._")
    if tech.get("pending"):
        reasons = {}
        for p in tech["pending"]:
            reasons.setdefault(p["text"], []).append(p["app"])
        total = len(report["apps"])
        for text, names in list(reasons.items())[:2]:
            scope = f"all {total} apps" if len(names) == total else f"{len(names)} app(s)"
            block.append(f"• {scope} — {text}")
    if tech.get("unmapped"):
        u = tech["unmapped"][0]
        block.append(f"• Column map to confirm: `{u['metric']}` looked for "
                     f"{', '.join(u['looked_for'])}, the export carries "
                     f"{', '.join((u.get('header') or [])[:6])}")
    return block


def render_tech_slack(report):
    """The technical-health block of the App Store message."""
    tech = report.get("tech_summary") or {}
    if not (tech.get("perf_apps") or tech.get("analytics_apps") or tech.get("pending")):
        return []
    total = len(report["apps"])
    block = ["", "*Device metrics (Xcode Organizer, opted-in devices):*"]
    if tech.get("perf_apps"):
        block.append(f"• Reported for {tech['perf_apps']}/{total} apps")
        lags = [(l["behind"] or 0, a["name"], l) for a in report["apps"]
                for l in [perf_version_lag(a)]
                if l and l["live_version"] and l["live_version"] != l["metrics_version"]]
        if lags:
            lags.sort(reverse=True)
            named = ", ".join(f"{name} {fmt_version_lag(l, short=True)}"
                              for _, name, l in lags[:3])
            behind = [b for b, _, _ in lags if b]
            span = (f"{min(behind)}-{max(behind)} releases behind"
                    if behind and min(behind) != max(behind)
                    else f"{behind[0]} release(s) behind" if behind else "behind the live version")
            block.append(f"• These describe older builds — {span} for {len(lags)} app(s): {named}")
    for key in ("termination", "hang", "launch", "memory"):
        w = (tech.get("worst") or {}).get(key)
        if not w or not w["value"]:
            continue
        bar = w.get("alert") or w.get("watch")
        block.append(f"• Worst {w['label'].lower()} ({w['percentile']}): "
                     f"{fmt_perf(w['value'], w['unit'])} — {w['app']} v{w['version']}"
                     + (f" (bar {fmt_perf(bar, w['unit'])})" if bar else ""))
    if tech.get("crash_1k"):
        top = tech["crash_1k"][0]
        block.append(f"• Crashes per 1k sessions: worst {top['value']:.2f} ({top['app']}), "
                     f"median {tech['crash_1k_median']:.2f} · as of {top.get('as_of')}")
    if tech.get("regressions"):
        listed = ", ".join(f"{r['app']} {r['label'].lower()} {r['delta_pct']:+.0f}%"
                           for r in tech["regressions"][:3])
        block.append(f"• Regressed against the previous versions ({len(tech['regressions'])}): {listed}")
    return block


def store_has_any_data(report, store):
    return any((a.get("status_by_store") or {}).get(store, "nodata") != "nodata"
               for a in report["apps"])


SLACK_ONE_MESSAGE_BUDGET = 3400


def slack_len(text):
    """Length in the unit the Slack poster splits on: JS string length = UTF-16 code
    units, so an emoji outside the BMP counts as 2. Byte length would over-trim."""
    return sum(2 if ord(ch) > 0xFFFF else 1 for ch in text)


def _cap_block(block, keep, noun):
    """Keep a block's title plus `keep` items; name what moved to the attached report."""
    head, items = block[:2], block[2:]
    if not items or len(items) <= keep:
        return block
    if keep <= 0:
        return head[:1] + [f"_{len(items)} {noun} — in the attached report._"]
    return head + items[:keep] + [f"  _+{len(items) - keep} more {noun} in the attached report._"]


def fit_one_message(blocks, order, limit=SLACK_ONE_MESSAGE_BUDGET):
    """Keep a store report inside ONE Slack message.

    The poster splits text over ~3500 chars into several messages, which silently breaks
    the one-message-per-store contract. Trim the least decision-critical detail here —
    the attached .md always carries the full picture.
    """
    def size():
        return sum(slack_len(line) + 1 for key in order for line in blocks[key])

    for key, keep, noun in (("quotes", 4, "reviews"), ("gaps", 4, "apps"), ("quotes", 2, "reviews"),
                            ("apps", 10, "apps"), ("gaps", 0, "apps"), ("quotes", 1, "reviews"),
                            ("tech", 4, "device lines"), ("core", 5, "app versions"),
                            ("att", 6, "findings"), ("apps", 6, "apps"),
                            ("tech", 2, "device lines"), ("core", 3, "app versions")):
        if size() <= limit:
            break
        if key in blocks:
            blocks[key] = _cap_block(blocks[key], keep, noun)
    return "\n".join(line for key in order for line in blocks[key]) + "\n"


def render_store_slack(report, store):
    """A self-contained report for one store, delivered as its own Slack message."""
    b = report["brand"]
    sm = report["store_summaries"][store]
    overall = report["overall_by_store"][store]
    label = STORE_LABEL[store]
    lines = [f"*{b['org']} — {label}, {report['report_day']}*  {ICON[overall]} *{STATUS_LABEL[overall]}*",
             f"_{sm['apps_rated']}/{sm['apps_total']} apps rated · {fmt_int(sm['ratings_total'])} ratings"
             f" · {sm['reviews_new']} new reviews · generated {report['generated_utc']}_"]
    pending = report["credential_state"]
    if store == "play" and pending.get("google") is not True:
        lines.append(f"_credentials pending: {pending.get('google')}_")
    if store == "play" and pending.get("bucket") is not True:
        lines.append(f"_reports bucket pending: {pending.get('bucket')}_")
    if store == "ios" and pending.get("apple") is not True:
        lines.append(f"_credentials pending: {pending.get('apple')}_")

    lines.append("")
    lines.append("*Portfolio*")
    if sm["rating_median"] is not None:
        lines.append(f"• Ratings {sm['rating_min']:.2f}–{sm['rating_max']:.2f}★ · median "
                     f"{sm['rating_median']:.2f}★ · lowest {sm['worst_app']}")
    lines.append(f"• Reviews: {sm['reviews_new']} new, {sm['reviews_neg']} ≤2★"
                 + (f" — themes: " + ", ".join(f"{k} ×{v}" for k, v in list(sm["topics"].items())[:4])
                    if sm["topics"] else ""))
    if sm["backlog"]:
        lines.append(f"• Unanswered: {sm['backlog']} total — " + ", ".join(sm["backlog_by_app"]))
    if sm["movers"]:
        lines.append("• Rating movers: " + ", ".join(sm["movers"]))
    else:
        lines.append("• Rating movers: none — no snapshot to compare against yet"
                     if not report["baseline_reports"] else "• Rating movers: none today")
    if store == "ios" and sm["release_states"]:
        lines.append("• Releases: " + " · ".join(f"{v} {k}" for k, v in sm["release_states"].items()))
    if store == "play":
        if sm["worst_crash"] is not None:
            lines.append(f"• Worst crash rate: {sm['worst_crash']:.2f}% ({sm['worst_crash_app']})"
                         + (f" · worst ANR {sm['worst_anr']:.2f}% ({sm['worst_anr_app']})"
                            if sm["worst_anr"] is not None else ""))
        if sm["conversion_median"] is not None:
            lines.append(f"• Store conversion (median): {sm['conversion_median']:.1f}%")
        if sm["installs"]:
            lines.append(f"• Installs {fmt_int(sm['installs'])} · uninstalls {fmt_int(sm['uninstalls'])}")

    att = [a for a in report["attention"] if a["store"] == store]
    att_block = [""]
    if att:
        att_block.append(f"*⚠️ Needs attention ({len(att)}):*")
        for a in att:
            att_block.append(f"{ICON['degraded'] if a['sev'] == 'degraded' else ICON['watch']} "
                             f"*{a['app']}* — {a['text']}")
    else:
        att_block.append(f"✅ *Nothing over threshold on {label}.*")

    trans = [f"{a['name']} {STATUS_LABEL[a['prior_status_by_store'][store]]}→"
             f"{STATUS_LABEL[a['status_by_store'][store]]}"
             for a in report["apps"]
             if (a.get("prior_status_by_store") or {}).get(store)
             and a["prior_status_by_store"][store] != a["status_by_store"][store]]
    if trans:
        lines.append("")
        lines.append("*Changes since the last report:* " + "; ".join(trans))

    app_block = ["", "*Per app:*"]
    ranked = sorted(report["apps"],
                    key=lambda a: (STATUS_ORDER.get(a["status_by_store"][store], 0) * -1,
                                   -((a.get("rating", {}).get(store) or {}).get("count") or 0)))
    for a in ranked:
        st = a["status_by_store"][store]
        if st == "nodata":
            continue
        line = _app_store_line(a, store)
        app_block.append(f"{ICON[st]} *{a['name']}* — {line or 'no data'}")

    review_key = "ios_reviews" if store == "ios" else "play_reviews"
    samples = []
    for a in report["apps"]:
        for smp in (a["slices"].get(review_key) or {}).get("sample", []):
            samples.append((smp["stars"], a["name"], smp))
    quote_block = []
    if samples:
        samples.sort(key=lambda x: x[0])
        quote_block = ["", "*What the unhappy users say (fresh ≤2★):*"]
        for stars, name, smp in samples[:6]:
            where = smp.get("territory") or smp.get("app_version") or ""
            title = (smp.get("title") or "").strip()
            body = (smp.get("text") or "").strip()
            head = f"“{title}” — " if title else ""
            quote_block.append(f"• *{name}* {stars}★{' ' + where if where else ''}: {head}{body[:200]}")

    gaps = [g for g in (report.get("coverage_gaps") or []) if g["store"] == label]
    gap_block = []
    if gaps:
        gap_block = ["", "*Not on the store:*"]
        for g in gaps[:8]:
            rj = None
            for a in report["apps"]:
                if a["name"] == g["app"]:
                    rj = (a["slices"].get("ios_release") or {}).get("rejection")
                    break
            extra = ""
            if rj and rj.get("submission_state"):
                extra = (f" · last submitted {rj.get('submitted')} in state "
                         f"`{rj['submission_state']}`"
                         + (f", {rj['days_unresolved']}d unresolved" if rj.get("days_unresolved") is not None else ""))
            gap_block.append(f"⚪ {g['app']} — {g['text']}{extra}")

    quiet = [a["name"] for a in report["apps"] if a["status_by_store"][store] == "nodata"]
    quiet_block = ["", f"_No {label} data for: {', '.join(quiet)}._"] if quiet else []

    core_block = render_core_slack(report) if store == "ios" else []
    tech_block = render_tech_slack(report) if store == "ios" else []
    blocks = {"head": lines, "core": core_block, "att": att_block, "tech": tech_block,
              "apps": app_block, "quotes": quote_block, "gaps": gap_block, "quiet": quiet_block}
    return fit_one_message(blocks, ("head", "core", "att", "tech", "apps", "quotes",
                                    "gaps", "quiet"))


RELEASED_STATES = ("READY_FOR_DISTRIBUTION", "READY_FOR_SALE", "AVAILABLE")


def perf_version_lag(app):
    """How far behind the store the device metrics are.

    Apple publishes a metric for an app version only once enough opted-in devices have
    reported it, so the newest metric is always some releases behind what users are
    downloading today. Reporting the metric's version without that gap reads as "now".
    """
    perf = app["slices"].get("ios_perf") or {}
    metrics_version = perf.get("version")
    if not metrics_version:
        return None
    versions = (app["slices"].get("ios_release") or {}).get("versions") or []
    live = next((v for v in versions
                 if any(st in (v.get("state") or "").upper() for st in RELEASED_STATES)), None)
    live_version = (live or {}).get("version")
    names = [v.get("version") for v in versions]
    behind = names.index(metrics_version) if metrics_version in names else None
    return {"metrics_version": metrics_version, "live_version": live_version,
            "behind": behind, "in_recent_versions": metrics_version in names,
            "recent_versions": len(names)}


def fmt_version_lag(lag, short=False):
    if not lag:
        return ""
    if not lag["live_version"] or lag["live_version"] == lag["metrics_version"]:
        return f"v{lag['metrics_version']}"
    if short:
        return f"v{lag['metrics_version']} (live v{lag['live_version']})"
    if lag["behind"]:
        return (f"v{lag['metrics_version']} — live v{lag['live_version']}, "
                f"{lag['behind']} release{'s' if lag['behind'] != 1 else ''} newer")
    if not lag["in_recent_versions"]:
        return (f"v{lag['metrics_version']} — live v{lag['live_version']}, not in the last "
                f"{lag['recent_versions']} App Store versions")
    return f"v{lag['metrics_version']} — live v{lag['live_version']}"


def _analytics_version_rows(an):
    """Per-version join of the breakdowns Apple returns separately per report."""
    metrics = an.get("metrics") or {}
    versions = {}
    for key in ("crashes", "sessions", "installs", "deletions"):
        for row in ((metrics.get(key) or {}).get("breakdown") or {}).get("App Version") or []:
            versions.setdefault(row["key"], {})[key] = row["value"]
    out = []
    for version, vals in versions.items():
        crashes, sessions = vals.get("crashes"), vals.get("sessions")
        vals["crashes_per_1k"] = (crashes / sessions * 1000.0
                                  if crashes is not None and sessions else None)
        out.append(dict(vals, version=version))
    out.sort(key=lambda r: -(r.get("crashes") or r.get("sessions") or 0))
    return out


def _tech_metric_keys(apps):
    """Metric columns in config order, taken from the apps that actually reported."""
    keys = []
    for a in apps:
        for key in ((a["slices"].get("ios_perf") or {}).get("metrics") or {}):
            if key not in keys:
                keys.append(key)
    return keys


def render_tech_md(report):
    """Technical health for the App Store report: device metrics, then App Analytics."""
    tech = report.get("tech_summary") or {}
    apps = report["apps"]
    if not (tech.get("perf_apps") or tech.get("analytics_apps") or tech.get("pending")):
        return []
    L = ["## Technical health", "",
         f"- Device metrics (App Store Connect `perfPowerMetrics`, Xcode Organizer data from "
         f"opted-in devices): {tech.get('perf_apps', 0)} of {len(apps)} apps",
         f"- App Analytics report instances with a usable value: "
         f"{tech.get('analytics_apps', 0)} of {len(apps)} apps",
         "- Device metrics are keyed by **app version**, not by day: the value is the current "
         "release and the baseline is the mean of the versions before it.", ""]
    keys = _tech_metric_keys(apps)
    if keys:
        labels, units = {}, {}
        for a in apps:
            for key, m in ((a["slices"].get("ios_perf") or {}).get("metrics") or {}).items():
                labels.setdefault(key, m["label"])
                units.setdefault(key, m["unit"])
        head = " | ".join(f"{labels[k]} ({units[k]})" for k in keys)
        L += [f"### Device metrics ({(apps[0]['slices'].get('ios_perf') or {}).get('device', 'all_iphones')}, "
              f"p90 unless noted)", "",
              f"| App | Metrics version | Live version | {head} |",
              "|---|---|---|" + "---|" * len(keys)]
        for a in apps:
            perf = a["slices"].get("ios_perf") or {}
            metrics = perf.get("metrics") or {}
            if not metrics:
                continue
            cells = []
            for key in keys:
                m = metrics.get(key)
                if not m or m.get("value") is None:
                    cells.append("—")
                    continue
                cell = fmt_perf(m["value"])
                if m.get("delta_pct") is not None:
                    cell += f" ({m['delta_pct']:+.0f}%)"
                if m.get("version") and m["version"] != perf.get("version"):
                    cell += f" @v{m['version']}"
                cells.append(cell)
            lag = perf_version_lag(a) or {}
            live = lag.get("live_version")
            behind = lag.get("behind")
            live_cell = "—" if not live else (
                "same" if live == lag.get("metrics_version")
                else f"{live} (+{behind})" if behind
                else f"{live} (not in last {lag.get('recent_versions')})"
                if not lag.get("in_recent_versions") else live)
            L.append(f"| {a['name']} | {perf.get('version') or '—'} | {live_cell} | "
                     + " | ".join(cells) + " |")
        L += ["", "_`Live version` is the newest released App Store version; `(+N)` is how many "
              "releases newer it is than the version these metrics describe — Apple publishes a "
              "version's metrics only once enough opted-in devices report it, so the newest "
              "metric always trails what users are downloading today._",
              "", "_Value (change against the mean of the previous versions). `@v…` marks a "
              "metric whose newest data point is a different version from the app's headline "
              "version — Apple publishes a metric only once enough opted-in devices report it._",
              ""]
    worst_device = []
    for a in apps:
        for key, m in ((a["slices"].get("ios_perf") or {}).get("metrics") or {}).items():
            wd = m.get("worst_device")
            if wd and m.get("value") and wd.get("value") and wd["value"] >= m["value"] * 1.5:
                worst_device.append((wd["value"] / m["value"], a["name"], m, wd))
    if worst_device:
        worst_device.sort(reverse=True, key=lambda x: x[0])
        L += ["### Device outliers", "",
              "| App | Metric | All iPhones | Worst device | Ratio |", "|---|---|---|---|---|"]
        for ratio, name, m, wd in worst_device[:10]:
            L.append(f"| {name} | {m['label']} | {fmt_perf(m['value'], m['unit'])} "
                     f"| {wd['device']} {fmt_perf(wd['value'], m['unit'])} | ×{ratio:.1f} |")
        L.append("")
    insights = [(a["name"], i) for a in apps
                for i in ((a["slices"].get("ios_perf") or {}).get("insights") or [])
                if i["direction"] == "regressions"]
    if insights:
        L += ["### What Apple flags as a regression", ""]
        for name, i in insights[:20]:
            L.append(f"- **{name}** — {i['summary']}")
        L.append("")
    rows = [a for a in apps if _has_measured_value(a["slices"].get("ios_analytics"))]
    if rows:
        L += ["### App Analytics (per report instance)", "",
              "| App | As of | Crashes | Sessions | Crashes/1k | Installs | Deletions | Source |",
              "|---|---|---|---|---|---|---|---|"]
        for a in rows:
            an = a["slices"]["ios_analytics"]
            m = an.get("metrics") or {}
            def val(key):
                v = (m.get(key) or {}).get("value")
                return "—" if v is None else fmt_int(v)
            per_1k = (an.get("derived") or {}).get("crashes_per_1k_sessions")
            access = {mm.get("access_type") for mm in m.values() if mm.get("access_type")}
            L.append(f"| {a['name']} | {an.get('as_of') or '—'} | {val('crashes')} "
                     f"| {val('sessions')} | {'—' if per_1k is None else f'{per_1k:.2f}'} "
                     f"| {val('installs')} | {val('deletions')} "
                     f"| {', '.join(sorted(access)) or an.get('pending') or '—'} |")
        L.append("")
        for a in rows:
            an = a["slices"]["ios_analytics"]
            by_version = _analytics_version_rows(an)
            if not by_version:
                continue
            L += [f"#### {a['name']} — by app version ({an.get('as_of')})", "",
                  "| Version | Crashes | Sessions | Crashes/1k | Installs | Deletions |",
                  "|---|---|---|---|---|---|"]
            for row in by_version:
                per_1k = row.get("crashes_per_1k")
                L.append(f"| {row['version']} | {fmt_int(row.get('crashes'))} "
                         f"| {fmt_int(row.get('sessions'))} "
                         f"| {'—' if per_1k is None else f'{per_1k:.2f}'} "
                         f"| {fmt_int(row.get('installs'))} "
                         f"| {fmt_int(row.get('deletions'))} |")
            L.append("")
            for dim in ("Device", "Platform Version"):
                slices = (((an.get("metrics") or {}).get("crashes") or {}).get("breakdown")
                          or {}).get(dim) or []
                if not slices:
                    continue
                L += [f"Crashes by {dim.lower()}: "
                      + " · ".join(f"{d['key']} {fmt_int(d['value'])}" for d in slices), ""]
        L += ["_Apple returns the top slices per dimension, not the full list, so these tables "
              "rank rather than total._", ""]
    if tech.get("pending"):
        grouped = {}
        for p in tech["pending"]:
            grouped.setdefault(p["text"], []).append(p["app"])
        L += ["### App Analytics not yet answering", ""]
        for text, names in grouped.items():
            if len(names) == len(apps):
                L.append(f"- all {len(names)} apps — {text}")
            else:
                L.append(f"- {', '.join(names)} — {text}")
        L.append("")
    if tech.get("unmapped"):
        L += ["### Column mapping to confirm", "",
              "Apple's export did not carry the column the config looks for. "
              "The first live instance is the evidence for the fix.", ""]
        for u in tech["unmapped"]:
            L.append(f"- **{u['app']}** `{u['metric']}` — looked for "
                     f"{', '.join(u['looked_for'])}; export header: "
                     f"{', '.join(u.get('header') or []) or 'empty'}")
        L.append("")
    return L


def render_crash_trend_md(report):
    """How the crash rate moved: over time from the disk baseline, and between releases."""
    apps = report["apps"]
    over_time = [a for a in apps if (a.get("crash_delta") or {}).get("rate") is not None]
    between = [a for a in apps if ((a.get("crash_delta") or {}).get("between_versions"))]
    core = (report.get("tech_summary") or {}).get("core") or {}
    if not over_time and not between and core.get("crashes_per_1k") is None:
        return []
    L = ["### How the crash rate is moving", ""]
    floor = ((apps[0].get("crash_delta") or {}).get("min_sessions")
             if apps else None) or DEFAULTS["thresholds"]["ios_crash_min_sessions"]
    L += [f"_A rate is only compared when both sides clear {fmt_int(floor)} sessions; below that "
          f"the cell is `—` rather than a delta of noise._", ""]
    if core.get("crashes_per_1k") is not None:
        bits = [f"portfolio {core['crashes_per_1k']:.2f}/1k"]
        if core.get("d_crashes_per_1k") is not None:
            bits.append(f"{core['d_crashes_per_1k']:+.2f} vs {core.get('prev_day')}")
        if core.get("d_crashes_per_1k_7d") is not None:
            bits.append(f"{core['d_crashes_per_1k_7d']:+.2f} vs {core.get('week_day')}")
        L += ["- " + " · ".join(bits), ""]
    if over_time:
        L += ["| App | Crashes/1k | Δ vs previous report | Δ vs ~7d | Sessions |",
              "|---|---|---|---|---|"]
        for a in over_time:
            d = a["crash_delta"]
            d_day = "—" if d["d"] is None else f"{d['d']:+.2f}"
            d_week = "—" if d["d_7d"] is None else f"{d['d_7d']:+.2f}"
            L.append(f"| {a['name']} | {d['rate']:.2f} | {d_day} | {d_week} "
                     f"| {fmt_int(d['sessions'])} |")
        L.append("")
    if between:
        L += ["**Between releases** — the newest version against the one before it, ordered by "
              "Apple's own version list (version strings in this portfolio are not sortable):", "",
              "| App | New version | Crashes/1k | Previous version | Crashes/1k | Δ |",
              "|---|---|---|---|---|---|"]
        for a in between:
            b = a["crash_delta"]["between_versions"]
            pct = "" if b.get("delta_pct") is None else f" ({b['delta_pct']:+.0f}%)"
            L.append(f"| {a['name']} | {b['version']} | {b['rate']:.2f} | {b['prev_version']} "
                     f"| {b['prev_rate']:.2f} | {b['delta']:+.2f}{pct} |")
        L.append("")
    thin = [a["name"] for a in apps
            if (a.get("crash_delta") or {}).get("rate") is None
            and (a.get("crash_delta") or {}).get("sessions")]
    if thin:
        L += [f"_Below the session floor, so no rate is claimed: {', '.join(thin)}._", ""]
    return L


def _att_of(report, nature, store=None):
    return [a for a in report["attention"]
            if a.get("nature", finding_nature(a["kind"])) == nature
            and (store is None or a["store"] == store)]


def render_technical_slack(report):
    """The store-side section of the technical report message.

    Returns section lines, not a whole message: the technical report is assembled from the
    client-log side and this side, and only the assembler knows the message header.
    """
    lines = ["", "*From the stores — device metrics, crashes and vitals*"]
    corrupt = ((report.get("trust") or {}).get("corrupt_candidates") or [])
    if corrupt:
        lines.append(f"⚠️ _{len(corrupt)} corrupt baseline candidate(s) were ignored; "
                     "trend comparisons are partial._")
    degraded = [(name, st) for name, st in (report.get("slice_state") or {}).items()
                if name.startswith("ios") and st.get("failed")]
    for name, st in degraded:
        lines.append(f"⚠️ _`{name}` failed for {st['failed']} app(s) this run — the coverage "
                     f"below is partial, not the whole portfolio._")
    lines += [l for l in render_core_slack(report)[1:]]     # drop the leading blank
    lines += [l for l in render_tech_slack(report)[1:]]
    play = [a for a in _att_of(report, "technical", "play")]
    if play:
        lines.append("")
        lines.append(f"*Google Play vitals ({len(play)}):*")
        for a in play:
            lines.append(f"{ICON['degraded'] if a['sev'] == 'degraded' else ICON['watch']} "
                         f"*{a['app']}* — {a['text']}")
    ios = _att_of(report, "technical", "ios")
    if ios:
        lines.append("")
        lines.append(f"*App Store technical findings ({len(ios)}):*")
        for a in ios:
            lines.append(f"{ICON['degraded'] if a['sev'] == 'degraded' else ICON['watch']} "
                         f"*{a['app']}* — {a['text']}")
    if not play and not ios:
        lines.append("")
        lines.append("✅ *No store-side technical finding over threshold.*")
    return lines


def render_experience_slack(report):
    """The store & user-experience message: ratings, reviews, releases — no device metrics."""
    b = report["brand"]
    status = (report.get("overall_by_nature") or {}).get("experience", "nodata")
    ios, play = report["store_summaries"]["ios"], report["store_summaries"]["play"]
    experience_slices = {"ios_rating", "ios_reviews", "ios_release", "play_reviews",
                         "play_rating", "play_store_perf", "play_installs"}
    slice_state = report.get("slice_state") or {}
    incomplete = [(name, state) for name, state in slice_state.items()
                  if name in experience_slices and not state.get("complete", True)]
    review_text = ("review totals incomplete" if any(name in ("ios_reviews", "play_reviews")
                                                       for name, _ in incomplete)
                   else f"{ios['reviews_new']} new reviews")
    lines = [f"*{b['org']} — store & user experience, {report['report_day']}*  "
             f"{ICON[status]} *{STATUS_LABEL[status]}*"]
    if incomplete:
        lines.append("⚠️ *Source completeness: PARTIAL — unknown values are not business zeroes.*")
        for name, state in incomplete:
            lines.append(f"• `{name}`: {state.get('ok', 0)}/{state.get('expected', 0)} apps; "
                         f"failed {state.get('failed', 0)}, skipped {state.get('skipped_count', 0)}")
    lines += [
             f"_{ios['apps_rated']}/{ios['apps_total']} apps rated · "
             f"{fmt_int(ios['ratings_total'])} ratings · {review_text} "
             f"· generated {report['generated_utc']}_",
             "_Ratings, reviews, release states and store conversion. Crash rates and device "
             "metrics are in the technical report._"]
    pending = [f"{k}: {v}" for k, v in report["credential_state"].items() if v is not True]
    if pending:
        lines.append(f"_Credentials pending — {'; '.join(pending)}_")
    corrupt = ((report.get("trust") or {}).get("corrupt_candidates") or [])
    if corrupt:
        lines.append(f"⚠️ *Baseline integrity:* {len(corrupt)} corrupt candidate(s) were ignored; "
                     "trend conclusions are incomplete.")
    for store, sm in (("ios", ios), ("play", play)):
        if not store_has_any_data(report, store):
            continue
        lines.append("")
        lines.append(f"*{STORE_LABEL[store]}*")
        if sm["rating_median"] is not None:
            lines.append(f"• Ratings {sm['rating_min']:.2f}–{sm['rating_max']:.2f}★ · median "
                         f"{sm['rating_median']:.2f}★ · lowest {sm['worst_app']}")
        review_key = "ios_reviews" if store == "ios" else "play_reviews"
        if not (slice_state.get(review_key) or {}).get("complete", True):
            lines.append("• Reviews: unknown — required source incomplete")
        else:
            lines.append(f"• Reviews: {sm['reviews_new']} new, {sm['reviews_neg']} ≤2★"
                         + (" — themes: "
                            + ", ".join(f"{k} ×{v}" for k, v in list(sm["topics"].items())[:4])
                            if sm["topics"] else ""))
        if sm["backlog"]:
            lines.append(f"• Unanswered: {sm['backlog']} total — "
                         + ", ".join(sm["backlog_by_app"]))
        if sm["movers"]:
            lines.append("• Rating movers: " + ", ".join(sm["movers"]))
        if store == "ios" and sm["release_states"]:
            lines.append("• Releases: "
                         + " · ".join(f"{v} {k}" for k, v in sm["release_states"].items()))
        if store == "play":
            if sm["conversion_median"] is not None:
                lines.append(f"• Store conversion (median): {sm['conversion_median']:.1f}%")
            if sm["installs"]:
                lines.append(f"• Installs {fmt_int(sm['installs'])} · "
                             f"uninstalls {fmt_int(sm['uninstalls'])}")

    att = _att_of(report, "experience")
    att_block = [""]
    if att:
        att_block.append(f"*⚠️ Needs attention ({len(att)}):*")
        for a in att:
            att_block.append(f"{ICON['degraded'] if a['sev'] == 'degraded' else ICON['watch']} "
                             f"*{a['app']}* — {a['text']} _({STORE_LABEL[a['store']]})_")
    elif not incomplete:
        att_block.append("✅ *Nothing over threshold on ratings, reviews or releases.*")
    else:
        att_block.append("⚠️ *Threshold conclusion suppressed because required sources are partial.*")

    app_block = ["", "*Per app:*"]
    ranked = sorted(report["apps"],
                    key=lambda a: (-STATUS_ORDER.get((a.get("status_by_nature") or {})
                                                     .get("experience", "nodata"), 0),
                                   -((a.get("rating", {}).get("ios") or {}).get("count") or 0)))
    for a in ranked:
        st = (a.get("status_by_nature") or {}).get("experience", "nodata")
        if st == "nodata":
            continue
        bits = []
        for store, label in (("ios", "iOS"), ("play", "Play")):
            r = (a.get("rating") or {}).get(store) or {}
            rv = a["slices"].get("ios_reviews" if store == "ios" else "play_reviews") or {}
            seg = []
            if r.get("avg") is not None:
                seg.append(f"{r['avg']:.2f}★ ({fmt_int(r.get('count'))})"
                           + (f" {r['d_avg']:+.2f}" if r.get("d_avg") else ""))
            if rv.get("count") or rv.get("backlog_unanswered"):
                piece = f"{rv.get('count', 0)} new"
                if rv.get("neg_count"):
                    piece += f", {rv['neg_count']}≤2★"
                if rv.get("backlog_unanswered"):
                    piece += f", {rv['backlog_unanswered']} unanswered"
                seg.append(piece)
            if seg:
                bits.append(f"{label} " + " · ".join(seg))
        cur = ((a["slices"].get("ios_release") or {}).get("current")) or {}
        if cur.get("version"):
            state = (cur.get("state") or "").upper()
            bits.append(f"v{cur['version']} "
                        + ("live" if "READY" in state or "AVAILABLE" in state
                           else state.replace("_", " ").lower()))
        app_block.append(f"{ICON[st]} *{a['name']}* — " + (" | ".join(bits) or "no data"))

    samples = []
    for a in report["apps"]:
        for key in ("ios_reviews", "play_reviews"):
            for smp in (a["slices"].get(key) or {}).get("sample", []):
                samples.append((smp["stars"], a["name"], smp))
    quote_block = []
    if samples:
        samples.sort(key=lambda x: x[0])
        quote_block = ["", "*What the unhappy users say (fresh ≤2★):*"]
        for stars, name, smp in samples[:6]:
            where = smp.get("territory") or smp.get("app_version") or ""
            title = (smp.get("title") or "").strip()
            body = (smp.get("text") or "").strip()
            quote_block.append(f"• *{name}* {stars}★{' ' + where if where else ''}: "
                               + (f"“{title}” — " if title else "") + body[:200])

    gap_block = []
    gaps = report.get("coverage_gaps") or []
    if gaps:
        gap_block = ["", "*Not on the store:*"]
        for g in gaps[:8]:
            gap_block.append(f"⚪ {g['app']} — {g['text']}")

    named_in_gaps = {g["app"] for g in (report.get("coverage_gaps") or [])}
    quiet = [a["name"] for a in report["apps"]
             if (a.get("status_by_nature") or {}).get("experience", "nodata") == "nodata"
             and a["name"] not in named_in_gaps]
    quiet_block = ["", f"_No store-listing data for: {', '.join(quiet)}._"] if quiet else []

    blocks = {"head": lines, "att": att_block, "apps": app_block,
              "quotes": quote_block, "gaps": gap_block, "quiet": quiet_block}
    return fit_one_message(blocks, ("head", "att", "apps", "quotes", "gaps", "quiet"))


def render_store_md(report, store, nature=None):
    """Triage-oriented per-store report.

    `nature` scopes it to one half of the split: "experience" drops the device-metric and
    crash sections and the technical findings, so the experience attachment cannot restate
    the technical report.
    """
    b = report["brand"]
    sm = report["store_summaries"][store]
    label = STORE_LABEL[store]
    review_key = "ios_reviews" if store == "ios" else "play_reviews"
    L = [f"# {b['org']} — {label} report {report['report_day']}", "",
         f"- Overall: **{STATUS_LABEL[report['overall_by_store'][store]]}**",
         f"- Apps rated: {sm['apps_rated']} of {sm['apps_total']} · {fmt_int(sm['ratings_total'])} ratings total",
         f"- Reviews in window: {sm['reviews_new']} new, {sm['reviews_neg']} ≤2★"
         + (f" · unanswered backlog {sm['backlog']}" if sm["backlog"] else ""),
         f"- Generated: {report['generated_utc']}",
         f"- Baseline snapshots on disk: {', '.join(report['baseline_reports']) or 'none yet (first run)'}",
         ""]
    if sm["topics"]:
        L += ["## Themes in negative reviews", "",
              " · ".join(f"`{k}` ×{v}" for k, v in sm["topics"].items()), ""]
    att = [a for a in report["attention"] if a["store"] == store
           and (nature is None
                or a.get("nature", finding_nature(a["kind"])) == nature)]
    if att:
        L += ["## Needs attention", "", "| Sev | App | Finding |", "|---|---|---|"]
        for a in att:
            L.append(f"| {STATUS_LABEL[a['sev']]} | {a['app']} | {a['text']} |")
        L.append("")
    L += ["## Per app", ""]
    vitals_cols = nature != "experience"
    if store == "ios":
        L += ["| App | Rating | Δ d/d | Δ 7d | Ratings | New | ≤2★ | Unanswered | Version | State |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    elif vitals_cols:
        L += ["| App | Rating | Δ d/d | Ratings | Crash % | ANR % | Conv % | Uninstall % | New | Unanswered |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    else:
        L += ["| App | Rating | Δ d/d | Ratings | Conv % | Uninstall % | New | Unanswered |",
              "|---|---|---|---|---|---|---|---|"]
    def num(v, fmt="{:.2f}"):
        return "—" if v is None else fmt.format(v)
    for a in report["apps"]:
        if a["status_by_store"][store] == "nodata":
            continue
        r = (a.get("rating") or {}).get(store) or {}
        rv = a["slices"].get(review_key) or {}
        if store == "ios":
            cur = ((a["slices"].get("ios_release") or {}).get("current")) or {}
            L.append(f"| {a['name']} | {num(r.get('avg'))} | {num(r.get('d_avg'), '{:+.2f}')} "
                     f"| {num(r.get('d_avg_7d'), '{:+.2f}')} | {fmt_int(r.get('count'))} "
                     f"| {rv.get('count', 0)} | {rv.get('neg_count', 0)} "
                     f"| {rv.get('backlog_unanswered', 0)} | {cur.get('version') or '—'} "
                     f"| {cur.get('state') or '—'} |")
        else:
            m = (a["slices"].get("play_vitals") or {}).get("metrics") or {}
            perf = a["slices"].get("play_store_perf") or {}
            inst = a["slices"].get("play_installs") or {}
            vitals = (f"| {num(m.get('userPerceivedCrashRate'))} "
                      f"| {num(m.get('userPerceivedAnrRate'))} " if vitals_cols else "")
            L.append(f"| {a['name']} | {num(r.get('avg'))} | {num(r.get('d_avg'), '{:+.2f}')} "
                     f"| {fmt_int(r.get('count'))} {vitals}"
                     f"| {num(perf.get('conversion_pct'), '{:.1f}')} "
                     f"| {num(inst.get('uninstall_ratio_pct'), '{:.0f}')} | {rv.get('count', 0)} "
                     f"| {rv.get('backlog_unanswered', 0)} |")
    L.append("")
    if store == "ios" and nature != "experience":
        L += render_tech_md(report)
        L += render_crash_trend_md(report)
    if store == "play" and nature != "experience":
        for a in report["apps"]:
            issues = a["slices"].get("play_issues") or []
            if not issues:
                continue
            L += [f"### {a['name']} — top Play issues", "",
                  "| Issue | Type | Users % | Users | Reports | Versions |", "|---|---|---|---|---|---|"]
            for it in issues:
                L.append(f"| {it.get('cause') or it.get('location') or '—'} | {it.get('type') or '—'} "
                         f"| {it.get('users_pct') or 0:.2f} | {fmt_int(it.get('users'))} "
                         f"| {fmt_int(it.get('reports'))} "
                         f"| {it.get('first_version') or '?'}→{it.get('last_version') or '?'} |")
            L.append("")
    L += ["## Negative review excerpts", ""]
    any_sample = False
    for a in report["apps"]:
        rv = a["slices"].get(review_key) or {}
        for smp in rv.get("sample", []):
            any_sample = True
            where = " · ".join(x for x in (smp.get("territory"), smp.get("app_version"),
                                           smp.get("at")) if x)
            L.append(f"**{a['name']} — {smp['stars']}★** ({where})  ")
            L.append(f"> {(smp.get('title') or '').strip()} {(smp.get('text') or '').strip()}".strip())
            L.append("")
    if not any_sample:
        L += ["_No ≤2★ reviews with text in the window._", ""]
    gaps = [g for g in (report.get("coverage_gaps") or []) if g["store"] == label]
    if gaps:
        L += ["## Not on the store", "", "| App | Configured id | Finding |", "|---|---|---|"]
        for g in gaps:
            L.append(f"| {g['app']} | `{g['id']}` | {g['text']} |")
        L.append("")
    notes = {}
    for a in report["apps"]:
        cred, local = split_skips(a, report)
        rel = [f"`{k}` failed — {v}" for k, v in a["errors"].items() if k.startswith(store[:3])]
        rel += [f"`{k}` skipped — {v}" for k, v in local if k.startswith(store[:3])]
        if rel:
            notes[a["name"]] = rel
    if notes:
        L += ["## Slices not collected", ""]
        for name, items in notes.items():
            L.append(f"- **{name}**: " + "; ".join(items))
        L.append("")
    return "\n".join(L) + "\n"


def render_technical_md(report):
    """The technical attachment: device metrics, crashes and vitals, both stores."""
    b = report["brand"]
    status = (report.get("overall_by_nature") or {}).get("technical", "nodata")
    L = [f"# {b['org']} — store technical report {report['report_day']}", "",
         f"- Verdict on technical grounds: **{STATUS_LABEL[status]}**",
         f"- Generated: {report['generated_utc']}",
         "- What is here: Apple device metrics (Xcode Organizer), App Analytics crashes / "
         "sessions / installs, and Google Play vitals. Ratings, reviews and release states are "
         "in the experience report.", ""]
    att = _att_of(report, "technical")
    if att:
        L += ["## Needs attention (technical)", "", "| Sev | App | Store | Finding |",
              "|---|---|---|---|"]
        for a in att:
            L.append(f"| {STATUS_LABEL[a['sev']]} | {a['app']} | {STORE_LABEL[a['store']]} "
                     f"| {a['text']} |")
        L.append("")
    else:
        L += ["_No store-side technical finding over threshold._", ""]
    L += render_tech_md(report)
    L += render_crash_trend_md(report)
    for a in report["apps"]:
        issues = a["slices"].get("play_issues") or []
        if not issues:
            continue
        L += [f"### {a['name']} — top Play issues", "",
              "| Issue | Type | Users % | Users | Reports | Versions |", "|---|---|---|---|---|---|"]
        for it in issues:
            L.append(f"| {it.get('cause') or it.get('location') or '—'} | {it.get('type') or '—'} "
                     f"| {it.get('users_pct') or 0:.2f} | {fmt_int(it.get('users'))} "
                     f"| {fmt_int(it.get('reports'))} "
                     f"| {it.get('first_version') or '?'}→{it.get('last_version') or '?'} |")
        L.append("")
    return "\n".join(L) + "\n"


def render_experience_md(report):
    """The experience attachment: ratings, reviews and release states, both stores."""
    b = report["brand"]
    status = (report.get("overall_by_nature") or {}).get("experience", "nodata")
    L = [f"# {b['org']} — store & user experience {report['report_day']}", "",
         f"- Verdict on experience grounds: **{STATUS_LABEL[status]}**",
         f"- Generated: {report['generated_utc']}",
         "- What is here: ratings, reviews, release and submission states, store conversion. "
         "Crash rates and device metrics are in the technical report.", ""]
    for store in ("ios", "play"):
        if not store_has_any_data(report, store):
            continue
        L.append(f"---\n")
        L.append(render_store_md(report, store, nature="experience"))
    return "\n".join(L) + "\n"


def render_md(report):
    b = report["brand"]
    L = [f"# {b['org']} {b['product']} — store report {report['report_day']}", "",
         f"- Overall: **{STATUS_LABEL[report['overall_status']]}**",
         f"- Generated: {report['generated_utc']}",
         f"- Apps: {len(report['apps'])}",
         f"- Baseline snapshots on disk: {', '.join(report['baseline_reports']) or 'none yet (first run)'}",
         ""]
    L += ["## Source availability", "", "| Slice | Collected | Failed | Skipped because |", "|---|---|---|---|"]
    for name, st in sorted(report["slice_state"].items()):
        L.append(f"| `{name}` | {st['ok']} | {st['failed']} | {st['skipped'] or '—'} |")
    L.append("")
    if report["attention"]:
        L += ["## Needs attention", "", "| Sev | App | Finding |", "|---|---|---|"]
        for a in report["attention"]:
            L.append(f"| {STATUS_LABEL[a['sev']]} | {a['app']} | {a['text']} |")
        L.append("")
    if report.get("coverage_gaps"):
        L += ["## Coverage gaps", "", "| App | Store | Configured id | Finding |", "|---|---|---|---|"]
        for g in report["coverage_gaps"]:
            L.append(f"| {g['app']} | {g['store']} | `{g['id']}` | {g['text']} |")
        L.append("")
    L += render_tech_md(report)
    L += ["## Ratings", "", "| App | iOS | Δ d/d | Δ 7d | iOS ratings | Play | Δ d/d | Play as of |",
          "|---|---|---|---|---|---|---|---|"]
    for a in report["apps"]:
        i = (a.get("rating") or {}).get("ios") or {}
        p = (a.get("rating") or {}).get("play") or {}
        pr = a["slices"].get("play_rating") or {}
        def num(v, fmt="{:.2f}"):
            return "—" if v is None else fmt.format(v)
        L.append(f"| {a['name']} | {num(i.get('avg'))} | {num(i.get('d_avg'), '{:+.2f}')} "
                 f"| {num(i.get('d_avg_7d'), '{:+.2f}')} | {fmt_int(i.get('count'))} "
                 f"| {num(p.get('avg'))} | {num(p.get('d_avg'), '{:+.2f}')} "
                 f"| {pr.get('as_of') or '—'} |")
    L.append("")
    for a in report["apps"]:
        L.append(f"## {a['name']} — {STATUS_LABEL[a['status']]}")
        L.append("")
        ios = a["slices"].get("ios_rating") or {}
        if ios.get("by_storefront"):
            L += ["| Storefront | Avg | Ratings | Current version avg | Version | Released |",
                  "|---|---|---|---|---|---|"]
            for cc, v in ios["by_storefront"].items():
                if not v.get("listed"):
                    L.append(f"| {cc} | not listed | — | — | — | — |")
                    continue
                L.append(f"| {cc} | {v.get('avg') if v.get('avg') is not None else '—'} "
                         f"| {fmt_int(v.get('count'))} | {v.get('avg_current') or '—'} "
                         f"| {v.get('version') or '—'} | {v.get('released') or '—'} |")
            L.append("")
        vit = a["slices"].get("play_vitals") or {}
        if vit.get("metrics"):
            L += ["| Play vital | Value | Google bar | Verdict |", "|---|---|---|---|"]
            th = report.get("thresholds", {})
            for metric, bar in (("userPerceivedCrashRate", th.get("play_crash_alert_pct")),
                                ("userPerceivedAnrRate", th.get("play_anr_alert_pct")),
                                ("crashRate", None), ("anrRate", None)):
                val = vit["metrics"].get(metric)
                if val is None:
                    continue
                verdict = "—" if not bar else ("over bar" if val >= bar else "inside bar")
                L.append(f"| `{metric}` | {val:.3f}% | {bar if bar else '—'} | {verdict} |")
            L.append("")
        issues = a["slices"].get("play_issues") or []
        if issues:
            L += ["| Play issue | Type | Users % | Users | Reports | Versions |", "|---|---|---|---|---|---|"]
            for it in issues:
                L.append(f"| {it.get('cause') or it.get('location') or '—'} | {it.get('type') or '—'} "
                         f"| {it.get('users_pct') or 0:.2f} | {fmt_int(it.get('users'))} "
                         f"| {fmt_int(it.get('reports'))} "
                         f"| {it.get('first_version') or '?'}→{it.get('last_version') or '?'} |")
            L.append("")
        for key, label in (("ios_reviews", "App Store"), ("play_reviews", "Play")):
            rv = a["slices"].get(key) or {}
            if not rv.get("count"):
                continue
            L.append(f"**{label} reviews since {rv.get('window_start')}** — {rv['count']} new, "
                     f"avg {rv.get('avg') or '—'}★, {rv.get('neg_count')} ≤2★ "
                     f"({rv.get('neg_share_pct') or 0:.0f}%), {rv.get('backlog_unanswered')} unanswered overall.")
            if rv.get("topics"):
                L.append("")
                L.append("Topics in negative reviews: "
                         + ", ".join(f"`{k}`×{v}" for k, v in rv["topics"].items()))
            for s in rv.get("sample", []):
                L.append("")
                L.append(f"> {s['stars']}★ — {s.get('title') or ''} {s.get('text') or ''}".strip())
            L.append("")
        cred_skips, local_skips = split_skips(a, report)
        notes = [f"`{k}` low data — too few users for the rate to mean anything"
                 for k in a.get("low_data", [])]
        notes += [f"`{k}` failed — {v}" for k, v in a["errors"].items()]
        notes += [f"`{k}` skipped — {v}" for k, v in local_skips]
        if cred_skips:
            notes.append(f"{len(cred_skips)} slice(s) waiting on credentials "
                         f"({', '.join('`' + k + '`' for k, _ in cred_skips)})")
        if notes:
            L.append("_Slices not collected:_ " + "; ".join(notes))
            L.append("")
    return "\n".join(L) + "\n"


SKELETON_HEAD = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
                 '<meta name="viewport" content="width=device-width,initial-scale=1">'
                 "<title>{title}</title><style>body{{margin:0}}</style></head><body>")
SKELETON_TAIL = "</body></html>"

CSS = """
:root{--bg:#f7f8fa;--card:#fff;--fg:#16181d;--dim:#61656e;--line:#e3e5ea;
--ok:#1a7f45;--warn:#a86400;--bad:#b3261e;--accent:#2b5fd9}
@media (prefers-color-scheme:dark){:root{--bg:#12141a;--card:#1a1d24;--fg:#e8eaee;--dim:#9aa0aa;
--line:#2a2e37;--ok:#4ec97f;--warn:#e0a63a;--bad:#f2685c;--accent:#7aa2ff}}
*{box-sizing:border-box}body{background:var(--bg);color:var(--fg);
font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;padding:24px}
h1{font-size:22px;margin:0 0 4px}h2{font-size:16px;margin:0 0 10px}
.sub{color:var(--dim);font-size:12px;margin-bottom:18px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px}
.pill{display:inline-block;padding:1px 8px;border-radius:999px;font-size:11px;font-weight:600;
border:1px solid currentColor}
.healthy{color:var(--ok)}.watch{color:var(--warn)}.degraded{color:var(--bad)}.nodata{color:var(--dim)}
.tiles{display:flex;gap:10px;flex-wrap:wrap;margin:10px 0}
.tile{flex:1 1 120px;background:var(--bg);border:1px solid var(--line);border-radius:9px;padding:8px 10px}
.tile b{display:block;font-size:19px;font-weight:650}
.tile span{color:var(--dim);font-size:11px;text-transform:uppercase;letter-spacing:.04em}
.up{color:var(--ok)}.down{color:var(--bad)}
table{width:100%;border-collapse:collapse;font-size:12px;margin-top:8px}
th,td{text-align:left;padding:4px 6px;border-bottom:1px solid var(--line)}
th{color:var(--dim);font-weight:600}
.bar{height:6px;border-radius:4px;background:var(--line);overflow:hidden;margin-top:4px}
.bar>i{display:block;height:100%}
.att{margin:0 0 18px;padding:12px 14px;background:var(--card);border:1px solid var(--line);border-radius:12px}
.att li{margin:3px 0}.dim{color:var(--dim)}
.chip{display:inline-block;background:var(--bg);border:1px solid var(--line);border-radius:999px;
padding:1px 8px;font-size:11px;margin:2px 3px 0 0}
"""


def _esc(v):
    return html.escape(str(v)) if v is not None else "—"


def _tile(label, value, delta=None, suffix=""):
    cls = ""
    d = ""
    if delta is not None and delta != 0:
        cls = "up" if delta > 0 else "down"
        d = f' <span class="{cls}">{delta:+.2f}</span>'
    return (f'<div class="tile"><span>{_esc(label)}</span><b>'
            f'{"—" if value is None else _esc(value)}{suffix}{d}</b></div>')


def _bar(value, bar, tone):
    if value is None or not bar:
        return ""
    pct = min(100.0, value / bar * 100.0)
    return f'<div class="bar"><i style="width:{pct:.0f}%;background:var(--{tone})"></i></div>'


def uniform_pending(report):
    """The one App Analytics wait reason, when every app is waiting for the same thing.

    Printing it on fifteen cards says nothing fifteen times; the portfolio block says it once.
    """
    pending = (report.get("tech_summary") or {}).get("pending") or []
    if len(pending) != len(report["apps"]):
        return None
    reasons = {p["text"] for p in pending}
    return reasons.pop() if len(reasons) == 1 else None


def render_inner(report, image=False, store=None, scope=None):
    """The dashboard. `scope` splits it the same way the messages are split.

    A dashboard is an attachment to one message, so it must not show the other message's
    subject: the experience page carries no device metrics, and the technical page carries
    no review quotes.
    """
    b = report["brand"]
    shared_pending = uniform_pending(report)
    th = report.get("thresholds", {})
    tech_ok = scope in (None, "technical")
    exp_ok = scope in (None, "experience")
    if scope:
        status = (report.get("overall_by_nature") or {}).get(scope, "nodata")
    else:
        status = report["overall_by_store"][store] if store else report["overall_status"]
    scope_label = {"technical": "technical — devices, crashes, vitals",
                   "experience": "store & user experience"}.get(scope)
    heading = (f"{b['org']} — {scope_label}" if scope_label
               else f"{b['org']} — {STORE_LABEL[store]}" if store
               else f"{b['org']} {b['product']} — stores")
    sub_extra = ""
    if store:
        sm = report["store_summaries"][store]
        sub_extra = (f' · {sm["apps_rated"]}/{sm["apps_total"]} rated · '
                     f'{fmt_int(sm["ratings_total"])} ratings · {sm["reviews_new"]} new reviews')
    out = [f"<style>{CSS}</style>",
           f"<h1>{_esc(heading)}</h1>",
           f'<div class="sub">{_esc(report["report_day"])} · '
           f'<span class="pill {status}">{STATUS_LABEL[status]}</span> · '
           f'{len(report["apps"])} apps{sub_extra} · generated {_esc(report["generated_utc"])}</div>']
    relevant = {"ios": ("apple",), "play": ("google", "bucket")}.get(store) or \
               ("google", "apple", "bucket")
    pending = [f"{k}: {v}" for k, v in report["credential_state"].items()
               if v is not True and k in relevant]
    if pending:
        out.append(f'<div class="att dim">Credentials pending — {"; ".join(_esc(p) for p in pending)}</div>')
    att = [a for a in report["attention"]
           if (not store or a["store"] == store)
           and (not scope or a.get("nature", finding_nature(a["kind"])) == scope)]
    if att:
        items = "".join(f'<li><span class="pill {a["sev"]}">{STATUS_LABEL[a["sev"]]}</span> '
                        f'<b>{_esc(a["app"])}</b> — {_esc(a["text"])}</li>'
                        for a in att[:20])
        out.append(f'<div class="att"><h2>Needs attention ({len(att)})</h2><ul>{items}</ul></div>')
    else:
        out.append('<div class="att">✅ Nothing over threshold: ratings, vitals and reviews all inside bars.</div>')
    if store or scope:
        sm = report["store_summaries"][store or "ios"]
        tiles = ['<div class="tiles">']
        if exp_ok and sm["rating_median"] is not None:
            tiles.append(_tile("Median rating", f"{sm['rating_median']:.2f}★"))
            tiles.append(_tile("Range", f"{sm['rating_min']:.2f}–{sm['rating_max']:.2f}★"))
        if exp_ok:
            tiles.append(_tile("Ratings", fmt_int(sm["ratings_total"])))
            tiles.append(_tile("New reviews", fmt_int(sm["reviews_new"])))
            if sm["reviews_neg"]:
                tiles.append(_tile("≤2★ reviews", fmt_int(sm["reviews_neg"])))
            if sm["backlog"]:
                tiles.append(_tile("Unanswered", fmt_int(sm["backlog"])))
        if tech_ok and sm.get("worst_crash") is not None:
            tiles.append(_tile("Worst crash", f"{sm['worst_crash']:.2f}%"))
        if exp_ok and sm.get("conversion_median") is not None:
            tiles.append(_tile("Median conv.", f"{sm['conversion_median']:.1f}%"))
        tech = report.get("tech_summary") or {}
        if tech_ok and store != "play":
            if tech.get("crash_1k"):
                tiles.append(_tile("Worst crashes/1k", f"{tech['crash_1k'][0]['value']:.2f}"))
            for key in ("hang", "launch"):
                w = (tech.get("worst") or {}).get(key)
                if w:
                    tiles.append(_tile(f"Worst {w['label'].lower()}",
                                       fmt_perf(w["value"], w["unit"])))
            if tech.get("regressions"):
                tiles.append(_tile("Version regressions", len(tech["regressions"])))
        tiles.append("</div>")
        if tech_ok and shared_pending:
            tiles.append(f'<div class="dim">App Analytics (crashes, sessions, '
                         f'installs/deletions) — {_esc(shared_pending)}</div>')
        chips = ("".join(f'<span class="chip">{_esc(k)} ×{v}</span>'
                         for k, v in sm["topics"].items()) if exp_ok else "")
        out.append('<div class="att"><h2>Portfolio</h2>' + "".join(tiles)
                   + (f'<div>Themes in negative reviews: {chips}</div>' if chips else "")
                   + (f'<div class="dim" style="margin-top:6px">Releases: '
                      + " · ".join(f"{v} {_esc(k)}" for k, v in sm["release_states"].items())
                      + "</div>" if sm.get("release_states") else "")
                   + "</div>")
    gaps = [g for g in (report.get("coverage_gaps") or [])
            if not store or g["store"] == STORE_LABEL[store]] if exp_ok else []
    if gaps:
        out.append('<div class="att dim"><b>Not on the store</b><ul>'
                   + "".join(f'<li>{_esc(g["app"])} — {_esc(g["text"])} '
                             f'(<code>{_esc(g["id"])}</code>)</li>' for g in gaps) + "</ul></div>")
    out.append('<div class="grid">')
    cards = [a for a in report["apps"]
             if (not store or (a.get("status_by_store") or {}).get(store) != "nodata")
             and (not scope or (a.get("status_by_nature") or {}).get(scope) != "nodata")]
    for a in cards:
        i = (a.get("rating") or {}).get("ios") or {}
        p = (a.get("rating") or {}).get("play") or {}
        vit = (a["slices"].get("play_vitals") or {}).get("metrics") or {}
        st = (a.get("status_by_store") or {}).get(store) if store else a["status"]
        st = st or a["status"]
        card = [f'<div class="card"><h2>{_esc(a["name"])} '
                f'<span class="pill {st}">{STATUS_LABEL[st]}</span></h2>',
                '<div class="tiles">']
        if exp_ok and store != "play":
            card.append(_tile("App Store", None if i.get("avg") is None else f"{i['avg']:.2f}★",
                              i.get("d_avg")))
            card.append(_tile("iOS ratings", fmt_int(i.get("count"))))
        if exp_ok and store != "ios":
            card.append(_tile("Play", None if p.get("avg") is None else f"{p['avg']:.2f}★",
                              p.get("d_avg")))
            if p.get("count") is not None:
                card.append(_tile("Play ratings", fmt_int(p.get("count"))))
        card.append('</div>')
        crash, anr = vit.get("userPerceivedCrashRate"), vit.get("userPerceivedAnrRate")
        if tech_ok and (crash is not None or anr is not None):
            card.append("<table><tr><th>Play vital</th><th>Value</th><th>Bar</th></tr>")
            for label, val, bar in (("User-perceived crash", crash, th.get("play_crash_alert_pct")),
                                    ("User-perceived ANR", anr, th.get("play_anr_alert_pct"))):
                if val is None:
                    continue
                tone = "bad" if bar and val >= bar else ("warn" if bar and val >= bar * 0.6 else "ok")
                card.append(f"<tr><td>{label}{_bar(val, bar, tone)}</td>"
                            f'<td class="{tone}">{val:.2f}%</td><td class="dim">{bar}%</td></tr>')
            card.append("</table>")
        perf = (a["slices"].get("ios_perf") or {}) if tech_ok and store != "play" else {}
        pm = perf.get("metrics") or {}
        if pm:
            lag_text = fmt_version_lag(perf_version_lag(a), short=True) or \
                f'v{perf.get("version")}'
            card.append(f'<table><tr><th>Device metric — {_esc(lag_text)}</th>'
                        f"<th>Value</th><th>vs prev</th></tr>")
            for m in pm.values():
                if m.get("value") is None:
                    continue
                bar = m.get("alert") or m.get("watch")
                tone = ("bad" if m.get("alert") and m["value"] >= m["alert"]
                        else "warn" if m.get("watch") and m["value"] >= m["watch"] else "ok")
                delta = m.get("delta_pct")
                dcls = "bad" if delta is not None and delta >= 50 else (
                    "warn" if delta is not None and delta >= 25 else "dim")
                card.append(f"<tr><td>{_esc(m['label'])}{_bar(m['value'], bar, tone)}</td>"
                            f'<td class="{tone}">{_esc(fmt_perf(m["value"], m["unit"]))}</td>'
                            f'<td class="{dcls}">'
                            f'{"—" if delta is None else f"{delta:+.0f}%"}</td></tr>')
            card.append("</table>")
        an = (a["slices"].get("ios_analytics") or {}) if tech_ok and store != "play" else {}
        if an:
            am = an.get("metrics") or {}
            per_1k = (an.get("derived") or {}).get("crashes_per_1k_sessions")
            got = {k: v.get("value") for k, v in am.items() if v.get("value") is not None}
            if got or per_1k is not None:
                card.append('<div class="tiles">')
                if per_1k is not None:
                    card.append(_tile("Crashes/1k sess", f"{per_1k:.2f}"))
                for key, label in (("crashes", "Crashes"), ("sessions", "Sessions"),
                                   ("installs", "Installs"), ("deletions", "Deletions")):
                    if key in got:
                        card.append(_tile(label, fmt_int(got[key])))
                card.append("</div>")
                if an.get("as_of"):
                    card.append(f'<div class="dim">App Analytics as of {_esc(an["as_of"])}</div>')
            elif an.get("pending") and not shared_pending:
                card.append(f'<div class="dim" style="margin-top:6px">App Analytics — '
                            f'{_esc(an["pending"])}</div>')
        issues = (a["slices"].get("play_issues") or [])[:4] if tech_ok else []
        if issues:
            card.append("<table><tr><th>Top Play issues</th><th>Users</th><th>%</th></tr>")
            for it in issues:
                card.append(f"<tr><td>{_esc((it.get('cause') or it.get('location') or '—')[:60])}"
                            f'<br><span class="dim">{_esc(it.get("type"))}</span></td>'
                            f"<td>{fmt_int(it.get('users'))}</td>"
                            f"<td>{it.get('users_pct') or 0:.2f}</td></tr>")
            card.append("</table>")
        for key, label in ((("ios_reviews", "App Store"), ("play_reviews", "Play"))
                           if exp_ok else ()):
            if store and not key.startswith(store[:3] if store == "ios" else "play"):
                continue
            rv = a["slices"].get(key) or {}
            if not rv.get("count"):
                continue
            chips = "".join(f'<span class="chip">{_esc(k)} ×{v}</span>' for k, v in rv.get("topics", {}).items())
            card.append(f'<div style="margin-top:8px"><b>{label} reviews</b> '
                        f'<span class="dim">{rv["count"]} new · {rv.get("neg_count")} ≤2★ · '
                        f'{rv.get("backlog_unanswered")} unanswered</span><br>{chips}</div>')
            if not image:
                for s in rv.get("sample", [])[:2]:
                    card.append(f'<div class="dim" style="margin-top:4px">{s["stars"]}★ '
                                f'{_esc((s.get("title") or s.get("text") or "")[:120])}</div>')
        perf = (a["slices"].get("play_store_perf") or {}) if exp_ok else {}
        inst = (a["slices"].get("play_installs") or {}) if exp_ok else {}
        if perf.get("conversion_pct") is not None or inst.get("installs") is not None:
            card.append('<div class="tiles">')
            if perf.get("conversion_pct") is not None:
                card.append(_tile("Store conversion", f"{perf['conversion_pct']:.1f}%"))
            if inst.get("installs") is not None:
                card.append(_tile("Installs", fmt_int(inst.get("installs"))))
            if inst.get("uninstall_ratio_pct") is not None:
                card.append(_tile("Uninstall ratio", f"{inst['uninstall_ratio_pct']:.0f}%"))
            card.append("</div>")
        rel = (a["slices"].get("ios_release") or {}) if exp_ok and store != "play" else {}
        if rel.get("current"):
            ph = rel.get("phased") or {}
            card.append(f'<div class="dim" style="margin-top:8px">App Store '
                        f'{_esc(rel["current"].get("version"))} — {_esc(rel["current"].get("state"))}'
                        + (f' · phased {_esc(ph.get("state"))} day {_esc(ph.get("day"))}' if ph else "")
                        + "</div>")
        cred_skips, local_skips = split_skips(a, report)
        pre = {"ios": "ios_", "play": "play_"}.get(store)
        keep = (lambda k: k.startswith(pre)) if pre else (lambda k: True)
        notes = [f"{k} failed: {v[:70]}" for k, v in a["errors"].items() if keep(k)]
        notes += [f"{k} skipped: {v[:60]}" for k, v in local_skips if keep(k)]
        cred_here = [k for k, _ in cred_skips if keep(k)]
        if cred_here:
            notes.append(f"{len(cred_here)} slice(s) waiting on credentials")
        if notes:
            card.append(f'<div class="dim" style="margin-top:8px;font-size:11px">'
                        f'{_esc(" · ".join(notes))}</div>')
        card.append("</div>")
        out.append("".join(card))
    out.append("</div>")
    return "".join(out)


# ------------------------------------------------------------------ commands

def cmd_doctor(cfg, creds, transport, app_filter=None):
    print("Store Pulse doctor — credential and reachability matrix\n")
    for name in ("google", "apple", "bucket"):
        state = "available" if creds.has(name) else f"UNAVAILABLE — {creds.reasons.get(name)}"
        print(f"  credential {name:8} {state}")
    if creds.google:
        try:
            creds.google.token()
            print(f"  google token  ok (service account {creds.google.client_email})")
        except AuthError as exc:
            print(f"  google token  FAILED — {exc}")
    if creds.apple:
        try:
            creds.apple.token()
            print("  apple token   ok (ES256 signed)")
        except AuthError as exc:
            print(f"  apple token   FAILED — {exc}")
    print("")
    apps = [a for a in cfg["apps"] if not app_filter or a["key"] in app_filter]
    day = dt.date.today() - dt.timedelta(days=1)
    ctx = {"cfg": cfg, "creds": creds, "transport": transport, "day": day,
           "now": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "window_start": (day - dt.timedelta(days=1)).isoformat()}
    width = max(len(a["name"]) for a in apps)
    for app in apps:
        res = collect_app(ctx, app)
        marks = []
        for name in SLICE_NEEDS:
            if name in res["slices"]:
                marks.append(f"{name}=ok")
            elif name in res["errors"]:
                marks.append(f"{name}=FAIL")
            elif name in res["skipped"]:
                marks.append(f"{name}=skip")
        print(f"  {app['name']:<{width}}  " + "  ".join(marks))
        for name, err in res["errors"].items():
            print(f"      {name}: {err}")
    if creds.apple:
        print("\n  App Analytics report requests (they gate crashes/sessions/installs):")
        headers = creds.apple_headers()
        for app in apps:
            if not app.get("ios"):
                continue
            try:
                app_id = _ios_app_id(ctx, app)
                reqs = src.asc_analytics_requests(transport, headers, app_id)
                live = [r for r in reqs if not r.get("stopped")]
                kinds = ", ".join(sorted(r["access_type"] for r in live)) or "none — run bootstrap"
                inst = "—"
                if live:
                    index, _ = _analytics_report_index(ctx, live)
                    probe = index.get("App Crashes")
                    if probe:
                        found = None
                        for candidate in [probe] + (probe.get("fallbacks") or []):
                            found = (_latest_analytics_instance(
                                ctx, candidate["id"], cfg["ios_analytics_granularity"])
                                if candidate.get("access_type") == "ONE_TIME_SNAPSHOT"
                                else _analytics_instance(
                                    ctx, candidate["id"], cfg["ios_analytics_granularity"]))
                            if found:
                                break
                        inst = (f"App Crashes instance {found['processing_date']}" if found
                                else "no instance yet (Apple needs 24-48h)")
                    else:
                        inst = "no reports listed yet"
                print(f"    {app['name']:<{width}}  {kinds:<34} {inst}")
            except (HttpError, AuthError, RuntimeError) as exc:
                print(f"    {app['name']:<{width}}  FAILED — {safe_error(exc)}")
    print("\nSlices marked skip are waiting on a credential or an identifier, not broken.")
    return 0


def cmd_bootstrap(cfg, creds, transport, app_filter=None, access_types=("ONGOING",)):
    """Register the Apple analytics report requests (they need days of lead time).

    ONGOING is what the daily report reads: one instance per day, from tomorrow on.
    ONE_TIME_SNAPSHOT backfills the trailing year once and is what makes the first
    reports non-empty. Both need an Admin-role key; a lesser role gets 403.
    """
    if not creds.apple:
        print(f"cannot bootstrap: apple credentials unavailable — {creds.reasons.get('apple')}")
        return 1
    headers = creds.apple_headers()
    ctx = {"cfg": cfg, "creds": creds, "transport": transport}
    failures = 0
    for app in cfg["apps"]:
        if app_filter and app["key"] not in app_filter:
            continue
        if not app.get("ios"):
            continue
        try:
            app_id = _ios_app_id(ctx, app)
            existing = src.asc_analytics_requests(transport, headers, app_id)
            live = [r for r in existing if not r.get("stopped")]
            for access in access_types:
                if any(r["access_type"] == access for r in live):
                    print(f"  {app['name']}: {access} request already present")
                    continue
                new_id = src.asc_create_request(transport, headers, app_id, access)
                print(f"  {app['name']}: created {access} analytics request {new_id} "
                      f"(first instances land in ~24-48h)")
        except (HttpError, AuthError, RuntimeError) as exc:
            failures += 1
            print(f"  {app['name']}: FAILED — {safe_error(exc)}")
    if failures:
        print(f"\n{failures} app(s) failed. A 403 here means the key lacks the Admin role, "
              f"the only role allowed to create analytics report requests.")
    return 1 if failures else 0


def _refresh_backfilled_report(report, cfg, history, day):
    """Re-score a stored report after replacing only its analytics slice."""
    for app in report.get("apps", []):
        _, prev = _prior_app(history, app.get("key"))
        week_limit = (day - dt.timedelta(days=6)).isoformat()
        _, week = _prior_app_at_or_before(history, app.get("key"), week_limit)
        attach_crash_deltas(app, prev, week, cfg["thresholds"]["ios_crash_min_sessions"])
        score_app(app, cfg)
    report["attention"] = [dict(item, app=app["name"])
                           for app in report.get("apps", [])
                           for item in app.get("attention", [])]
    report["store_summaries"] = {
        store: build_store_summary(report.get("apps", []), store)
        for store in ("ios", "play")}
    report["tech_summary"] = attach_core_deltas(
        build_tech_summary(report.get("apps", []), cfg["thresholds"]), history, day)
    for store in ("ios", "play"):
        measured = [(a.get("status_by_store") or {}).get(store, "nodata")
                    for a in report.get("apps", [])]
        measured = [s for s in measured if s != "nodata"]
        report.setdefault("overall_by_store", {})[store] = (
            max(measured, key=lambda s: STATUS_ORDER[s]) if measured else "nodata")
    for nature in ("technical", "experience"):
        measured = [(a.get("status_by_nature") or {}).get(nature, "nodata")
                    for a in report.get("apps", [])]
        measured = [s for s in measured if s != "nodata"]
        report.setdefault("overall_by_nature", {})[nature] = (
            max(measured, key=lambda s: STATUS_ORDER[s]) if measured else "nodata")
    measured = [a.get("status") for a in report.get("apps", [])
                if a.get("status") != "nodata"]
    report["overall_status"] = (
        max(measured, key=lambda s: STATUS_ORDER[s]) if measured else "nodata")
    report["analytics_backfilled_utc"] = dt.datetime.now(dt.timezone.utc).isoformat(
        timespec="seconds")


def cmd_backfill(cfg, creds, transport, out_dir, slug="store_pulse", days=14,
                 app_filter=None, through=None):
    """Merge Apple snapshot analytics into existing daily StorePulse artifacts."""
    if not creds.has("apple"):
        print(f"analytics backfill unavailable — {creds.reasons.get('apple')}")
        return 0
    end = through or dt.datetime.now(dt.timezone.utc).date()
    start = end - dt.timedelta(days=max(1, days) - 1)
    docs = {}
    for path in sorted(glob.glob(os.path.join(out_dir, f"{slug}_????-??-??.json"))):
        stamp = os.path.basename(path)[len(slug) + 1:-5]
        try:
            date = dt.date.fromisoformat(stamp)
            if start <= date <= end:
                with open(path) as handle:
                    docs[stamp] = {"path": path, "report": json.load(handle)}
        except (OSError, ValueError):
            continue
    if not docs:
        print(f"analytics backfill: no existing {slug}_YYYY-MM-DD.json files in "
              f"{start}..{end}")
        return 0
    apps_cfg = [a for a in cfg["apps"] if not app_filter or a["key"] in app_filter]
    updated = set()
    for stamp in sorted(docs):
        day = dt.date.fromisoformat(stamp)
        ctx = {"cfg": cfg, "creds": creds, "transport": transport, "day": day,
               "now": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
               "window_start": day.isoformat(), "prev_window_start": day.isoformat()}
        existing = {a.get("key"): a for a in docs[stamp]["report"].get("apps", [])}
        with ThreadPoolExecutor(max_workers=cfg["max_workers"]) as ex:
            futures = {a["key"]: ex.submit(collect_ios_analytics, ctx, a) for a in apps_cfg}
            for key, future in futures.items():
                try:
                    analytics = future.result()
                except Exception as exc:
                    print(f"  {stamp} {key}: skipped ({safe_error(exc)})")
                    continue
                if key in existing and _has_measured_value(analytics):
                    existing[key].setdefault("slices", {})["ios_analytics"] = analytics
                    updated.add(stamp)
    if not updated:
        print("analytics backfill: Apple snapshot has no usable daily rows yet; no files changed")
        return 0
    for stamp in sorted(updated):
        earlier = [(d, docs[d]["report"]) for d in sorted(docs, reverse=True) if d < stamp]
        report = docs[stamp]["report"]
        _refresh_backfilled_report(report, cfg, earlier, dt.date.fromisoformat(stamp))
        base = docs[stamp]["path"][:-5]
        atomic_write_json(base + ".json", report, indent=2, default=str)
        atomic_write_text(base + ".md", safety_redact(render_md(report)))
        atomic_write_text(base + ".technical.slack.txt",
                          safety_redact("\n".join(render_technical_slack(report)) + "\n"))
        atomic_write_text(base + ".technical.md", safety_redact(render_technical_md(report)))
        print(f"analytics backfill: updated {os.path.basename(base)}")
    marker = os.path.join(out_dir, f".{slug}_ios_analytics_backfill_complete")
    atomic_write_text(marker, safety_redact(
        f"completed_utc={dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')}\n"
        f"through={end.isoformat()}\nfiles={len(updated)}\n"))
    print(f"analytics backfill: {len(updated)} daily file(s) updated")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Store health reporter for Google Play + App Store Connect")
    ap.add_argument("command", nargs="?", default="report",
                    choices=("report", "doctor", "bootstrap", "backfill"))
    ap.add_argument("--config", required=True)
    ap.add_argument("--out", default=".")
    ap.add_argument("--day", default=None, help="report day (default: today UTC)")
    ap.add_argument("--slug", default="store_pulse")
    ap.add_argument("--mode", default=None, choices=("daily", "weekly", "monthly"),
                    help="explicit read-depth override. Omit it and the config's own "
                         "review_window_days / review_pages stand — a host that declares a "
                         "7-day review window means it. daily=1 day, weekly=7, monthly=30 + "
                         "3 pages of history, and weekly/monthly write their own report series.")
    ap.add_argument("--only", default=None, help="comma-separated slice allow-list")
    ap.add_argument("--apps", default=None, help="comma-separated app key allow-list")
    ap.add_argument("--dashboard", action="store_true",
                    help="also write the HTML dashboard files. Off by default: the reports "
                         "are read as the Slack message plus the markdown attachment, and a "
                         "large rendered page is not read at all.")
    ap.add_argument("--access", default="ONGOING",
                    help="bootstrap only: comma-separated access types to register "
                         "(ONGOING, ONE_TIME_SNAPSHOT). ONGOING feeds the daily report; "
                         "ONE_TIME_SNAPSHOT backfills the trailing year once.")
    ap.add_argument("--days", type=int, default=14,
                    help="backfill only: merge this many days into existing daily files")
    args = ap.parse_args()

    cfg = apply_mode(load_config(args.config), args.mode)
    transport = Transport(timeout=cfg["http_timeout"], retries=cfg["http_retries"],
                          deadline=time.monotonic() + cfg["run_timeout"])
    creds = Creds(cfg, transport)
    app_filter = set(args.apps.split(",")) if args.apps else None

    if args.command == "doctor":
        return cmd_doctor(cfg, creds, transport, app_filter)
    if args.command == "bootstrap":
        access = tuple(a.strip().upper() for a in args.access.split(",") if a.strip())
        unknown = set(access) - {"ONGOING", "ONE_TIME_SNAPSHOT"}
        if unknown:
            ap.error(f"unknown --access value(s): {', '.join(sorted(unknown))}")
        return cmd_bootstrap(cfg, creds, transport, app_filter, access)
    if args.command == "backfill":
        through = dt.date.fromisoformat(args.day) if args.day else None
        return cmd_backfill(cfg, creds, transport, args.out, args.slug, args.days,
                            app_filter, through)

    day = dt.date.fromisoformat(args.day) if args.day else dt.datetime.now(dt.timezone.utc).date()
    only = set(args.only.split(",")) if args.only else None
    slug = args.slug
    if only:
        unknown = only - set(SLICE_NEEDS)
        if unknown:
            ap.error(f"unknown slice(s) in --only: {', '.join(sorted(unknown))}")
        # A partial run must not overwrite the full daily snapshot: that file is the
        # baseline every later run reads. Partial runs keep their own slug history.
        if slug == ap.get_default("slug"):
            slug += "_partial"
    if args.mode in ("weekly", "monthly") and slug == ap.get_default("slug"):
        # a wider window is a different series; it must not overwrite the daily baseline
        slug = f"{slug}_{args.mode}"

    os.makedirs(args.out, exist_ok=True)
    report = build_report(cfg, creds, transport, day, args.out, slug, only, app_filter)
    report["thresholds"] = cfg["thresholds"]

    base = os.path.join(args.out, f"{slug}_{day.isoformat()}")
    atomic_write_json(base + ".json", report, indent=2, default=str)
    written = "json"
    if args.dashboard:
        title = html.escape(f"{cfg['brand']['org']} {cfg['brand']['product']} stores")
        inner = render_inner(report)
        atomic_write_text(base + ".inner.html", safety_redact(inner))
        atomic_write_text(base + ".html", safety_redact(
            SKELETON_HEAD.format(title=title) + inner + SKELETON_TAIL))
        atomic_write_text(base + ".render.html", safety_redact(
            SKELETON_HEAD.format(title=title) + render_inner(report, image=True) + SKELETON_TAIL))
        written += ",html,inner.html,render.html"
    atomic_write_text(base + ".md", safety_redact(render_md(report)))
    written += ",md"

    # The reports are split by concern, not by store: the technical half joins the client-log
    # technical report, the experience half is its own message. Play is folded into both rather
    # than getting a third message of its own.
    ready = []
    any_store = any(store_has_any_data(report, st) for st in ("ios", "play"))
    if any_store:
        ready.append("technical")
        atomic_write_text(f"{base}.technical.slack.txt",
                          safety_redact("\n".join(render_technical_slack(report)) + "\n"))
        atomic_write_text(f"{base}.technical.md", safety_redact(render_technical_md(report)))
        ready.append("experience")
        atomic_write_text(f"{base}.experience.slack.txt",
                          safety_redact(render_experience_slack(report)))
        atomic_write_text(f"{base}.experience.md", safety_redact(render_experience_md(report)))
        written += ",technical.{slack.txt,md},experience.{slack.txt,md}"
        if args.dashboard:
            for scope in ("technical", "experience"):
                title = html.escape(f"{cfg['brand']['org']} {scope}")
                atomic_write_text(f"{base}.{scope}.render.html", safety_redact(
                    SKELETON_HEAD.format(title=title)
                    + render_inner(report, image=True, scope=scope) + SKELETON_TAIL))
            written += ",{technical,experience}.render.html"

    print(f"report_day: {report['report_day']}  overall: {report['overall_status']}  "
          f"apps: {len(report['apps'])}  http_calls: {transport.calls}")
    for a in report["apps"]:
        i = (a.get("rating") or {}).get("ios") or {}
        p = (a.get("rating") or {}).get("play") or {}
        by = a["status_by_store"]
        print(f"  apple={by['ios']:8} play={by['play']:8} {a['name']:20} "
              f"ios={star(i.get('avg'), i.get('d_avg')):>16} "
              f"play={star(p.get('avg'), p.get('d_avg')):>16} "
              f"slices={len(a['slices'])} failed={len(a['errors'])}")
    pending = [f"{k} ({v})" for k, v in report["credential_state"].items() if v is not True]
    if pending:
        print("  credentials pending: " + "; ".join(pending))
    for nature in ("technical", "experience"):
        state = STATUS_LABEL[(report.get("overall_by_nature") or {}).get(nature, "nodata")]
        print(f"  {nature:11} {state}")
    for st in ("ios", "play"):
        print(f"  store {STORE_LABEL[st]:12} "
              + ("has data" if store_has_any_data(report, st) else "no data"))
    print(f"reports_ready: {','.join(ready) if ready else 'none'}")
    print(f"base_path: {base}")
    print(f"written: {base}.{{{written}}}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
