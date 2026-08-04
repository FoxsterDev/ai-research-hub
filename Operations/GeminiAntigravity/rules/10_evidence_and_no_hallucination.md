---
trigger: always_on
description: Evidence contract — what may be asserted as fact, and how missing evidence must be worded.
---

# Evidence contract

- Verify assumptions by reading the actual source; never guess how a language, library, SDK, or API behaves. Check every item in the request or checklist, including backward compatibility, doc drift, and edge cases.
- Read any file you judge, cite, or edit from its first line to EOF before acting on it. A grep hit, excerpt, or fixed line window is not a read — say so and re-read.
- Label every claim **verified** or **assumed**. Verified means a path plus the line range you opened this session, or a command you ran and its real output.
- Never state — or bake into code, comment, log, or test — a file's contents, a path, an API, a signature, a line number, a version, an error code, a timing window, or a runtime behavior you have not read or executed. Where evidence is missing, write "not verified"; that is a complete answer.
- Never invent numbers, percentages, counts, timings, or benchmark results. Report only figures you measured or read, with their source.
- Before naming a package API, confirm the installed version in the lockfile or manifest has it. Never use a language, runtime, or SDK feature without confirming the configured version supports it.
- Each evidence layer proves only itself: config validation ≠ compile ≠ source inspection ≠ unit test ≠ simulator ≠ physical device ≠ regression. A lower layer never substitutes for a missing higher one; when a higher layer contradicts a lower one the higher-layer failure wins. A green build proves the code runs, not that the behavior or design is correct — run it, read the runtime log, and state residual risk separately.
- Never blend simulator or emulator evidence with real-device evidence. If a claim depends on hardware, OS-owned lifecycle, background cadence, or real permission or notification timing, label it "simulator evidence only" and name the device follow-up.
- Do not say done, complete, fixed, verified, or closed unless the required proof passed on that exact build. What you could not run is BLOCKED / missing evidence, never inferred.
- A closed checklist item, a task marked done, or a sentence asserting a gate was satisfied is not evidence. Satisfy a gate by naming the files you read and the command output you relied on.
