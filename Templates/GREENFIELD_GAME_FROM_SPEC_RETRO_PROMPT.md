# Greenfield Game From A Product Spec — Retro Prompt

Date: `2026-09-03`
Status: `active public prompt`

## Purpose

Use this prompt after a session whose request was shaped like:

> "Build the core gameplay of a new game from scratch from this product design document, in an
> existing multi-project engine monorepo, reusing art from a reference project, validated through the
> project's own editor-automation lane, mobile-ready, high quality."

That request class has a distinctive failure profile that generic code-review or MCP-reliability
retros miss, because most of the wasted effort is spent **before the first gameplay line is written**
(project bootstrap, dependency baseline, art/asset provenance) and **after it works** (proving it
works on the surfaces the product owner will actually look at).

This prompt is engine- and vendor-agnostic. Keep private package names, business context and
per-company conventions out of the prompt body; pass them as evidence inputs.

## Use When

- a new project/module was created inside a monorepo that already contains working sibling projects
- a product design document was the primary requirement source
- assets (art, audio, fonts) were reused from a reference or purchased project
- scenes, prefabs and serialized bindings were authored programmatically
- validation ran through an editor-automation lane rather than a human clicking the app
- the session took materially longer than the code it produced would suggest

## Inputs To Gather First

1. the product design document (or a faithful condensation)
2. the final file inventory of what was created, by assembly/module
3. the test and validation evidence actually produced (verdicts, not claims)
4. the screenshots or captures used to judge visual correctness, with their resolutions
5. the sequence of user corrections during the session — these are the highest-signal input
6. the sibling projects' configuration baseline (project settings, dependency manifest)

## Prompt

```text
Analyze this greenfield-game-from-spec session as a delivery retrospective.

Goal:
- separate the quality of the DELIVERABLE from the efficiency of the PATH to it
- find which costs were structural (unavoidable) and which were self-inflicted
- convert every user correction into a rule that would have prevented it
- decide what should become reusable process versus what was project-specific

Required questions:

A. Requirement fidelity
 1. Which spec rules are implemented exactly, which are approximated, which are missing?
    Quote the spec clause beside each.
 2. For every rule with a worked example in the spec, is there a test that encodes that example?
 3. What did the spec leave open, and what did the session decide on the owner's behalf?
    Was each decision surfaced or silently taken?

B. Bootstrap efficiency
 4. Did the new project start from a copy of the newest working sibling, or from a blank template?
    Count the hours spent on configuration failures that a copy would have prevented.
 5. Which dependency, toolchain or project-setting divergence from the siblings caused a failure?
 6. Was the engine/toolchain version chosen to match the portfolio, or chosen by convenience?

C. Asset provenance
 7. Where did every reused asset come from, and is that source the one the owner intended?
 8. Can an artist replace the art without touching code or re-binding prefabs? Prove the seam.
 9. Were house/shared assets (fonts, shared UI kits) used where they exist, or re-imported from the
    reference project by default?

D. Observation-surface truth
10. For every "it does not work" moment: was the code wrong, or was the observation surface wrong
    (loop not running, stale build, capture rendered at a different size than the runtime saw,
    log read from the wrong file)? Count each class.
11. What single cheap probe would have distinguished them at the first sighting?

E. Correction analysis
12. List every user correction in order. For each: what did the agent assume, what was the actual
    constraint, and what rule prevents that assumption class?
13. Which corrections were about scope, which about convention, which about defect?

F. Validation honesty
14. What is proven by executed evidence, what is proven by inspection, what is unproven?
15. Which claims would not survive an adversarial reviewer asking "show me the run"?
16. Was anything validated on a surface that cannot express the claim (editor-only evidence for a
    device-runtime claim, compile evidence for a behaviour claim)?

G. Repeat-cost
17. Which manual sequence was repeated three or more times before being scripted?
18. What would the same deliverable have cost with perfect foresight? Express the waste as a share.

Output format:
1. Deliverable inventory with proof column
2. Cost timeline by phase, with a self-inflicted / structural split
3. Spec-fidelity matrix (implemented / approximated / missing / decided-on-owner's-behalf)
4. The mistakes, ordered by cost, each with root cause and a preventive rule
5. What went right and should be repeated verbatim
6. Improvement plan for the next project of this class, ordered by expected time saved
7. Honest scoring
8. Continuation state: what remains, with the exact next action

Rules for the output:
- Score the path separately from the product. A good deliverable does not excuse a wasteful path.
- Every rule must be actionable at a specific decision point, not a virtue ("copy the sibling's
  manifest before writing one" beats "be careful with configuration").
- Do not report a validation as passing without naming the command and its verdict.
- Name the mistakes plainly. This document exists to make the next session cheaper, not to look good.
```

## Standing Rules This Class Of Work Keeps Rediscovering

These are the recurring, high-cost lessons. Check them at the start, not in the retro.

1. **Copy the newest working sibling's project configuration; never hand-author it.** In a monorepo
   with N shipping projects, the configuration baseline is solved. Divergence is a defect, not a
   simplification. Patch only identity fields afterwards.
2. **Match the portfolio's engine version.** Serialized scene and prefab formats are forward-only; a
   newer editor silently forfeits reuse of everything authored in it.
3. **A deferred feature is not a deferred toolchain.** "Integrate later" usually constrains what the
   player sees, not which shared packages may be referenced. Confirm which one is meant.
4. **Prefer shared/house assets over re-importing from the reference project**, especially fonts and
   UI kits. Ask once; do not infer from the art folder you were pointed at.
5. **Route all art through one theme/config asset.** The acceptance criterion "artists must be able to
   update the art" means: swap a field on one asset, no code and no prefab rebinding.
6. **Author scenes and prefabs with a re-runnable editor scaffolder**, not by hand and not at runtime.
   The result is a real, inspector-editable asset; the cost of the fifth layout revision is then the
   same as the first.
7. **Generate content through its own validator.** A level generator that can emit an unsolvable board
   will eventually ship one; make the validator the gate inside the generator, then re-prove it from
   the serialized artifact in a test.
8. **Before trusting any runtime observation, prove the observation surface**: the loop is advancing,
   the build is current, the capture matches the runtime's own view of the screen, the log is the
   live one. One cheap probe each, once, at the start.
9. **Script any manual verification sequence on its third repetition.**
10. **Put a positive control beside every assertion of absence.** "Nothing happened" is unfalsifiable
    without a sibling case where something does.
11. **Keep one editor-only diagnostic line per subsystem whose correctness depends on an ambient
    value** the environment can misreport (screen size, safe area, density, time scale).
12. **Re-read the durable memory index by symptom when a new failure appears**, not only by topic at
    session start.

## Expected Outputs

- a session retro saved beside the project's other operational documents
- an improvement plan whose items are decision-point rules
- a continuation prompt that a fresh session can execute without re-deriving context
- any reusable lesson promoted into this file's standing-rules list
