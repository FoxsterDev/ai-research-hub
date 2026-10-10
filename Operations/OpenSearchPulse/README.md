# OpenSearch Pulse

A generic, config-driven daily health reporter for any OpenSearch log domain
whose documents are partitioned into per-day indices (`{prefix}{YYYY-MM-DD}`).

It queries error/warning volume, unique users, top error/warning signatures,
per-category breakdowns, custom message signals (with affected users), version
distribution, and a period-over-period comparison. It also classifies signatures
for **log hygiene** (mute / fix / UX-review), derives **business-metric funnels**
from message phrases, and renders a per-issue **business-impact bar** — then
produces an HTML dashboard and a delivery-ready summary. Read-only: it issues only
`_cat` and `_search` requests.

This tool is intentionally free of any endpoint, org, project, or credential
data — everything target-specific lives in a JSON config file the caller
supplies. That keeps this directory safe to share publicly.

## Requirements

- Python 3.9+ (standard library only; no third-party packages).
- The host must already be able to **reach** the domain. For a VPC-only AWS
  OpenSearch domain that means being on the VPN / Zero Trust tunnel / same VPC.
  This tool does not establish network access.
- If the domain requires an API key, name the env var that holds it in
  `api_key_env`; the value is read from the environment and never stored here.

## Configure

Copy `config.example.json`, fill it in for your domain, and keep the filled
copy out of this public directory (see the project-specific caller below).

Key fields:

| Field | Meaning |
|---|---|
| `base_url` / `base_url_env` | Endpoint inline, or the env var to read it from. |
| `api_key_env` / `api_key_header` | Optional auth; value comes from the env, header name defaults to `x-api-key`. |
| `window_days` | Comparison window length; current = last N complete days, baseline = the N before. |
| `max_aggs_per_search` | Top-level aggregations per search request (default 2). A wide aggregation over a high-volume index can outrun the domain's search-backpressure cancellation bar (30s of SearchShardTask elapsed time); the engine splits the query into this many aggregations per request and merges the results. Lower it if shard tasks are still cancelled. |
| `server_type` | Filter to prod traffic only (`{field, value}`); set `value` to `""` to disable. |
| `fields` | Map of logical field → OpenSearch field (use `.keyword` for aggregations). |
| `projects` | Explicit `{prefix, name}` list. |
| `auto_discover` + `discover_contains` | Also pick up any index prefix containing this substring. |
| `signals` | Named `match_phrase` counters over the message text (`{phrase, label}`); each reports events **and** affected users. |
| `funnels` | Business-metric funnels: ordered stages counted by message phrase with `cardinality(user)`, plus conversion `rates`. See below. |
| `overview` | Optional fixed portfolio surface: family mapping and ordered supporting metrics. Per-platform store state, stability, versions and configured flows use fixed positions; missing values render explicitly rather than being inferred. |
| `durations` | Duration metrics: percentiles of a numeric attribute carried by one message phrase, per platform × cohort (e.g. time to lobby for new vs existing users). See below. |
| `incidents` | Portfolio-wide incident detectors over a phrase family (e.g. backend HTTP 5xx), bucketed by time; each incident window reports start/end, users, peak, endpoints, apps and whether it is resolved or still ongoing at the end of the window. See below. |
| `hygiene` | Ordered issue rule table shared by the log-sanitation view and the per-issue impact bar. See below. |
| `thresholds` | `degraded_pct` / `watch_pct` on the error-rate delta; `new_release_min_share`. |
| `brand` | `org` + `product` shown in the header. |

## Run

```bash
export OPENSEARCH_PULSE_URL="https://your-domain..."   # if using base_url_env
python3 opensearch_pulse.py --config /path/to/config.json --out /path/to/reports
```

Optional: `--day YYYY-MM-DD` (the completed day to report on; default = yesterday UTC),
`--baseline-days N`, `--slug name`. (`--today`/`--window` accepted as aliases.)

## Model: report day vs baseline

- Reports **one completed day**; compares it to the **N days before it** (diff %).
- **Baseline source is disk-first**: if prior `<slug>_<date>.json` reports for the
  baseline days exist in `--out`, the baseline and the appeared/disappeared signature
  comparison are read **from those saved reports**; OpenSearch is queried for the
  baseline only when no prior report covers a project. Run daily and history accrues.

## Outputs (never posted anywhere by this tool)

- `<slug>_<day>.json` — raw computed metrics (also the baseline source for future days)
- `<slug>_<day>.html` — standalone dashboard (theme-aware, self-contained, sortable),
  incl. the impact bar, business funnels and log-hygiene sections per project
- `<slug>_<day>.inner.html` — body-only fragment for embedding / preview
- `<slug>_<day>.slack.txt` — delivery-ready summary text (error/warning rate and reach deltas,
  new/gone signatures, the worst-issue action, and funnel highlights)
- `<slug>_<day>.md` — structured, fix-oriented report (per-signature total/users/%DAU and
  baseline dynamics for errors and warnings, the impact bar, funnels, hygiene buckets, versions by platform,
  new/resolved signatures,
  representative stacktraces) for AI/engineer triage
