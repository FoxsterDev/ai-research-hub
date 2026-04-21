# XUUnity Code Style: CSharp

## Goals
- production readability
- safe async and ownership patterns
- low-allocation runtime paths
- clear boundaries between game logic, services, and platform bridges

## Rules
- Use English for identifiers, logs, and documentation.
- Do not add inline comments in C# unless the project explicitly requires them.
- Public APIs may use XML docs when the contract is not obvious.
- Prefer explicit naming over clever abstractions.
- Prefer small focused types over broad mixed-responsibility classes.
- Prefer intent-oriented public APIs over exposing transient technical state directly when callers only need a business decision such as whether an action may start.
- Keep async ownership explicit and avoid hidden fire-and-forget flows.
- Avoid per-frame allocations, hidden LINQ allocations, and unnecessary closure captures on hot paths.
- Prefer dependency boundaries that are testable and easy to reason about.
- If thread safety matters, make synchronization explicit.
- Do not call virtual members from constructors. If controlled overrides are needed, move bridge or service setup into an explicit initialization step.
- Prefer test doubles or test-only implementations over compile-flag fake branches mixed into production hot paths.

## Naming
- Types, methods, properties, and public members use `PascalCase`.
- Private instance fields use `_camelCase`.
- Unity serialized fields also use `_camelCase`.
- Interfaces use `I` + `PascalCase`.
- Type parameters use `T` + `PascalCase`.
- Private constants use `ALL_UPPER_CASE` when they are true constants.
- For platform-specific variants, keep the platform suffix at the end of the identifier: `BannerUrliOS`, `StoreConfigAndroid`.

## Member Shape
- Always use explicit accessibility on non-interface members.
- Prefer modifier order like `public static`, `private readonly`, `protected override`.
- Prefer `var` when the type is obvious or repeated on the right-hand side.
- Do not qualify instance members with `this.` unless disambiguation is required.
- Prefer `sealed` on concrete classes that are not designed for inheritance.
- Prefer expression-bodied members for simple getters or one-line forwarding members when readability stays high.
- Prefer early-return guard clauses over deep nesting.
- Remove one-line forwarding wrappers and duplicate guards when they do not preserve a real boundary or contract.
- Keep transient synchronization or pending-confirmation flags private or internal by default when outward callers can use a behavior method such as `CanStartAction(...)` instead.
- Avoid `partial` types unless generation, tooling, or a strong separation boundary genuinely requires them.
- Avoid nested public types for reusable contract or result objects when a small top-level type in its own file would keep the API surface clearer.

## Braces And Blocks
- Open braces go on a new line.
- Always use braces for `if`, `else`, `for`, `foreach`, and `while`.
- Single-line blocks are acceptable only when they stay naturally short and clear.

## Spacing And Formatting
- Use 4 spaces for indentation.
- Keep line length near 120 characters.
- Use one space after control-flow keywords: `if (...)`, `for (...)`.
- Use spaces around binary operators.
- Use one space after commas.
- Do not use spaces inside method-call parentheses or square brackets.
- Keep method declarations and method calls tight: `Foo(bar)`, not `Foo ( bar )`.
- Wrap parameters, arguments, long assignments, tuples, and call chains only when needed.

## Structure
- Use block-style namespaces.
- Keep `using` directives at the top of the file.
- Keep files and types arranged for readability, not for stylistic cleverness.
- Do not group unrelated fields or methods just to reduce line count.
- Keep declaration order stable when editing existing files unless there is a clear reason to reorganize.
- Keep long-lived domain or UI state mutation and derived availability rules in the model or state-owning layer.
- Keep network wait timeouts, cancellation, and refresh orchestration in the coordinating layer rather than pushing them down into leaf state objects.
- Common class order:
  1. constants
  2. readonly fields
  3. serialized fields or regular private fields
  4. public properties
  5. events
  6. constructors
  7. public methods
  8. protected overrides
  9. private methods

## Review Focus
- naming clarity
- format consistency
- ownership clarity
- async safety
- API intent clarity versus technical-state leakage
- allocation behavior
- behavior-preserving structure
- lock scope minimalism and side-effect placement
