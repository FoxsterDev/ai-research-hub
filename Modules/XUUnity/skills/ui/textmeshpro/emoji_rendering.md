# Skill: TextMeshPro Emoji & Symbol Rendering

## Use For
- upstream content carries emoji, flags, or symbols the project font does not cover
- choosing how to render them: native font fallback vs sprite asset vs separate UI image vs text substitute

## Five Options
| Option | What it is | Disk cost | When to pick |
|---|---|---|---|
| **A. TMP Sprite Asset** | Purpose-built atlas + TMP Sprite Asset. Data layer rewrites codepoints to `<sprite name="…">`. | ~100–300 KB | Known small glyph set (~30 codepoints), stable. Best default. |
| **B. Color emoji font fallback** | `NotoColorEmoji` / `EmojiOne SDF` added to `Fallback Font Assets`. | 5–10 MB | Unbounded emoji set upstream can ship freely AND TMP 3.x + Dynamic atlas mode confirmed working. |
| **C. UI Image badge** | Strip codepoint; classify into `BadgeKind` enum; render sibling `Image` from a project sprite atlas. | minimal | Badges need different size/anchor/padding than inline glyphs, or atlas is reused outside the feature. |
| **D. Replace at parse time** | `U+1F30D` → `(Global)`, regional indicator pair → `(US)`. | none | Release guardrail only. Not a long-term product surface. |
| **E. OS font fallback (TMP 3.x)** | System emoji font (Apple Color Emoji / NotoColorEmoji) as fallback. | none | TMP 3.x project + reliable OS coverage in shipping markets. |

## Decision Rubric
- **Known, small, stable glyph set** → A.
- **Need bigger badges or animation** → C.
- **Upstream emoji set is genuinely unbounded** → B if atlas budget allows, else C with a curated atlas + sanitizer fallback.
- **Can't ship any new asset and on TMP 3.x** → E, but accept OS coverage drift.
- **Asset/art budget is zero and visual fidelity is negotiable** → D as a guardrail behind the sanitizer.

## Sprite Asset Filename Convention
- Single codepoint: lowercase hex, e.g. `1f30d.png` for 🌍.
- Regional indicator pair (flags): hyphen-joined hex, e.g. `1f1fa-1f1f8.png` for 🇺🇸.
- Older TMP versions only resolve single-codepoint filenames; pair-encoded filenames need TMP ≥ 2.1.
- Uppercase filenames (`1F30D.png`) fail to resolve silently — keep lowercase.

## Reference Pattern (Option A)
1. Atlas: 1024×1024 or 2048×2048, glyphs at 64–128 px, transparent background.
2. Generate the TMP Sprite Asset via `Window → TextMeshPro → Sprite Asset Creator`.
3. Wire as `TMP Settings → Default Sprite Asset` OR per-component on the specific labels. Changing the global default affects every TMP_Text in the project — if other features rely on a different default, prefer the per-component route.
4. Data-layer formatter rewrites codepoints to `<sprite name="…">` BEFORE the string reaches `TMP_Text.text`.
5. Keep the `glyph_coverage.md` sanitizer in the pipeline as defense-in-depth for codepoints the atlas does not cover. Order matters: formatter runs first, sanitizer second.

## Anti-Patterns
- Mixing Option A and Option E for the same codepoints — resolution order is non-obvious and editor / device can diverge.
- Reaching for Option B without checking TMP version. On TMP 2.x and 3.0.x baselines, color emoji often renders as B&W outlines.
- Adding emoji font fallback without verifying regional-indicator combining via `OpenType GSUB`. Flags then render as two side-by-side letters.
- Treating Option D as permanent.

## Cross-Links
- `rich_text_rendering.md` for the broader formatter that sits next to the sprite-tag rewriter.
- `glyph_coverage.md` for the sanitizer that protects against codepoints the atlas does not cover.
