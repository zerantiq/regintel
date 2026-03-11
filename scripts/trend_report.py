#!/usr/bin/env python3
"""Build trend reports from stored Regintel snapshots."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from ._contract import with_meta
except ImportError:
    from _contract import with_meta  # type: ignore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-dir", default=".regintel/snapshots", help="Directory containing snapshot files and index.json.")
    parser.add_argument("--limit", type=int, default=20, help="Max number of most recent snapshots to include.")
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    return parser.parse_args()


def load_index(snapshot_dir: Path) -> list[dict[str, Any]]:
    index_path = snapshot_dir / "index.json"
    if not index_path.exists():
        return []
    with index_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    snapshots = data.get("snapshots", []) if isinstance(data, dict) else []
    return [item for item in snapshots if isinstance(item, dict)]


def load_snapshot(snapshot_dir: Path, entry: dict[str, Any]) -> dict[str, Any] | None:
    relative = entry.get("path")
    if not isinstance(relative, str):
        return None
    path = snapshot_dir / relative
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return data if isinstance(data, dict) else None


def framework_scores(scan: dict[str, Any] | None) -> dict[str, int]:
    if not isinstance(scan, dict):
        return {}
    result: dict[str, int] = {}
    for item in scan.get("candidate_frameworks", []):
        if not isinstance(item, dict):
            continue
        framework = item.get("framework")
        if isinstance(framework, str):
            result[framework] = int(item.get("score", 0))
    return result


def top_framework(scan: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(scan, dict):
        return None
    items = [item for item in scan.get("candidate_frameworks", []) if isinstance(item, dict)]
    if not items:
        return None
    items.sort(key=lambda item: (-int(item.get("score", 0)), str(item.get("display_name", ""))))
    return {"framework": items[0].get("framework"), "display_name": items[0].get("display_name"), "score": int(items[0].get("score", 0))}


def build_report(snapshot_dir: Path, limit: int) -> dict[str, Any]:
    entries = load_index(snapshot_dir)
    if not entries:
        return with_meta(
            "trend_report",
            {
                "snapshot_count": 0,
                "window": 0,
                "history": [],
                "framework_trends": [],
                "latest_snapshot": None,
            },
        )

    entries.sort(key=lambda item: str(item.get("created_at", "")))
    window_entries = entries[-max(limit, 1) :]
    history: list[dict[str, Any]] = []
    framework_series: dict[str, list[dict[str, Any]]] = {}

    for entry in window_entries:
        snapshot = load_snapshot(snapshot_dir, entry)
        if not snapshot:
            continue
        metrics = snapshot.get("metrics", {}) if isinstance(snapshot.get("metrics"), dict) else {}
        scan = snapshot.get("scan") if isinstance(snapshot.get("scan"), dict) else None
        scores = framework_scores(scan)
        for framework, score in scores.items():
            framework_series.setdefault(framework, []).append(
                {"snapshot_id": entry.get("snapshot_id"), "created_at": entry.get("created_at"), "score": score}
            )

        history.append(
            {
                "snapshot_id": entry.get("snapshot_id"),
                "created_at": entry.get("created_at"),
                "signal_count": int(metrics.get("signal_count", 0)),
                "framework_count": int(metrics.get("framework_count", 0)),
                "not_observed_control_count": int(metrics.get("not_observed_control_count", 0)),
                "high_or_critical_deadline_count": int(metrics.get("high_or_critical_deadline_count", 0)),
                "structural_finding_count": int(metrics.get("structural_finding_count", 0)),
                "top_framework": top_framework(scan),
            }
        )

    trends = []
    for framework, points in framework_series.items():
        if len(points) < 2:
            continue
        first = points[0]["score"]
        latest = points[-1]["score"]
        delta = latest - first
        if delta == 0:
            continue
        trends.append(
            {
                "framework": framework,
                "first_score": first,
                "latest_score": latest,
                "delta": delta,
                "direction": "up" if delta > 0 else "down",
            }
        )
    trends.sort(key=lambda item: (-abs(int(item["delta"])), item["framework"]))

    latest_snapshot = history[-1] if history else None
    return with_meta(
        "trend_report",
        {
            "snapshot_count": len(entries),
            "window": len(history),
            "history": history,
            "framework_trends": trends,
            "latest_snapshot": latest_snapshot,
        },
    )


def render_markdown(report: dict[str, Any]) -> str:
    lines = ["# Trend Report", ""]
    if report["snapshot_count"] == 0:
        lines.append("No snapshots found.")
        return "\n".join(lines) + "\n"

    lines.append(f"- Total snapshots: {report['snapshot_count']}")
    lines.append(f"- Report window: {report['window']}")
    latest = report.get("latest_snapshot")
    if latest:
        lines.append(f"- Latest snapshot: `{latest.get('snapshot_id')}` ({latest.get('created_at')})")
    lines.append("")

    lines.append("## Snapshot History")
    lines.append("")
    lines.append("| Snapshot | Signals | Frameworks | Not Observed Controls | High/Critical Deadlines |")
    lines.append("|---|---:|---:|---:|---:|")
    for item in report["history"]:
        lines.append(
            f"| {item.get('snapshot_id')} | {item.get('signal_count', 0)} | {item.get('framework_count', 0)} | {item.get('not_observed_control_count', 0)} | {item.get('high_or_critical_deadline_count', 0)} |"
        )

    lines.append("")
    lines.append("## Framework Score Trends")
    trends = report.get("framework_trends", [])
    if not trends:
        lines.append("")
        lines.append("No framework score movement detected in this window.")
    else:
        lines.append("")
        lines.append("| Framework | First | Latest | Delta |")
        lines.append("|---|---:|---:|---:|")
        for trend in trends:
            lines.append(
                f"| {trend['framework']} | {trend['first_score']} | {trend['latest_score']} | {trend['delta']:+d} |"
            )

    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    snapshot_dir = Path(args.snapshot_dir)
    report = build_report(snapshot_dir, args.limit)
    if args.format == "markdown":
        sys.stdout.write(render_markdown(report))
    else:
        json.dump(report, sys.stdout, indent=2)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
