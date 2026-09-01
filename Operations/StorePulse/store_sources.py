"""Per-source collectors for Store Pulse.

Every collector takes an explicit transport plus already-resolved credentials and
returns a plain dict. No collector reads config globals, so each one is callable
from a test with a fake transport and a recorded payload.

Read-only, with one exception that is opt-in and creates nothing but a report
request: `asc_create_request` (used by `store_pulse.py bootstrap`).
"""

import csv
import datetime as dt
import io
import os
import re
import sys
import urllib.parse

from store_auth import HttpError

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from report_safety import redact

PLAY_REPORTING = "https://playdeveloperreporting.googleapis.com/v1beta1"
PLAY_PUBLISHER = "https://androidpublisher.googleapis.com/androidpublisher/v3"
GCS_API = "https://storage.googleapis.com/storage/v1/b"
ASC_API = "https://api.appstoreconnect.apple.com/v1"
ITUNES_LOOKUP = "https://itunes.apple.com/lookup"
PLAY_TZ = "America/Los_Angeles"

def clean_user_text(text, limit=240):
    """Review text is user content: redact, collapse whitespace, truncate."""
    flat = re.sub(r"\s+", " ", redact(text or "")).strip()
    return flat[:limit] + ("…" if len(flat) > limit else "")


def _date_params(prefix, day, with_tz=True, tz=None):
    out = {f"{prefix}.year": day.year, f"{prefix}.month": day.month, f"{prefix}.day": day.day}
    if with_tz:
        out[f"{prefix}.timeZone.id"] = tz or PLAY_TZ
    return out


def _date_obj(day):
    return {"year": day.year, "month": day.month, "day": day.day, "timeZone": {"id": PLAY_TZ}}


def _parse_date_obj(obj):
    if not obj:
        return None
    try:
        return dt.date(int(obj["year"]), int(obj["month"]), int(obj["day"]))
    except (KeyError, TypeError, ValueError):
        return None


