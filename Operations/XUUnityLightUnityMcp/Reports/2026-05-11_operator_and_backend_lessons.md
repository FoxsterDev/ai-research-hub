# XUUnity Light Unity MCP Operator And Backend Lessons

Date: `2026-05-11`
Status: `public distilled lessons`
Scope: extract the highest-value public-safe lessons from earlier backend evaluation, hands-on harness work, and first real project build automation sessions

## Why This Exists

Several earlier evaluation and onboarding reports contained useful operating
lessons, but much of that value was trapped inside point-in-time notes.

This report keeps only the reusable lessons that still matter for the public
lightweight MCP contract.

## Backend Selection Lessons

### 1. Trustworthy validation beats broader raw power

When choosing a backend or adapter path, prefer the candidate that gives:
- correct final test accounting
- explicit ready state
- stable project targeting
- understandable operator flow

over the candidate that merely exposes:
- more tools
- broader mutation surface
- more extension points

If one backend can start tests but cannot report final totals reliably, it is a
weak validation backend even if its feature breadth is attractive.

### 2. Hidden runtime behavior is operator debt

Treat these as real costs, not minor setup details:
- runtime server auto-downloads
- token requirements for local-only bootstrap
- hidden network activity during first startup
- multi-step install flows that are hard to reason about in automation

A backend can still be useful with those costs, but the costs should count
against it for a conservative default path.

### 3. Extensibility and validation reliability are different strengths

One candidate can be better for:
- custom tool registration
- thin adapter experiments

while another is better for:
- install/open/wait/test loops
- repeatable validation
- honest final result accounting

Do not collapse those strengths into one score and assume the same backend
should own both jobs.

## Build Automation Lessons

### 1. Interactive editor control and artifact production should be split

The same-host MCP lane is strong for:
- health checks
- editor state
- scene inspection
- compile validation
- bounded smoke workflows

It is not the right primary waiter for long-running artifact builds.

Artifact production should prefer:
- batch mode
- process exit code
- generated outputs
- compact result artifacts

### 2. Generated output is stronger evidence than source inspection

For build-sensitive changes, verify:
- generated manifest
- generated plist
- generated Gradle/Xcode output
- built artifact

before trusting source-only inspection.

This is especially important when processors or post-build hooks can mutate the
final output after source inspection looked correct.

### 3. Automation should be non-destructive by default

Batch and profile-aware build automation should default to:
- no autorun
- no implicit config persistence
- no implicit version drift
- explicit tracked-file restore
- explicit reporting of whether state was restored

Manual interactive workflows can tolerate some state mutation.
Repeatable MCP automation should not assume that tolerance.

### 4. Long-running correctness should come from build facts, not wait-loop optimism

For artifact builds, success should be derived from:
- process exit
- artifact existence
- generated evidence
- compact result summary

not from:
- a still-open scenario request
- transport survival alone
- intermediate queued state

## Public Design Implications

These lessons strengthen the public lightweight MCP design in four ways:

1. keep the default service validation-first
2. keep artifact builds on a batch-oriented lane
3. keep evidence compact and explicit for operators
4. keep backend comparison grounded in trustworthy outcomes, not marketing breadth

## Recommended Reading

1. `../README.md`
2. `../BUILD_AUTOMATION.md`
3. `../COMPARISON.md`
4. `2026-05-07_unity_version_matrix.md`
