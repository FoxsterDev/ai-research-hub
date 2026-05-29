# Skill: TextMeshPro Glyph Coverage

## Use For
- a label shows the missing-glyph square `□` on upstream content
- writing a sanitizer that strips codepoints the bound font cannot render
- choosing between expanding the font fallback chain and code-side filtering

## `HasCharacter` Across TMP Versions
| TMP version | `HasCharacter(int)` | `HasCharacter(char, bool, bool)` | `HasCharacter(int, bool, bool)` | `HasCharacter(uint, bool, bool)` | `HasCharacters(string, out uint[], bool, bool)` |
|---|:---:|:---:|:---:|:---:|:---:|
| 1.x | ✓ | — | — | — | — |
| 2.x | ✓ | ✓ | ✓ | — | ✓ |
| **3.0.x** | ✓ | ✓ | — | — | ✓ |
| 3.2+ | ✓ | ✓ | ✓ | ✓ | ✓ |

- The 3-arg `int` overload is **absent** from the TMP 3.0.x baseline. Code that writes `font.HasCharacter((int)cp, true, false)` fails with `CS1503: cannot convert from 'int' to 'char'`.
- `char` cannot hold supplementary-plane codepoints (> `0xFFFF`). Emoji like 🌍 (`U+1F30D`) cannot be checked via the `char` overload.

## Rule
- Prefer `HasCharacters(string text, out uint[] missingCharacters, bool searchFallbacks: true, bool tryAddCharacter: false)`. It exists in every TMP version from 2.x onward, walks surrogate pairs correctly, searches the fallback chain in one call, and returns the missing-codepoint set in one pass.
- Pass `tryAddCharacter: false` for read-only coverage checks. `true` mutates the dynamic atlas at runtime — only opt in when the font asset is configured for runtime atlas population AND the caller wants it.
- Before writing any `HasCharacter` call, verify the installed package version via `Packages/packages-lock.json` and check the actual overload set in `Library/PackageCache/<package>/.../TMP_FontAsset.cs`. Don't assume the latest docs match the installed surface.

## Sanitizer Recipe
1. Call `HasCharacters(text, out var missing, searchFallbacks: true, tryAddCharacter: false)`. If `true`, return the string unchanged.
2. Build a `HashSet<uint>` from `missing`.
3. Walk the string codepoint-aware: high+low surrogate pair → 2 chars consumed, otherwise 1. Use `char.ConvertToUtf32` for the pair.
4. Skip codepoints in the missing set. Append the rest to a `StringBuilder`.
5. Return the rebuilt string.

The sanitizer is glyph-driven, not codepoint-classification-driven. Latin-extended characters that the font's fallback chain covers (Czech `á`, Polish `ł`, German `ß`) survive because `HasCharacters` returns `true` for them.

## Anti-Patterns
- Casting `int` codepoint to `char` to satisfy the `HasCharacter(char, bool, bool)` overload — silently drops the high half of supplementary-plane codepoints, so emoji checks always return false.
- Per-character `HasCharacter` calls in a loop — quadratic in style, easy to break on surrogate pairs. Use `HasCharacters` once.
- Stripping codepoints the font already covers via fallback chain because the sanitizer hard-codes a denylist instead of asking the font.

## Cross-Links
- `rich_text_rendering.md` for the markup transform step that runs BEFORE this sanitizer.
- `emoji_rendering.md` when the right answer is to render the codepoint instead of strip it.