- `<slug>_<day>.overview.slack.txt` — first Slack-safe overview part; every project card is atomic
- `<slug>_<day>.overview.part-NN.slack.txt` — continuation parts when the portfolio exceeds one
  Slack message; project counts are balanced across the minimum number of parts
- `<slug>_<day>.overview.parts` — ordered basename manifest consumed by resumable delivery
- `<slug>_<day>.overview.md` — expanded work-ready version of the same portfolio surface,
  including trigger ownership and explicit coverage gaps

Delivery (Slack, email, etc.) is a separate, explicit step owned by the caller.
Pair the outputs with a delivery integration such as `AIRoot/Operations/CodexSlackMcp/`.

## Log hygiene, business funnels & impact bar

Three config-driven capabilities turn the raw error stream into a triage- and
business-ready report. All are generic mechanisms; every domain-specific value
(phrases, verdicts, impact text, owners) lives in the config.

**`funnels`** — first-class business metrics derived from message phrases (works
even when structured attributes are not aggregatable). Each funnel is a set of
ordered `stages`, each matched by a `phrase` (optionally scoped to a `category`
or `level`); the engine reports each stage's affected users and % of DAU, and
computes the `rates` you declare. A rate's `den` is `"dau"`, a single stage key,
or a **list** of stage keys (summed — e.g. `success ÷ (success+failed)`). Scope a
funnel to specific projects with `"apps": ["KEY", …]`; funnels with no activity
for a project are dropped automatically. Give a rate optional `good_at` / `bad_at`
thresholds to colour it green / amber / red (direction from `good: "high"|"low"`);
rates **without** thresholds render neutral, so reach / volume / expected-noise
rates are never mislabelled good-or-bad.

A stage emitted only inside a client-side debug sample (for example a `Debug`-level line that
the logger ships for a percentage of sessions) is flagged `"debug_sampled": true`. The engine
then matches it only on documents whose `fields.debug_mode` boolean (default `DebugMode`) is
`true`, reports its users as a share of those sampled sessions instead of DAU, appends
`debug-sampled` to its label, and lets a rate use it only together with other sampled stages
(or `"dau"`, which then means the sampled sessions). A rate that mixes a sampled stage with an
unsampled one, or a sampled stage inside a `split_by_tag` funnel, is rejected at config load.

```jsonc
"funnels": [{
  "key": "signup", "label": "Signup", "apps": ["APP1"],
  "note": "shown under the note line",
  "stages": [
    {"key": "start", "label": "Started",   "phrase": "signup started",  "category": "Auth"},
    {"key": "done",  "label": "Completed", "phrase": "signup completed", "category": "Auth"}
  ],
  "rates": [
    {"label": "completion", "num": "done", "den": "start", "good": "high",
     "good_at": 95, "bad_at": 85, "business": "share of entrants who finish"}
  ]
}]
```

**`hygiene`** — an ordered rule table (first match wins) that classifies every top
error/warning signature into a `verdict` (`mute` / `fix` / `ux-assess` / `review`)
and attaches impact fields. A rule's `match` combines any of: `category`,
`level`, `empty_message: true` (the empty-message/stack-only class), `phrase`
(string or list; substring, case-insensitive), and `regex`. The optional
`ux` / `business` / `owner` / `action` strings feed the impact bar. Unmatched
signatures fall to `hygiene.default`.

```jsonc
"hygiene": {
  "default": {"verdict": "review"},
  "rules": [
    {"match": {"empty_message": true}, "verdict": "fix",
     "ux": "…", "business": "…", "owner": "…", "action": "…"},
    {"match": {"category": "Ads", "phrase": ["no fill", "timeout"]}, "verdict": "ux-assess", "…": "…"},
    {"match": {"regex": "missing script|referenced script"}, "verdict": "mute", "…": "…"}
  ]
}
```

The report renders a **log-hygiene** section (mute/fix/ux-assess buckets with
counts, events and worst reach) and a per-project **business-impact bar** (the
highest-reach `fix`/`ux-assess` issues, each with affected users + %DAU, events,
events-per-affected-user, platform/version split, and the rule's UX/business/
action/owner). Impact is only asserted for signatures a rule actually matched —
unmatched issues stay `review`, never fabricated impact. Secrets are redacted
before classification, so no secret value reaches any output.

## Duration metrics (`durations`)

A funnel says how many users reached a stage; a duration metric says how long it took. Each
entry names one message phrase (optionally scoped to a `category` / `level`) whose stringified
attributes blob carries a numeric `attribute` (for example `StartupSummary` with `durationMs`).
The engine computes the configured `percentiles` of that attribute with a scripted percentiles
aggregation (the blob is text, so the number is regexed out of `_source` per document — one
request per project and metric), per platform and per `cohort`, plus the all-platform total.

