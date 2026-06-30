# Skill: TextMeshPro Rich-Text Rendering

## Use For
- product strings that arrive as HTML or HTML-shaped markup from upstream services or content APIs
- TMP labels that must render formatting, links, line breaks, or inline icons
- review or implementation work on text components where users would see raw markup tokens (`<p>`, `<a>`, `<br>`, `&amp;`) inside the rendered label

## Background
- TextMeshPro parses only its own closed-set rich-text tag list. The set is:
  `<align>`, `<allcaps>`, `<alpha>`, `<b>`, `<br>`, `<color>`, `<cspace>`,
  `<font>`, `<gradient>`, `<i>`, `<indent>`, `<line-height>`, `<line-indent>`,
  `<link>`, `<lowercase>`, `<margin>`, `<mark>`, `<mspace>`, `<nobr>`, `<noparse>`,
  `<page>`, `<pos>`, `<rotate>`, `<s>`, `<size>`, `<smallcaps>`, `<space>`,
  `<sprite>`, `<style>`, `<sub>`, `<sup>`, `<u>`, `<uppercase>`, `<voffset>`, `<width>`.
- Any HTML tag outside that set is rendered as literal text. No TMP component setting expands the parser.
- `richText` is a single boolean — on or off — that controls whether the closed set is parsed at all. It does NOT add tags.
- TMP renders a glyph only if the bound font asset or one of its fallbacks has the codepoint. Rich-text parsing does not affect glyph coverage; for coverage questions see `glyph_coverage.md`.

## Rules
- Treat any upstream HTML-shaped string as a foreign format that must be transformed at the data boundary before reaching a TMP component. Do not feed raw HTML to a `TextMeshProUGUI` and expect the parser to "handle" it.
- Build the transform as a small pure formatter co-located with the data model, not inside the view component. The view should receive TMP-ready text.
- Convert known HTML to TMP-native equivalents:
  - `<a href="URL">label</a>` → `<link="URL"><color=#RRGGBB><u>label</u></color></link>` is acceptable for short, controlled config URLs; pick a project-consistent link color and add `<u>` only if links should be visually distinct.
  - `<br>`, `<br/>`, `<br />` → `\n` (single newline).
  - `<p>...</p>` → strip wrappers, preserve inner text. Paragraphs become spaces unless the upstream consistently wraps with blank lines, in which case insert a single newline between paragraphs.
- Do not put unbounded upstream URLs directly into `<link="...">`. TMP parses the whole tag before it can render the label, and long link ids can exceed the installed TMP parser tag buffer. Prefer short structural link ids such as `terms`, `vendor_terms_42`, or generated ids, then resolve them to full URLs in the click handling layer.
- Preserve existing direct URL ids from controlled config. A resolver that supports registered short ids should pass through unknown/direct ids unless they are explicitly registered for rewriting.
- Drop unknown HTML tags by removing the tag and keeping the inner text. Whitelist the TMP-native tag set above so designer-authored TMP markup is preserved through the same formatter.
- Decode common HTML entities (`&nbsp;` → space, `&amp;` → `&`, `&lt;` → `<`, `&gt;` → `>`, `&quot;` → `"`, `&#39;` and `&apos;` → `'`). Stop at this minimal set unless evidence of broader entity use appears.
- Collapse runs of whitespace to a single space (but preserve `\n`). Trim leading and trailing whitespace once at the end.
- For clickable links, host a `TMProLinkClickHandler`-equivalent component on the same GameObject and route `OnLinkClicked(linkId)` to whatever opens external URLs. Do not bake URLs directly into click handlers — keep the click event keyed by `linkId`.
- When a view assigns dynamic link-bearing text, verify the target text has an active raycast path and a link-click handler on the same GameObject, or an equivalent explicitly wired click path.
- If a label hosts a Show More / Show Less affordance over a long string, build the toggle link the same way (`<link="expand_toggle"><color=#xxxxxx><u>Show more</u></color></link>`) and reuse the same handler. Use the non-breaking space ` ` between "Show" and "more/less" so the label never wraps mid-affordance.
- Never trust the upstream `</tag>` count to match opens. The formatter must produce valid TMP markup even when the source HTML is unbalanced.
- After transform, the formatter is the single source of truth for what TMP sees. The view's `OnValidate` should NOT re-process the string.

## Anti-Patterns
- Toggling `richText: off` on the TMP component as a way to "show HTML literally". This still leaves entities like `&amp;` un-decoded and looks worse than the original.
- Adding `<p>` to a custom shader / parser fork to "support HTML". The closed-set parser is shared with every other TMP user; forking creates a maintenance trap.
- Pre-processing inside `Update` or `OnRectTransformDimensionsChange`. Format once when the data binds; cache the result on the view data.
- Embedding raw URLs as label text and then trying to detect them with regex at click time. Always use `<link="…">` so the link target is structural, not parsed from rendered text.

## Reference Implementation Shape
- `<FeatureName>TextFormatter.Format(string upstreamHtml)` static method.
- Inputs: raw HTML-shaped string from a service DTO.
- Outputs: TMP-ready string.
- Tests: unit tests covering null/empty input, `<p>` stripping + entity decode, `<a>` → `<link>`, `<br>` variants, unknown-tag drop, TMP-native preservation, whitespace collapse.

## External Libraries (Survey)
- **No mainstream HTML → TMP converter exists.** Unity community discussions confirm the default answer is "write a small preprocessor at the data boundary".
- **`<a href="url">` is NOT natively supported on TMP 3.0.x baselines** despite some forum posts that quote TMP 4.0.0-pre docs. On TMP 3.0.x convert `<a>` to `<link>` manually. Re-verify against the installed TMP version (see `glyph_coverage.md`).
- **FancyTextRendering** (`JimmyCushnie/FancyTextRendering`, MIT) — markdown → TMP rich text with clickable-link handling, ~100ms / 12k words, low GC. Pick when upstream is markdown-shaped (chat, changelogs, in-game text). Not for HTML.
- **RichUp** (`5argon/RichUp`) — narrower markdown preprocessor for TMP_Text. Same use case as FancyTextRendering at smaller scope.
- **tmpro-custom-tags** (`oneir0mancer/tmpro-custom-tags`) — extends TMP with `ITextPreprocessor` so you can register custom tags (e.g. add `<p>` as a real TMP-parsed tag instead of stripping it). Pick when the formatter shape is growing into a real "subset of HTML" parser.
- Decision: stay with the data-layer formatter while the markup surface is small (paragraphs + links + line breaks + entities). Switch to FancyTextRendering only if upstream becomes Markdown. Switch to `ITextPreprocessor` only if upstream becomes a real HTML subset that needs structural parsing.

## Routing Hints For Reviewers
- If the change adds or modifies a TMP component that binds a string from a service DTO, check whether a formatter exists. If the raw DTO field is bound directly, that is a finding.
- If the upstream string is known to be ASCII-only (e.g. a price string assembled from `{decimal:F2}`), do NOT add a sanitizer — it is pure overhead and obscures intent.

## Validation Focus
- editor-time preview: paste a representative upstream string into a test scene and confirm the rendered output has no literal `<p>`, `&nbsp;`, or other markup tokens.
- runtime: click a link in the rendered string and confirm `OnLinkClicked(linkId)` fires with the expected `linkId`.
- unit tests as listed above.
