from tests.base_test import BaseRegintelTest


class TestASTScanner(BaseRegintelTest):
    """v0.3: Structured code analysis via Python AST scanner."""

    def test_ast_scanner_detects_pii_in_return_value(self) -> None:
        result = self.run_json_script("ast_signal_scan.py", "--path", str(self.fixtures_root / "ai-saas"))
        finding_ids = [f["id"] for f in result["structural_findings"]]
        self.assertIn("pii-in-return-value", finding_ids)

    def test_ast_scanner_detects_unlogged_db_write(self) -> None:
        result = self.run_json_script("ast_signal_scan.py", "--path", str(self.fixtures_root / "ai-saas"))
        finding_ids = [f["id"] for f in result["structural_findings"]]
        self.assertIn("unlogged-db-write", finding_ids)

    def test_ast_scanner_detects_unencrypted_storage_write(self) -> None:
        result = self.run_json_script("ast_signal_scan.py", "--path", str(self.fixtures_root / "ai-saas"))
        finding_ids = [f["id"] for f in result["structural_findings"]]
        self.assertIn("unencrypted-storage-write", finding_ids)

    def test_ast_findings_have_required_fields(self) -> None:
        result = self.run_json_script("ast_signal_scan.py", "--path", str(self.fixtures_root / "ai-saas"))
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
        result = self.run_json_script("ast_signal_scan.py", "--path", str(self.fixtures_root / "ai-saas"))
        pii_findings = [f for f in result["structural_findings"] if f["id"] == "pii-in-return-value"]
        self.assertTrue(pii_findings, "Expected at least one pii-in-return-value finding")
        functions = {ev["function"] for f in pii_findings for ev in f["evidence"]}
        self.assertIn("get_user_profile", functions)

    def test_ast_scanner_db_write_finding_cites_correct_function(self) -> None:
        result = self.run_json_script("ast_signal_scan.py", "--path", str(self.fixtures_root / "ai-saas"))
        db_findings = [f for f in result["structural_findings"] if f["id"] == "unlogged-db-write"]
        self.assertTrue(db_findings, "Expected at least one unlogged-db-write finding")
        functions = {ev["function"] for f in db_findings for ev in f["evidence"]}
        self.assertIn("delete_user_account", functions)

    def test_ast_scanner_low_risk_fixture_has_no_findings(self) -> None:
        result = self.run_json_script("ast_signal_scan.py", "--path", str(self.fixtures_root / "low-risk"))
        self.assertEqual(result["structural_findings"], [])

    def test_ast_scanner_markdown_output(self) -> None:
        import sys
        result = self.run_command(
            [
                sys.executable,
                str(self.scripts_root / "ast_signal_scan.py"),
                "--path",
                str(self.fixtures_root / "ai-saas"),
                "--format",
                "markdown",
            ]
        )
        self.assertIn("AST Structural Scan", result.stdout)
        self.assertIn("finding(s)", result.stdout)
