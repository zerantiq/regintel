from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES_ROOT = REPO_ROOT / "tests" / "fixtures" / "repos"
SCRIPTS_ROOT = REPO_ROOT / "scripts"
TOOLS_ROOT = REPO_ROOT / "tools"


def run_command(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        args,
        cwd=str(cwd or REPO_ROOT),
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


def run_json_script(script_name: str, *args: str, cwd: Path | None = None) -> dict:
    result = run_command([sys.executable, str(SCRIPTS_ROOT / script_name), *args], cwd=cwd)
    return json.loads(result.stdout)


class RegintelRegressionTests(unittest.TestCase):
    maxDiff = None

    def test_validate_repo_passes_without_creating_script_pycache(self) -> None:
        run_command([sys.executable, str(TOOLS_ROOT / "validate_repo.py")])
        self.assertFalse((REPO_ROOT / "scripts" / "__pycache__").exists())
        self.assertFalse((REPO_ROOT / "tools" / "__pycache__").exists())

    def test_ai_saas_scan_detects_expected_frameworks_and_missing_controls(self) -> None:
        result = run_json_script("repo_signal_scan.py", "--path", str(FIXTURES_ROOT / "ai-saas"), "--scope", "full")
        frameworks = {item["framework"]: item["score"] for item in result["candidate_frameworks"]}
        self.assertIn("gdpr", frameworks)
        self.assertIn("us-state-privacy", frameworks)
        self.assertIn("eu-ai-act", frameworks)
        self.assertGreater(frameworks["gdpr"], frameworks["eu-ai-act"])

        controls = {item["control"]: item["status"] for item in result["control_observations"]}
        self.assertEqual(controls["privacy-user-controls"], "not-observed")
        self.assertEqual(controls["ai-governance-controls"], "not-observed")

    def test_ai_saas_diff_scan_limits_scope_to_changed_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir) / "repo"
            shutil.copytree(FIXTURES_ROOT / "ai-saas", repo_dir)
            run_command(["git", "init", "-q"], cwd=repo_dir)
            run_command(["git", "config", "user.email", "test@example.com"], cwd=repo_dir)
            run_command(["git", "config", "user.name", "Test"], cwd=repo_dir)
            run_command(["git", "add", "."], cwd=repo_dir)
            run_command(["git", "commit", "-q", "-m", "initial"], cwd=repo_dir)
            client_path = repo_dir / "services" / "llm" / "client.py"
            client_path.write_text(
                client_path.read_text(encoding="utf-8") + "\n# TODO: add moderation later\n",
                encoding="utf-8",
            )

            result = run_json_script("repo_signal_scan.py", "--path", str(repo_dir), "--scope", "diff")
            self.assertEqual(result["scan"]["scanned_files"], 1)
            for signal in result["signals"]:
                for evidence in signal["evidence"]:
                    self.assertEqual(evidence["path"], "services/llm/client.py")

    def test_healthcare_scan_requires_strong_health_signals(self) -> None:
        result = run_json_script("repo_signal_scan.py", "--path", str(FIXTURES_ROOT / "healthcare"), "--scope", "full")
        frameworks = {item["framework"]: item["score"] for item in result["candidate_frameworks"]}
        self.assertGreaterEqual(frameworks["hipaa"], 50)
        self.assertIn("fda-software", frameworks)
        controls = {item["control"]: item["status"] for item in result["control_observations"]}
        self.assertEqual(controls["healthcare-safeguards"], "not-observed")

    def test_low_risk_scan_ignores_lockfile_noise(self) -> None:
        result = run_json_script("repo_signal_scan.py", "--path", str(FIXTURES_ROOT / "low-risk"), "--scope", "full")
        self.assertEqual(result["signals"], [])
        self.assertEqual(result["candidate_frameworks"], [])

    def test_applicability_scoring_with_example_company_context(self) -> None:
        scan_result = run_json_script("repo_signal_scan.py", "--path", str(FIXTURES_ROOT / "ai-saas"), "--scope", "full")
        with tempfile.TemporaryDirectory() as tmpdir:
            scan_path = Path(tmpdir) / "scan.json"
            scan_path.write_text(json.dumps(scan_result), encoding="utf-8")
            result = run_json_script(
                "applicability_score.py",
                "--signals",
                str(scan_path),
                "--company",
                str(REPO_ROOT / "examples" / "company-context.json"),
            )
        frameworks = {item["framework"]: item["score"] for item in result["applicability"]}
        self.assertIn("eu-ai-act", frameworks)
        self.assertEqual(frameworks["gdpr"], 100)
        self.assertEqual(frameworks["us-state-privacy"], 100)

    def test_example_deadlines_have_expected_warning_labels(self) -> None:
        result = run_json_script(
            "check_deadlines.py",
            "--input",
            str(REPO_ROOT / "examples" / "developments.json"),
            "--as-of",
            "2026-03-10",
            "--format",
            "json",
        )
        labels = {item["id"]: item["warning_label"] for item in result["developments"]}
        self.assertEqual(labels["eu-ai-act-gpai"], "Upcoming Change")
        self.assertEqual(labels["gdpr-retention-review"], "Action Needed Soon")

    def test_example_change_diff_reports_added_and_changed_items(self) -> None:
        result = run_json_script(
            "change_diff.py",
            "--old",
            str(REPO_ROOT / "examples" / "old-scan.json"),
            "--new",
            str(REPO_ROOT / "examples" / "new-scan.json"),
            "--format",
            "json",
        )
        self.assertTrue(result["collections"]["signals"]["added"])
        self.assertTrue(result["collections"]["candidate_frameworks"]["changed"])
        self.assertTrue(result["collections"]["applicability"]["changed"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
