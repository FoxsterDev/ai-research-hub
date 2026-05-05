# AI Integration Instructions

Use this document when an AI agent is integrating this Unity package into a new
project.

## Primary Rule

Do not assume that installing this package alone is enough.

The full system requires:

1. this Unity package
2. the host-side lightweight MCP server
3. bridge enablement for the target project
4. Unity capability verification before real use

## Required Integration Steps

1. add the package to `Packages/manifest.json`
2. install the host-side service from `AIRoot/Operations/XUUnityLightUnityMcp/`
3. enable the bridge for the target project
4. open Unity
5. verify:
   - bridge state
   - capability report
   - health probe
6. only then run compile, tests, play mode, or screenshot commands

## Safety Rules

An AI agent should:

- keep the bridge disabled unless Unity-aware validation is needed
- trust capability gating for version-sensitive operations
- prefer validation before mutation
- keep validation gaps explicit

An AI agent should not:

- rewrite `ProjectSettings` just to make the package work
- inject broad define symbols
- assume Game View reflection is always valid
- treat shell compile as equivalent to Unity validation

## Current Recommended First Pass

1. status
2. capabilities
3. health probe
4. compile or EditMode tests
5. scene snapshot
6. play mode
7. screenshot
8. scenario validate
9. scenario run
10. scenario result
11. implement `IXUUnityLightMcpScenarioHook` in `Assets/Editor/` when the project needs local scenario automation not worth promoting upstream yet

## Upstream Docs

- public guide: `AIRoot/Operations/XUUnityLightUnityMcp/README.md`
- AI integration guide: `AIRoot/Operations/XUUnityLightUnityMcp/AI_INTEGRATION.md`
- roadmap: `AIRoot/Operations/XUUnityLightUnityMcp/ROADMAP.md`
- license: `AIRoot/Operations/XUUnityLightUnityMcp/LICENSE.md`
