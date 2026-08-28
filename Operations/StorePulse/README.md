# Store Pulse

A generic, config-driven store-health reporter for a mobile app portfolio. It reads
**Google Play** and **Apple App Store Connect** per app and answers three questions
every day: *is the store-visible score moving*, *what are users saying*, and *is the
platform's own telemetry saying our builds are unhealthy* — then adds the store funnel
and release state as the context that makes those numbers readable.

It produces JSON, a self-contained dashboard, a delivery-ready digest, a **compact block
for embedding into an existing report**, and a triage markdown file. Delivery (Slack,
e-mail) is a separate, explicit step owned by the caller.

The tool holds no app, org or credential data: everything target-specific lives in the
JSON config the caller supplies, and every secret is read from a path named by an
environment variable. Nothing here is safe-to-share-sensitive.

## Requirements

- Python 3.9+, standard library only. No `requests`, no `google-auth`, no `PyJWT`.
- `openssl` on `PATH` — provider JWTs are signed by delegating to it (RS256 for Google,
  ES256 with a DER→JWS conversion for Apple).
- Outbound HTTPS. Nothing needs a VPN.

## Data sources and what each needs

| Slice | Source | Credential |
|---|---|---|
| `ios_rating` | public iTunes Lookup (`bundleId`, per storefront) | **none** |
| `ios_reviews` | App Store Connect `customerReviews` | Apple key |
| `ios_release` | ASC `appStoreVersions` + phased release | Apple key |
| `ios_analytics` | ASC analytics reports → instances → gzip segments (crashes, sessions, installs/deletions) | Apple **Admin** key (+ a registered request) |
| `ios_perf` | ASC `perfPowerMetrics` (hangs, launch, memory, disk, battery, terminations) | Apple key |
| `play_vitals` | Play Developer Reporting API metric sets | Google service account |
| `play_issues` | Reporting API `errorIssues:search` | Google service account |
| `play_anomalies` | Reporting API `anomalies.list` | Google service account |
| `play_reviews` | Android Publisher `reviews.list` | Google service account |
| `play_rating` | Play Console bulk CSV `stats/ratings/…` | Google SA + reports bucket |
| `play_store_perf` | bulk CSV `stats/store_performance/…` | Google SA + reports bucket |
| `play_installs` | bulk CSV `stats/installs/…` | Google SA + reports bucket |

Aggregate App Store ratings are not exposed by the App Store Connect API, so `ios_rating`
uses Apple's public lookup endpoint; that slice runs with **no credentials at all**, which
makes the tool useful on day one. Play has no ratings metric set either — Play ratings come
from the Console's bulk CSV export, read here over the plain GCS JSON API (no `gsutil`).

## Configure

Copy `config.example.json`, fill in the `apps` table, and keep the filled copy outside this
directory. Key fields:

| Field | Meaning |
|---|---|
| `apps[]` | `{key, name, android, ios}` — the package name and bundle id. `ios_app_id` is resolved automatically and cached into the report. Either identifier may be `null`. |
| `storefronts` | Lookup storefronts; the first is the headline one. |
| `slices` | Per-slice on/off; `apps[].slices` overrides per app. |
| `credentials` | The **names** of the env vars holding credential paths — never values. |
| `thresholds` | Rating floors and drops, Play vitals bars, negative-review shares, conversion drops. |
| `play_vitals_sets` | Which Reporting API metric sets, metrics and dimensions to query. |
| `play_reports` | Bulk-CSV specs: object path template plus which header names map to which value, and whether a value is summed across rows (`sum`, for country/version breakdowns) or read once per day (`last`). |
| `review_topics` | Phrase buckets used to classify negative reviews. |

## Run

