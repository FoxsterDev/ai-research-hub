import json
import os
import subprocess
import textwrap
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


OPS_ROOT = Path(__file__).resolve().parents[1]
RUNNER = OPS_ROOT / "run_multi_project_batch_compile_matrix.sh"


class MultiProjectBatchRunnerTests(unittest.TestCase):
    def test_jsonl_progress_plus_final_json_stdout_counts_as_success(self) -> None:
        with TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            project_root = temp_root / "Sudoku"
            (project_root / "Packages").mkdir(parents=True)
            (project_root / "ProjectSettings").mkdir()
            (project_root / "Packages" / "manifest.json").write_text(
                json.dumps({"dependencies": {"com.xuunity.light-mcp": "file:package"}}),
                encoding="utf-8",
            )
            (project_root / "ProjectSettings" / "ProjectVersion.txt").write_text(
                "m_EditorVersion: 6000.0.58f2\n",
                encoding="utf-8",
            )

            wrapper_path = temp_root / "fake_xuunity_light_unity_mcp.sh"
            wrapper_path.write_text(
                textwrap.dedent(
                    """\
                    #!/usr/bin/env bash
                    set -euo pipefail
                    command_name="${1:-}"
                    case "$command_name" in
                      batch-build-config-compile-matrix)
                        printf '{"event":"batch_progress","phase":"preflight"}\\n'
                        cat <<'JSON'
                    {
                      "action": "batch_build_config_compile_matrix",
                      "succeeded": true,
                      "result_summary": {
                        "matrix": {
                          "status": "passed",
                          "total": 4,
                          "passed": 4,
                          "failed": 0,
                          "skipped": 0
                        }
                      },
                      "summary_file": "/tmp/summary.json",
                      "result_file": "/tmp/result.json",
                      "log_path": "/tmp/editor.log"
                    }
                    JSON
                        ;;
                      recover-editor-session)
                        printf '{"recovery_classification":"not_needed"}\\n'
                        ;;
                      *)
                        echo "unexpected command: $command_name" >&2
                        exit 2
                        ;;
                    esac
                    """
                ),
                encoding="utf-8",
            )
            wrapper_path.chmod(0o755)

            results_dir = temp_root / "results"
            env = os.environ.copy()
            env["XUUNITY_LIGHT_UNITY_MCP_WRAPPER"] = str(wrapper_path)
            completed = subprocess.run(
                [
                    "bash",
                    str(RUNNER),
                    "--repo-root",
                    str(temp_root),
                    "--project-root",
                    str(project_root),
                    "--parallelism",
                    "1",
                    "--no-close-live-editors",
                    "--results-dir",
                    str(results_dir),
                ],
                cwd=OPS_ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(0, completed.returncode, completed.stderr + completed.stdout)
            status = json.loads((results_dir / "Sudoku_status.json").read_text(encoding="utf-8"))
            self.assertTrue(status["json_parse_ok"])
            self.assertTrue(status["succeeded"])
            self.assertEqual("passed", status["matrix_status"])
            self.assertEqual(4, status["total"])
            self.assertEqual(4, status["passed"])
            self.assertEqual(0, status["failed"])
            self.assertIn('"projects_failed": 0', completed.stdout)


if __name__ == "__main__":
    unittest.main()
