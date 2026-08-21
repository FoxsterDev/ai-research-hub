# XUUnity Knowledge: Response Field Gating

## Use For
- client-side filters, gates, or restore paths keyed on a field of a server response
- a feature that reports "nothing found" while the captured payload plainly carries the data
- reuse of a request-side discriminator constant as a response-side tag

## Load Signals
- a predicate comparing a response DTO string field to a feature constant
- an optional discriminator (`SourceType`, `Origin`, `Kind`, `Category`) used as an equality gate
- a "no active X to restore" or "no matching Y" log that fires against a non-empty payload

## Rules
- Prove the field is populated by a captured production payload before making it a gate. A property declared on the
  DTO is not evidence that the endpoint sends it.
- Bind the DTO to a captured **endpoint response**. An admin-panel or config-entity export of the same data is a
  different artifact: it pins the nested shapes but not the envelope, and it can differ in section name, in root
  members the endpoint never sends, in default values the endpoint omits instead of transmitting, and in ids the
  server resolves before serving. A model built from the export compiles, passes its own fixtures, and still misses
  on the wire.
- Gate on what the contract demonstrably carries — type, timestamps, scope or owner ids — not on the field the client
  wishes it carried.
- For a genuinely optional discriminator, reject only on present-and-mismatched so an absent field degrades to
  permissive: `if (!string.IsNullOrEmpty(field) && field != Expected) { reject; }`. This stays correct when the server
  later starts sending the field, with no second patch.
- Do not reuse a request-side discriminator as a response-side tag. The request states what the caller wants; the
  response is under no obligation to echo it back.
- A gate whose rejection is observationally identical to "no data" is unfalsifiable in production. Give the rejected
  branch its own message text and severity before shipping it.
- When two call paths consume the same payload and only one applies the gate, treat that divergence as the primary
  lead: the ungated path shows what the payload actually contains.

## What This Is Not
Tolerant Reader and the robustness principle cover *ignoring unknown* fields. This file covers the inverse failure —
an *expected but absent* field used as an equality gate, which silently turns every record into a non-match. Schema
validation does not catch it either: the payload is valid, the client's assumption is not. Nor is this contract-first
versus code-first design: both are fine, and both still fail here when the artifact the contract was read from is not
the one the endpoint serves.

## Related
`knowledge/assetbundle_compatibility.md` and `skills/sdk/callback_safety.md` state the same doctrine for bundle
schemas and SDK callbacks. This file owns the client/server response case.
