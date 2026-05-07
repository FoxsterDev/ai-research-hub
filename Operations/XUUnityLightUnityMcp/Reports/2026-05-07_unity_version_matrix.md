# XUUnity Light Unity MCP Unity Version Matrix

Date: `2026-05-07`
Host: `macOS 15.7.3`
Scope: clean-project MCP regression on locally installed Unity editors

## Regression Contract

Each version was tested on a fresh clean Unity project created specifically for the run.

The MCP regression contract was:

1. create clean project
2. wire `com.xuunity.light-mcp` as a local `file:` package
3. enable the bridge
4. run `ensure-ready`
5. run `request-status`
6. run `request-health-probe`
7. run `request-capabilities`
8. run `interactive_acceptance_smoke.json`
9. run `refresh_contract_smoke.json`
10. run `compile_contract_smoke.json`

Automation used:

- `AIRoot/Operations/XUUnityLightUnityMcp/run_unity_version_matrix.sh`

Note:

- the public runner now supports auto-discovery of installed editors on macOS, Windows, and Linux default locations plus `XUUNITY_UNITY_EDITOR_ROOTS`
- this report itself is still host-specific evidence from a macOS run on `2026-05-07`

## Summary

| Unity version | Result | Notes |
| --- | --- | --- |
| `2021.3.45f2` | blocked before MCP | clean-project creation failed on this host because the editor reported no valid Unity license |
| `2021.3.58f1` | passed | full clean-project MCP regression passed after version-aware package-source generation |
| `2022.3.62f3` | passed | full clean-project MCP regression passed after version-aware package-source generation |
| `2022.3.67f2` | passed | full clean-project MCP regression passed after version-aware package-source generation |
| `6000.0.58f2` | passed | full clean-project MCP regression passed |
| `6000.0.61f1` | passed | full clean-project MCP regression passed |
| `6000.2.14f1` | passed | full clean-project MCP regression passed |
| `6000.3.3f1` | passed | full clean-project MCP regression passed |

## Verified Supported Versions On This Host

Live-proven on this macOS host:

- `2021.3.58f1`
- `2022.3.62f3`
- `2022.3.67f2`
- `6000.0.58f2`
- `6000.0.61f1`
- `6000.2.14f1`
- `6000.3.3f1`

Not live-proven on this macOS host:

- `2021.3.45f2`

## Root Cause Notes

### 2021.3.45f2

The run did not reach MCP package validation. Clean-project creation failed because the editor reported:

- `No valid Unity Editor license found. Please activate your license.`

So this version is not a clean MCP compatibility signal on this host. The run never reached package import or bridge activation.

### 2021.3.58f1 / 2022.3.62f3 / 2022.3.67f2

These versions originally failed against the single `6000`-oriented package manifest.
The working fix was to make package-source generation version-aware instead of forcing one static manifest for every editor line.

Implemented change:

- added manifest templates under:
  - `AIRoot/Operations/XUUnityLightUnityMcp/templates/package-manifests/unity-package-2021_2022.json`
  - `AIRoot/Operations/XUUnityLightUnityMcp/templates/package-manifests/unity-package-6000.json`
- updated installer and host wrapper to materialize a version-selected package source per project
- generated package source now lives at:
  - `<Project>/XUUnityLightMcpPackageSource/com.xuunity.light-mcp`
  - not under `Library/`, because Unity rejects `file:` packages located under `Library/`

The key compatibility adjustments for legacy editors were:

- `unity` minimum changed from the `6000` package line to a legacy template line
- `com.unity.test-framework` changed from `1.5.1` to `1.1.33` for the `2021/2022` template

Result after the change:

- `2021.3.58f1` passed full MCP regression
- `2022.3.62f3` passed full MCP regression
- `2022.3.67f2` passed full MCP regression

So on this host, the package is now live-proven across:

- `2021.3.58f1`
- `2022.3.62f3`
- `2022.3.67f2`
- `6000.0.58f2`
- `6000.0.61f1`
- `6000.2.14f1`
- `6000.3.3f1`

## Evidence Paths

Original pre-fix matrix run summary:

- `/private/var/folders/z5/_nnwz2wx7rbc9m83l3qsjhf40000gn/T/xuunity-light-unity-mcp-version-matrix/20260507T160449Z/summary.tsv`

Original pre-fix matrix result root:

- `/private/var/folders/z5/_nnwz2wx7rbc9m83l3qsjhf40000gn/T/xuunity-light-unity-mcp-version-matrix/20260507T160449Z/results/`

Focused `2022.3.67f2` rerun showing the old package-resolution failure:

- summary: `/private/var/folders/z5/_nnwz2wx7rbc9m83l3qsjhf40000gn/T/xuunity-light-unity-mcp-version-matrix/20260507T160926Z/summary.tsv`
- project root: `/private/var/folders/z5/_nnwz2wx7rbc9m83l3qsjhf40000gn/T/xuunity-light-unity-mcp-version-matrix/20260507T160926Z/projects/SampleProject_2022_3_67f2`
- editor log: `/private/var/folders/z5/_nnwz2wx7rbc9m83l3qsjhf40000gn/T/xuunity-light-unity-mcp-version-matrix/20260507T160926Z/projects/SampleProject_2022_3_67f2/Library/XUUnityLightMcp/logs/unity_editor.log`

Focused rerun after version-aware package generation proved `2022.3.67f2` end to end:

- summary: `/private/var/folders/z5/_nnwz2wx7rbc9m83l3qsjhf40000gn/T/xuunity-light-unity-mcp-version-matrix/20260507T162425Z/summary.tsv`
- result root: `/private/var/folders/z5/_nnwz2wx7rbc9m83l3qsjhf40000gn/T/xuunity-light-unity-mcp-version-matrix/20260507T162425Z/results/2022.3.67f2`

Current post-fix full matrix:

- summary: `/private/var/folders/z5/_nnwz2wx7rbc9m83l3qsjhf40000gn/T/xuunity-light-unity-mcp-version-matrix/20260507T162524Z/summary.tsv`
- result root: `/private/var/folders/z5/_nnwz2wx7rbc9m83l3qsjhf40000gn/T/xuunity-light-unity-mcp-version-matrix/20260507T162524Z/results/`

## Recommendation For README

The README should now say:

- live-proven on this macOS host for:
  - `2021.3.58f1`
  - `2022.3.62f3`
  - `2022.3.67f2`
  - `6000.0.58f2`
  - `6000.0.61f1`
  - `6000.2.14f1`
  - `6000.3.3f1`
- current checked-in base package manifest remains the `6000` line
- `2021/2022` support currently depends on version-aware generated package source selection
- `2021.3.45f2` is still unresolved on this host because project creation is blocked by editor licensing
