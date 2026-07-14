# Nexus Deletion Manifest — 2026-07-14

## Status

`remote_deletion_user_owned; local_source_archived`

This manifest records the completed extraction, validation, integration, and recovery gates. The user owns the remote GitHub deletion. The last local source was archived rather than deleted.

## Identified deletion scope

| Item | Exact identifier | Intended action | Current state |
| --- | --- | --- | --- |
| Private remote repository | `github.com/FoxsterDev/Unity-Nexus-Twin` | Permanently delete after confirmation | Identity recorded from local Git remote configuration and refs; authenticated access is not currently available. |
| Last local source clone | `/Users/siarheikha/Projects/FoxsterDev/Archive/Unity-Nexus-Twin` | Retain as a local archive | Moved on 2026-07-14; source commit and working-tree status were rechecked after the move. |
| Superseded nearby archive | `/Users/siarheikha/Documents/Разобрать/Unity-Nexus-Twin.zip` | No action requested | Still present; not needed for recovery after the verified backup below. |
| Verified recovery backup | `/Users/siarheikha/Documents/Nexus-Recovery/Unity-Nexus-Twin_2026-07-14T1408BRT` | Retain | Must not be deleted by this operation. |

## Source and recovery evidence

| Check | Result |
| --- | --- |
| Source commit | `756e18295743f3fc0ccf3abcfdd3f408b1cd7cd7` on `master` |
| Source remote | `https://github.com/FoxsterDev/Unity-Nexus-Twin.git` |
| Bundle recovery artifact | `Unity-Nexus-Twin.bundle` — SHA-256 `73f5d7e1bd69834d24952f131cb506097c90709b4c2036cf4c836330914ed210` |
| Full working-tree archive | `working-tree-full.tar.gz` — SHA-256 `b92fd4425570418682839f2cd1480f1c77a57e7b96c5e4a91939357f6e3a0230` |
| Restore guide | `RESTORE.md` — SHA-256 `f197017d4783f7baaece0fe163450a56e60c397c5426bc76d76421033cab5080` |
| Recovery validation | Bundle clone, archive extraction, all 18 checksums, tracked inventory comparison, staged diff application, and unstaged diff application passed. |

The source had local work beyond `origin/master` when captured: one commit ahead, staged changes, an unstaged registry change, untracked files, and ignored files. The full archive preserves that state; the Git bundle preserves repository refs.

## Knowledge-extraction triage and integration

The current XUUnity knowledge-extraction triage, review, integration, and system-maintenance contracts were used. The complete source-by-source rationale is in [the triage inventory](../../../../AIOutput/Reports/ReviewArtifacts/2026-07-14_nexus_decommission_inventory.md).

Integrated, source-backed knowledge:

| Destination | Integrated rule |
| --- | --- |
| `AIRoot/Modules/XUUnity/skills/async/unitask.md` | In shared single-flight work, caller cancellation is limited to that caller's wait; only the owner may cancel the shared operation. |
| `AIRoot/Modules/XUUnity/skills/tests/runtime_service_testability.md` | PlayMode singleton cleanup must not dispose or recreate lifetime infrastructure production cannot safely re-establish. |
| `ApperfunHub/Assets/AIOutput/ProjectMemory/platform_constraints.md` | `EligibleGeoCache` country and region eligibility outcomes must be retained and revalidated against active settings. |

Material already covered by stronger current XUUnity sources was not duplicated. Historical analyses were retained only under `ApperfunHub/Assets/AIOutput/Archive/2026-07_nexus_decommission/`; no Nexus-derived private material was copied into the public `AIRoot/Modules/XUUnity` core.

## Dependency removal and validation

| Gate | Result |
| --- | --- |
| Active `AIModules/Nexus` symlink | Removed after confirming no active dependency remains. |
| Active routes and launchers | Removed from the root router, project routers, Gemini launchers, setup check, operations docs, and relevant generated HTML. |
| Active-reference scan | Passed with zero results outside explicit historical/archive/review evidence. |
| Public-core private-reference scan | Passed with zero Nexus/private-path references in `AIRoot`. |
| XUUnity entrypoint kernel | Passed: `python3 AIRoot/Modules/XUUnity/scripts/check_entrypoint_kernel.py`. |
| Setup protocol check | Passed: `bash scripts/setup_ai_protocols.sh --check`. |
| XUUnity Python tests | Passed: 33 tests via `python3 -m unittest discover -s AIRoot/Modules/XUUnity/scripts/tests -p 'test_*.py'`. |
| Diff whitespace check | Passed: `git diff --check`. |
| Markdown lint/link tools | Not available in the environment (`markdownlint`, `markdown-link-check`, `lychee`, and `vale`). |

## Remote-access gate

On 2026-07-14, unauthenticated Git access failed because credentials are not configured. The in-app browser also reached a GitHub 404 page with a sign-in form for the recorded URL. For a private repository, this does not establish that the repository has been removed; it only establishes that the current session lacks access.

Before deletion, use an authenticated GitHub session with authority to delete `FoxsterDev/Unity-Nexus-Twin`, confirm its identity in the repository settings, delete it, and then independently verify that access is no longer possible. Record the result in this manifest.

## Current deletion authority

The remote GitHub deletion is user-owned. No local deletion is pending: the source clone is archived at the path above, and the ZIP has not been touched. Any future deletion of the archived clone or ZIP requires a new action-time confirmation.

The verified recovery backup above remains retained regardless of future deletion choices.
