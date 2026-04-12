# XUUnity Product Protocol: Feature Explainer

## Use For
- explain what a feature does
- explain when a popup, offer, screen, or reward appears
- explain current logic in product language

## Process
1. Read relevant project memory and prior reports.
2. Identify the likely source-code ownership points.
3. For gameplay-oriented projects that use a project-local gameplay bridge or runtime-support bridge, start from the bridge entry artifact(s) defined by the repo router, project router, or project memory when the request is phrased as a user flow, trigger, reward, popup, or gameplay moment rather than as a class name.
4. Do not apply the bridge-first rule when the current project router or project memory explicitly marks the project as an opt-out to that path.
5. If the feature is implemented by a project-local class, inspect its constructor wiring, inheritance, and delegated services before concluding behavior.
6. If a project-local class inherits from a shared base class or forwards behavior into a shared presenter, manager, controller, service, or trigger layer, read that shared layer too.
7. Perform a fast verification pass in code for current behavior.
8. Explain only verified or clearly marked inferred behavior.

## Special Rule
- For names that look like feature entry points or orchestration points such as `*Feature`, `*Triggers`, `*Manager`, `*Controller`, or `*Service`, do not explain from the local file alone.
- Follow the runtime boundary far enough to cover:
  - project-local trigger points
  - shared behavior contract
  - user-visible outcome
  - key dependencies that materially affect the feature explanation
- For gameplay projects with a project-local gameplay bridge, flow-level questions should usually be traced through that bridge's events, state, or trigger surface first, then through the subscribed feature classes.
- Treat project-router or project-memory opt-outs as exceptions to that bridge-first rule.


## Output
- what it does
- trigger conditions
- user-visible flow
- systems involved
- key dependencies
- verification status
