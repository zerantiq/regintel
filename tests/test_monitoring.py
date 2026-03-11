import json
import sys
import tempfile
from pathlib import Path

from tests.base_test import BaseRegintelTest


class TestMonitoringAndReporting(BaseRegintelTest):
    def _create_snapshot_history(self, snapshot_dir: Path) -> None:
        ai_scan = self.run_json_script("repo_signal_scan.py", "--path", str(self.fixtures_root / "ai-saas"), "--scope", "full")
        fintech_scan = self.run_json_script("repo_signal_scan.py", "--path", str(self.fixtures_root / "fintech"), "--scope", "full")

        ai_scan_path = snapshot_dir / "scan-ai.json"
        fintech_scan_path = snapshot_dir / "scan-fintech.json"
        ai_scan_path.write_text(json.dumps(ai_scan), encoding="utf-8")
        fintech_scan_path.write_text(json.dumps(fintech_scan), encoding="utf-8")

        self.run_json_script(
            "snapshot_store.py",
            "--scan",
            str(ai_scan_path),
            "--snapshot-dir",
            str(snapshot_dir),
            "--timestamp",
            "2026-03-10T10:00:00Z",
            "--tag",
            "baseline",
        )
        self.run_json_script(
            "snapshot_store.py",
            "--scan",
            str(fintech_scan_path),
            "--snapshot-dir",
            str(snapshot_dir),
            "--timestamp",
            "2026-03-11T10:00:00Z",
            "--tag",
            "nightly",
        )

    def test_snapshot_store_persists_index_and_reports_delta(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_dir = Path(tmpdir) / "snapshots"
            snapshot_dir.mkdir(parents=True, exist_ok=True)
            scan = self.run_json_script("repo_signal_scan.py", "--path", str(self.fixtures_root / "ai-saas"), "--scope", "full")
            scan_path = snapshot_dir / "scan.json"
            scan_path.write_text(json.dumps(scan), encoding="utf-8")

            first = self.run_json_script(
                "snapshot_store.py",
                "--scan",
                str(scan_path),
                "--snapshot-dir",
                str(snapshot_dir),
                "--timestamp",
                "2026-03-10T10:00:00Z",
            )
            self.assertIsNone(first["trend"]["baseline_snapshot_id"])

            updated_scan = self.run_json_script("repo_signal_scan.py", "--path", str(self.fixtures_root / "fintech"), "--scope", "full")
            scan_path.write_text(json.dumps(updated_scan), encoding="utf-8")
            second = self.run_json_script(
                "snapshot_store.py",
                "--scan",
                str(scan_path),
                "--snapshot-dir",
                str(snapshot_dir),
                "--timestamp",
                "2026-03-11T10:00:00Z",
            )
            self.assertIsNotNone(second["trend"]["baseline_snapshot_id"])
            self.assertIsInstance(second["trend"]["signal_delta"], int)

            index_path = snapshot_dir / "index.json"
            index = json.loads(index_path.read_text(encoding="utf-8"))
            self.assertEqual(len(index["snapshots"]), 2)

    def test_trend_report_summarizes_snapshot_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_dir = Path(tmpdir) / "snapshots"
            snapshot_dir.mkdir(parents=True, exist_ok=True)
            self._create_snapshot_history(snapshot_dir)

            report = self.run_json_script("trend_report.py", "--snapshot-dir", str(snapshot_dir), "--format", "json")
            self.assertEqual(report["snapshot_count"], 2)
            self.assertEqual(report["window"], 2)
            self.assertEqual(len(report["history"]), 2)
            self.assertTrue(report["latest_snapshot"])
            self.assertIsInstance(report["framework_trends"], list)

    def test_dashboard_report_renders_markdown_and_html(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_dir = Path(tmpdir) / "snapshots"
            snapshot_dir.mkdir(parents=True, exist_ok=True)
            self._create_snapshot_history(snapshot_dir)

            markdown = self.run_command(
                [
                    sys.executable,
                    str(self.scripts_root / "dashboard_report.py"),
                    "--snapshot-dir",
                    str(snapshot_dir),
                    "--format",
                    "markdown",
                ]
            )
            self.assertIn("Regintel Monitoring Dashboard", markdown.stdout)
            self.assertIn("Latest Snapshot", markdown.stdout)

            html_path = Path(tmpdir) / "dashboard.html"
            self.run_command(
                [
                    sys.executable,
                    str(self.scripts_root / "dashboard_report.py"),
                    "--snapshot-dir",
                    str(snapshot_dir),
                    "--format",
                    "html",
                    "--output",
                    str(html_path),
                ]
            )
            content = html_path.read_text(encoding="utf-8")
            self.assertIn("<html", content)
            self.assertIn("Regintel Monitoring Dashboard", content)

    def test_sync_regulatory_feeds_produces_deadline_compatible_output(self) -> None:
        feed_config = self.repo_root / "tests" / "fixtures" / "feeds" / "feed-config.json"
        synced = self.run_json_script("sync_regulatory_feeds.py", "--config", str(feed_config), "--format", "json")
        self.assertEqual(synced["feed_count"], 2)
        frameworks = {item["framework"] for item in synced["developments"]}
        self.assertIn("EU AI Act", frameworks)
        self.assertIn("NIS2", frameworks)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "synced-developments.json"
            output_path.write_text(json.dumps({"developments": synced["developments"]}), encoding="utf-8")
            deadlines = self.run_json_script(
                "check_deadlines.py",
                "--input",
                str(output_path),
                "--as-of",
                "2026-03-10",
                "--format",
                "json",
            )
            self.assertTrue(deadlines["developments"])
            for item in deadlines["developments"]:
                self.assertIn("warning_label", item)

    def test_change_diff_supports_snapshot_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_dir = Path(tmpdir) / "snapshots"
            snapshot_dir.mkdir(parents=True, exist_ok=True)
            self._create_snapshot_history(snapshot_dir)

            index = json.loads((snapshot_dir / "index.json").read_text(encoding="utf-8"))
            snapshots = index["snapshots"]
            self.assertGreaterEqual(len(snapshots), 2)
            old_snapshot = snapshot_dir / snapshots[-2]["path"]
            new_snapshot = snapshot_dir / snapshots[-1]["path"]

            diff = self.run_json_script(
                "change_diff.py",
                "--old",
                str(old_snapshot),
                "--new",
                str(new_snapshot),
                "--format",
                "json",
            )
            changed_or_added = (
                diff["collections"]["signals"]["added"]
                or diff["collections"]["signals"]["changed"]
                or diff["collections"]["candidate_frameworks"]["changed"]
            )
            self.assertTrue(changed_or_added)
