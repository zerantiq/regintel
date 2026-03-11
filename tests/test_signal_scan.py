import json
import shutil
import tempfile
from pathlib import Path

from tests.base_test import BaseRegintelTest


class TestSignalScan(BaseRegintelTest):
    def test_v09_repo_scan_cache_reuse_and_parallel_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / "cache"
            first = self.run_json_script(
                "repo_signal_scan.py",
                "--path",
                str(self.fixtures_root / "ai-saas"),
                "--scope",
                "full",
                "--cache-dir",
                str(cache_dir),
                "--workers",
                "2",
            )
            second = self.run_json_script(
                "repo_signal_scan.py",
                "--path",
                str(self.fixtures_root / "ai-saas"),
                "--scope",
                "full",
                "--cache-dir",
                str(cache_dir),
                "--workers",
                "2",
            )

        self.assertEqual(first["scan"]["parallel_workers"], 2)
        self.assertTrue(first["scan"]["cache_enabled"])
        self.assertGreater(first["scan"]["cache_misses"], 0)
        self.assertEqual(second["scan"]["parallel_workers"], 2)
        self.assertTrue(second["scan"]["cache_enabled"])
        self.assertGreaterEqual(second["scan"]["cache_hits"], second["scan"]["scanned_files"])
        self.assertEqual(second["scan"]["cache_misses"], 0)
        self.assertEqual(first["signals"], second["signals"])

    def test_ai_saas_scan_detects_expected_frameworks_and_missing_controls(self) -> None:
        result = self.run_json_script("repo_signal_scan.py", "--path", str(self.fixtures_root / "ai-saas"), "--scope", "full")
        self.assertIn("parallel_workers", result["scan"])
        self.assertIn("cache_enabled", result["scan"])
        self.assertIn("cache_hits", result["scan"])
        self.assertIn("cache_misses", result["scan"])
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
            shutil.copytree(self.fixtures_root / "ai-saas", repo_dir)
            self.run_command(["git", "init", "-q"], cwd=repo_dir)
            self.run_command(["git", "config", "user.email", "test@example.com"], cwd=repo_dir)
            self.run_command(["git", "config", "user.name", "Test"], cwd=repo_dir)
            self.run_command(["git", "add", "."], cwd=repo_dir)
            self.run_command(["git", "commit", "-q", "-m", "initial"], cwd=repo_dir)
            client_path = repo_dir / "services" / "llm" / "client.py"
            client_path.write_text(
                client_path.read_text(encoding="utf-8") + "\n# TODO: add moderation later\n",
                encoding="utf-8",
            )

            result = self.run_json_script("repo_signal_scan.py", "--path", str(repo_dir), "--scope", "diff")
            self.assertEqual(result["scan"]["scanned_files"], 1)
            for signal in result["signals"]:
                for evidence in signal["evidence"]:
                    self.assertEqual(evidence["path"], "services/llm/client.py")

    def test_healthcare_scan_requires_strong_health_signals(self) -> None:
        result = self.run_json_script("repo_signal_scan.py", "--path", str(self.fixtures_root / "healthcare"), "--scope", "full")
        frameworks = {item["framework"]: item["score"] for item in result["candidate_frameworks"]}
        self.assertGreaterEqual(frameworks["hipaa"], 50)
        self.assertIn("fda-software", frameworks)
        controls = {item["control"]: item["status"] for item in result["control_observations"]}
        self.assertEqual(controls["healthcare-safeguards"], "not-observed")

    def test_low_risk_scan_ignores_lockfile_noise(self) -> None:
        result = self.run_json_script("repo_signal_scan.py", "--path", str(self.fixtures_root / "low-risk"), "--scope", "full")
        self.assertEqual(result["signals"], [])
        self.assertEqual(result["candidate_frameworks"], [])

    def test_applicability_scoring_with_example_company_context(self) -> None:
        scan_result = self.run_json_script("repo_signal_scan.py", "--path", str(self.fixtures_root / "ai-saas"), "--scope", "full")
        with tempfile.TemporaryDirectory() as tmpdir:
            scan_path = Path(tmpdir) / "scan.json"
            scan_path.write_text(json.dumps(scan_result), encoding="utf-8")
            result = self.run_json_script(
                "applicability_score.py",
                "--signals",
                str(scan_path),
                "--company",
                str(self.repo_root / "examples" / "company-context.json"),
            )
        frameworks = {item["framework"]: item["score"] for item in result["applicability"]}
        self.assertIn("eu-ai-act", frameworks)
        self.assertEqual(frameworks["gdpr"], 100)
        self.assertEqual(frameworks["us-state-privacy"], 100)

    def test_fintech_scan_detects_sox_dora_and_financial_signals(self) -> None:
        result = self.run_json_script("repo_signal_scan.py", "--path", str(self.fixtures_root / "fintech"), "--scope", "full")
        frameworks = {item["framework"]: item["score"] for item in result["candidate_frameworks"]}
        signal_ids = [signal["id"] for signal in result["signals"]]

        self.assertIn("financial-reporting", signal_ids)
        self.assertIn("ict-risk-management", signal_ids)
        self.assertIn("incident-response", signal_ids)
        self.assertIn("encryption-key-management", signal_ids)

        self.assertIn("sox", frameworks)
        self.assertIn("dora", frameworks)
        self.assertGreaterEqual(frameworks["sox"], 40)
        self.assertGreaterEqual(frameworks["dora"], 50)

        controls = {item["control"]: item["status"] for item in result["control_observations"]}
        self.assertEqual(controls["ict-resilience"], "observed")
        self.assertEqual(controls["disclosure-readiness"], "observed")

    def test_iot_scan_detects_nis2_and_network_signals(self) -> None:
        result = self.run_json_script("repo_signal_scan.py", "--path", str(self.fixtures_root / "iot"), "--scope", "full")
        frameworks = {item["framework"]: item["score"] for item in result["candidate_frameworks"]}
        signal_ids = [signal["id"] for signal in result["signals"]]

        self.assertIn("network-critical-infra", signal_ids)
        self.assertIn("encryption-key-management", signal_ids)

        self.assertIn("nis2", frameworks)
        self.assertGreaterEqual(frameworks["nis2"], 50)

        self.assertNotIn("medical-device-claims", signal_ids)

    def test_evidence_class_tracking_in_scan_output(self) -> None:
        result = self.run_json_script("repo_signal_scan.py", "--path", str(self.fixtures_root / "ai-saas"), "--scope", "full")
        for signal in result["signals"]:
            for evidence in signal["evidence"]:
                self.assertIn("evidence_class", evidence)
                self.assertIn(evidence["evidence_class"], {"source", "config", "infra", "docs", "comment"})

    def test_new_frameworks_appear_in_applicability_scoring(self) -> None:
        scan_result = self.run_json_script("repo_signal_scan.py", "--path", str(self.fixtures_root / "fintech"), "--scope", "full")
        with tempfile.TemporaryDirectory() as tmpdir:
            scan_path = Path(tmpdir) / "scan.json"
            scan_path.write_text(json.dumps(scan_result), encoding="utf-8")
            result = self.run_json_script("applicability_score.py", "--signals", str(scan_path))
        frameworks = {item["framework"]: item for item in result["applicability"]}
        self.assertIn("dora", frameworks)
        self.assertIn("assumptions", frameworks["dora"])

    def test_focus_flag_filters_to_single_new_framework(self) -> None:
        result = self.run_json_script("repo_signal_scan.py", "--path", str(self.fixtures_root / "fintech"), "--scope", "full", "--focus", "dora")
        for signal in result["signals"]:
            self.assertIn("dora", signal["frameworks"])
        for candidate in result["candidate_frameworks"]:
            self.assertEqual(candidate["framework"], "dora")

    def test_v04_polyglot_scan_detects_extended_frameworks(self) -> None:
        result = self.run_json_script("repo_signal_scan.py", "--path", str(self.fixtures_root / "polyglot-regulated"), "--scope", "full")
        frameworks = {item["framework"]: item["score"] for item in result["candidate_frameworks"]}
        signal_ids = {signal["id"] for signal in result["signals"]}

        self.assertIn("iso-42001", frameworks)
        self.assertIn("uk-gdpr", frameworks)
        self.assertIn("ccpa-cpra", frameworks)
        self.assertIn("pci-dss", frameworks)
        self.assertGreaterEqual(frameworks["ccpa-cpra"], 40)
        self.assertGreaterEqual(frameworks["pci-dss"], 35)

        self.assertIn("ai-management-system", signal_ids)
        self.assertIn("uk-data-protection-regime", signal_ids)
        self.assertIn("cpra-privacy-rights", signal_ids)
        self.assertIn("payment-card-processing", signal_ids)

    def test_v04_polyglot_scan_detects_language_specific_signals(self) -> None:
        result = self.run_json_script("repo_signal_scan.py", "--path", str(self.fixtures_root / "polyglot-regulated"), "--scope", "full")
        signal_ids = {signal["id"] for signal in result["signals"]}
        self.assertIn("go-backend-service", signal_ids)
        self.assertIn("java-backend-service", signal_ids)
        self.assertIn("csharp-backend-service", signal_ids)
        self.assertIn("rust-backend-service", signal_ids)

    def test_v04_infra_templates_scanned_and_classified_as_infra(self) -> None:
        result = self.run_json_script("repo_signal_scan.py", "--path", str(self.fixtures_root / "polyglot-regulated"), "--scope", "full")
        iac_signal = next(signal for signal in result["signals"] if signal["id"] == "iac-deployment")
        evidence = iac_signal["evidence"]
        paths = {item["path"] for item in evidence}

        self.assertTrue(any(path.endswith(".tf") for path in paths))
        self.assertTrue(any(path.endswith(".bicep") for path in paths))
        self.assertTrue(any(path.endswith("Chart.yaml") or path.endswith("template.yaml") for path in paths))
        self.assertTrue(all(item["evidence_class"] == "infra" for item in evidence))

    def test_v04_applicability_scores_new_frameworks_with_company_context(self) -> None:
        scan_result = self.run_json_script(
            "repo_signal_scan.py",
            "--path",
            str(self.fixtures_root / "polyglot-regulated"),
            "--scope",
            "full",
        )
        company = {
            "jurisdictions": ["UK", "US-CA", "US-VA"],
            "uses_ai": True,
            "processes_card_payments": True,
            "deployment_model": "hosted-saas",
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            scan_path = Path(tmpdir) / "scan.json"
            company_path = Path(tmpdir) / "company.json"
            scan_path.write_text(json.dumps(scan_result), encoding="utf-8")
            company_path.write_text(json.dumps(company), encoding="utf-8")
            result = self.run_json_script("applicability_score.py", "--signals", str(scan_path), "--company", str(company_path))

        frameworks = {item["framework"]: item for item in result["applicability"]}
        self.assertIn("iso-42001", frameworks)
        self.assertIn("uk-gdpr", frameworks)
        self.assertIn("ccpa-cpra", frameworks)
        self.assertIn("pci-dss", frameworks)
        self.assertIn("us-va-cdpa", frameworks)

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
            result = self.run_json_script("repo_signal_scan.py", "--path", tmpdir, "--scope", "full")
            signal_ids = [s["id"] for s in result["signals"]]
            self.assertNotIn(
                "personal-data-processing",
                signal_ids,
                "personal-data-processing signal should not fire when matches are only in docstrings",
            )
