import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from tests.base_test import BaseRegintelTest


class TestComplianceGate(BaseRegintelTest):
    def test_compliance_gate_passes_with_balanced_policy(self) -> None:
        scan = self.run_json_script("repo_signal_scan.py", "--path", str(self.fixtures_root / "fintech"), "--scope", "full")
        ast_data = self.run_json_script("ast_signal_scan.py", "--path", str(self.fixtures_root / "fintech"), "--format", "json")
        policy = self.repo_root / "examples" / "compliance-gate-policy.json"

        with tempfile.TemporaryDirectory() as tmpdir:
            scan_path = Path(tmpdir) / "scan.json"
            ast_path = Path(tmpdir) / "ast.json"
            scan_path.write_text(json.dumps(scan), encoding="utf-8")
            ast_path.write_text(json.dumps(ast_data), encoding="utf-8")

            result = self.run_json_script(
                "compliance_gate.py",
                "--policy",
                str(policy),
                "--scan",
                str(scan_path),
                "--ast",
                str(ast_path),
                "--format",
                "json",
            )

        self.assertTrue(result["passed"])
        self.assertEqual(result["failed_checks"], 0)

    def test_compliance_gate_fails_when_thresholds_are_exceeded(self) -> None:
        scan = self.run_json_script("repo_signal_scan.py", "--path", str(self.fixtures_root / "ai-saas"), "--scope", "full")
        ast_data = self.run_json_script("ast_signal_scan.py", "--path", str(self.fixtures_root / "ai-saas"), "--format", "json")
        deadlines = self.run_json_script(
            "check_deadlines.py",
            "--input",
            str(self.repo_root / "examples" / "developments.json"),
            "--as-of",
            "2026-03-10",
            "--format",
            "json",
        )

        strict_policy = {
            "name": "strict-policy",
            "max_not_observed_controls": 1,
            "max_high_or_critical_deadlines": 1,
            "max_structural_findings": 2,
            "minimum_framework_scores": {"gdpr": 90, "sox": 20},
            "required_signals_all": ["consent-management"],
            "forbidden_signals": ["analytics-and-tracking"],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            scan_path = Path(tmpdir) / "scan.json"
            ast_path = Path(tmpdir) / "ast.json"
            deadlines_path = Path(tmpdir) / "deadlines.json"
            policy_path = Path(tmpdir) / "policy.json"
            scan_path.write_text(json.dumps(scan), encoding="utf-8")
            ast_path.write_text(json.dumps(ast_data), encoding="utf-8")
            deadlines_path.write_text(json.dumps(deadlines), encoding="utf-8")
            policy_path.write_text(json.dumps(strict_policy), encoding="utf-8")

            result_proc = subprocess.run(
                [
                    sys.executable,
                    str(self.scripts_root / "compliance_gate.py"),
                    "--policy",
                    str(policy_path),
                    "--scan",
                    str(scan_path),
                    "--deadlines",
                    str(deadlines_path),
                    "--ast",
                    str(ast_path),
                    "--format",
                    "json",
                ],
                cwd=str(self.repo_root),
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                check=False,
                capture_output=True,
                text=True,
            )
            result = json.loads(result_proc.stdout)
            self.assertEqual(result_proc.returncode, 1)

        self.assertFalse(result["passed"])
        self.assertGreater(result["failed_checks"], 0)
        failed_checks = {item["check"] for item in result["checks"] if item["status"] == "fail"}
        self.assertIn("max_not_observed_controls", failed_checks)
        self.assertIn("max_high_or_critical_deadlines", failed_checks)
        self.assertIn("max_structural_findings", failed_checks)

    def test_compliance_gate_detects_framework_drop_from_trend(self) -> None:
        scan = self.run_json_script("repo_signal_scan.py", "--path", str(self.fixtures_root / "fintech"), "--scope", "full")
        trend = {
            "snapshot_count": 2,
            "window": 2,
            "framework_trends": [
                {"framework": "gdpr", "first_score": 80, "latest_score": 60, "delta": -20, "direction": "down"}
            ],
            "history": [],
            "latest_snapshot": None,
        }
        policy = {"name": "trend-drop-policy", "max_framework_score_drop": {"gdpr": 10}}

        with tempfile.TemporaryDirectory() as tmpdir:
            scan_path = Path(tmpdir) / "scan.json"
            trend_path = Path(tmpdir) / "trend.json"
            policy_path = Path(tmpdir) / "policy.json"
            scan_path.write_text(json.dumps(scan), encoding="utf-8")
            trend_path.write_text(json.dumps(trend), encoding="utf-8")
            policy_path.write_text(json.dumps(policy), encoding="utf-8")

            result_proc = subprocess.run(
                [
                    sys.executable,
                    str(self.scripts_root / "compliance_gate.py"),
                    "--policy",
                    str(policy_path),
                    "--scan",
                    str(scan_path),
                    "--trend",
                    str(trend_path),
                    "--format",
                    "json",
                ],
                cwd=str(self.repo_root),
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                check=False,
                capture_output=True,
                text=True,
            )
            result = json.loads(result_proc.stdout)
            self.assertEqual(result_proc.returncode, 1)

        self.assertFalse(result["passed"])
        failed_checks = [item for item in result["checks"] if item["status"] == "fail"]
        self.assertTrue(any(item["check"] == "max_framework_score_drop" for item in failed_checks))
