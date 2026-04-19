# XUUnity Task: Bug Fixing

## Goal
Resolve a concrete defect with the minimum safe change while preserving production stability.

## Focus
- Narrow the defect to ownership, threading, lifecycle, marshaling, state, or initialization order.
- Prefer low-risk fixes before structural redesign.
- Check project memory before changing platform or SDK behavior.
- For Android manifest, Gradle, resolver, or SDK-startup defects, verify that the inspected generated artifacts come from the same fresh build being diagnosed.
- If `Library/` was deleted, reimport is in progress, or generated Bee/Gradle outputs may predate a clean rebuild, treat those artifacts as potentially stale evidence rather than root-cause proof.
- Before proposing a source-level fix for vendor-managed manifest entries, inspect the same-build `Editor.log` for resolver and postprocess execution.
- Do not convert a vendor-owned build-time declaration into a permanent checked-in source fix unless a clean rebuild reproduces the failure and ownership transfer is explicitly justified.

## Output
- Root cause
- Fix strategy
- Regression risk
- Validation steps
