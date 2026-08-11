# Design Tech Doc — <batch name>

Status: `draft | approved | exported | generated | published | accepted`
Source file: `<figma file key>` (link without token material)
Selected by: `<who confirmed S1 selection>`
Date: `<YYYY-MM-DD>`

## 1. Selection Record (S1)

| Frame | Node id | Section | Verdict | Reason |
| --- | --- | --- | --- | --- |
| <frame name> | <node id> | <figma section> | selected | matches `<content contract>` |
| <frame name> | <node id> | <figma section> | out_of_scope | <not_contract_shaped / different_runtime_surface / duplicate> |

Every frame in the reviewed sections appears here exactly once. No implicit skips.

## 2. Per-Item Extraction (S2)

One block per selected item.

### <ItemName>

- Content contract: `<host contract id, e.g. infoview_skin>`
- Runtime id / key: `<the id the runtime will use, e.g. lowercase skin name>`
- Frame node: `<node id>` (frame size `<w>x<h>`)
- Role mapping:

| Contract role | Figma node id | Node name | Natural size | Target export size | Export scale |
| --- | --- | --- | --- | --- | --- |
| card_art | <id> | <name> | <w>x<h> | <W>x<H> | <W/w> |
| cta_button | <id> | <name> | <w>x<h> | <W>x<H> | <W/w> |
| close_icon | <id or `template_default`> | <name> | — | <W>x<H> | — |

- Layout parameters (frame space -> contract space conversion shown explicitly):
  - `cta_position`: `<x,y>` (derivation: <how computed from Figma coordinates>)
  - `close_position`: `<x,y>` (derivation)
  - other contract fields: `<...>`
- Text policy (S3a — needs explicit approval before export/generation):

| Figma text node | Content | Verdict | Slot / server field | Layout rect (from node geometry) | Required | Rationale |
| --- | --- | --- | --- | --- | --- | --- |
| <id> | "<text>" | bake | — | — | — | static copy / non-reproducible typography |
| <id> | "<value>" | configure | <slot> / <field> | pos `<x,y>` size `<w,h>`, align `<h>/<v>` | yes/no | varies by <user/campaign/reward> |
| <id> | "<text>" | dynamic | — | — | — | derived from live client state → needs a different surface |

  - Blockers: `<more configured texts than the view renders / typography mismatch / text welded into card art>` or `none`
  - Excluded from exported art: `<node ids of configured texts>`
  - Approval: `pending | approved by <who> on <date>`
- Variability / masks for acceptance: `<dynamic regions, counters, timers — or none>`
- Open questions: `<anything the designer must confirm — or none>`

## 3. Export Table (S4)

Machine-readable spec consumed by `figma_export.py export --spec`:

```json
{
  "file_key": "<figma file key>",
  "out_dir": "<staging output directory>",
  "items": [
    {
      "item": "<ItemName>",
      "exports": [
        { "node_id": "<id>", "file": "<ItemName>/Popup.png", "target_width": 0, "target_height": 0 },
        { "node_id": "<id>", "file": "<ItemName>/ButtonCTA.png", "target_width": 0, "target_height": 0 }
      ]
    }
  ]
}
```

## 4. Generation Parameters (S5)

| Item | Generator input | Value |
| --- | --- | --- |
| <ItemName> | <generator field> | <value> |

Template asset baseline: `<host template asset path>` — generation clones importer/atlas/config settings from it; any waived contract warning is listed here explicitly.

## 5. Publish Record (S6)

- Lane: `<host publish lane>`
- Environment: `<dev/staging/prod>`
- Evidence: `<build/upload evidence pointers>`

## 6. Acceptance Record (S7)

- Reference manifest: `<ui-reference manifest path>`
- Fixture / render lane: `<deterministic state used>`
- Verdict: `passed | failed | blocked_nondeterministic | pending_manual_style`
- Artifacts: `<expected/actual/overlay/diff pointers>`