```bash
export STORE_PULSE_GOOGLE_SA_JSON=~/keys/play-sa.json     # optional
export STORE_PULSE_ASC_KEY_P8=~/keys/AuthKey_ABC123.p8    # optional
export STORE_PULSE_ASC_KEY_ID=ABC123
export STORE_PULSE_ASC_ISSUER_ID=1a2b3c4d-…
export STORE_PULSE_PLAY_BUCKET=pubsite_prod_rev_01234567890123456789

python3 store_pulse.py report --config /path/to/config.json --out /path/to/reports
python3 store_pulse.py doctor --config /path/to/config.json     # what is reachable, per app per slice
python3 store_pulse.py bootstrap --config /path/to/config.json  # register the Apple analytics requests
python3 store_pulse.py bootstrap --config /path/to/config.json \
    --access ONGOING,ONE_TIME_SNAPSHOT                          # + backfill the trailing year
```

Options: `--day YYYY-MM-DD`, `--slug NAME`, `--only slice,slice`, `--apps KEY,KEY`, `--dive`,
`--access` (bootstrap only).

`doctor` is the credential-landing gate: it prints a per-app, per-slice `ok` / `FAIL` / `skip`
matrix with reasons and no secret values, then the analytics-request state per app — the thing
that gates the crash numbers. `bootstrap` is the tool's only write, and it only registers Apple
analytics report requests: `ONGOING` accrues one instance per day from registration on,
`ONE_TIME_SNAPSHOT` backfills the trailing year once, and either needs an **Admin-role** key
(a lesser role authenticates fine and then answers 403 on this one endpoint). Apple needs 24–48h
of lead time before the first instance exists, so run it as soon as the key lands.

## Model: snapshots, not a single day

The sources do not agree on "today": Play vitals are daily in America/Los_Angeles and lag
(the tool reads each metric set's `freshnessInfo` and clamps to the day the API admits to),
Play bulk CSVs land 1–2 days late inside a monthly file, Apple analytics is complete two days
after the fact, and the iTunes aggregate is a live lifetime number with no history at all.

So every metric carries its own `as_of`, and deltas are computed **disk-first**: each run
writes `<slug>_<day>.json`, and later runs read the newest earlier snapshot (plus the newest
one at least 6 days old) as the baseline. Run it daily and history accrues; the first run has
levels but no deltas. A `--only` run writes to `<slug>_partial_<day>` so a narrow run can
never overwrite the full daily snapshot other runs depend on.

## Status model

Per app, from explicit config thresholds — never an invented severity:

- **Play vitals**: `degraded` at or above Google's own bad-behaviour bars (user-perceived
  crash 1.09%, ANR 0.47%, or 8% on a single dimension slice), `watch` at `watch_fraction` of
  them. Below `min_vitals_users` the slice is marked low-data and scores nothing.
- **Rating**: `degraded` on a drop past `rating_drop_alert` (day-over-day) or
  `rating_drop_7d_alert`, and also on an absolute level below `rating_floor_alert` once at
  least `rating_floor_min_count` ratings exist. Thin samples get a `watch` with the sample
  size stated. Rising ratings are never flagged.
- **Reviews**: `watch`/`degraded` on the ≤2★ share of fresh reviews, gated by `neg_min_count`.
- **Conversion**: relative drop vs the trailing baseline.
- **Release**: rejected/removed states alert; an in-flight phased release is a `watch`,
  because it explains other deltas.
- **iOS device metrics** (`ios_perf`): per-metric `watch`/`alert` bars from the config's
  `ios_perf_metrics` table, plus a bar-free **regression** verdict — `perf_regression_watch_pct`
  / `_alert_pct` against the mean of the previous `ios_perf_baseline_versions` app versions, with
  a per-metric `min_for_regression` floor so a near-zero value cannot produce a large percentage.
  These metrics are keyed by app version, not by day, and each finding names the version its own
  metric reports on. At most `perf_findings_per_app` reach the attention list, severity first and
  then distance past the bar; the device table carries the rest. Apple's own `insights.regressions`
  strings are reported but score nothing, so one fact is not counted twice.
