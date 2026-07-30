"""Run isolation: environment, read namespace, network, hermetic oracles
(design P2.2).

Nothing here claims enforcement it did not prove. OS sandboxing is provided
by per-platform backends — Seatbelt (``sandbox-exec``) on macOS, Bubblewrap
(``bwrap`` with mount/network namespaces) on Linux — and every policy is
*probed* with real child processes: the probe must show that a protected
read, an out-of-namespace write, and a network connection are actually
denied while control operations succeed. A platform without a working
backend (including Windows, which ships no equivalent primitive this module
can drive) is reported unenforced and the run stays audited; that is the
honest state, never a silent assumption. Model/tool network is default-deny
and separate from the parent-owned provider transport; required external
responses come from a pre-captured content-addressed replay corpus whose
hash enters the strict profile key, and a corpus miss is an error, never a
live fetch."""

from __future__ import annotations

import errno
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, NamedTuple

from . import MODULE_SCRIPTS_DIR  # noqa: F401  (bootstraps module imports)
from . import baseline
from .broker import BoundaryReport

import xuunity_canonical as xc  # noqa: E402

ENVIRONMENT_ALLOWLIST_SCHEMA = "xuunity.environment-allowlist.v1"
NETWORK_POLICY_SCHEMA = "xuunity.network-policy.v1"
READ_NAMESPACE_SCHEMA = "xuunity.read-namespace-policy.v1"
REPLAY_CORPUS_SCHEMA = "xuunity.replay-corpus.v1"

SANDBOX_EXEC = Path("/usr/bin/sandbox-exec")

DARWIN_SYSTEM_READ_ROOTS = (
    "/usr",
    "/bin",
    "/sbin",
    "/opt",
    "/System",
    "/Library",
    "/private/etc",
    "/private/var/db",
    "/private/var/select",
    "/var",
)

LINUX_SYSTEM_READ_ROOTS = (
    "/usr",
    "/bin",
    "/sbin",
    "/lib",
    "/lib32",
    "/lib64",
    "/etc",
    "/opt",
)

_DENIED_CONNECT_ERRNOS = frozenset(
    str(code)
    for code in (
        errno.EPERM,
        errno.EACCES,
        errno.ENETUNREACH,
        errno.ENETDOWN,
        errno.EHOSTUNREACH,
        errno.EADDRNOTAVAIL,
    )
)


class IsolationError(ValueError):
    pass


def scrub_environment(
    base_env: dict[str, str], allowlist: list[str]
) -> tuple[dict[str, str], str]:
    names = sorted(set(allowlist))
    env = {name: base_env[name] for name in names if name in base_env}
    allowlist_hash = xc.domain_digest(
        ENVIRONMENT_ALLOWLIST_SCHEMA, {"names": names, "values": env}
    )
    return env, allowlist_hash


def network_policy(
    *,
    provider_transport: str,
    replay_corpus_hash: str | None = None,
) -> tuple[dict[str, Any], str]:
    if provider_transport not in {"parent_owned", "shared_with_model"}:
        raise IsolationError(
            f"unknown provider transport: {provider_transport}"
        )
    policy = {
        "mode": "default_deny",
        "provider_transport": provider_transport,
        "replay_corpus_hash": replay_corpus_hash,
    }
    return policy, xc.domain_digest(NETWORK_POLICY_SCHEMA, policy)


def read_namespace_policy(
    *,
    readable_roots: list[str],
    writable_roots: list[str],
    protected_classes: list[str],
) -> tuple[dict[str, Any], str]:
    policy = {
        "readable_roots": sorted(readable_roots),
        "writable_roots": sorted(writable_roots),
        "protected_classes": sorted(protected_classes),
    }
    return policy, xc.domain_digest(READ_NAMESPACE_SCHEMA, policy)


class SandboxSpec(NamedTuple):
    readable_roots: tuple[str, ...]
    writable_roots: tuple[str, ...]
    allow_network: bool = False


def _profile_paths(paths: list[str]) -> str:
    return " ".join(
        f'(subpath "{Path(path).resolve()}")' for path in sorted(set(paths))
    )


