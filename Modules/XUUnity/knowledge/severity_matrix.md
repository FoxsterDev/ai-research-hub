# XUUnity Severity Matrix

- Critical: likely crash, ANR, data loss, privacy violation, or release blocker.
- High: strong regression risk, broken lifecycle, unsafe ownership, or major startup cost.
- Medium: maintainability or performance issue with bounded production risk.
- Low: clarity or consistency issue with low behavioral risk.

- A duplication or clone finding is `Medium` only while the copies' derived state and teardown are still identical. Inspect them before grading; once either has diverged the finding is a correctness defect at the severity of the divergence, and "a future fix must land twice" is the wrong frame for a defect that has already shipped.