- **iOS crash rate** (`ios_analytics`): crashes per 1,000 sessions from the day's report instance,
  `ios_crash_per_1k_watch` / `_alert`, gated by `ios_crash_min_sessions`. A registered request with
  no instance yet is reported as pending — never as a failure, and never as data. Qualified
  per-version rows remain in `crash_delta.versions`, newest App Store release first, so consumers
  can retain the latest measured release while a new release accumulates data.
- **Play stability breakdowns** retain the API's raw `metrics` and add normalized percentage values
  plus `distinctUsers` in `metrics_pct`. This lets consumers compare sampled `versionCode` cohorts
  without guessing whether Google's value was a fraction or an already formatted percentage.
- An app with no store signal at all is `nodata` and is excluded from the overall verdict,
  which is the worst app verdict.

## Outputs (never posted anywhere by this tool)

- `<slug>_<day>.json` — computed metrics, per-slice `as_of`, errors; **the baseline** for later runs
- `<slug>_<day>.html` / `.render.html` — optional theme-aware dashboard (`--dashboard`)
- `<slug>_<day>.inner.html` — body-only fragment for embedding
- `<slug>_<day>.technical.{slack.txt,md}` — Store technical section for a caller to join
- `<slug>_<day>.experience.{slack.txt,md}` — ratings/reviews/releases/conversion report
- `<slug>_<day>.md` — combined local triage view

Every finding still records its store and nature. The CLI prints the concern outputs that are
ready; delivery remains owned by the caller.

## Review topics

Negative reviews are tagged by config-declared phrases (`review_topics`: a key, a label, its
phrases) and counted per topic, so a report can say *"5 of 7 complaints mention ads"* with the
matched phrases behind it. That is all this is — keyword matching, not interpretation: the engine
does not assign an owner, a diagnosis, or an action, and unmatched negatives are reported rather
than dropped so the phrase table can be extended.

`--mode daily|weekly|monthly` is an **explicit** override of the read depth (1 / 7 / 30 days, and
monthly reads 3 pages of history). Without the flag the config's own `review_window_days` /
`review_pages` stand — a host that declares a 7-day window means it, and the engine must not narrow
it by default. `weekly` and `monthly` write their own report series so they cannot overwrite the
daily baseline. Verbatim ≤2★ excerpts are included in the per-store report — redacted,
truncated, and with reviewer nicknames dropped.

Qualitative analysis of review content is deliberately **not** in this engine. Anything that
routes a complaint to a team or recommends an action is a judgement, and a judgement authored as a
config table only looks like analysis while actually being a static opinion that ages badly. If it
is wanted, it belongs in a real model call behind an explicit hook and an API key — not here.

## Privacy and safety

- Review bodies are user content: secret-redacted, whitespace-collapsed and truncated to
  `review_excerpt_chars`; **reviewer nicknames are dropped** before anything is written.
  No per-user profile is ever assembled.
- Read-only apart from `bootstrap`. No review replies, no metadata writes, no release actions.
- Credentials are read from env-named paths. Failures report the field name and whether a
  value exists — never the value. Temporary key material staged for signing is written 0600
  and removed in a `finally`.
- A failing slice is recorded against its app and never takes the report down; a missing
  credential disables its slices with a stated reason. Required incomplete slices suppress a
  green conclusion and are rendered as coverage, not as zero.
- App Analytics follows all JSON:API pages. Safety caps produce an explicit incomplete metric;
  rates use only matched app + instance-date components and expose their population.
- Outputs use same-directory temp files, fsync and atomic replace. Corrupt history candidates are
  surfaced in the `trust` envelope.
- POST retries are opt-in only for read/query operations. The bootstrap write is not replayed.
- All rendered text is HTML-escaped: an app name or review body cannot inject markup.

## Tests

```bash
python3 -m unittest discover -s tests
```

The provider paths are covered offline with recorded payload shapes (freshness clamping,
pagination, matched populations, typed/idempotent retry, UTF-16 CSVs, `include=response`
fallback and redaction), alongside scoring, completeness and rendering.