A cohort is a `match_phrase` on the attributes text (`attributes_phrase`) or its negation
(`exclude_attributes_phrase`); with the standard analyzer the phrase `sessionNumber 1 durationMs`
matches exactly `"sessionNumber":1,"durationMs"`, so attribute order in the blob is what makes the
cohort precise. `thresholds` are per cohort and percentile (`watch` / `alert`, higher is worse);
a cohort under `min_samples` documents is reported as low sample, never as a number. Values are
divided by `divisor` and labelled with `unit`. Baselines come from the prior saved reports, like
the funnel rates, and the overview prints one line per platform:
`Load time (p50/p90): new install 11.6s/31.0s · existing 1.5s/3.8s`. A cohort over its bar
colours the platform row, raises an overview trigger and appears in *Needs attention*.

```jsonc
"durations": [{
  "key": "time_to_ready", "label": "Time to ready", "short_label": "Load time",
  "phrase": "StartupSummary", "category": "Loading", "attribute": "durationMs",
  "divisor": 1000, "unit": "s", "percentiles": [50, 90], "min_samples": 30,
  "cohorts": [
    {"key": "new",       "label": "new install", "attributes_phrase": "sessionNumber 1 durationMs"},
    {"key": "returning", "label": "existing",    "exclude_attributes_phrase": "sessionNumber 1 durationMs"}
  ],
  "thresholds": {"returning": {"p50": {"watch": 3, "alert": 6}, "p90": {"watch": 6, "alert": 10}}}
}]
```

Requires Painless scripting with regex enabled on the domain (`script.painless.regex.enabled`);
when the aggregation is rejected the metric is reported as *query failed*, never as zeros.

## Release row (`overview.release_compare`)

Every platform card has two rows: *Now* (this window's value of each printed metric with its
temporal delta) and *Release* (`v<current> (<rollout>%) vs <previous>: <verdict> — …`). The release
cohorts are the two newest sufficiently sampled versions on that platform; the compared metrics are
errors/user and the store crash rate per release (already selected), the project's configured
`loading` secondary metric and `reward_complete` recomputed per version (funnel stages are also
aggregated per platform × version), and the first/declared duration metric's cohort percentile per
version. Noise bands and bars: `err_same_pct` / `err_better_pct`, `crash_same_pct` /
`crash_better_pct`, `rate_same_pp` (funnel pp band; watch/alert come from the secondary metric's
`delta_watch_pp` / `delta_alert_pp`), `duration_key` / `duration_cohort` / `duration_percentile`
with `duration_same_delta` / `duration_watch_delta` / `duration_alert_delta`, and `min_metrics`
(comparable metrics needed for a verdict). Verdict: WORSE on any alert-level regression or two
watch-level ones, WATCH on one, BETTER when something improved and nothing regressed, SAME
otherwise; below the sample gates the row prints the reason.

## Incidents (`incidents`)

Per-project health is a day-level average and hides a 45-minute backend outage. An incident
detector counts affected users per time bucket (`interval_minutes`) for a phrase family —
`phrases` (any of) and/or `require_phrases` (all of), optionally scoped to a `category` — over the
whole source, all apps at once. A bucket is *hot* when its users reach both `min_users` and
`spike_factor` × the window's median bucket (its typical quiet level, zero buckets included); hot
buckets separated by at most `max_gap_buckets` quiet ones form one incident window. For each
window the engine reports start/end (UTC), duration, distinct users, peak users per bucket, the
top endpoints (`endpoint_regex` group 1 applied to the message signature, e.g. `'([^']+)'` for
`>> 'api/core/Login' RETRY SCHEDULED …`), the apps touched with their users, and the status:
`resolved`, or `ONGOING` when the last hot bucket touches the end of the report window (on a
rolling report that means *now*).

Incidents print at the top of the Slack overview before any project card, in *Needs attention*
of the technical message, and as a table in both markdown reports. A detector whose scan failed
is printed as *not measured*; silence is never implied.

```jsonc
"incidents": [{
  "key": "backend_5xx", "label": "Backend HTTP 5xx",
  "phrases": ["HTTP/1.1 500", "HTTP/1.1 502", "HTTP/1.1 503", "HTTP/1.1 504"],
  "require_phrases": ["ServerError"], "category": "Network",
  "interval_minutes": 5, "min_users": 40, "spike_factor": 5, "endpoint_regex": "'([^']+)'"
}]
```

## Health model

- **error rate** = errors ÷ report-day DAU; compared to the baseline daily average.
- Status is the worst of relative error movement, absolute errors/user and DAU loss against the
  baseline. Below `min_dau` or without a usable baseline is **Low data** unless an absolute/traffic
  guard already proves Watch/Degraded. Zero DAU after a measured baseline is Degraded.
- HTTP success is not data success: `timed_out`, failed shards, missing aggregations, missing
  required indices and failed project queries enter the `trust` envelope and forbid Healthy.
- The expected split-source population includes configured app ids even when no bucket/index is
  returned. Query failures remain visible as health rows.
- Headline reach = per-signature affected users ÷ that day's DAU. Message groups are
  exact `.keyword` signatures; variable tails fragment counts — read them as signatures.

Every output is redacted again at persistence and written with same-directory temp + fsync +
atomic replace. Corrupt baseline candidates are surfaced instead of silently changing history.
