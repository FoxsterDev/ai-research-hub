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
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import store_sources as src
from store_auth import AppleAuth, AuthError, GoogleAuth, HttpError, Transport

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
    for app in cfg["apps"]:
        if not app.get("key"):
            raise SystemExit("config error: every app needs a 'key'")
        app.setdefault("name", app["key"])
        app.setdefault("android", None)
        app.setdefault("ios", None)
        app.setdefault("ios_app_id", None)
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
    text = str(exc) if isinstance(exc, (HttpError, AuthError)) else f"{type(exc).__name__}: {exc}"
    text = _URL_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}/…" if m.group(3) else m.group(0),
                       src.redact(text))
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


def collect_ios_analytics(ctx, app):
    """P2 slice: report the standing-request state so bootstrap gaps are visible."""
    app_id = _ios_app_id(ctx, app)
    requests = src.asc_analytics_requests(ctx["transport"], ctx["creds"].apple_headers(), app_id)
    ongoing = [r for r in requests if r["access_type"] == "ONGOING" and not r.get("stopped")]
    out = {"requests": requests, "ongoing": len(ongoing), "reports": []}
    if ongoing:
        out["reports"] = src.asc_analytics_reports(
            ctx["transport"], ctx["creds"].apple_headers(), ongoing[0]["id"],
            categories=ctx["cfg"].get("ios_analytics_categories", []),
            name_filter=ctx["cfg"].get("ios_analytics_reports", []))
    return out


def collect_ios_perf(ctx, app):
    app_id = _ios_app_id(ctx, app)
    raw = src.asc_perf_power(ctx["transport"], ctx["creds"].apple_headers(), app_id)
    insights = []
    for group in (raw.get("insights") or {}).get("regressions", []) or []:
        insights.append({"metric": group.get("metric"), "summary": group.get("summaryString")})
    return {"insight_count": len(insights), "insights": insights[:5],
            "categories": [c.get("identifier") for c in raw.get("productData", [{}])[0]
                           .get("metricCategories", [])] if raw.get("productData") else []}


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
        out["sets"][key] = {"as_of": block["as_of"], "pct": pcts, "users": users, "trail": trail,
                            "breakdown": block["breakdown"], "freshness": block["freshness"]}
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
           "ios": app.get("ios"), "errors": {}, "skipped": {}, "slices": {}}
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


def prior_reports(out_dir, slug, day, max_files=30):
    """Disk-first history: every earlier run of this slug is a baseline candidate."""
    found = []
    for path in sorted(glob.glob(os.path.join(out_dir, f"{slug}_*.json")), reverse=True):
        stamp = os.path.basename(path)[len(slug) + 1:-5]
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", stamp) or stamp >= day.isoformat():
            continue
        try:
            with open(path) as fh:
                found.append((stamp, json.load(fh)))
        except (OSError, ValueError):
            continue
        if len(found) >= max_files:
            break
    return found


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
    app_out["prior_status"] = (prev or {}).get("status")
    app_out["prior_status_by_store"] = (prev or {}).get("status_by_store") or {}
    return app_out


def _worse(current, candidate):
    return candidate if STATUS_ORDER[candidate] > STATUS_ORDER[current] else current


STORE_LABEL = {"ios": "App Store", "play": "Google Play"}


def _store_has_data(app_out, store):
    s = app_out["slices"]
    if store == "ios":
        return any([(app_out.get("rating", {}).get("ios") or {}).get("avg") is not None,
                    (s.get("ios_reviews") or {}).get("count"),
                    (s.get("ios_reviews") or {}).get("backlog_unanswered")])
    return any([(app_out.get("rating", {}).get("play") or {}).get("avg") is not None,
                (s.get("play_vitals") or {}).get("metrics"),
                (s.get("play_reviews") or {}).get("count"),
                (s.get("play_reviews") or {}).get("backlog_unanswered"),
                (s.get("play_store_perf") or {}).get("conversion_pct") is not None,
                (s.get("play_installs") or {}).get("installs") is not None,
                s.get("play_issues"), s.get("play_anomalies")])


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

    app_out["status_by_store"] = by_store
    app_out["status"] = ("nodata" if all(v == "nodata" for v in by_store.values())
                         else max((v for v in by_store.values() if v != "nodata"),
                                  key=lambda v: STATUS_ORDER[v]))
    app_out["attention"] = sorted(att, key=lambda a: STATUS_ORDER[a["sev"]], reverse=True)
    return app_out


def _median(xs):
    xs = sorted(xs)
    if not xs:
        return None
    mid = len(xs) // 2
    return xs[mid] if len(xs) % 2 else (xs[mid - 1] + xs[mid]) / 2


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


