# AI External Repo Path Migration Runbook

## Purpose
Use this runbook only if the optional external-repo feature is re-enabled in the future.

Current policy:
- do not keep an active submodule binding for `external_repo_test_1`
- keep external repo content as optional local material only

If the feature is re-enabled later, create a fresh migration plan for the chosen transport instead of assuming an active submodule.
