# Skill: UI Toolkit

## Use For
- editor-facing UI
- runtime UI Toolkit flows if the project already standardizes on it

## Rules
- Prefer UI Toolkit where retained-mode behavior is a clear fit.
- Do not mix UI Toolkit and UGUI on the same runtime flow without a reason.
- Validate event, focus, and navigation behavior on both iOS and Android.
- Avoid broad style or tree rebuilds on frequently updated screens.

## Lists That Grow With Content
- Use a virtualized `ListView` or `TreeView` when content can become large, unbounded, or expensive to rebuild. Prefer `CollectionVirtualizationMethod.FixedHeight` with `fixedItemHeight` for genuinely uniform rows; use `DynamicHeight` when the content contract requires variable row heights. A small, explicitly bounded collection may use a simpler element tree when measurement shows that the simpler shape is sufficient.
- A recycled row must resolve its current binding at event time instead of capturing the `bindItem` index in a newly registered callback. Register handlers once in `makeItem`; update a dedicated row-state object or custom row element in `bindItem`, clear it in `unbindItem`, and resolve the current item or stable identity when the event fires. Treat a stored index as last-bound state, not as proof that the data source has not changed.
- Do not build a large or repeatedly refreshed item surface with `label.text += line`; repeated immutable-string growth plus text re-layout scales poorly. Aggregate once for a small bounded text block, or use a virtualized collection when rows are independently interactive or the volume can grow.
- For large trees, prefer a deliberate initial expansion policy and show child counts on collapsed folders. Defaulting to collapsed is useful when expansion would create noise, but discovery-oriented or shallow trees may justify a different default.

## State, Not Just Data
- Separate *loading* from *empty*. Clearing the backing collection before an async fetch renders a genuinely empty model, so the panel truthfully reports "nothing found" while it is in fact still loading. Accumulate into locals, publish at the end, and show an explicit loading row while a fetch is in flight.
- Pause scheduled animations when their element remains attached to a panel but is hidden. `element.schedule.Execute(...).Every(ms)` can keep ticking while `display` suppresses rendering; pair `Pause()`/`Resume()` with the visibility toggle so an idle window stays idle.
- Pointer callbacks clobber programmatic state. A `PointerLeaveEvent` handler that restores a *constant* colour erases any accent set by code. Keep the element's resting value on the element and have the handler restore that, not a literal.

## Theming And Styling
- Use Unity editor USS variables (`--unity-colors-*`) for editor chrome and theme-dependent surfaces, with `EditorGUIUtility.isProSkin` only where USS cannot express the required policy. Brand or semantic colours may be explicit, but their foreground/background combinations must be validated in both Light and Dark skins instead of assuming one palette.
- Prefer USS over per-element inline style assignments for anything reused. High C# style-setter density is the direct cost of not having a stylesheet.
- Prefer plain ASCII for generated glyph content such as spinner frames. Editor font coverage for decorative Unicode is not guaranteed across platforms and versions.

## Multi-Step Tool Layout
- Render a sequential workflow as one coherent stepper in execution order, numbered when the order is material. Use a horizontal row only when the editor window can preserve legibility; prefer a vertical or responsive layout when the sequence is long or the panel is narrow. Do not split required steps by technical category when that hides their order.
- Keep actions that are not steps in a separate, deliberately unnumbered group. Prefer a single entry point per action; when duplicate access is intentional, bind every entry point to the same state, guards, and progress owner so one cannot run out of order.
- Mark the next actionable step. Enabled versus disabled alone does not tell the user where they are in a sequence.
- Put resolved state in tooltips or adjacent detail text instead of restating the label: the actual paths, target, counts, and whether a precondition currently holds. Rebuild that state on refresh, and do not make a tooltip the only carrier of information required to use a critical or destructive action safely.

## Reviewer Focus
- is every potentially large or expensive collection virtualized, and does each recycled row resolve its current item or stable identity at event time
- can an in-flight refresh be distinguished from an empty result by looking at the panel
- does the panel follow the editor skin, or does it assume one
- does the layout communicate the required order of a multi-step flow without a tooltip