def build_report(cfg, creds, transport, day, out_dir, slug, only=None, app_filter=None):
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    apps_cfg = [a for a in cfg["apps"] if not app_filter or a["key"] in app_filter]
    window_days = cfg.get("review_window_days", 1)
    ctx = {"cfg": cfg, "creds": creds, "transport": transport, "day": day, "now": now,
           "window_start": (day - dt.timedelta(days=window_days)).isoformat(),
           "prev_window_start": (day - dt.timedelta(days=window_days * 2)).isoformat()}
    history = prior_reports(out_dir, slug, day)
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
        attach_deltas(block, history, day)
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
    slice_state = {}
    for name in SLICE_NEEDS:
        ok = sum(1 for a in apps if name in a["slices"])
        failed = sum(1 for a in apps if name in a["errors"])
        skipped = {a["skipped"][name] for a in apps if name in a["skipped"]}
        if ok or failed or skipped:
            slice_state[name] = {"ok": ok, "failed": failed,
                                 "skipped": sorted(skipped)[:1][0] if skipped else None}
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
        "store_summaries": store_summaries,
        "baseline_reports": [h[0] for h in history[:3]],
        "credential_state": {k: (True if creds.has(k) else creds.reasons.get(k, "unavailable"))
                             for k in ("google", "apple", "bucket")},
    }


# ------------------------------------------------------------------ render

def fmt_int(n):
    if n is None:
        return "—"
    n = int(n)
    return f"{n/1_000_000:.1f}M" if n >= 1_000_000 else (f"{n/1_000:.0f}k" if n >= 10_000 else f"{n:,}")


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
                            ("att", 6, "findings"), ("apps", 6, "apps")):
        if size() <= limit:
            break
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

    blocks = {"head": lines, "att": att_block, "apps": app_block,
              "quotes": quote_block, "gaps": gap_block, "quiet": quiet_block}
    return fit_one_message(blocks, ("head", "att", "apps", "quotes", "gaps", "quiet"))


