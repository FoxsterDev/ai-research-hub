# Skill: Adaptive Grids

## Use For
- inventory and store grids
- reward, gallery, and collection shelves
- adaptive mobile card grids in UGUI
- scrollable grid-heavy screens

## Rules
- Start from an explicit grid contract before authoring the layout:
  - fixed column count
  - fixed row count
  - expected scroll axis
  - minimum tappable cell size
  - tolerated aspect-ratio drift
- Do not leave `GridLayoutGroup` on `Flexible` when the product needs deterministic columns, rows, or card sizes across phones.
- Use `Canvas Scaler` with `Scale With Screen Size` for mobile screen-space UI, then verify the `Match` value against both reference orientation and aspect-ratio extremes; do not rely on scaler defaults alone.
- Use anchors to preserve shell layout, then adapt the grid inside that shell. Do not expect grid scaling alone to keep outer spacing and edge pinning correct on narrow phones.
- Do not solve every width change by adding more columns. On wider mobile windows, constrain card width and add columns or companion panes only when readability and tap safety stay intact.
- Remember that `GridLayoutGroup` ignores the minimum, preferred, and flexible size of its children. If cells must adapt to parent width, compute or assign the cell size at the grid owner level instead of expecting child `LayoutElement` settings to drive the result.
- For mobile grids with fixed width and vertical growth, prefer `Fixed Column Count` plus flexible height. For horizontal shelves with fixed height and horizontal growth, prefer `Fixed Row Count` plus flexible width.
- Avoid stacking `GridLayoutGroup`, `ContentSizeFitter`, and extra nested layout groups on hot or frequently refreshed grids. If the grid changes often, prefer on-demand sizing code or a narrower custom layout over deeper auto-layout chains.
- Keep static chrome, headers, and background visuals off the same Canvas as fast-changing grid content. If a dragged card, selection frame, countdown, or animated badge updates every frame, isolate that moving region further when rebuild cost is measurable.
- For complex scrollable grids, prefer pooling once the visible item count is much smaller than the total data count. If the data set is `100` items and the viewport only needs about `10`, do not instantiate `100` UI cards by default; keep only the visible window plus a small preload buffer, for example `10` visible + `3` above + `3` below.
- Treat large scrollable collections as windowed UI, not as one-view-per-data-item UI. The data source can contain hundreds of entries while the instantiated visual pool stays near the number of concurrently visible cells.
- On uniform cell sizes, prefer position-based pooling over reparenting-based pooling to avoid avoidable dirty and rebuild cascades.
- For variable-size cells, use pooling only with an explicit sizing strategy. If item height or width is content-driven, the implementation must still preserve stable scroll math and avoid full-tree relayout on every bind.
- Infinite scroll or virtualized scroll is required once full instantiation would create measurable startup cost, memory waste, or scroll hitching. The goal is to bind new data into recycled cells as items enter the viewport, not to keep off-screen cards alive forever.
- If native `ScrollRect` sizing convenience is useful, a hybrid placeholder layout is acceptable, but only if rebuild cost stays within budget on low-end phones.
- A practical default is:
  - instantiate enough cells to cover the viewport
  - add a small overscan buffer on each edge to hide rebinding during drag
  - recycle and rebind cells when they leave the buffered viewport
- Size the overscan buffer from scroll speed and cell complexity. Too little buffer causes visible pop-in; too much buffer turns pooling back into near-full instantiation.
- Add `RectMask2D` to sizable scrolling grids so off-viewport cells do not stay in the drawable set during Canvas rebuild analysis.
- Minimize raycast work per cell. Prefer one intentional root hit target for the card and disable raycast targets on decorative child graphics and labels unless they truly need direct interaction.
- Keep effective tap targets safe after scaling and localization. If multiple tiny actions compete inside one card, move secondary actions into detail or overflow instead of letting accidental taps become normal.
- For text-bearing cards, test larger text, long localizations, and RTL before freezing column counts; when text no longer fits cleanly, prefer vertical reflow or a different card template over severe truncation.
- Keep each cell hierarchy shallow. Avoid many nested layout groups, fitters, and animated text elements inside every card unless the product value justifies the rebuild and batching cost.
- For sample, debug, or SDK-validation grids, prefer the cheapest authoring path that stays readable. Do not jump to custom grid code unless the screen is meant to represent production runtime behavior.

## Validation Focus
- portrait and landscape aspect-ratio extremes
- low-end mobile profiler capture
- `Canvas.BuildBatch` and `Canvas.RenderOverlays` spikes
- startup cost and memory use versus visible-item count
- scroll smoothness under realistic item counts
- rebinding stability during fast scroll and fling
- tap target safety after scaling
- larger-text, RTL, and long-localization breakpoints
