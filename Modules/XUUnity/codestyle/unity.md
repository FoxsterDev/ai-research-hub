# XUUnity Code Style: Unity

## Goals
- safe runtime behavior
- minimal impact on frame time and startup
- explicit lifecycle control

## Rules
- Keep Unity lifecycle methods focused and predictable.
- Avoid heavy work in `Awake`, `OnEnable`, and first-frame startup unless required.
- Do not hide expensive work in property accessors or lazy initialization that can hit critical flows unexpectedly.
- Prefer composition and clear service boundaries over tightly coupled scene logic.
- Make main-thread assumptions explicit when callbacks or SDK responses are involved.
- Treat app launch, ads, purchases, saves, restore, notifications, attribution, and analytics as critical flows.

## Serialized Fields
- Prefer private serialized fields over public mutable fields.
- Use `[SerializeField] private Type _fieldName;`
- Keep inspector-facing fields near the top of the class.
- Do not expose fields publicly just for inspector binding.
- Group serialized fields together in a single block.
- Keep runtime-only private fields in a separate block below serialized fields.

## Lifecycle
- Keep `Awake`, `OnEnable`, `Start`, `OnDisable`, and `OnDestroy` responsibilities clear and non-overlapping.
- Subscribe and unsubscribe symmetrically.
- Do not hide critical initialization across too many lifecycle methods.
- Keep scene object access explicit and predictable.
- Prefer presenters, models, and view interfaces to keep scene components thin when the feature is UI-heavy or flow-heavy.

## Runtime Discipline
- Avoid allocations and expensive lookups in `Update`, `LateUpdate`, and `FixedUpdate`.
- Cache references that are reused on hot paths.
- Keep gameplay state mutations out of unpredictable callback paths unless thread and order guarantees are clear.
- Prefer deterministic code paths for startup and resume-from-background flows.
- Use guard clauses for null, empty, and invalid-state exits before heavier logic.
- Prefer small helper methods for repeated UI or transaction update steps instead of duplicating logic inline.

## Review Focus
- lifecycle safety
- startup impact
- scene coupling
- critical flow protection
