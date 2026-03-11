from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from tests.base_test import BaseRegintelTest


class TestBenchmarkHarness(BaseRegintelTest):
    def test_benchmark_harness_reports_metrics_and_passes_default_policy(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / "bench-cache"
            result = self.run_json_script(
                "benchmark_harness.py",
                "--labels",
                str(self.repo_root / "tests" / "fixtures" / "benchmarks" / "labeled-corpus.json"),
                "--fixtures-root",
                str(self.fixtures_root),
                "--baseline",
                str(self.repo_root / "tests" / "fixtures" / "benchmarks" / "baseline-metrics.json"),
                "--policy",
                str(self.repo_root / "examples" / "benchmark-gate-policy.json"),
                "--workers",
                "2",
                "--cache-dir",
                str(cache_dir),
            )

        self.assertEqual(result["meta"]["tool"], "benchmark_harness")
        self.assertEqual(result["meta"]["schema_version"], "1.0.0")
        self.assertIn("overall", result)
        self.assertIn("signals", result["overall"])
        self.assertIn("ast", result["overall"])
        self.assertIn("combined", result["overall"])
        self.assertTrue(result["trends"]["available"])
        self.assertTrue(result["gate"]["passed"])
        self.assertEqual(result["gate"]["failed_checks"], 0)

    def test_benchmark_harness_fails_when_policy_thresholds_are_unreachable(self) -> None:
        strict_policy = {
            "name": "strict-benchmark-policy",
            "minimum_metrics": {"signals": {"precision": 1.1}},
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            policy_path = tmp / "strict-policy.json"
            policy_path.write_text(json.dumps(strict_policy), encoding="utf-8")
            cache_dir = tmp / "bench-cache"

            proc = subprocess.run(
                [
                    sys.executable,
                    str(self.scripts_root / "benchmark_harness.py"),
                    "--labels",
                    str(self.repo_root / "tests" / "fixtures" / "benchmarks" / "labeled-corpus.json"),
                    "--fixtures-root",
                    str(self.fixtures_root),
                    "--baseline",
                    str(self.repo_root / "tests" / "fixtures" / "benchmarks" / "baseline-metrics.json"),
                    "--policy",
                    str(policy_path),
                    "--workers",
                    "2",
                    "--cache-dir",
                    str(cache_dir),
                    "--format",
                    "json",
                ],
                cwd=str(self.repo_root),
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                check=False,
                capture_output=True,
                text=True,
            )
            payload = json.loads(proc.stdout)

        self.assertEqual(proc.returncode, 1)
        self.assertFalse(payload["gate"]["passed"])
        failed = [item for item in payload["gate"]["checks"] if item["status"] == "fail"]
        self.assertTrue(any(item["check"] == "minimum_signals_precision" for item in failed))
