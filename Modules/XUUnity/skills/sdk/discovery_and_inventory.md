# Skill: SDK Discovery And Inventory

## Use For
- sdk version discovery
- native package inventory
- upgrade readiness
- dependency and connector audits

## Rules
- Identify the exact Unity wrapper version, bundled native Android and iOS SDK versions, and any connector or adapter versions before judging upgrade safety.
- Do not treat the top-level plugin tag as sufficient evidence of runtime compatibility.
- Detect parallel release branches when the same release line ships different compatibility options.
- Check whether bundled native SDK versions improved, regressed, or changed compliance posture relative to the current project.
- Record the inventory in a stable format that can be promoted into project memory if it becomes durable project knowledge.
- Verify the final merged package state when the build pipeline can rewrite manifests, plist entries, Gradle dependencies, or stripping behavior.
- Record each SDK's shipped asset and code footprint, not only versions: bundled textures (dimensions, format, max size), font and emoji atlases, and native `.so` / DEX size. Cross-ref `knowledge/unity_build_size_measurement.md`.
- Flag a support or utility SDK that ships large UI art the app never surfaces (for example a chat SDK bundling multi-megapixel masks, an emoji atlas, and full fallback fonts). Distinguish per-asset oversize from whole-SDK inclusion for an unused feature.

## Review Focus
- exact version mapping
- hidden native downgrades
- connector or billing mismatches
- manifest or plist drift after build merge
- shipped asset/build-size footprint and unused-feature art