def render_store_md(report, store):
    """Triage-oriented per-store report; the file attached to that store's message."""
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
    att = [a for a in report["attention"] if a["store"] == store]
    if att:
        L += ["## Needs attention", "", "| Sev | App | Finding |", "|---|---|---|"]
        for a in att:
            L.append(f"| {STATUS_LABEL[a['sev']]} | {a['app']} | {a['text']} |")
        L.append("")
    L += ["## Per app", ""]
    if store == "ios":
        L += ["| App | Rating | Δ d/d | Δ 7d | Ratings | New | ≤2★ | Unanswered | Version | State |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    else:
        L += ["| App | Rating | Δ d/d | Ratings | Crash % | ANR % | Conv % | Uninstall % | New | Unanswered |",
              "|---|---|---|---|---|---|---|---|---|---|"]
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
            L.append(f"| {a['name']} | {num(r.get('avg'))} | {num(r.get('d_avg'), '{:+.2f}')} "
                     f"| {fmt_int(r.get('count'))} | {num(m.get('userPerceivedCrashRate'))} "
                     f"| {num(m.get('userPerceivedAnrRate'))} | {num(perf.get('conversion_pct'), '{:.1f}')} "
                     f"| {num(inst.get('uninstall_ratio_pct'), '{:.0f}')} | {rv.get('count', 0)} "
                     f"| {rv.get('backlog_unanswered', 0)} |")
    L.append("")
    if store == "play":
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


def render_inner(report, image=False, store=None):
    b = report["brand"]
    th = report.get("thresholds", {})
    status = report["overall_by_store"][store] if store else report["overall_status"]
    heading = f"{b['org']} — {STORE_LABEL[store]}" if store else f"{b['org']} {b['product']} — stores"
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
    att = [a for a in report["attention"] if not store or a["store"] == store]
    if att:
        items = "".join(f'<li><span class="pill {a["sev"]}">{STATUS_LABEL[a["sev"]]}</span> '
                        f'<b>{_esc(a["app"])}</b> — {_esc(a["text"])}</li>'
                        for a in att[:20])
        out.append(f'<div class="att"><h2>Needs attention ({len(att)})</h2><ul>{items}</ul></div>')
    else:
        out.append('<div class="att">✅ Nothing over threshold: ratings, vitals and reviews all inside bars.</div>')
    if store:
        sm = report["store_summaries"][store]
        tiles = ['<div class="tiles">']
        if sm["rating_median"] is not None:
            tiles.append(_tile("Median rating", f"{sm['rating_median']:.2f}★"))
            tiles.append(_tile("Range", f"{sm['rating_min']:.2f}–{sm['rating_max']:.2f}★"))
        tiles.append(_tile("Ratings", fmt_int(sm["ratings_total"])))
        tiles.append(_tile("New reviews", fmt_int(sm["reviews_new"])))
        if sm["reviews_neg"]:
            tiles.append(_tile("≤2★ reviews", fmt_int(sm["reviews_neg"])))
        if sm["backlog"]:
            tiles.append(_tile("Unanswered", fmt_int(sm["backlog"])))
        if sm.get("worst_crash") is not None:
            tiles.append(_tile("Worst crash", f"{sm['worst_crash']:.2f}%"))
        if sm.get("conversion_median") is not None:
            tiles.append(_tile("Median conv.", f"{sm['conversion_median']:.1f}%"))
        tiles.append("</div>")
        chips = "".join(f'<span class="chip">{_esc(k)} ×{v}</span>' for k, v in sm["topics"].items())
        out.append('<div class="att"><h2>Portfolio</h2>' + "".join(tiles)
                   + (f'<div>Themes in negative reviews: {chips}</div>' if chips else "")
                   + (f'<div class="dim" style="margin-top:6px">Releases: '
                      + " · ".join(f"{v} {_esc(k)}" for k, v in sm["release_states"].items())
                      + "</div>" if sm.get("release_states") else "")
                   + "</div>")
    gaps = [g for g in (report.get("coverage_gaps") or [])
            if not store or g["store"] == STORE_LABEL[store]]
    if gaps:
        out.append('<div class="att dim"><b>Not on the store</b><ul>'
                   + "".join(f'<li>{_esc(g["app"])} — {_esc(g["text"])} '
                             f'(<code>{_esc(g["id"])}</code>)</li>' for g in gaps) + "</ul></div>")
    out.append('<div class="grid">')
    cards = [a for a in report["apps"]
             if not store or (a.get("status_by_store") or {}).get(store) != "nodata"]
    for a in cards:
        i = (a.get("rating") or {}).get("ios") or {}
        p = (a.get("rating") or {}).get("play") or {}
        vit = (a["slices"].get("play_vitals") or {}).get("metrics") or {}
        st = (a.get("status_by_store") or {}).get(store) if store else a["status"]
        st = st or a["status"]
        card = [f'<div class="card"><h2>{_esc(a["name"])} '
                f'<span class="pill {st}">{STATUS_LABEL[st]}</span></h2>',
                '<div class="tiles">']
        if store != "play":
            card.append(_tile("App Store", None if i.get("avg") is None else f"{i['avg']:.2f}★",
                              i.get("d_avg")))
            card.append(_tile("iOS ratings", fmt_int(i.get("count"))))
        if store != "ios":
            card.append(_tile("Play", None if p.get("avg") is None else f"{p['avg']:.2f}★",
                              p.get("d_avg")))
            if p.get("count") is not None:
                card.append(_tile("Play ratings", fmt_int(p.get("count"))))
        card.append('</div>')
        crash, anr = vit.get("userPerceivedCrashRate"), vit.get("userPerceivedAnrRate")
        if crash is not None or anr is not None:
            card.append("<table><tr><th>Play vital</th><th>Value</th><th>Bar</th></tr>")
            for label, val, bar in (("User-perceived crash", crash, th.get("play_crash_alert_pct")),
                                    ("User-perceived ANR", anr, th.get("play_anr_alert_pct"))):
                if val is None:
                    continue
                tone = "bad" if bar and val >= bar else ("warn" if bar and val >= bar * 0.6 else "ok")
                card.append(f"<tr><td>{label}{_bar(val, bar, tone)}</td>"
                            f'<td class="{tone}">{val:.2f}%</td><td class="dim">{bar}%</td></tr>')
            card.append("</table>")
        issues = (a["slices"].get("play_issues") or [])[:4]
        if issues:
            card.append("<table><tr><th>Top Play issues</th><th>Users</th><th>%</th></tr>")
            for it in issues:
                card.append(f"<tr><td>{_esc((it.get('cause') or it.get('location') or '—')[:60])}"
                            f'<br><span class="dim">{_esc(it.get("type"))}</span></td>'
                            f"<td>{fmt_int(it.get('users'))}</td>"
                            f"<td>{it.get('users_pct') or 0:.2f}</td></tr>")
            card.append("</table>")
        for key, label in (("ios_reviews", "App Store"), ("play_reviews", "Play")):
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
        perf = a["slices"].get("play_store_perf") or {}
        inst = a["slices"].get("play_installs") or {}
        if perf.get("conversion_pct") is not None or inst.get("installs") is not None:
            card.append('<div class="tiles">')
            if perf.get("conversion_pct") is not None:
                card.append(_tile("Store conversion", f"{perf['conversion_pct']:.1f}%"))
            if inst.get("installs") is not None:
                card.append(_tile("Installs", fmt_int(inst.get("installs"))))
            if inst.get("uninstall_ratio_pct") is not None:
                card.append(_tile("Uninstall ratio", f"{inst['uninstall_ratio_pct']:.0f}%"))
            card.append("</div>")
        rel = (a["slices"].get("ios_release") or {}) if store != "play" else {}
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
    print("\nSlices marked skip are waiting on a credential or an identifier, not broken.")
    return 0


def cmd_bootstrap(cfg, creds, transport, app_filter=None):
    """Create the standing Apple analytics report requests (they need days of lead time)."""
    if not creds.apple:
        print(f"cannot bootstrap: apple credentials unavailable — {creds.reasons.get('apple')}")
        return 1
    headers = creds.apple_headers()
    ctx = {"cfg": cfg, "creds": creds, "transport": transport}
    for app in cfg["apps"]:
        if app_filter and app["key"] not in app_filter:
            continue
        if not app.get("ios"):
            continue
        try:
            app_id = _ios_app_id(ctx, app)
            existing = src.asc_analytics_requests(transport, headers, app_id)
            ongoing = [r for r in existing if r["access_type"] == "ONGOING" and not r.get("stopped")]
            if ongoing:
                print(f"  {app['name']}: ONGOING request already present ({ongoing[0]['id']})")
                continue
            new_id = src.asc_create_ongoing_request(transport, headers, app_id)
            print(f"  {app['name']}: created ONGOING analytics request {new_id} "
                  f"(first instances land in ~24–48h)")
        except (HttpError, AuthError, RuntimeError) as exc:
            print(f"  {app['name']}: FAILED — {str(exc)[:200]}")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Store health reporter for Google Play + App Store Connect")
    ap.add_argument("command", nargs="?", default="report", choices=("report", "doctor", "bootstrap"))
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
    args = ap.parse_args()

    cfg = apply_mode(load_config(args.config), args.mode)
    transport = Transport(timeout=cfg["http_timeout"], retries=cfg["http_retries"])
    creds = Creds(cfg, transport)
    app_filter = set(args.apps.split(",")) if args.apps else None

    if args.command == "doctor":
        return cmd_doctor(cfg, creds, transport, app_filter)
    if args.command == "bootstrap":
        return cmd_bootstrap(cfg, creds, transport, app_filter)

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
    with open(base + ".json", "w") as fh:
        json.dump(report, fh, indent=2, default=str)
    title = html.escape(f"{cfg['brand']['org']} {cfg['brand']['product']} stores")
    inner = render_inner(report)
    with open(base + ".inner.html", "w") as fh:
        fh.write(inner)
    with open(base + ".html", "w") as fh:
        fh.write(SKELETON_HEAD.format(title=title) + inner + SKELETON_TAIL)
    with open(base + ".render.html", "w") as fh:
        fh.write(SKELETON_HEAD.format(title=title) + render_inner(report, image=True) + SKELETON_TAIL)
    with open(base + ".slack.txt", "w") as fh:
        fh.write(render_slack(report))
    with open(base + ".md", "w") as fh:
        fh.write(render_md(report))
    written = "json,html,inner.html,render.html,slack.txt,md"

    # One self-contained report per store: each is delivered as its own message, so each
    # gets its own digest, dashboard and triage file. A store with no data writes nothing.
    ready = []
    for st, tag in (("ios", "apple"), ("play", "play")):
        if not store_has_any_data(report, st):
            continue
        ready.append(tag)
        with open(f"{base}.{tag}.slack.txt", "w") as fh:
            fh.write(render_store_slack(report, st))
        with open(f"{base}.{tag}.md", "w") as fh:
            fh.write(render_store_md(report, st))
        store_title = html.escape(f"{cfg['brand']['org']} {STORE_LABEL[st]}")
        with open(f"{base}.{tag}.html", "w") as fh:
            fh.write(SKELETON_HEAD.format(title=store_title)
                     + render_inner(report, store=st) + SKELETON_TAIL)
        with open(f"{base}.{tag}.render.html", "w") as fh:
            fh.write(SKELETON_HEAD.format(title=store_title)
                     + render_inner(report, image=True, store=st) + SKELETON_TAIL)
        written += f",{tag}.{{slack.txt,md,html,render.html}}"

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
    for st, tag in (("ios", "apple"), ("play", "play")):
        state = (f"{STATUS_LABEL[report['overall_by_store'][st]]}" if tag in ready
                 else "no data — nothing to report")
        print(f"  store {STORE_LABEL[st]:12} {state}")
    print(f"stores_ready: {','.join(ready) if ready else 'none'}")
    print(f"base_path: {base}")
    print(f"written: {base}.{{{written}}}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
