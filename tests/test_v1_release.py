from __future__ import annotations

import json
import tempfile
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    import tomli as tomllib  # type: ignore[no-redef]

from scripts.repo_signal_scan import FRAMEWORKS
from tests.base_test import BaseRegintelTest


class TestV1Release(BaseRegintelTest):
    def test_json_outputs_expose_stable_v1_meta_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            snapshot_dir = tmp / "snapshots"
            snapshot_dir.mkdir(parents=True, exist_ok=True)

            scan_ai = self.run_json_script("repo_signal_scan.py", "--path", str(self.fixtures_root / "ai-saas"), "--scope", "full")
            scan_fintech = self.run_json_script("repo_signal_scan.py", "--path", str(self.fixtures_root / "fintech"), "--scope", "full")
            ast_fintech = self.run_json_script("ast_signal_scan.py", "--path", str(self.fixtures_root / "fintech"), "--format", "json")
            deadlines = self.run_json_script(
                "check_deadlines.py",
                "--input",
                str(self.repo_root / "examples" / "developments.json"),
                "--as-of",
                "2026-03-10",
                "--format",
                "json",
            )
            diff = self.run_json_script(
                "change_diff.py",
                "--old",
                str(self.repo_root / "examples" / "old-scan.json"),
                "--new",
                str(self.repo_root / "examples" / "new-scan.json"),
                "--format",
                "json",
            )
            feed_sync = self.run_json_script(
                "sync_regulatory_feeds.py",
                "--config",
                str(self.repo_root / "tests" / "fixtures" / "feeds" / "feed-config.json"),
                "--format",
                "json",
            )

            scan_ai_path = tmp / "scan-ai.json"
            scan_fintech_path = tmp / "scan-fintech.json"
            ast_fintech_path = tmp / "ast-fintech.json"
            scan_ai_path.write_text(json.dumps(scan_ai), encoding="utf-8")
            scan_fintech_path.write_text(json.dumps(scan_fintech), encoding="utf-8")
            ast_fintech_path.write_text(json.dumps(ast_fintech), encoding="utf-8")

            applicability = self.run_json_script("applicability_score.py", "--signals", str(scan_ai_path), "--format", "json")
            snapshot = self.run_json_script(
                "snapshot_store.py",
                "--scan",
                str(scan_ai_path),
                "--snapshot-dir",
                str(snapshot_dir),
                "--timestamp",
                "2026-03-10T10:00:00Z",
                "--format",
                "json",
            )
            trend = self.run_json_script("trend_report.py", "--snapshot-dir", str(snapshot_dir), "--format", "json")
            gate = self.run_json_script(
                "compliance_gate.py",
                "--policy",
                str(self.repo_root / "examples" / "compliance-gate-policy.json"),
                "--scan",
                str(scan_fintech_path),
                "--ast",
                str(ast_fintech_path),
                "--format",
                "json",
            )
            benchmark = self.run_json_script(
                "benchmark_harness.py",
                "--labels",
                str(self.repo_root / "tests" / "fixtures" / "benchmarks" / "labeled-corpus.json"),
                "--fixtures-root",
                str(self.repo_root / "tests" / "fixtures" / "repos"),
                "--baseline",
                str(self.repo_root / "tests" / "fixtures" / "benchmarks" / "baseline-metrics.json"),
                "--policy",
                str(self.repo_root / "examples" / "benchmark-gate-policy.json"),
                "--workers",
                "2",
                "--cache-dir",
                str(tmp / "bench-cache"),
                "--format",
                "json",
            )

        outputs = {
            "repo_signal_scan": scan_ai,
            "applicability_score": applicability,
            "check_deadlines": deadlines,
            "change_diff": diff,
            "ast_signal_scan": ast_fintech,
            "snapshot_store": snapshot,
            "trend_report": trend,
            "sync_regulatory_feeds": feed_sync,
            "compliance_gate": gate,
            "benchmark_harness": benchmark,
        }
        for tool, output in outputs.items():
            self.assertIn("meta", output)
            self.assertEqual(output["meta"]["tool"], tool)
            self.assertEqual(output["meta"]["schema_version"], "1.0.0")

    def test_fixture_matrix_covers_all_supported_frameworks(self) -> None:
        fixtures = ("ai-saas", "healthcare", "fintech", "iot", "polyglot-regulated")
        discovered: set[str] = set()
        for fixture in fixtures:
            scan = self.run_json_script(
                "repo_signal_scan.py",
                "--path",
                str(self.fixtures_root / fixture),
                "--scope",
                "full",
            )
            discovered.update(item["framework"] for item in scan["candidate_frameworks"])
        self.assertEqual(discovered, set(FRAMEWORKS.keys()))

    def test_pyproject_console_scripts_reference_importable_modules(self) -> None:
        pyproject = tomllib.loads((self.repo_root / "pyproject.toml").read_text(encoding="utf-8"))
        scripts = pyproject["project"]["scripts"]
        expected = {
            "regintel-scan",
            "regintel-ast-scan",
            "regintel-applicability",
            "regintel-deadlines",
            "regintel-diff",
            "regintel-snapshot",
            "regintel-trend",
            "regintel-dashboard",
            "regintel-feed-sync",
            "regintel-gate",
            "regintel-benchmark",
        }
        self.assertEqual(set(scripts.keys()), expected)

        for target in scripts.values():
            module_name, attr = target.split(":")
            module = __import__(module_name, fromlist=[attr])
            self.assertTrue(callable(getattr(module, attr)))
