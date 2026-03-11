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
        self.assertEqual(labels["dora-full-application"], "Critical Deadline")
        self.assertEqual(labels["nis2-transposition"], "Upcoming Change")

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

    def test_fintech_scan_detects_sox_dora_and_financial_signals(self) -> None:
        result = run_json_script("repo_signal_scan.py", "--path", str(FIXTURES_ROOT / "fintech"), "--scope", "full")
        frameworks = {item["framework"]: item["score"] for item in result["candidate_frameworks"]}
        signal_ids = [signal["id"] for signal in result["signals"]]

        # Financial reporting and ICT risk signals should be detected
        self.assertIn("financial-reporting", signal_ids)
        self.assertIn("ict-risk-management", signal_ids)
        self.assertIn("incident-response", signal_ids)
        self.assertIn("encryption-key-management", signal_ids)

        # SOX and DORA frameworks should be present with meaningful scores
        self.assertIn("sox", frameworks)
        self.assertIn("dora", frameworks)
        self.assertGreaterEqual(frameworks["sox"], 40)
        self.assertGreaterEqual(frameworks["dora"], 50)

        # ICT resilience control should be satisfied
        controls = {item["control"]: item["status"] for item in result["control_observations"]}
        self.assertEqual(controls["ict-resilience"], "observed")
        self.assertEqual(controls["disclosure-readiness"], "observed")

    def test_iot_scan_detects_nis2_and_network_signals(self) -> None:
        result = run_json_script("repo_signal_scan.py", "--path", str(FIXTURES_ROOT / "iot"), "--scope", "full")
        frameworks = {item["framework"]: item["score"] for item in result["candidate_frameworks"]}
        signal_ids = [signal["id"] for signal in result["signals"]]

        # Network-critical-infra and encryption signals should be detected
        self.assertIn("network-critical-infra", signal_ids)
        self.assertIn("encryption-key-management", signal_ids)

        # NIS2 should be the top-scoring framework
        self.assertIn("nis2", frameworks)
        self.assertGreaterEqual(frameworks["nis2"], 50)

        # Medical-device-claims should NOT fire on generic IoT device telemetry
        self.assertNotIn("medical-device-claims", signal_ids)

    def test_evidence_class_tracking_in_scan_output(self) -> None:
        result = run_json_script("repo_signal_scan.py", "--path", str(FIXTURES_ROOT / "ai-saas"), "--scope", "full")
        for signal in result["signals"]:
            for evidence in signal["evidence"]:
                self.assertIn("evidence_class", evidence)
                self.assertIn(evidence["evidence_class"], {"source", "config", "infra", "docs", "comment"})

    def test_new_frameworks_appear_in_applicability_scoring(self) -> None:
        scan_result = run_json_script("repo_signal_scan.py", "--path", str(FIXTURES_ROOT / "fintech"), "--scope", "full")
        with tempfile.TemporaryDirectory() as tmpdir:
            scan_path = Path(tmpdir) / "scan.json"
            scan_path.write_text(json.dumps(scan_result), encoding="utf-8")
            result = run_json_script("applicability_score.py", "--signals", str(scan_path))
        frameworks = {item["framework"]: item for item in result["applicability"]}
        self.assertIn("dora", frameworks)
        self.assertIn("assumptions", frameworks["dora"])

    def test_focus_flag_filters_to_single_new_framework(self) -> None:
        result = run_json_script("repo_signal_scan.py", "--path", str(FIXTURES_ROOT / "fintech"), "--scope", "full", "--focus", "dora")
        for signal in result["signals"]:
            self.assertIn("dora", signal["frameworks"])
        for candidate in result["candidate_frameworks"]:
            self.assertEqual(candidate["framework"], "dora")


