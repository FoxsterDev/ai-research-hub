# XUUnity Light MCP Unity Package

This Unity package provides the editor-side bridge for the lightweight
`xuunity` Unity MCP service.

Author:
- Siarhei Khalandachou
- LinkedIn: `https://www.linkedin.com/in/khalandachou/`

It is intended to be:

- editor-only
- removable
- disabled by default
- safe to consume from more than one repo

## GitHub Install

Add this to `Packages/manifest.json`:

```json
{
  "dependencies": {
    "com.xuunity.light-mcp": "https://github.com/FoxsterDev/ai-research-hub.git?path=/Operations/XUUnityLightUnityMcp/templates/unity-package#master"
  }
}
```

## What This Package Does

This package exposes the Unity-side bridge for:

- status
- capability probe
- console tail
- scene snapshot
- EditMode tests
- compile validation
- play mode control
- Game View control and screenshots
- scenario validation, execution, and persisted results
- project-defined scenario hooks through `IXUUnityLightMcpScenarioHook`

The host-side MCP server is not inside this package.
It must be installed separately on the machine that runs the AI client.

## License

This package is MIT-licensed and provided as-is, without warranty or liability.

See:
- `../LICENSE.md`

## Next Read

- `AI_INTEGRATION.md`
