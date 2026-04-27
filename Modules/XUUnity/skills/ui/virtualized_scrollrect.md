# Skill: Virtualized ScrollRect

## Use For
- large scrollable lists and grids
- inventory, store, gallery, and feed virtualization
- infinite scroll and windowed UI
- `ScrollRect` performance work in UGUI

## Architecture
- Separate the problem into two layers:
  - data set size
  - instantiated view window size
- The data source may contain hundreds or thousands of entries. The instantiated UI should stay near:
  - visible cell count
  - plus a small overscan buffer
- Use a controller that owns:
  - viewport metrics
  - pool lifetime
  - index-to-position mapping
  - bind and unbind flow
  - content extent sizing

## Contracts
- Define the collection contract before implementation:
  - scroll axis
  - fixed-size or variable-size cells
  - total item count source
  - async page loading or fully local data
  - selection ownership
  - cell interaction model
- Do not treat one visual cell as one permanent data item. A virtualized collection reuses cell views as data indices move through the viewport.

## Project Adaptation Checklist
- Resolve the existing UI ownership model before designing the virtualization layer:
  - scene-authored binder
  - presenter-driven screen
  - controller-owned runtime wiring
- Identify the project text stack:
  - `TMP`
  - `UnityEngine.UI.Text`
- Identify how cell state is owned:
  - visual-only in the view
  - selection in presenter or controller
  - data-driven badges, timers, and async thumbnails
- Identify the accepted event wiring style:
  - direct button listeners
  - binder callbacks
  - presenter commands
  - reactive stream or signal layer
- Identify async ownership:
  - synchronous local bind only
  - async thumbnails
  - paged remote data
  - cancellation required on recycle
- Identify whether the project already standardizes on:
  - object pool abstraction
  - list or grid presenter base class
  - visibility lifecycle hooks
  - analytics hooks on item exposure or click
- Confirm the content contract:
  - uniform cells or variable-size cells
  - sorting and filtering
  - insert or remove at runtime
  - pull-to-refresh
  - end-of-list behavior
- Confirm what must be reset on recycle:
  - listeners
  - tweens
  - async handles
  - selected state
  - loading state
  - placeholder visuals
- Do not write the implementation template until these answers are known. The architecture is reusable; the concrete class shape is project-specific.

## Rules
- If the viewport shows about `10` cells, instantiate only the visible window plus overscan, not all `100+` item views.
  - for single-column lists, a practical starting point is `visible + 2..4` cells per edge depending on fling speed and bind cost
  - for multi-column grids, size overscan in full buffered rows or columns, not partial per-cell fragments
- Prefer one pool per cell template family. If cards have materially different shapes, keep separate pools rather than mutating one pooled object through incompatible states.
- Bind data only when a recycled cell enters a new index assignment. Do not rebinding every visible cell on every scroll tick.
- Unbind or reset recycled cells before reuse when stale state is possible:
  - selection markers
  - async image requests
  - timers
  - badges
  - button listeners
  - tween state
- Position-based virtualization is the default for uniform cells. Move pooled `RectTransform`s and update their bound indices instead of reparenting them through the hierarchy.
- For uniform-size collections, make scroll math deterministic:
  - derive visible index range from scroll offset and cell stride
  - resize the content root to the total virtual extent
  - map each visible index to a stable anchored position
- For grids, compute:
  - items per row or column
  - row or column count
  - index-to-row and row-to-position mapping
  - visible row window instead of visible item-by-item window when that keeps math simpler
- For multi-column grids, prefer recycling by visible row window plus buffered rows. This keeps overscan symmetric and avoids under-buffering fast flings with only a few extra loose cells.
- Overscan exists to hide rebinding during drag and fling. Too little causes pop-in; too much erodes the value of virtualization.
- For grids, overscan should usually be expressed as buffered rows or columns, because the user perceives row-pop and column-pop, not isolated off-screen cells.
- Keep bind cost small. A virtualized list with expensive bind work can still hitch even if object count is low.
- Infinite scroll means data pagination and virtualization together:
  - virtualization limits view count
  - pagination limits loaded data count when the backend or local source is large
- Trigger page fetches from a threshold near the trailing edge of loaded data, but guard against duplicate in-flight requests.
- Guard paginated responses with a request or query version when sort, filter, or search inputs can change while requests are in flight. An old page response must not append into a newer dataset snapshot.
- Loading indicators, retry rows, and terminal "end of list" rows should be part of the data contract, not ad hoc sibling objects floating outside the virtualization model.

## Pagination Safety
- Treat each logical dataset revision as a versioned stream:
  - base query
  - sort
  - filter
  - search text
  - parent scope
