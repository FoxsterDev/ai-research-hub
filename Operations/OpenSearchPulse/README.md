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
| `server_type` | Filter to prod traffic only (`{field, value}`); set `value` to `""` to disable. |
| `fields` | Map of logical field → OpenSearch field (use `.keyword` for aggregations). |
| `projects` | Explicit `{prefix, name}` list. |
| `auto_discover` + `discover_contains` | Also pick up any index prefix containing this substring. |
| `signals` | Named `match_phrase` counters over the message text (`{phrase, label}`); each reports events **and** affected users. |
| `funnels` | Business-metric funnels: ordered stages counted by message phrase with `cardinality(user)`, plus conversion `rates`. See below. |
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
- `<slug>_<day>.slack.txt` — delivery-ready summary text (with the worst-issue action + funnel highlights)
- `<slug>_<day>.md` — structured, fix-oriented report (per-signature total/users/%DAU,
  the impact bar, funnels, hygiene buckets, versions by platform, new/resolved errors,
  representative stacktraces) for AI/engineer triage

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

## Health model

- **error rate** = errors ÷ report-day DAU; compared to the baseline daily average.
- **Degraded** when the error-rate diff ≥ `degraded_pct`, **Watch** at ≥ `watch_pct`,
  else **Healthy**; below `min_dau` DAU → **Low data** (excluded from severity).
  Overall status is the worst project.
- Headline reach = per-signature affected users ÷ that day's DAU. Message groups are
  exact `.keyword` signatures; variable tails fragment counts — read them as signatures.
