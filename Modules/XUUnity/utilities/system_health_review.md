# XUUnity Utility: System Health Review

## Goal
Review the health of the prompt system itself, not only the product code.

## Rules
- Prefer identifying structural problems over rewriting everything.
- Treat duplicated routing, conflicting source-of-truth rules, and dead paths as high-severity issues.
- Flag any prompt file that adds cost without changing behavior.
- Recommend deletions, merges, or moves only when they improve clarity and routing reliability.
- Check whether the public `xuunity` core and the monorepo-internal `xuunity` overlay are clearly separated.
- Flag any active rule that still treats all reusable knowledge as a single shared layer.
- Flag any active rule that allows non-public-safe guidance to drift into `AIRoot/Modules/XUUnity/`.
- Include the health of the knowledge extraction pipeline when `xuunity extract ...` is part of the active system.
- If a knowledge extraction evaluation baseline or recent regression run exists, use it as evidence during the review.
- Prefer a machine-readable extraction regression summary when available.
- Prefer the canonical latest authoritative summary over ad hoc run files.
- If extraction routing changed recently and no regression evidence exists, flag that gap explicitly.
- Audit shared knowledge reachability:
    - identify shared `knowledge/` or internal overlay knowledge files that have no explicit routing, trigger hints, utility references, or load path
    - treat knowledge with no realistic selection path as dead ballast
    - flag knowledge added without corresponding trigger updates as a system-health issue
- Check storage-consistency explicitly:
    - repo-level storage rule in `Agents.md`
    - public core references to `AIRoot/Modules/XUUnity/`
    - internal shared references to `AIModules/XUUnityInternal/`
    - project-router references to `Assets/AIOutput/`
    - project-router references to `Assets/AIOutput/ProjectMemory/`
    - whether prior-output loading accidentally points only at `ProjectMemory`
    - whether local routers duplicate or contradict the repo-level storage contract
- Prefer project routers that reference the repo storage contract over rephrasing it locally.

## Output
- High-severity conflicts
- Redundant files or sections
- Missing files or weak layers
- Knowledge extraction regression status
- Knowledge reachability status
- Public core versus internal overlay boundary status
- Storage consistency status
- Recommended cleanup order
