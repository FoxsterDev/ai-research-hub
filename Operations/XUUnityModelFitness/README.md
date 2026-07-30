# XUUnity Model Fitness — Public Deterministic Engine

Public core of the fitness engine from
`AIRoot/Design/XUUNITY_MODEL_FITNESS_AND_REDUCED_STACK_GATE_DESIGN.md`
(phase P2). Everything here is public-safe and host-agnostic: no fixture
prompts, raw transcripts, host paths, tokens, or provider secrets. Host
installations keep their confidential fixtures, adapter configuration, and
raw evidence in their own private operation and compose this engine.

## What is implemented (P2.1 + P2.2)

### `model_fitness/baseline.py` — content-addressed baseline (P2.1)

- Merkle-style seed identity over sorted entries (repo-relative path, entry
  type, outcome-relevant mode, byte length, content sha256; symlink targets
  hashed, gitlink boundaries take an attested nested content hash).
- Timestamps, absolute paths, worktree names, and generated commit ids never
  enter the identity; mtimes are normalized in the materialized seed.
- `materialize_seed` / `clone_seed` verify identity on every copy; a
  corrupted seed store fails closed.
- `task_measurement_key` and `strict_profile_key` are strict-field domain
  digests: a missing or unknown field is an error, so no declared
  environment/inference field can silently drop out of the comparison key.

### `model_fitness/attestation.py` — parent-owned attestations

- Session attestation build/verify with a MAC (domain
  `xuunity:session-attestation:v1`) whose key never enters the model
  namespace; tamper, wrong key, malformed timestamps, and expiry fail
  closed. Sanitized projections keep opaque ids only.
- Request-boundary attestation (`xuunity.request-attestation.v1`): the exact
  post-truncation payload serialized into one provider request, with located
  artifact byte segments and a truncation canary that must survive after the
  last segment. Only a verified attestation upgrades an artifact to
  `trusted_runtime_delivered`; anything else stays
  `runtime_delivered_unverified` and earns no delivery credit. Raw tool logs
  and local stdout are never this boundary.
- Protected run manifest builder (`xuunity.protected-run-manifest.v1`),
  anchored outside the model-writable worktree.

### `model_fitness/broker.py` — exclusive write broker (authoritative mode)

- The only component that can mint `enforcement_mode: authoritative`, and
  only after: session-attestation MAC verification, a `pass` from the P1
  reduced-stack gate over protected inputs, and a verified OS write
  boundary. Same-uid chmod is explicitly non-authoritative (revocable);
  loose-file CLI results remain `audited` always.
- One-use mutation capabilities in MAC domain
  `xuunity:mutation-capability:v1`, bound to attestation id, session id,
  repository content hash, plan/ledger/semantic-result hashes, mutation
  generation, scope, and expiry. Issuance and consumption are atomic
  (`O_CREAT|O_EXCL`); replay, concurrent double-spend, expiry, wrong domain,
  cross-session use, and generation rollback fail closed. The token itself
  never appears in any stored record — only its sha256.
- Batch application enforces capability scope plus attested mutation roots,
  rejects traversal and symlinked paths, journals before/after hashes of
  every intermediate mutation (mutate-then-restore cannot disappear), and
  requires a gate reconcile after each batch before the next authorization.

### `model_fitness/isolation.py` — read namespace, network, hermetic oracles

- Per-platform sandbox backends behind one contract:
  - macOS: Seatbelt (`sandbox-exec`), deny-by-default profile on a
    `system.sb` base;
  - Linux: Bubblewrap (`bwrap`) mount namespaces (protected paths are simply
    absent) plus `--unshare-net`;
  - platforms without a workable primitive (including Windows) return an
    explicit `NullBackend` — enforcement is reported **unenforced** and runs
    stay `audited`; nothing is assumed.
- `probe_enforcement` proves policies with real child processes: control
  read/write must succeed while a protected read, an out-of-namespace
  write, and a loopback connect are denied (errno-discriminated: refused ≠
  denied). `SandboxProbeWriteBoundary` feeds the broker only a probe-proven
  boundary.
- Environment scrubbing to an explicit allowlist with a policy hash;
  default-deny network policy separated from the parent-owned provider
  transport; content-addressed `ReplayCorpus` for pre-captured external
  responses (a miss is an error, never a live fetch); hermetic
  materialization of the captured final tree with identity verification and
  scrubbed-environment oracle execution.

### `schemas/` — control-plane contracts

`xuunity.adapter-profile.v1`, `xuunity.request-attestation.v1`,
`xuunity.mutation-capability.v1`, `xuunity.protected-run-manifest.v1`,
`xuunity.run-result.v1`. Module-owned contracts (envelope, plan, ledger,
gate result, session attestation) stay in
`AIRoot/Modules/XUUnity/schemas/` and are consumed unchanged.

## Honest boundaries

- **P2.3/P2.4 are not finished here.** Generic adapter transcript parsing
  and the orthogonal scoring engine still live in host compatibility
  operations; they compose the public `observation_contract` /
  `shell_observer` but have not been ported into this operation yet. No
  numeric fitness score exists anywhere until a runner-owned semantic oracle
  does (design P3).
- **Windows enforcement.** The engine runs on Windows (broker, baseline,
  attestation, replay, hermetic materialization are OS-neutral and the
  capability store uses portable `O_EXCL` atomicity), but no OS sandbox
  backend is driven there, so read-namespace/network policies report
  unenforced and results stay `audited`. A parent that supplies its own OS
  boundary (read-only mount, user separation) can still declare it via the
  write-boundary contract.
- **Provider transport.** CLI surfaces that share network between the model
  process and the provider cannot be network-isolated by this module alone;
  the adapter profile records that honestly and such runs are not
  adoption-grade (design rule).

## Tests

From this directory:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p "test_*.py"
```

The suite covers: parallel-identical seeds, identity sensitivity (content,
mode, symlink target, gitlink), store/clone tamper detection, strict
comparison-key fields; attestation roundtrip/tamper/expiry/wrong-key,
truncation-canary semantics, the gate bridge (attested manifest satisfies an
obligation, unverified never does); capability conformance (canonical
binding, per-field authentication, wrong domain, expiry, replay, concurrent
double-spend, generation rollback), broker authorize/apply/reconcile flows,
scope and symlink escapes, audited downgrades (gate fail, unverified
boundary, expired session); environment scrubbing, policy hashes, replay
corpus, hermetic materialization, bubblewrap argv contract, null-backend
degradation, and — where a sandbox backend exists — real OS enforcement
probes (denied read, denied write, denied network with errno
discrimination). Enforcement tests skip only where no backend exists, which
is exactly the configuration that reports itself unenforced.