def _num(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        pass
    if isinstance(value, str):
        try:
            return float(value.replace(",", "").replace("\u00a0", "").strip())
        except ValueError:
            return None
    return None


parse_num = _num


# --------------------------------------------------------------- iTunes lookup

def itunes_lookup(transport, bundle_id, storefronts=("us",)):
    """Public App Store aggregate rating per storefront. Needs no credentials."""
    out = {"bundle_id": bundle_id, "storefronts": {}, "track_id": None, "name": None}
    for cc in storefronts:
        q = urllib.parse.urlencode({"bundleId": bundle_id, "country": cc,
                                    "entity": "software", "limit": 1})
        data = transport.json(f"{ITUNES_LOOKUP}?{q}")
        results = data.get("results") or []
        if not results:
            out["storefronts"][cc] = {"listed": False}
            continue
        r = results[0]
        out["track_id"] = out["track_id"] or r.get("trackId")
        out["name"] = out["name"] or r.get("trackName")
        count = int(r.get("userRatingCount") or 0)
        count_current = int(r.get("userRatingCountForCurrentVersion") or 0)
        # A storefront with no ratings reports 0.0, which is not a score — keep it null
        # so it can never be read as a rating or as a drop from one.
        out["storefronts"][cc] = {
            "listed": True,
            "avg": _num(r.get("averageUserRating")) if count else None,
            "count": count,
            "avg_current": _num(r.get("averageUserRatingForCurrentVersion")) if count_current else None,
            "count_current": count_current,
            "version": r.get("version"),
            "released": (r.get("currentVersionReleaseDate") or "")[:10],
            "min_os": r.get("minimumOsVersion"),
        }
    return out


# ------------------------------------------------------------- Play: vitals

def play_metric_freshness(transport, headers, package, metric_set, period="DAILY"):
    data = transport.json(f"{PLAY_REPORTING}/apps/{package}/{metric_set}", headers=headers)
    for entry in (data.get("freshnessInfo") or {}).get("freshnesses") or []:
        if entry.get("aggregationPeriod") == period:
            return _parse_date_obj(entry.get("latestEndTime"))
    return None


def play_metric_query(transport, headers, package, metric_set, metrics, start, end,
                      dimensions=(), page_size=1000, max_pages=50):
    body = {
        "timelineSpec": {"aggregationPeriod": "DAILY",
                         "startTime": _date_obj(start), "endTime": _date_obj(end)},
        "metrics": list(metrics),
        "dimensions": list(dimensions),
        "pageSize": page_size,
    }
    rows = []
    for _ in range(max_pages):
        data = transport.json(f"{PLAY_REPORTING}/apps/{package}/{metric_set}:query",
                              method="POST", payload=body, headers=headers, retry_safe=True)
        for row in data.get("rows") or []:
            day = _parse_date_obj(row.get("startTime"))
            dims = {}
            for d in row.get("dimensions") or []:
                dims[d.get("dimension")] = (d.get("stringValue") or d.get("int64Value")
                                            or d.get("valueLabel"))
            vals = {}
            for m in row.get("metrics") or []:
                raw = m.get("decimalValue", {}).get("value")
                if raw is None:
                    raw = m.get("value")
                vals[m.get("metric")] = _num(raw)
            rows.append({"day": day.isoformat() if day else None, "dims": dims, "metrics": vals})
        token = data.get("nextPageToken")
        if not token:
            break
        body["pageToken"] = token
    return rows


def play_vitals(transport, headers, package, day, metric_sets, trail_days=7):
    """Query each configured metric set over [day-trail, day], clamped to freshness."""
    out = {"sets": {}, "as_of": None, "errors": {}}
    newest = None
    for spec in metric_sets:
        name = spec["metric_set"]
        try:
            fresh = play_metric_freshness(transport, headers, package, name)
            end = min(day, fresh) if fresh else day
            rows = play_metric_query(transport, headers, package, name, spec["metrics"],
                                     end - dt.timedelta(days=trail_days), end,
                                     spec.get("dimensions", ()))
            days = sorted({r["day"] for r in rows if r["day"]})
            as_of = days[-1] if days else None
            overall = {}
            trail = {}
            for r in rows:
                if r["dims"]:
                    continue
                if r["day"] == as_of:
                    overall = r["metrics"]
                elif r["day"]:
                    trail[r["day"]] = r["metrics"]
            out["sets"][spec["key"]] = {
                "metric_set": name, "as_of": as_of, "overall": overall, "trail": trail,
                "breakdown": [r for r in rows if r["dims"] and r["day"] == as_of],
                # every dimensioned day in the window, not just as_of — the weekly
                # rollout diff needs per-version daily samples to weight and gate on
                "breakdown_trail": [r for r in rows if r["dims"] and r["day"]],
                "freshness": fresh.isoformat() if fresh else None,
            }
            if as_of and (newest is None or as_of > newest):
                newest = as_of
        except HttpError as exc:
            out["errors"][spec["key"]] = f"HTTP {exc.status}: {exc.detail[:160]}"
    out["as_of"] = newest
    return out


def play_error_issues(transport, headers, package, day, trail_days=1, limit=8,
                      issue_types=("CRASH", "ANR"), order_by="distinctUsers desc"):
    start = day - dt.timedelta(days=trail_days)
    params = {"pageSize": limit, "orderBy": order_by, "sampleErrorReportLimit": 1}
    # errorIssues:search accepts only UTC intervals, unlike the vitals queries.
    params.update(_date_params("interval.startTime", start, tz="UTC"))
    params.update(_date_params("interval.endTime", day + dt.timedelta(days=1), tz="UTC"))
    if issue_types:
        params["filter"] = " OR ".join(f"errorIssueType = {t}" for t in issue_types)
    url = f"{PLAY_REPORTING}/apps/{package}/errorIssues:search?{urllib.parse.urlencode(params)}"
    data = transport.json(url, headers=headers)
    issues = []
    for it in data.get("errorIssues") or []:
        issues.append({
            "type": it.get("type") or it.get("errorIssueType"),
            "cause": clean_user_text(it.get("cause"), 160),
            "location": clean_user_text(it.get("location"), 160),
            "reports": int(it.get("errorReportCount") or 0),
            "users": int(it.get("distinctUsers") or 0),
            "users_pct": _num((it.get("distinctUsersPercent") or {}).get("value")
                              if isinstance(it.get("distinctUsersPercent"), dict)
                              else it.get("distinctUsersPercent")),
            "first_version": it.get("firstAppVersion", {}).get("versionCode")
                             if isinstance(it.get("firstAppVersion"), dict) else it.get("firstAppVersion"),
            "last_version": it.get("lastAppVersion", {}).get("versionCode")
                            if isinstance(it.get("lastAppVersion"), dict) else it.get("lastAppVersion"),
            "uri": it.get("issueUri"),
        })
    return issues


def play_anomalies(transport, headers, package, limit=10):
    url = f"{PLAY_REPORTING}/apps/{package}/anomalies?{urllib.parse.urlencode({'pageSize': limit})}"
    data = transport.json(url, headers=headers)
    out = []
    for an in data.get("anomalies") or []:
        metric = an.get("metric") or {}
        day = _parse_date_obj((an.get("timelineSpec") or {}).get("startTime"))
        out.append({
            "metric_set": (an.get("metricSet") or "").split("/")[-1],
            "metric": metric.get("metric"),
            "value": _num((metric.get("decimalValue") or {}).get("value")),
            "dims": {d.get("dimension"): (d.get("stringValue") or d.get("int64Value"))
                     for d in an.get("dimensions") or []},
            "day": day.isoformat() if day else None,
        })
    return out


def play_release_catalog(transport, headers, package):
    """Currently serving releases per track, read-only via fetchReleaseFilterOptions.

    This is the only sanctioned versionCode→versionName source: it never opens an
    Android Publisher edit, but it also names only *serving* releases — historical
    codes stay unlabeled and callers must tolerate that.
    """
    data = transport.json(f"{PLAY_REPORTING}/apps/{package}:fetchReleaseFilterOptions",
                          headers=headers)
    tracks = []
    names = {}
    for track in data.get("tracks") or []:
        track_name = track.get("displayName") or track.get("type") or "?"
        releases = []
        for rel in track.get("servingReleases") or []:
            codes = [str(c) for c in rel.get("versionCodes") or []]
            label = rel.get("displayName") or rel.get("name")
            releases.append({"name": label, "codes": codes})
            for code in codes:
                # production wins when one code serves several tracks
                if code not in names or track_name == "production":
                    names[code] = {"name": label, "track": track_name}
        tracks.append({"track": track_name, "type": track.get("type"),
                       "releases": releases})
    return {"tracks": tracks, "version_names": names}


# ------------------------------------------------------------- Play: reviews

def play_reviews(transport, headers, package, max_results=100, translation=None):
    params = {"maxResults": max_results}
    if translation:
        params["translationLanguage"] = translation
    url = f"{PLAY_PUBLISHER}/applications/{package}/reviews?{urllib.parse.urlencode(params)}"
    data = transport.json(url, headers=headers)
    out = []
    for rv in data.get("reviews") or []:
        user, dev = {}, None
        for c in rv.get("comments") or []:
            if "userComment" in c and not user:
                user = c["userComment"]
            if "developerComment" in c:
                dev = c["developerComment"]
        ts = ((user.get("lastModified") or {}).get("seconds"))
        out.append({
            "stars": int(user.get("starRating") or 0),
            "text": clean_user_text(user.get("text")),
            "lang": user.get("reviewerLanguage"),
            "device": user.get("device"),
            "os": user.get("androidOsVersion"),
            "app_version": user.get("appVersionName") or user.get("appVersionCode"),
            "app_version_code": user.get("appVersionCode"),
            "app_version_name": user.get("appVersionName"),
            "thumbs_up": int(user.get("thumbsUpCount") or 0),
            "at": dt.datetime.fromtimestamp(int(ts), dt.timezone.utc).isoformat()[:19] if ts else None,
            "answered": dev is not None,
        })
    return out


# --------------------------------------------------- Play: bulk report bucket

def gcs_list(transport, headers, bucket, prefix, limit=200, max_pages=10):
    params = {"prefix": prefix, "maxResults": limit,
              "fields": "items(name,size,updated),nextPageToken"}
    items, token, pages = [], None, 0
    while pages < max_pages:
        q = dict(params)
        if token:
            q["pageToken"] = token
        data = transport.json(f"{GCS_API}/{bucket}/o?{urllib.parse.urlencode(q)}", headers=headers)
        items.extend(data.get("items") or [])
        token = data.get("nextPageToken")
        pages += 1
        if not token:
            break
    return items


def gcs_get_text(transport, headers, bucket, object_name):
    quoted = urllib.parse.quote(object_name, safe="")
    raw = transport.raw(f"{GCS_API}/{bucket}/o/{quoted}?alt=media", headers=headers)
    return decode_report_bytes(raw)


def decode_report_bytes(raw):
    """Play stats CSVs are UTF-16 with a BOM; other exports are UTF-8."""
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16")
    if raw[:3] == b"\xef\xbb\xbf":
        return raw.decode("utf-8-sig")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("utf-16", "replace")


def parse_delimited(text, delimiter=","):
    rows = list(csv.reader(io.StringIO(text), delimiter=delimiter))
    if not rows:
        return [], []
    header = [h.strip() for h in rows[0]]
    return header, [r for r in rows[1:] if any(c.strip() for c in r)]


def pick_col(header, candidates):
    lowered = [h.lower() for h in header]
    for cand in candidates:
        c = cand.lower()
        for i, h in enumerate(lowered):
            if h == c:
                return i
        for i, h in enumerate(lowered):
            if c in h:
                return i
    return None


def report_object(bucket_items, prefix, month):
    """Newest object under prefix matching the YYYYMM month token."""
    hits = [i for i in bucket_items if i["name"].startswith(prefix) and month in i["name"]]
    hits.sort(key=lambda i: i.get("updated", ""))
    return hits[-1] if hits else None


def play_csv_series(text, date_cols, value_cols, delimiter=","):
    """Generic {date -> {key: float}} extraction from a Play stats CSV.

    `value_cols` maps an output key to `{"cols": [candidate header names],
    "agg": "sum" | "last"}`. `sum` is for files with several rows per day
    (a country or version breakdown); `last` is for one-row-per-day overviews.
    """
    header, rows = parse_delimited(text, delimiter)
    di = pick_col(header, date_cols)
    if di is None:
        return {}, header
    idx = {}
    for key, spec in value_cols.items():
        cols = spec["cols"] if isinstance(spec, dict) else spec
        agg = spec.get("agg", "last") if isinstance(spec, dict) else "last"
        idx[key] = (pick_col(header, cols), agg)
    series = {}
    for row in rows:
        if di >= len(row):
            continue
        day = row[di].strip()[:10]
        bucket = series.setdefault(day, {})
        for key, (i, agg) in idx.items():
            if i is None or i >= len(row):
                continue
            val = _num(row[i].strip())
            if val is None:
                continue
            bucket[key] = bucket.get(key, 0.0) + val if agg == "sum" else val
    return series, header


# --------------------------------------------------------- App Store Connect

def asc_get(transport, headers, path, params=None, accept=None):
    hdrs = dict(headers)
    if accept:
        hdrs["Accept"] = accept
    url = f"{ASC_API}/{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True)
    return transport.json(url, headers=hdrs)


def asc_get_pages(transport, headers, path, params=None, max_pages=100):
    """Follow ASC JSON:API `links.next`; fail instead of returning a truncated catalogue."""
    first = asc_get(transport, headers, path, params)
    pages, data = [first], first
    while (data.get("links") or {}).get("next"):
        if len(pages) >= max_pages:
            raise HttpError(0, path, f"pagination exceeded safety bound ({max_pages} pages)")
        data = transport.json(data["links"]["next"], headers=headers)
        pages.append(data)
    return pages


def asc_app_by_bundle(transport, headers, bundle_id):
    data = asc_get(transport, headers, "apps",
                   {"filter[bundleId]": bundle_id, "limit": 5,
                    "fields[apps]": "name,bundleId,sku"})
    for item in data.get("data") or []:
        if (item.get("attributes") or {}).get("bundleId") == bundle_id:
            return {"id": item.get("id"), "name": (item["attributes"]).get("name")}
    items = data.get("data") or []
    if items:
        return {"id": items[0].get("id"), "name": (items[0].get("attributes") or {}).get("name")}
    return None


def asc_customer_reviews(transport, headers, app_id, limit=200, territory=None, max_pages=1):
    """Newest-first customer reviews. `max_pages` follows `links.next` for the deeper
    research modes; one page (200) is enough for the daily and weekly reports."""
    params = {"sort": "-createdDate", "limit": min(limit, 200), "include": "response"}
    if territory:
        params["filter[territory]"] = territory
    try:
        data = asc_get(transport, headers, f"apps/{app_id}/customerReviews", params)
    except HttpError as exc:
        if exc.status != 400:
            raise
        params.pop("include", None)
        data = asc_get(transport, headers, f"apps/{app_id}/customerReviews", params)
    pages = [data]
    while len(pages) < max_pages:
        nxt = ((data.get("links") or {}).get("next"))
        if not nxt:
            break
        data = transport.json(nxt, headers=headers)
        pages.append(data)
    out = []
    for page in pages:
        out.extend(_parse_reviews(page))
    return out


def _parse_reviews(data):
    out = []
    for rv in data.get("data") or []:
        attrs = rv.get("attributes") or {}
        resp = ((rv.get("relationships") or {}).get("response") or {}).get("data")
        out.append({
            "stars": int(attrs.get("rating") or 0),
            "title": clean_user_text(attrs.get("title"), 120),
            "text": clean_user_text(attrs.get("body")),
            "territory": attrs.get("territory"),
            "at": (attrs.get("createdDate") or "")[:19],
            "answered": bool(resp),
        })
    return out


def asc_review_submissions(transport, headers, app_id, limit=10):
    """App Review submission timeline. UNRESOLVED_ISSUES is what a rejection looks like here.

    The reviewer's actual message lives only in Resolution Center — there is no
    `resolutionCenterMessages` relationship on the API (verified: 404), so the most a tool
    can state is the submission state, when it was submitted, and how long it has sat.
    """
    data = asc_get(transport, headers, f"apps/{app_id}/reviewSubmissions", {"limit": limit})
    out = []
    for it in data.get("data") or []:
        a = it.get("attributes") or {}
        out.append({"id": it.get("id"), "state": a.get("state"),
                    "submitted": (a.get("submittedDate") or "")[:19],
                    "platform": a.get("platform"), "canceled": a.get("canceled")})
    out.sort(key=lambda x: x.get("submitted") or "", reverse=True)
    return out


def asc_review_detail(transport, headers, version_id):
    """Our own submission notes for a version. Contact fields are deliberately dropped:
    they are a colleague's name, phone and e-mail and have no place in a report."""
    try:
        data = asc_get(transport, headers, f"appStoreVersions/{version_id}/appStoreReviewDetail")
    except HttpError as exc:
        if exc.status in (404, 409):
            return None
        raise
    a = (data.get("data") or {}).get("attributes") or {}
    if not a:
        return None
    return {"notes": clean_user_text(a.get("notes"), 400),
            "demo_account_required": a.get("demoAccountRequired")}


def asc_versions(transport, headers, app_id, limit=5):
    params = {"limit": limit,
              "fields[appStoreVersions]": "versionString,appStoreState,appVersionState,createdDate,releaseType"}
    data = asc_get(transport, headers, f"apps/{app_id}/appStoreVersions", params)
    out = []
    for v in data.get("data") or []:
        a = v.get("attributes") or {}
        out.append({"id": v.get("id"), "version": a.get("versionString"),
                    "state": a.get("appVersionState") or a.get("appStoreState"),
                    "release_type": a.get("releaseType"),
                    "created": (a.get("createdDate") or "")[:10]})
    return out


def asc_phased_release(transport, headers, version_id):
    try:
        data = asc_get(transport, headers, f"appStoreVersions/{version_id}/appStoreVersionPhasedRelease")
    except HttpError as exc:
        if exc.status in (404, 409):
            return None
        raise
    attrs = (data.get("data") or {}).get("attributes") or {}
    if not attrs:
        return None
    return {"state": attrs.get("phasedReleaseState"), "day": attrs.get("currentDayNumber"),
            "start": (attrs.get("startDate") or "")[:10]}


def asc_analytics_requests(transport, headers, app_id):
    pages = asc_get_pages(transport, headers, f"apps/{app_id}/analyticsReportRequests",
                          {"limit": 50, "fields[analyticsReportRequests]":
                           "accessType,stoppedDueToInactivity"})
    return [{"id": r.get("id"),
             "access_type": (r.get("attributes") or {}).get("accessType"),
             "stopped": (r.get("attributes") or {}).get("stoppedDueToInactivity")}
            for data in pages for r in data.get("data") or []]


def asc_create_request(transport, headers, app_id, access_type="ONGOING"):
    """The one write in this module: register an analytics report request.

    ONGOING accrues a new instance per day from now on; ONE_TIME_SNAPSHOT backfills the
    trailing year once. Neither publishes anything — Apple simply exposes no way to read
    App Analytics without a registered request, so this is the price of the data.
    """
    payload = {"data": {"type": "analyticsReportRequests",
                        "attributes": {"accessType": access_type},
                        "relationships": {"app": {"data": {"type": "apps", "id": app_id}}}}}
    data = transport.json(f"{ASC_API}/analyticsReportRequests", method="POST",
                          payload=payload, headers=headers)
    return (data.get("data") or {}).get("id")


def asc_create_ongoing_request(transport, headers, app_id):
    return asc_create_request(transport, headers, app_id, "ONGOING")


def asc_analytics_reports(transport, headers, request_id, categories=(), name_filter=()):
    params = {"limit": 200}
    if categories:
        # comma-joined, not repeated keys: Apple answers a repeated filter with a 400
        params["filter[category]"] = ",".join(categories)
    pages = asc_get_pages(transport, headers,
                          f"analyticsReportRequests/{request_id}/reports", params)
    out = []
    for data in pages:
        for r in data.get("data") or []:
            a = r.get("attributes") or {}
            name = a.get("name") or ""
            if name_filter and not any(nf.lower() in name.lower() for nf in name_filter):
                continue
            out.append({"id": r.get("id"), "name": name, "category": a.get("category")})
    return out


def asc_report_instance(transport, headers, report_id, granularity="DAILY",
                        processing_date=None, limit=20):
    params = {"limit": limit, "filter[granularity]": granularity}
    if processing_date:
        params["filter[processingDate]"] = processing_date
    pages = asc_get_pages(transport, headers, f"analyticsReports/{report_id}/instances", params)
    items = [{"id": i.get("id"),
              "processing_date": (i.get("attributes") or {}).get("processingDate"),
              "granularity": (i.get("attributes") or {}).get("granularity")}
             for data in pages for i in data.get("data") or []]
    items.sort(key=lambda i: i.get("processing_date") or "")
    return items


def asc_instance_segments(transport, headers, instance_id):
    pages = asc_get_pages(transport, headers,
                          f"analyticsReportInstances/{instance_id}/segments", {"limit": 50})
    return [{"url": (s.get("attributes") or {}).get("url"),
             "size": (s.get("attributes") or {}).get("sizeInBytes")}
            for data in pages for s in data.get("data") or []]


def asc_segment_rows(transport, url, max_rows=None):
    """One analytics-report segment: a pre-signed gzip download, tab- or comma-delimited.

    The URL carries its own signature, so it is fetched WITHOUT the ASC auth header —
    Apple's storage front end rejects a request that also presents a bearer token.
    Apple documents these as CSV and ships them tab-delimited, so the delimiter is
    decided from the payload rather than trusted.
    """
    raw = transport.raw(url)
    text = decode_report_bytes(raw)
    first = text.split("\n", 1)[0]
    delimiter = "\t" if first.count("\t") >= first.count(",") else ","
    header, rows = parse_delimited(text, delimiter)
    out = []
    selected = rows if max_rows is None else rows[:max_rows]
    for row in selected:
        out.append({header[i]: row[i] for i in range(min(len(header), len(row)))})
    return header, out


PERF_PERCENTILE = {"percentile.fifty": "p50", "percentile.ninety": "p90"}


def asc_perf_series(raw, device="all_iphones"):
    """Flatten perfPowerMetrics into {(category, metric): entry} for one device slice.

    Apple keys these metrics by app version, not by date: the last point is the current
    release and the points before it are the versions to compare it against. Points are
    returned in Apple's own order, which is oldest-first.
    """
    out = {}
    for product in raw.get("productData") or []:
        for cat in product.get("metricCategories") or []:
            for metric in cat.get("metrics") or []:
                unit = metric.get("unit") or {}
                entry = out.setdefault((cat.get("identifier"), metric.get("identifier")),
                                       {"category": cat.get("identifier"),
                                        "metric": metric.get("identifier"),
                                        "unit": unit.get("identifier"),
                                        "unit_label": unit.get("displayName"),
                                        "percentiles": {}, "devices": {}})
                for ds in metric.get("datasets") or []:
                    crit = ds.get("filterCriteria") or {}
                    pct = PERF_PERCENTILE.get(crit.get("percentile"))
                    if not pct:
                        continue
                    points = [{"version": p.get("version"), "value": _num(p.get("value"))}
                              for p in ds.get("points") or []
                              if p.get("version") and _num(p.get("value")) is not None]
                    if not points:
                        continue
                    if crit.get("device") == device:
                        entry["percentiles"][pct] = points
                    else:
                        entry["devices"].setdefault(pct, []).append(
                            {"device": crit.get("deviceMarketingName") or crit.get("device"),
                             "version": points[-1]["version"], "value": points[-1]["value"]})
    return out


def asc_perf_insights(raw):
    """Apple's own regression / trending-up calls on the latest version."""
    out = []
    for direction in ("regressions", "trendingUp"):
        for group in (raw.get("insights") or {}).get(direction) or []:
            out.append({"direction": direction,
                        "category": group.get("metricCategory"),
                        "metric": group.get("metric"),
                        "version": group.get("latestVersion"),
                        "summary": group.get("summaryString"),
                        "reference_versions": group.get("referenceVersions") or []})
    return out


def asc_perf_power(transport, headers, app_id, platform="IOS"):
    """Xcode-Organizer metrics; the vendor Accept header is required, JSON is the fallback."""
    try:
        return asc_get(transport, headers, f"apps/{app_id}/perfPowerMetrics",
                       {"filter[platform]": platform},
                       accept="application/vnd.apple.xcode-metrics+json")
    except HttpError as exc:
        if exc.status not in (400, 406):
            raise
        return asc_get(transport, headers, f"apps/{app_id}/perfPowerMetrics",
                       {"filter[platform]": platform})
