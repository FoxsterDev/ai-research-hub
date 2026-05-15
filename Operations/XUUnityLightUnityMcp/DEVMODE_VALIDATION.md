# XUUnity Light Unity MCP Devmode Validation

Use this document when changing the XUUnity Light Unity MCP host, server,
wrapper scripts, Unity package, package metadata, smoke runners, or package
source switching behavior.

## Rule

- Treat `devmode` as the local-package validation mode for MCP development.
- Validate MCP package changes through a consumer Unity project that resolves
  `com.xuunity.light-mcp` from the local `AIRoot` working tree.
- Project-specific smoke suites, compile matrices, scenario runs, and product
  PlayMode suites are useful additional evidence, but they do not replace the
  package-owned MCP regression lane.

## Required Closeout For Executable-Code Changes

After executable-code changes under `AIRoot/Operations/XUUnityLightUnityMcp/`
or its Unity package, run the package-owned self-test lane before closeout:

```bash
AIRoot/Operations/XUUnityLightUnityMcp/templates/smoke/run_package_self_tests.sh \
  --project-root <UnityProjectRoot> \
  --mode all
```

The lane must include both package assemblies:

- `com.xuunity.light-mcp.Editor.Tests`
- `com.xuunity.light-mcp.PlayMode.Tests`

If the package self-test lane cannot run, report that as an explicit MCP
validation gap instead of calling the MCP change fully validated.

## Runner Behavior

- Unity discovers test assemblies inside an installed package only when the
  package name is listed in the consumer project's `Packages/manifest.json`
  `testables` array.
- The package self-test runner temporarily adds `com.xuunity.light-mcp` to
  `testables`, refreshes the project, runs the selected package tests, and
  restores the original manifest on exit.
- Do not leave a permanent `testables` change in a consumer project unless that
  project intentionally wants package tests visible during normal Test Runner
  use.

## Scope Notes

- Documentation-only changes do not require the package self-test lane unless
  they also change executable scripts, host code, Unity package code, asmdefs,
  package metadata that affects compilation, or validation runner behavior.
- Host Python/server changes should also run the host Python test suite when
  available.
- Shell runner changes should at least pass shell syntax validation before
  closeout.
