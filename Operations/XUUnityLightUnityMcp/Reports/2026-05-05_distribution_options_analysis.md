# XUUnity Light Unity MCP Distribution Options Analysis

Date: `2026-05-05`
Status: `public options analysis`

## Scope

This note analyzes how the lightweight Unity MCP should be packaged for
external consumers who may not want to mount the full `AIRoot` repo into their
own repository.

## Core Distinction

There are three different shapes to keep separate:

1. source layout
2. runtime layout
3. distribution layout

Current reality:

- source layout is centralized under `AIRoot/Operations/XUUnityLightUnityMcp/`
- runtime layout is already split between:
  - host-side MCP server and wrappers
  - Unity-side editor package
- distribution layout is not yet fully optimized for standalone external
  adoption

## Why One Unity Package Is Not Enough

A single Unity package is not a complete replacement for the full MCP service.

Reason:

- the Unity package lives inside the Unity Editor process
- the MCP server must live outside Unity as a separate host-side process

The Unity package can provide:

- editor operations
- bridge state
- capability probing
- scenario execution

But the Unity package alone should not own:

- external MCP stdio process startup
- AI client process configuration
- host-side editor startup and reuse policy
- retry and reconnect orchestration outside the Unity process
- host-side closeout and editor-state restore

## Option Analysis

### Option 1. Keep everything as one Unity package

Verdict:

- not recommended

Why:

- mixes host-process concerns into Unity package delivery
- makes client integration and host install awkward
- weakens crash isolation and lifecycle supervision
- does not actually remove the need for an external MCP entrypoint

### Option 2. Keep one repo, but distribute two artifacts

Shape:

- artifact A: Unity UPM package
- artifact B: host MCP bundle

Verdict:

- recommended

Why:

- matches the real runtime boundary
- lets source stay in one repo
- lets consumers avoid mounting the whole `AIRoot` repo
- keeps Unity package and host bundle versioned together

This is the cleanest near-term path.

### Option 3. Split into separate repos

Shape:

- repo A: Unity package
- repo B: host MCP service

Verdict:

- possible, but not the first move

Why:

- improves external packaging clarity
- but increases release coordination and version-sync overhead
- source is currently easier to evolve while it still lives together

This only becomes attractive if the service matures into a more productized
public offering with independent release cadence.

## Recommended Target Shape

The most practical target is:

- one public source repo
- two installable artifacts

### Artifact A: Unity package

Consumer shape:

```json
{
  "dependencies": {
    "com.xuunity.light-mcp": "https://github.com/FoxsterDev/ai-research-hub.git?path=/Operations/XUUnityLightUnityMcp/templates/unity-package#<commit>"
  }
}
```

or local same-host `file:` route during active iteration.

### Artifact B: Host bundle

Should contain only what the external MCP client needs:

- `server.py`
- `run.sh`
- install/setup entrypoint
- client config snippets
- minimal docs for startup, readiness, and closeout

This should be installable without mounting the full `AIRoot` repo.

## Practical Conclusion

The right long-term answer is not:

- "put everything into one Unity package"

The right answer is:

- "ship one reusable MCP product with a Unity-side package and a host-side bundle"

That preserves the real process boundary while still allowing a simple external
adoption story.

## Next Packaging Step

Recommended next move:

- keep current source layout in `AIRoot`
- define a standalone host-bundle install surface
- keep the Unity package as the editor-side artifact
- document the two-artifact installation story as the canonical public route
