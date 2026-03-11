import shutil
import sys
from tests.base_test import BaseRegintelTest


class TestTooling(BaseRegintelTest):
    def test_validate_repo_passes_without_creating_script_pycache(self) -> None:
        for pycache_dir in (self.repo_root / "scripts" / "__pycache__", self.repo_root / "tools" / "__pycache__"):
            if pycache_dir.exists():
                shutil.rmtree(pycache_dir)
        self.run_command([sys.executable, str(self.tools_root / "validate_repo.py")])
        self.assertFalse((self.repo_root / "scripts" / "__pycache__").exists())
        self.assertFalse((self.repo_root / "tools" / "__pycache__").exists())

    def test_example_deadlines_have_expected_warning_labels(self) -> None:
        result = self.run_json_script(
            "check_deadlines.py",
            "--input",
            str(self.repo_root / "examples" / "developments.json"),
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
        result = self.run_json_script(
            "change_diff.py",
            "--old",
            str(self.repo_root / "examples" / "old-scan.json"),
            "--new",
            str(self.repo_root / "examples" / "new-scan.json"),
            "--format",
            "json",
        )
        self.assertTrue(result["collections"]["signals"]["added"])
        self.assertTrue(result["collections"]["candidate_frameworks"]["changed"])
        self.assertTrue(result["collections"]["applicability"]["changed"])

    def test_monitor_workflow_exists_with_schedule_and_dispatch(self) -> None:
        workflow_path = self.repo_root / ".github" / "workflows" / "monitor.yml"
        self.assertTrue(workflow_path.exists(), "Expected .github/workflows/monitor.yml to exist.")
        content = workflow_path.read_text(encoding="utf-8")
        self.assertIn("schedule:", content)
        self.assertIn("workflow_dispatch:", content)
        self.assertIn("snapshot_store.py", content)
        self.assertIn("trend_report.py", content)
        self.assertIn("compliance_gate.py", content)

    def test_v1_docs_site_files_and_navigation_exist(self) -> None:
        mkdocs_path = self.repo_root / "mkdocs.yml"
        self.assertTrue(mkdocs_path.exists(), "Expected mkdocs.yml to exist for the v0.7 docs site.")
        content = mkdocs_path.read_text(encoding="utf-8")
        self.assertIn("nav:", content)
        self.assertIn("tutorials/ci-monitoring.md", content)
        self.assertIn("reference/script-contracts.md", content)

    def test_docs_workflow_exists_for_site_deploy(self) -> None:
        workflow_path = self.repo_root / ".github" / "workflows" / "docs.yml"
        self.assertTrue(workflow_path.exists(), "Expected .github/workflows/docs.yml to exist.")
        content = workflow_path.read_text(encoding="utf-8")
        self.assertIn("mkdocs gh-deploy", content)
        self.assertIn("python -m pip install -e \".[docs]\"", content)

    def test_v1_package_metadata_has_console_scripts(self) -> None:
        pyproject = (self.repo_root / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('version = "1.0.0"', pyproject)
        self.assertIn("[project.scripts]", pyproject)
        self.assertIn('regintel-scan = "scripts.repo_signal_scan:main"', pyproject)
        self.assertIn('regintel-gate = "scripts.compliance_gate:main"', pyproject)

    def test_publish_workflow_exists_for_release_builds(self) -> None:
        workflow_path = self.repo_root / ".github" / "workflows" / "publish.yml"
        self.assertTrue(workflow_path.exists(), "Expected .github/workflows/publish.yml to exist.")
        content = workflow_path.read_text(encoding="utf-8")
        self.assertIn("gh-action-pypi-publish", content)
        self.assertIn("python -m build", content)