def render_sandbox_profile(
    *,
    readable_roots: list[str],
    writable_roots: list[str],
    allow_network: bool = False,
) -> str:
    readable = list(readable_roots) + [
        root for root in DARWIN_SYSTEM_READ_ROOTS if Path(root).exists()
    ]
    lines = [
        "(version 1)",
        "(deny default)",
        '(import "system.sb")',
        "(allow process*)",
        "(allow file-read-metadata)",
        f"(allow file-read* {_profile_paths(readable)})",
        '(allow file-read* file-write* (subpath "/dev"))',
    ]
    if writable_roots:
        lines.append(f"(allow file-write* {_profile_paths(writable_roots)})")
    if allow_network:
        lines.append("(allow network*)")
    return "\n".join(lines) + "\n"


class SeatbeltBackend:
    """macOS ``sandbox-exec`` (Seatbelt) backend."""

    name = "seatbelt"

    def available(self) -> tuple[bool, str]:
        if sys.platform != "darwin":
            return False, f"seatbelt_not_darwin:{sys.platform}"
        if not SANDBOX_EXEC.is_file():
            return False, "sandbox_exec_missing"
        return True, ""

    def run(
        self,
        spec: SandboxSpec,
        command: list[str],
        *,
        cwd: Path | None = None,
        timeout: int = 30,
    ) -> subprocess.CompletedProcess:
        profile = render_sandbox_profile(
            readable_roots=list(spec.readable_roots),
            writable_roots=list(spec.writable_roots),
            allow_network=spec.allow_network,
        )
        return subprocess.run(
            [str(SANDBOX_EXEC), "-p", profile, *command],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )


class BubblewrapBackend:
    """Linux ``bwrap`` backend: the namespace exposes only bound roots, so a
    protected path is simply absent, and ``--unshare-net`` removes network."""

    name = "bubblewrap"

    def __init__(self, bwrap_path: str | None = None) -> None:
        self._bwrap = bwrap_path or shutil.which("bwrap")

    def available(self) -> tuple[bool, str]:
        if not sys.platform.startswith("linux"):
            return False, f"bubblewrap_not_linux:{sys.platform}"
        if not self._bwrap:
            return False, "bwrap_missing"
        return True, ""

    def command_prefix(
        self, spec: SandboxSpec, cwd: Path | None = None
    ) -> list[str]:
        arguments = [
            self._bwrap,
            "--die-with-parent",
            "--dev", "/dev",
            "--proc", "/proc",
            "--tmpfs", "/tmp",
        ]
        for root in LINUX_SYSTEM_READ_ROOTS:
            if Path(root).exists():
                arguments += ["--ro-bind", root, root]
        for root in spec.readable_roots:
            resolved = str(Path(root).resolve())
            arguments += ["--ro-bind", resolved, resolved]
        for root in spec.writable_roots:
            resolved = str(Path(root).resolve())
            arguments += ["--bind", resolved, resolved]
        if not spec.allow_network:
            arguments += ["--unshare-net"]
        if cwd is not None:
            arguments += ["--chdir", str(cwd)]
        return arguments

    def run(
        self,
        spec: SandboxSpec,
        command: list[str],
        *,
        cwd: Path | None = None,
        timeout: int = 30,
    ) -> subprocess.CompletedProcess:
        return subprocess.run(
            [*self.command_prefix(spec, cwd), *command],
            capture_output=True,
            text=True,
            timeout=timeout,
        )


class NullBackend:
    """No OS sandbox primitive on this platform; enforcement is unprovable
    here, so policies are reported unenforced and runs stay audited."""

    name = "none"

    def __init__(self, reason: str) -> None:
        self.reason = reason

    def available(self) -> tuple[bool, str]:
        return False, self.reason


def detect_backend() -> Any:
    for backend in (SeatbeltBackend(), BubblewrapBackend()):
        ok, _ = backend.available()
        if ok:
            return backend
    return NullBackend(f"no_os_sandbox_backend:{sys.platform}")


class EnforcementProbe(NamedTuple):
    available: bool
    read_denied: bool
    write_denied: bool
    network_denied: bool
    backend: str
    details: tuple[str, ...]


