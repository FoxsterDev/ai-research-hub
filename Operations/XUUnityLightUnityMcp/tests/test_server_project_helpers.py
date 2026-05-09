import json
import sys
import tempfile
import unittest
from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"
if str(TEMPLATES_DIR) not in sys.path:
    sys.path.insert(0, str(TEMPLATES_DIR))

import server
from server_core import ToolInvocationError


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def make_unity_project(root: Path) -> Path:
    (root / "Assets").mkdir(parents=True, exist_ok=True)
    project_settings = root / "ProjectSettings"
    project_settings.mkdir(parents=True, exist_ok=True)
    (project_settings / "ProjectVersion.txt").write_text(
        "m_EditorVersion: 6000.0.58f2\n", encoding="utf-8"
    )
    return root


class ServerProjectHelperTests(unittest.TestCase):
    def test_ensure_project_root_accepts_valid_unity_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = make_unity_project(Path(tmp_dir) / "MyProject")
            resolved = server.ensure_project_root(str(project_root))
            self.assertEqual(project_root.resolve(), resolved)

    def test_ensure_project_root_rejects_invalid_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            invalid_root = Path(tmp_dir) / "NotAProject"
            invalid_root.mkdir(parents=True, exist_ok=True)

            with self.assertRaises(ToolInvocationError) as ctx:
                server.ensure_project_root(str(invalid_root))

            self.assertEqual("project_not_found", ctx.exception.code)

    def test_find_latest_request_event_is_sorted_and_project_local(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            project_a = base / "ProjectA"
            project_b = base / "ProjectB"
            journal_a = project_a / "Library" / "XUUnityLightMcp" / "journal" / "requests"
            journal_b = project_b / "Library" / "XUUnityLightMcp" / "journal" / "requests"

            write_json(
                journal_a / "01.json",
                {
                    "event_id": "01",
                    "event_type": "request_started",
                    "event_at_utc": "2026-05-09T15:00:00Z",
                    "request_id": "a-1",
                    "operation": "unity.status",
                },
            )
            write_json(journal_a / "invalid.json", {"request_id": ""})
            (journal_a / "broken.json").write_text("{not-json", encoding="utf-8")
            write_json(
                journal_a / "02.json",
                {
                    "event_id": "02",
                    "event_type": "request_started",
                    "event_at_utc": "2026-05-09T16:00:00Z",
                    "request_id": "a-2",
                    "operation": "unity.status",
                },
            )
            write_json(
                journal_b / "01.json",
                {
                    "event_id": "01",
                    "event_type": "request_started",
                    "event_at_utc": "2026-05-09T17:00:00Z",
                    "request_id": "b-1",
                    "operation": "unity.status",
                },
            )

            latest_a = server.find_latest_request_event(project_a, ["unity.status"])
            latest_b = server.find_latest_request_event(project_b, ["unity.status"])

            self.assertIsNotNone(latest_a)
            self.assertEqual("a-2", latest_a["request_id"])
            self.assertEqual("02", latest_a["event_id"])
            self.assertIsNotNone(latest_b)
            self.assertEqual("b-1", latest_b["request_id"])

    def test_inspect_package_dependency_alignment_for_repo_local_file_dependency(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            package_dir = (
                repo_root
                / "AIRoot"
                / "Operations"
                / "XUUnityLightUnityMcp"
                / "templates"
                / "unity-package"
            )
            package_dir.mkdir(parents=True, exist_ok=True)
            (package_dir / "package.json").write_text('{"name":"com.xuunity.light-mcp"}\n', encoding="utf-8")

            project_root = make_unity_project(repo_root / "MyProject")
            manifest_path = project_root / "Packages" / "manifest.json"
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            manifest_path.write_text(
                json.dumps(
                    {
                        "dependencies": {
                            "com.xuunity.light-mcp": "file:../../AIRoot/Operations/XUUnityLightUnityMcp/templates/unity-package"
                        }
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            result = server.inspect_package_dependency_alignment(project_root)

            self.assertEqual("file", result["dependency_mode"])
            self.assertEqual("aligned", result["alignment"])
            self.assertTrue(result["repo_local_package_source_present"])
            self.assertEqual(str(package_dir.resolve()), result["resolved_dependency_path"])

    def test_inspect_package_dependency_alignment_for_missing_dependency(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = make_unity_project(Path(tmp_dir) / "MyProject")
            manifest_path = project_root / "Packages" / "manifest.json"
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            manifest_path.write_text(json.dumps({"dependencies": {}}, indent=2) + "\n", encoding="utf-8")

            result = server.inspect_package_dependency_alignment(project_root)

            self.assertEqual("dependency_missing", result["alignment"])
            self.assertIn("not declared", result["warning"])


if __name__ == "__main__":
    unittest.main()