class ASTScannerTests(unittest.TestCase):
    """v0.3: Structured code analysis via Python AST scanner."""

    maxDiff = None

    def test_ast_scanner_detects_pii_in_return_value(self) -> None:
        result = run_json_script("ast_signal_scan.py", "--path", str(FIXTURES_ROOT / "ai-saas"))
        finding_ids = [f["id"] for f in result["structural_findings"]]
        self.assertIn("pii-in-return-value", finding_ids)

    def test_ast_scanner_detects_unlogged_db_write(self) -> None:
        result = run_json_script("ast_signal_scan.py", "--path", str(FIXTURES_ROOT / "ai-saas"))
        finding_ids = [f["id"] for f in result["structural_findings"]]
        self.assertIn("unlogged-db-write", finding_ids)

    def test_ast_scanner_detects_unencrypted_storage_write(self) -> None:
        result = run_json_script("ast_signal_scan.py", "--path", str(FIXTURES_ROOT / "ai-saas"))
        finding_ids = [f["id"] for f in result["structural_findings"]]
        self.assertIn("unencrypted-storage-write", finding_ids)

    def test_ast_findings_have_required_fields(self) -> None:
        result = run_json_script("ast_signal_scan.py", "--path", str(FIXTURES_ROOT / "ai-saas"))
        self.assertIn("scan", result)
        self.assertIn("structural_findings", result)
        self.assertIn("python_files", result["scan"])
        self.assertEqual(result["scan"]["ast_method"], "python-ast")
        for finding in result["structural_findings"]:
            self.assertIn("id", finding)
            self.assertIn("severity", finding)
            self.assertIn("title", finding)
            self.assertIn("frameworks", finding)
            self.assertIn("evidence", finding)
            for ev in finding["evidence"]:
                self.assertIn("path", ev)
                self.assertIn("line", ev)
                self.assertIn("function", ev)
                self.assertIn("detail", ev)
                self.assertEqual(ev["finding_class"], "ast")

    def test_ast_scanner_pii_finding_cites_correct_function(self) -> None:
        result = run_json_script("ast_signal_scan.py", "--path", str(FIXTURES_ROOT / "ai-saas"))
        pii_findings = [f for f in result["structural_findings"] if f["id"] == "pii-in-return-value"]
        self.assertTrue(pii_findings, "Expected at least one pii-in-return-value finding")
        functions = {ev["function"] for f in pii_findings for ev in f["evidence"]}
        self.assertIn("get_user_profile", functions)

    def test_ast_scanner_db_write_finding_cites_correct_function(self) -> None:
        result = run_json_script("ast_signal_scan.py", "--path", str(FIXTURES_ROOT / "ai-saas"))
        db_findings = [f for f in result["structural_findings"] if f["id"] == "unlogged-db-write"]
        self.assertTrue(db_findings, "Expected at least one unlogged-db-write finding")
        functions = {ev["function"] for f in db_findings for ev in f["evidence"]}
        self.assertIn("delete_user_account", functions)

    def test_python_docstring_matches_excluded_from_regex_scan(self) -> None:
        """Keyword matches inside Python docstrings should not inflate signal counts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "doc_only.py"
            test_file.write_text(
                '"""Module that describes email, phone, and address handling."""\n\n\n'
                "def foo():\n"
                '    """Processes user email address for notification."""\n'
                "    return 42\n",
                encoding="utf-8",
            )
            result = run_json_script("repo_signal_scan.py", "--path", tmpdir, "--scope", "full")
            signal_ids = [s["id"] for s in result["signals"]]
            self.assertNotIn(
                "personal-data-processing",
                signal_ids,
                "personal-data-processing signal should not fire when matches are only in docstrings",
            )

    def test_ast_scanner_low_risk_fixture_has_no_findings(self) -> None:
        result = run_json_script("ast_signal_scan.py", "--path", str(FIXTURES_ROOT / "low-risk"))
        self.assertEqual(result["structural_findings"], [])

    def test_ast_scanner_markdown_output(self) -> None:
        result = run_command(
            [
                sys.executable,
                str(SCRIPTS_ROOT / "ast_signal_scan.py"),
                "--path",
                str(FIXTURES_ROOT / "ai-saas"),
                "--format",
                "markdown",
            ]
        )
        self.assertIn("AST Structural Scan", result.stdout)
        self.assertIn("finding(s)", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