- When the dataset revision changes, invalidate older in-flight page requests or ignore their completion.
- Do not merge late responses from an older dataset revision into the active list, even if the page indices appear compatible.
- Preserve scroll position only when the product contract says the refreshed dataset is semantically the same collection. A filter or sort jump may require intentional reset instead.

## Uniform Cells Pattern
- Best default for stores, inventories, reward grids, and icon-heavy shelves.
- Flow:
  - compute visible index window from scroll offset
  - ensure pool size covers visible window plus overscan
  - recycle cells that leave the buffered window
  - assign recycled cells to new indices entering the buffered window
  - bind data and set anchored positions

## Variable-Size Fallback
- Variable-size virtualization is materially harder than uniform-size virtualization.
- Use it only when the product really needs content-driven height or width.
- Required extra contracts:
  - size estimation strategy
  - post-bind measurement strategy
  - cumulative offset lookup
  - relayout correction rules
- If the product can tolerate template normalization, prefer a small set of fixed card heights over fully freeform heights.

## Implementation Shape Matrix
- Scene-authored UGUI plus binder:
  - prefer a scene-authored cell prefab
  - keep layout, anchors, visuals, and child hierarchy in scene assets
  - use a thin binder API such as `Bind(viewModel)` and `ResetForRecycle()`
  - let the virtualization controller own pooling and visible-window math
- Presenter-driven screen:
  - keep visible-range math and pool ownership in the presenter or its dedicated collection controller
  - keep the cell view dumb
  - send item click, selection, and focus events back up through presenter-owned callbacks
  - prefer explicit `Bind`, `Unbind`, and `SetSelected` seams
- SDK sample or debug UI:
  - prefer the cheapest readable implementation
  - skip full virtualization unless list size or perf evidence justifies it
  - accept simpler pooling or even full instantiation for low-scale diagnostic surfaces
- Uniform inventory or store grid:
  - best fit for full virtualization
  - use deterministic cell stride, row math, and position-based recycling
  - use buffered rows for overscan and stable bind or unbind flow
- Variable-height feed or message list:
  - highest complexity
  - prefer normalization to a few template sizes first
  - only use true variable-size virtualization when the product value clearly justifies the extra sizing and offset machinery
- Async image-heavy collections:
  - require cancellation or version-guarding on recycle
  - stale thumbnail completion must not paint the wrong recycled cell
  - loading placeholders are part of the bind contract, not ad hoc patches
- Analytics-sensitive collections:
  - define whether impressions are counted on bind, first visible frame, or minimum visible percentage
  - recycled views must not double-count impressions accidentally

## Review Checklist
- Does the implementation instantiate one UI object per data item even when only a small visible window is needed?
- Is the pool size derived from visible window plus overscan, or did the implementation drift back toward near-full instantiation?
- Does recycling move and rebind cells, or does it reparent aggressively and dirty the hierarchy more than necessary?
- Are cells rebound only when their assigned index changes, or is bind work happening on every scroll update?
- Does recycle reset all stale state:
  - listeners
  - async image requests
  - selection markers
  - loading spinners
  - timers
  - tweens
- Can an async completion paint the wrong recycled cell because there is no cancellation or version guard?
- Does pagination guard against duplicate in-flight loads and repeated trailing-edge triggers?
- Can sort, filter, or search changes invalidate old page responses, or can stale data append into the active dataset?
- Is the loading, retry, or end-of-list row part of the collection contract, or is it hacked in outside the virtualization model?
- For uniform cells, is the visible-range math deterministic and based on stride, viewport size, and scroll offset?
- For variable-size cells, is there an explicit cumulative offset and measurement strategy, or is the code pretending variable height is as simple as fixed height?
- Is overscan large enough to hide pop-in during fling, but small enough that object count still stays close to visible demand?
- Does the implementation preserve stable selection, focus, and scroll position when data refreshes, inserts, removes, or reorders occur?
- Are `Canvas.BuildBatch`, layout rebuild, and allocation spikes measured on low-end mobile hardware or representative profiler targets?
- If the collection is sample or debug-only, is the complexity proportional to the scale of the problem, or was production-grade virtualization added without evidence?

## Validation Focus
- startup allocations versus visible-item count
- no `100-to-1000` view instantiation for `10-to-20` visible items
- smooth drag and fling on low-end devices
- no stale listeners, images, or selection state after recycle
- stable index mapping after insert, remove, or refresh
- pagination threshold behavior under slow and fast network responses
- stale-response rejection after query, filter, or sort changes
- no visible pop-in from undersized overscan