_READ_PROBE = "import sys; sys.stdout.write(open(sys.argv[1]).read())"
_WRITE_PROBE = "import sys; open(sys.argv[1], 'w').write('probe')"
_NETWORK_PROBE = (
    "import socket, sys\n"
    "try:\n"
    "    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)\n"
    "    s.settimeout(2)\n"
    "    s.connect((\"127.0.0.1\", 9))\n"
    "    print(\"connected\")\n"
    "except OSError as e:\n"
    "    print(e.errno if e.errno is not None else \"none\")\n"
)


def _python_roots() -> list[str]:
    return [
        sys.prefix,
        sys.exec_prefix,
        str(Path(sys.executable).resolve().parent),
    ]


def probe_enforcement(
    *,
    readable_roots: list[str],
    writable_roots: list[str],
    protected_file: Path,
    denied_write_path: Path,
    allowed_write_path: Path,
    backend: Any = None,
) -> EnforcementProbe:
    backend = backend or detect_backend()
    ok, reason = backend.available()
    if not ok:
        return EnforcementProbe(
            False, False, False, False, backend.name,
            (f"backend_unavailable:{reason}",),
        )
    spec = SandboxSpec(
        readable_roots=tuple(readable_roots) + tuple(_python_roots()),
        writable_roots=tuple(writable_roots),
    )
    cwd = Path(readable_roots[0]).resolve() if readable_roots else None
    details: list[str] = []
    allowed_file = None
    for root in readable_roots:
        candidates = [
            path for path in sorted(Path(root).rglob("*")) if path.is_file()
        ]
        if candidates:
            allowed_file = candidates[0]
            break
    if allowed_file is None:
        return EnforcementProbe(
            False, False, False, False, backend.name,
            ("no_readable_control_file",),
        )

    def run_python(script: str, argument: str | None) -> subprocess.CompletedProcess:
        command = [sys.executable, "-I", "-c", script]
        if argument is not None:
            command.append(argument)
        return backend.run(spec, command, cwd=cwd)

    try:
        control_read = run_python(_READ_PROBE, str(allowed_file.resolve()))
        if control_read.returncode != 0:
            details.append(
                f"control_read_failed:{control_read.stderr.strip()[-160:]}"
            )
            return EnforcementProbe(
                False, False, False, False, backend.name, tuple(details)
            )
        control_write = run_python(
            _WRITE_PROBE, str(Path(allowed_write_path).resolve())
        )
        if control_write.returncode != 0:
            details.append(
                f"control_write_failed:{control_write.stderr.strip()[-160:]}"
            )
            return EnforcementProbe(
                False, False, False, False, backend.name, tuple(details)
            )

        denied_read = run_python(_READ_PROBE, str(Path(protected_file).resolve()))
        read_denied = denied_read.returncode != 0
        if not read_denied:
            details.append("protected_read_succeeded")

        denied_write = run_python(
            _WRITE_PROBE, str(Path(denied_write_path).resolve())
        )
        write_denied = (
            denied_write.returncode != 0
            and not Path(denied_write_path).exists()
        )
        if not write_denied:
            details.append("denied_write_succeeded")

        network = run_python(_NETWORK_PROBE, None)
        marker = network.stdout.strip()
        network_denied = (
            network.returncode == 0 and marker in _DENIED_CONNECT_ERRNOS
        )
        if not network_denied:
            details.append(
                f"network_probe_result:{marker or network.stderr.strip()[-160:]}"
            )
    except (OSError, subprocess.TimeoutExpired) as error:
        return EnforcementProbe(
            False, False, False, False, backend.name, (f"probe_error:{error}",)
        )
    return EnforcementProbe(
        True, read_denied, write_denied, network_denied, backend.name,
        tuple(details),
    )


