# XUUnity Glossary

- Bridge crossing: one managed to native or native to managed transition.
- Agent-private layer: a tool-specific memory, entrypoint, or config layer that points to shared `xuunity` truth and records only that agent's capability map or calibration.
- Project memory: durable project-local rules stored in `Assets/AIOutput/ProjectMemory/`.
- Previous outputs: generated reports stored in `Assets/AIOutput/`.
- Release blocker: issue that should stop submission until remediated.
- Validation contract: the canonical five-field schema used to carry lane choice, expected evidence, and remaining validation gaps across `xuunity` task stages.
- Expected evidence class: the concrete proof expected from the chosen validation lane, such as `interactive scene snapshot` or `artifact build exit + artifact presence`.
- Validation gap: any missing proof, blocked lane, weak evidence, or observability hole that prevents a stronger claim.
- Trustworthy final accounting: a validation result that can report reliable final pass or fail totals, terminal artifact completion, or terminal result state for the claim being made.
