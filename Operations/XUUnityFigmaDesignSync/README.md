# XUUnity Figma Design Sync

Operational module for turning Figma design references into shipped Unity remote-content assets with a verified visual result.

This module is public-safe and host-agnostic. It defines the pipeline stages, the Design Tech Doc contract, and the generic Figma extraction tooling. Host repos supply the project-specific asset contract (folder layout, ScriptableObject schema, bundle/publish lanes) through a host-local overlay document; this module never hardcodes a specific game or bucket.

## Problem Shape

A designer publishes UI references (popups, banners, skins) in a Figma file. The engineering side needs to:

1. browse the file and select only the frames that match a supported runtime content contract (not every frame is shippable content);
2. extract the selected frames into a reviewable **Design Tech Doc** (node ids, export table, layout parameters, text policy);
3. export pixel-exact art at the contract's target sizes;
4. generate the Unity assets from the doc (folders, sprites, atlases, config ScriptableObjects) through Editor-API tooling, never raw YAML authoring;
5. publish through the host's existing content pipeline;
6. validate the rendered result against the Figma reference with the reference-driven UI acceptance loop.

## Figma Access Lanes

Pick the first available lane; they are complementary, not exclusive.

| Lane | Use for | Requirements | Notes |
| --- | --- | --- | --- |
| Remote Figma MCP (`https://mcp.figma.com/mcp`) | Interactive browsing, node metadata, screenshots, choosing frames | Any Figma seat/plan; OAuth in browser; MCP-capable client | Link-based: paste a Figma URL, the server resolves the node. Preferred selection/inspection surface. |
| Desktop Figma MCP (local server in the Figma app) | Same as remote, selection-based context | Paid plan, Dev or Full seat, desktop app running | Only when the remote lane is unavailable or org policy requires local. |
| Figma REST API (`figma_export.py`) | Deterministic, scriptable, pixel-exact PNG export at computed scales; node-tree listing for batch selection | Personal access token in an environment variable (never in the repo) | The export backbone. Exact target pixel sizes are computed per node from the Design Tech Doc. |
| Browser screen reuse (screenshots of the Figma canvas) | Last-resort browsing when neither MCP nor token exists | Logged-in browser session | Never acceptable as production sprite source: wrong scale, no transparency, canvas chrome. Selection aid only. |

Token rule: the REST lane reads the token from an environment variable (default `FIGMA_TOKEN`). Never write tokens into repo files, Design Tech Docs, or reports.

## Pipeline Stages

```
S1 Select   -> S2 Extract  -> S3 Design Tech Doc -> S3a Text-policy approval
S4 Export   -> S5 Generate -> S6 Publish         -> S7 Visual Acceptance
```

- **S1 Select.** Enumerate the file's sections/frames (MCP metadata or `figma_export.py list`). Classify each frame against the host content contracts declared in the host overlay. Only contract-shaped frames continue; everything else is explicitly listed as `out_of_scope` with a reason. Selection is a human-confirmable artifact, not an implicit filter.
- **S2 Extract.** For each selected frame, read the node tree and identify the contract roles (for example: card art node, CTA button node, close icon node, text nodes). Record node ids, natural sizes, positions in frame space, fills/typography where relevant.
- **S3 Design Tech Doc.** Write one doc per batch from `templates/design_tech_doc_template.md`. This is the single source of truth for everything downstream: export table, layout parameter mapping, text policy (baked-into-art versus runtime slots), validation manifest fields. The doc is reviewable and re-runnable.
- **S3a Text-policy approval (blocking gate).** Runtime content has three possible homes for every text in the design: **baked into the exported art**, **configured** (a runtime text slot fed by server/admin data), or **dynamic** (computed from live client state). This is a product decision with an irreversible cost — it determines both the baked pixels and the server data contract — so the agent must *propose*, not assume:
  1. analyse the frame (rendered image plus node tree) and list every text element with its content and role;
  2. mark each as bake / configure / dynamic, defaulting anything that varies by user, segment, campaign, reward math, locale, or time to **configure**, and anything static with non-reproducible typography to **bake**;
  3. for each configured text, name the concrete slot, its server field, the layout rect derived from the excluded node's geometry, and whether it is required;
  4. list blockers: more configured texts than the view can render, typography a text component cannot reproduce, or a text welded into the card art in Figma (that needs a designer split — never a screenshot crop);
  5. obtain explicit approval and record it in the Design Tech Doc.
  A configured text must be **excluded from the exported art**, while its decorative neighbours (icons, currency glyphs) stay baked. Until approval exists the batch is `text_policy=pending_approval` and must not be generated or published. The host overlay owns the concrete slot contract and its current render limit.
- **S4 Export Art.** Run the REST exporter with the doc's export table (`figma_export.py export --spec <spec.json>`). The exporter computes the Figma export scale per node from the target pixel size and verifies the produced PNG dimensions. Mismatches fail the stage; art is never hand-resized silently.
- **S5 Generate.** Drive the host project's Editor generator (menu tool, static API, or Unity MCP project-defined hook) with the doc parameters. Generation uses the Unity Editor API (importers, `SpriteAtlas` API, `SerializedObject`) — raw YAML asset authoring is prohibited. The generator clones importer/atlas/config settings from a host-declared template asset so contract drift is impossible.
- **S6 Publish.** Use the host's existing content build and upload lane exactly as a human would (build, stage, validate, upload). This module never introduces a parallel publish path.
- **S7 Visual Acceptance.** Register the exported reference art as a `ui-reference` manifest and compare the rendered Unity result with the reference-driven UI acceptance loop (register/validate/compare + isolated render or deterministic play-mode fixture). Acceptance is human-visible similarity on a resolution-independent grid with declared tolerances and masks — not raw pixel equality. The task is complete only with a passed verdict or an explicit human-owner handoff state.

## Stage Gates

- S1 output must name every skipped frame with a reason (`not_contract_shaped`, `different_runtime_surface`, `duplicate`, ...).
- S3a must be explicitly approved before S4; an unapproved or partially approved text policy blocks generation, not just publication.
- S4 fails when any exported PNG's dimensions differ from the doc's target size.
- S5 fails when the host generator reports a contract warning the doc did not explicitly waive.
- S7 follows the reference-acceptance discipline: no verdict without a deterministic state; `blocked_nondeterministic` and `pending_manual_style` are honest terminal states.

## Module Files

- `templates/design_tech_doc_template.md` — the per-batch Design Tech Doc contract.
- `scripts/figma_export.py` — generic node listing + pixel-exact PNG export over the Figma REST API.

## Host Overlay Contract

A host repo that adopts this module declares, in its own operations layer:

- a `host_config.json` (from `templates/host_config.example.json`) with the project's `reference_viewport` (the Figma frame/device resolution used for reference registration and full-frame exports) and per-contract role target pixel sizes — `figma_export.py export --config <host_config.json>` resolves `role`-based export entries against it, so target resolutions are configuration, never hardcoded in the public tooling;
- which Figma files/sections map to which runtime content contract;
- the asset contract per content type (folder naming, required art names and pixel sizes, config asset schema, template asset path);
- the generator entrypoint (menu path, static API, MCP hook name);
- the publish lane and its guardrails;
- the validation lane (fixture or isolated render) and reference manifest location.

The host overlay may contain private file keys, node ids, viewports, and infrastructure names. This public module must not.
