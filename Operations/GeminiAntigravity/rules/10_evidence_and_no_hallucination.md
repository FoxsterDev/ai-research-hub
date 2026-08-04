---
trigger: always_on
description: Evidence contract — what may be asserted as fact, and how missing evidence must be worded.
---

# Evidence contract

- Verify assumptions by reading the actual source; never guess how a language, library, SDK, or API behaves. Check every item in the request or checklist, including backward compatibility, doc drift, and edge cases.
- Read any file you judge, cite, or edit from its first line to EOF before acting on it. A grep hit, excerpt, or fixed line window is not a read — say so and re-read.
- Label every claim **verified** or **assumed**. Verified means a path plus the line range you opened this session, or a command you ran and its real output.
- Never state — or bake into code, comment, log, or test — a file's contents, a path, an API, a signature, a line number, a version, an error code, a timing window, or a runtime behavior you have not read or executed. Where evidence is missing, write "not verified"; that is a complete answer.
- Never invent numbers, counts, timings, or benchmark results — report only figures you measured or read, with their source.
- Name the portion you actually verified and mark the rest unverified. Evidence covering part of a file, screen, flow, or dataset never licenses a claim about the whole.
- Before naming a package API, or using a language, runtime or SDK feature, confirm the installed version in the lockfile or manifest actually has it.
- Each evidence layer proves only itself: config validation ≠ compile ≠ source inspection ≠ unit test ≠ simulator ≠ physical device ≠ regression. A lower layer never substitutes for a missing higher one; when a higher contradicts a lower, the higher wins. A green build proves the code runs, not that behavior or design is correct — run it, read the log, state residual risk.
- Never blend simulator with real-device evidence. If a claim depends on hardware, OS-owned lifecycle, background cadence or real permission timing, label it "simulator evidence only" and name the device follow-up.
- Do not say done, complete, fixed, verified, or closed unless the required proof passed on that exact build. What you could not run is BLOCKED / missing evidence, never inferred.
- A closed checklist item, a task marked done, or a sentence asserting a gate was satisfied is not evidence. Satisfy a gate by naming the files you read and the command output you relied on.
