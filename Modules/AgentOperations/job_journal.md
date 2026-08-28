# Job Journal

## Goal

Make a long multi-item job resumable, so an interruption costs one item instead
of the run. Use it when one job produces many artifacts - per-item generation, a
sweep across many projects, a staged migration - and a stall, quota limit, or
crash partway through is realistic.

This is ordinary checkpointing: a durable ledger plus idempotent per-item work.
When the host already provides a durable job runner, a resumable workflow
engine, or a build graph with idempotent targets, use that instead. This file is
for jobs driven from an agent session, where the only durable state is what the
session wrote to disk.

## Ledger Contract

- Create the ledger and one skeleton output per planned item before the first
  item runs. A missing file then means "not written yet", and the work list
  stops depending on session context that an interruption destroys.
- One row per item: id, destination path, status (`pending`, `in_progress`,
  `written`, `verified`, `failed`), attempt count, last update.
- Status changes are written when they happen, not collected at the end. A
  status the run knows and the file does not is lost at the interruption.

## Write Before Reporting

- An item is complete when its artifact exists, not when the step that produced
  it says so. Verify existence and non-triviality - a size floor, the required
  sections - before recording `written`.
- This matters most for delegated lanes: a worker's returned summary is not
  evidence that it wrote anything. A lane that returns prose with no artifact is
  a failed lane to retry, not a completed one (`subagent_delegation.md`).
- Bound retries per item and keep the attempt count in the ledger. Escalate a
  repeatedly failing item instead of looping on it.

## Resume And Repair

- Resume reads the ledger first, reports the status table, and continues only
  unfinished items. Re-running `verified` items to be safe is how a resume turns
  back into a restart.
- Include a repair pass for items that exist but are skeleton-only or truncated.
  A crash between create and write leaves exactly that shape, and existence
  alone cannot distinguish it from a finished artifact.
- When the run bounds its own coverage - top-N, sampling, a skipped retry -
  record what was dropped. Silent truncation reads as full coverage to the next
  reader.

## Reporting

- Report from the ledger rather than from recollection of the run: counts by
  status, which items remain, and the exact resume entry point.
