# XUUnity Knowledge: Change Complexity Budget

## Purpose
Make structural cost visible during implementation and review so safety machinery, test seams, and wrappers cannot earn architectural credit merely by being explicit.

This is an evidence budget, not a universal line-count quota. Compare the change with the resolved project's existing owners and closest current exemplars.

## Required Inventory
For a concrete change or architecture verdict, inventory the relevant delta:

- production files and production lines changed;
- growth of root composition, scene, bootstrap, navigation, or screen-owner types;
- new mutable state owners;
- new locks, atomics, semaphores, queues, generations, and thread/context hops;
- new interfaces, adapters, facades, coordinators, wrappers, and static global owners;
- new helper types whose only consumer already owns the data or flow they expose;
- new cross-layer callbacks or round trips;
- locally reimplemented lifecycle, completion, caching, request-sharing, or duplicate-entry behavior;
- production seams added primarily for tests;
- feature logic introduced into generic or app-root layers.

Use `none` when a category is genuinely unchanged. Do not omit expensive categories from the inventory.

## Justification Rule
Every added state owner or coordination/abstraction mechanism must name:

- the product invariant it owns;
- why an existing project capability or existing owner cannot express it;
- why a smaller state or boundary is insufficient;
- who constructs, starts, cancels, and disposes it;
- what can be deleted because it now owns the invariant.

If the same invariant is guarded in more than one layer, consolidate it or document the distinct semantics. “Defense in depth” without a different reachable failure mode is duplication, not a free safety improvement.

## Project-Fit Gate
Before introducing a new lifecycle, binding, shared-operation, popup-flow, cache, or request-coordination abstraction:

1. inspect the resolved project's core/framework layer and closest maintained exemplars;
2. identify capabilities by semantics rather than assuming universal type names;
3. record the matching implementation or the exact semantic mismatch;
4. prefer the project-native owner when its contract matches.

Project-specific primitive names and limitations belong in project memory or a host/project override, not in public core.

## Simplification Pass
Before approval or closeout:

- delete forwarding wrappers and implementation-shaped test seams;
- collapse duplicate guards and repeated thread normalization;
- move feature orchestration out of root composition owners;
- replace scattered flags with one locally readable state owner;
- verify that every surviving abstraction removes more call-hopping or risk than it adds;
- test behavioral invariants rather than the chosen lock, semaphore, enum, or helper shape.

## Review Consequence
Unexplained growth, duplicated lifecycle, speculative synchronization, feature logic in a root owner, or a call path that crosses layers and returns through callbacks must lower architecture, maintainability, and project-fit scores. A reviewer may not offset that cost by praising explicit gates or test seams without the evidence above.