class SandboxProbeWriteBoundary:
    """Write boundary proven by an OS sandbox probe over the model worktree.

    Authoritative only when the probe shows a write into the worktree is
    actually denied while control operations succeed. The runner must launch
    the model process under the same backend spec; this report proves the
    mechanism, the run manifest records the launch."""

    def __init__(
        self,
        readable_roots: list[str],
        scratch_dir: Path,
        backend: Any = None,
    ) -> None:
        self.readable_roots = readable_roots
        self.scratch_dir = Path(scratch_dir)
        self.backend = backend

    def verify(self, worktree: Path) -> BoundaryReport:
        worktree = Path(worktree)
        protected = self.scratch_dir / "protected-canary.txt"
        self.scratch_dir.mkdir(parents=True, exist_ok=True)
        protected.write_text("protected", encoding="utf-8")
        allowed_write_dir = self.scratch_dir / "allowed-write"
        allowed_write_dir.mkdir(exist_ok=True)
        probe = probe_enforcement(
            readable_roots=[str(worktree)] + self.readable_roots,
            writable_roots=[str(allowed_write_dir)],
            protected_file=protected,
            denied_write_path=worktree / ".sandbox-write-probe",
            allowed_write_path=allowed_write_dir / "probe.txt",
            backend=self.backend,
        )
        if probe.available and probe.write_denied:
            return BoundaryReport(
                True,
                "sandbox_profile_probe",
                (f"backend:{probe.backend}", "profile_must_wrap_model_process"),
            )
        return BoundaryReport(
            False,
            "sandbox_profile_probe",
            tuple(probe.details) or ("write_probe_not_denied",),
        )


class ReplayCorpus:
    """Content-addressed store of pre-captured external responses.

    Default-deny: a missing key is an IsolationError, never a live fetch."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        (self.root / "blobs").mkdir(parents=True, exist_ok=True)
        self._index_path = self.root / "index.json"
        if not self._index_path.exists():
            self._write_index({})

    def _index(self) -> dict[str, dict[str, Any]]:
        return json.loads(self._index_path.read_text(encoding="utf-8"))

    def _write_index(self, index: dict[str, dict[str, Any]]) -> None:
        self._index_path.write_text(
            json.dumps(index, indent=2, sort_keys=True), encoding="utf-8"
        )

    @staticmethod
    def _key_id(key: str) -> str:
        return xc.sha256_bytes(key.encode("utf-8"))

    def store(self, key: str, response: bytes) -> str:
        key_id = self._key_id(key)
        response_sha = xc.sha256_bytes(response)
        index = self._index()
        existing = index.get(key_id)
        if existing and existing["response_sha256"] != response_sha:
            raise IsolationError(
                f"replay corpus conflict for key {key_id}"
            )
        (self.root / "blobs" / key_id).write_bytes(response)
        index[key_id] = {
            "response_sha256": response_sha,
            "byte_length": len(response),
        }
        self._write_index(index)
        return key_id

    def fetch(self, key: str) -> bytes:
        key_id = self._key_id(key)
        index = self._index()
        if key_id not in index:
            raise IsolationError(f"replay_miss_default_deny:{key_id}")
        data = (self.root / "blobs" / key_id).read_bytes()
        if xc.sha256_bytes(data) != index[key_id]["response_sha256"]:
            raise IsolationError(f"replay_blob_tampered:{key_id}")
        return data

    def corpus_hash(self) -> str:
        return xc.domain_digest(REPLAY_CORPUS_SCHEMA, {"entries": self._index()})


def hermetic_materialize(
    tree_source: Path,
    destination: Path,
    *,
    expected_identity: str | None = None,
    gitlink_hashes: dict[str, str] | None = None,
) -> str:
    destination = Path(destination)
    if destination.exists():
        raise IsolationError(
            f"hermetic destination already exists: {destination}"
        )
    baseline._copy_tree_normalized(Path(tree_source), destination)
    identity = baseline.content_identity(
        destination, gitlink_hashes=gitlink_hashes
    )
    if expected_identity is not None and identity != expected_identity:
        shutil.rmtree(destination)
        raise IsolationError(
            "hermetic tree identity mismatch: "
            f"expected {expected_identity}, got {identity}"
        )
    return identity


def run_hermetic_oracle(
    command: list[str],
    tree: Path,
    *,
    env_allowlist: list[str],
    base_env: dict[str, str],
    timeout: int = 600,
) -> dict[str, Any]:
    env, allowlist_hash = scrub_environment(base_env, env_allowlist)
    completed = subprocess.run(
        command,
        cwd=Path(tree),
        env=env,
        capture_output=True,
        timeout=timeout,
    )
    return {
        "returncode": completed.returncode,
        "stdout_sha256": xc.sha256_bytes(completed.stdout),
        "stderr_sha256": xc.sha256_bytes(completed.stderr),
        "environment_allowlist_hash": allowlist_hash,
    }
