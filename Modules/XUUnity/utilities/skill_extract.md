# XUUnity Utility: Skill Extract

## Goal
Convert new knowledge provided by the user into reusable `XUUnity` skill candidates.

## Use For
- best practices shared in chat
- notes about async, UI, SDK, performance, tests, or architecture
- reusable engineering guidance that may belong in `skills/`
- upstream research artifacts that may become reusable skills or shared knowledge

## Process
1. Identify the topic, scope, and intended reuse level.
2. Separate durable rules from examples, incidents, and project-local details.
3. Map the knowledge to an existing skill family if possible.
4. If no family fits, propose a new skill family or topic file instead of discarding the knowledge.
5. Mark which parts belong in shared skills and which parts belong in project overrides.

## Rule
Unknown but valid reusable knowledge must not be skipped only because there is no current matching skill family.
If the knowledge is strong and reusable, propose:
- a new skill family
- a new topic file inside an existing family
- or a non-skill shared destination if skills are not the right abstraction

## Output
- Topic
- Candidate skill family
- Whether a new skill family is required
- Extracted rules
- Shared versus project-specific split
- Required verification
- Proposed target files
