from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

OPERATION_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(OPERATION_DIR))

from model_fitness import baseline, isolation  # noqa: E402

import xuunity_canonical as xc  # noqa: E402


class EnvironmentTests(unittest.TestCase):
    def test_scrub_drops_everything_outside_allowlist(self) -> None:
        base = {"PATH": "/usr/bin", "HOME": "/Users/nobody", "SECRET": "x"}
        env, digest = isolation.scrub_environment(base, ["PATH", "LANG"])
        self.assertEqual({"PATH": "/usr/bin"}, env)
        _, reordered = isolation.scrub_environment(base, ["LANG", "PATH"])
        self.assertEqual(digest, reordered)
        _, changed = isolation.scrub_environment(
            {"PATH": "/other"}, ["PATH", "LANG"]
        )
        self.assertNotEqual(digest, changed)


class PolicyTests(unittest.TestCase):
    def test_network_policy_hash_tracks_transport(self) -> None:
        parent, parent_hash = isolation.network_policy(
            provider_transport="parent_owned"
        )
        self.assertEqual("default_deny", parent["mode"])
        _, shared_hash = isolation.network_policy(
            provider_transport="shared_with_model"
        )
        self.assertNotEqual(parent_hash, shared_hash)
        with self.assertRaises(isolation.IsolationError):
            isolation.network_policy(provider_transport="open")

    def test_read_namespace_policy_is_deterministic(self) -> None:
        _, first = isolation.read_namespace_policy(
            readable_roots=["b", "a"],
            writable_roots=["w"],
            protected_classes=["fixture_answers", "sibling_runs"],
        )
        _, second = isolation.read_namespace_policy(
            readable_roots=["a", "b"],
            writable_roots=["w"],
            protected_classes=["sibling_runs", "fixture_answers"],
        )
        self.assertEqual(first, second)

    def test_profile_denies_by_default(self) -> None:
        profile = isolation.render_sandbox_profile(
            readable_roots=["/tmp/allowed"], writable_roots=[]
        )
        self.assertIn("(deny default)", profile)
        self.assertNotIn("(allow network*)", profile)


class BackendContractTests(unittest.TestCase):
    def test_bubblewrap_argv_isolates_mounts_and_network(self) -> None:
        backend = isolation.BubblewrapBackend(bwrap_path="/usr/bin/bwrap")
        with tempfile.TemporaryDirectory() as temporary:
            readable = Path(temporary) / "readable"
            writable = Path(temporary) / "writable"
            readable.mkdir()
            writable.mkdir()
            spec = isolation.SandboxSpec(
                readable_roots=(str(readable),),
                writable_roots=(str(writable),),
            )
            argv = backend.command_prefix(spec, cwd=readable)
        self.assertEqual("/usr/bin/bwrap", argv[0])
        self.assertIn("--unshare-net", argv)
        self.assertIn("--ro-bind", argv)
        readable_resolved = str(readable.resolve())
        writable_resolved = str(writable.resolve())
        pairs = list(zip(argv, argv[1:], argv[2:]))
        self.assertIn(
            ("--ro-bind", readable_resolved, readable_resolved), pairs
        )
        self.assertIn(("--bind", writable_resolved, writable_resolved), pairs)
        self.assertEqual(["--chdir", str(readable)], argv[-2:])
        network_spec = spec._replace(allow_network=True)
        self.assertNotIn(
            "--unshare-net", backend.command_prefix(network_spec)
        )

    def test_null_backend_degrades_to_unenforced(self) -> None:
        backend = isolation.NullBackend("no_os_sandbox_backend:test")
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            (work / "readable").mkdir()
            probe = isolation.probe_enforcement(
                readable_roots=[str(work / "readable")],
                writable_roots=[],
                protected_file=work / "protected.txt",
                denied_write_path=work / "denied.txt",
                allowed_write_path=work / "allowed.txt",
                backend=backend,
            )
            self.assertFalse(probe.available)
            self.assertIn(
                "backend_unavailable:no_os_sandbox_backend:test",
                probe.details,
            )
            boundary = isolation.SandboxProbeWriteBoundary(
                [], work / "scratch", backend=backend
            )
            report = boundary.verify(work)
            self.assertFalse(report.authoritative)


class ReplayCorpusTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        self.corpus = isolation.ReplayCorpus(
            Path(self._temporary.name) / "corpus"
        )

    def test_roundtrip_and_default_deny_miss(self) -> None:
        empty_hash = self.corpus.corpus_hash()
        self.corpus.store("GET https://example.invalid/config", b"{\"ok\":1}")
        self.assertEqual(
            b"{\"ok\":1}",
            self.corpus.fetch("GET https://example.invalid/config"),
        )
        self.assertNotEqual(empty_hash, self.corpus.corpus_hash())
        with self.assertRaises(isolation.IsolationError):
            self.corpus.fetch("GET https://example.invalid/other")

    def test_conflicting_capture_is_rejected(self) -> None:
        self.corpus.store("key", b"first")
        with self.assertRaises(isolation.IsolationError):
            self.corpus.store("key", b"second")

    def test_blob_tamper_detected(self) -> None:
        key_id = self.corpus.store("key", b"payload")
        blob = Path(self._temporary.name) / "corpus" / "blobs" / key_id
        blob.write_bytes(b"tampered")
        with self.assertRaises(isolation.IsolationError):
            self.corpus.fetch("key")


class HermeticMaterializationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        self.work = Path(self._temporary.name)
        self.source = self.work / "captured"
        self.source.mkdir()
        (self.source / "Foo.cs").write_text("class Foo { }\n", encoding="utf-8")

    def test_materialize_verifies_identity(self) -> None:
        expected = baseline.content_identity(self.source)
        identity = isolation.hermetic_materialize(
            self.source, self.work / "oracle-tree", expected_identity=expected
        )
        self.assertEqual(expected, identity)
        with self.assertRaises(isolation.IsolationError):
            isolation.hermetic_materialize(
                self.source, self.work / "oracle-tree"
            )
        with self.assertRaises(isolation.IsolationError):
            isolation.hermetic_materialize(
                self.source,
                self.work / "oracle-tree-2",
                expected_identity=xc.sha256_bytes(b"different"),
            )
        self.assertFalse((self.work / "oracle-tree-2").exists())

    def test_oracle_runs_with_scrubbed_environment(self) -> None:
        record = isolation.run_hermetic_oracle(
            [
                sys.executable,
                "-c",
                "import os; print(os.environ.get('LEAKED_SECRET'))",
            ],
            self.source,
            env_allowlist=["PATH"],
            base_env={"PATH": "/usr/bin:/bin", "LEAKED_SECRET": "token"},
        )
        self.assertEqual(0, record["returncode"])
        self.assertEqual(xc.sha256_bytes(b"None\n"), record["stdout_sha256"])


_BACKEND_AVAILABLE, _BACKEND_REASON = isolation.detect_backend().available()


@unittest.skipUnless(
    _BACKEND_AVAILABLE, f"no sandbox backend: {_BACKEND_REASON}"
)
class SandboxEnforcementTests(unittest.TestCase):
    """Real OS-enforcement probes; skipped where no sandbox backend exists
    (that platform honestly reports unenforced), and individually skipped
    when the control cases cannot run — an unprovable policy is reported
    unenforced, never assumed."""

    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory(
            dir="/private/tmp" if sys.platform == "darwin" else None
        )
        self.addCleanup(self._temporary.cleanup)
        self.work = Path(self._temporary.name)
        self.readable = self.work / "readable"
        self.readable.mkdir()
        (self.readable / "allowed.txt").write_text("ok\n", encoding="utf-8")
        self.protected = self.work / "protected" / "answers.json"
        self.protected.parent.mkdir()
        self.protected.write_text("{\"answer\": 42}", encoding="utf-8")
        self.writable = self.work / "writable"
        self.writable.mkdir()

    def test_probe_denies_read_write_and_network(self) -> None:
        probe = isolation.probe_enforcement(
            readable_roots=[str(self.readable)],
            writable_roots=[str(self.writable)],
            protected_file=self.protected,
            denied_write_path=self.protected.parent / "escape.txt",
            allowed_write_path=self.writable / "control.txt",
        )
        if not probe.available:
            self.skipTest(f"probe inconclusive: {probe.details}")
        self.assertTrue(probe.read_denied, probe.details)
        self.assertTrue(probe.write_denied, probe.details)
        self.assertTrue(probe.network_denied, probe.details)

    def test_probe_boundary_is_authoritative_only_when_proven(self) -> None:
        worktree = self.work / "worktree"
        worktree.mkdir()
        (worktree / "Foo.cs").write_text("class Foo { }\n", encoding="utf-8")
        boundary = isolation.SandboxProbeWriteBoundary(
            [str(self.readable)], self.work / "scratch"
        )
        report = boundary.verify(worktree)
        if not report.authoritative:
            self.skipTest(f"probe inconclusive: {report.reasons}")
        self.assertEqual("sandbox_profile_probe", report.mechanism)
        self.assertFalse((worktree / ".sandbox-write-probe").exists())


if __name__ == "__main__":
    unittest.main()
