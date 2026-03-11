#!/usr/bin/env python3
"""Store scan snapshots over time and compute deltas versus the prior snapshot."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from ._contract import with_meta
    from ._markdown import delta_badge, markdown_cell
except ImportError:
    from _contract import with_meta  # type: ignore
    from _markdown import delta_badge, markdown_cell  # type: ignore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scan", required=True, help="Path to repo_signal_scan JSON output.")
    parser.add_argument("--applicability", help="Optional path to applicability_score JSON output.")
    parser.add_argument("--deadlines", help="Optional path to check_deadlines JSON output.")
    parser.add_argument("--ast", dest="ast_path", help="Optional path to ast_signal_scan JSON output.")
    parser.add_argument("--snapshot-dir", default=".regintel/snapshots", help="Directory to store snapshots and index.")
    parser.add_argument("--tag", help="Optional tag for this snapshot (e.g., main, nightly, release-candidate).")
    parser.add_argument(
        "--timestamp",
        help="Optional UTC timestamp for deterministic runs (ISO 8601, e.g. 2026-03-11T12:00:00Z).",
    )
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    return parser.parse_args()


def load_json(path_str: str | None) -> Any:
    if not path_str:
        return None
    path = Path(path_str)
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def parse_timestamp(raw: str | None) -> str:
    if not raw:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    normalized = raw.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def make_snapshot_id(created_at: str) -> str:
    compact = re.sub(r"[^0-9]", "", created_at)
    return compact[:14] if len(compact) >= 14 else compact


def framework_scores(scan: dict[str, Any] | None) -> dict[str, int]:
    if not isinstance(scan, dict):
        return {}
    scores: dict[str, int] = {}
    for item in scan.get("candidate_frameworks", []):
        if not isinstance(item, dict):
            continue
        framework = item.get("framework")
        if isinstance(framework, str):
            scores[framework] = int(item.get("score", 0))
    return scores


def collect_metrics(
    scan: dict[str, Any] | None,
    applicability: dict[str, Any] | None,
    deadlines: dict[str, Any] | None,
    ast_data: dict[str, Any] | None,
) -> dict[str, Any]:
    signals = scan.get("signals", []) if isinstance(scan, dict) else []
    controls = scan.get("control_observations", []) if isinstance(scan, dict) else []
    frameworks = scan.get("candidate_frameworks", []) if isinstance(scan, dict) else []
    applicability_items = applicability.get("applicability", []) if isinstance(applicability, dict) else []
    developments = deadlines.get("developments", []) if isinstance(deadlines, dict) else []
    structural = ast_data.get("structural_findings", []) if isinstance(ast_data, dict) else []

    top_framework = None
    if frameworks:
        ranked = sorted(
            [item for item in frameworks if isinstance(item, dict)],
            key=lambda item: (-int(item.get("score", 0)), str(item.get("display_name", ""))),
        )
        if ranked:
            top_framework = {
                "framework": ranked[0].get("framework"),
                "display_name": ranked[0].get("display_name"),
                "score": int(ranked[0].get("score", 0)),
            }

    urgent = 0
    for item in developments:
        if not isinstance(item, dict):
            continue
        if str(item.get("urgency", "")).lower() in {"critical", "high"}:
            urgent += 1

    observed_controls = 0
    not_observed_controls = 0
    for control in controls:
        if not isinstance(control, dict):
            continue
        status = str(control.get("status", "")).lower()
        if status == "observed":
            observed_controls += 1
        elif status == "not-observed":
            not_observed_controls += 1

    return {
        "signal_count": len(signals),
        "framework_count": len(frameworks),
        "applicability_count": len(applicability_items),
        "structural_finding_count": len(structural),
        "observed_control_count": observed_controls,
        "not_observed_control_count": not_observed_controls,
        "high_or_critical_deadline_count": urgent,
        "top_framework": top_framework,
    }


def load_index(snapshot_dir: Path) -> dict[str, Any]:
    index_path = snapshot_dir / "index.json"
    if not index_path.exists():
        return {"version": 1, "snapshots": []}
    with index_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        return {"version": 1, "snapshots": []}
    snapshots = data.get("snapshots", [])
    if not isinstance(snapshots, list):
        snapshots = []
    return {"version": int(data.get("version", 1)), "snapshots": snapshots}


def save_index(snapshot_dir: Path, index: dict[str, Any]) -> None:
    index_path = snapshot_dir / "index.json"
    with index_path.open("w", encoding="utf-8") as handle:
        json.dump(index, handle, indent=2)
        handle.write("\n")


def resolve_previous_snapshot(snapshot_dir: Path, index: dict[str, Any]) -> dict[str, Any] | None:
    snapshots = index.get("snapshots", [])
    if not isinstance(snapshots, list) or not snapshots:
        return None
    latest = snapshots[-1]
    if not isinstance(latest, dict):
        return None
    relative = latest.get("path")
    if not isinstance(relative, str):
        return None
    path = snapshot_dir / relative
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def build_trend(current_snapshot: dict[str, Any], previous_snapshot: dict[str, Any] | None) -> dict[str, Any]:
    if not previous_snapshot:
        return {
            "baseline_snapshot_id": None,
            "signal_delta": None,
            "framework_delta": None,
            "not_observed_control_delta": None,
            "urgent_deadline_delta": None,
            "framework_score_changes": [],
        }

    current_metrics = current_snapshot.get("metrics", {})
    previous_metrics = previous_snapshot.get("metrics", {})

    current_scan = current_snapshot.get("scan")
    previous_scan = previous_snapshot.get("scan")
    current_scores = framework_scores(current_scan if isinstance(current_scan, dict) else None)
    previous_scores = framework_scores(previous_scan if isinstance(previous_scan, dict) else None)
    all_frameworks = sorted(set(current_scores) | set(previous_scores))
    changes = []
    for framework in all_frameworks:
        old_score = previous_scores.get(framework, 0)
        new_score = current_scores.get(framework, 0)
        if old_score == new_score:
            continue
        changes.append({"framework": framework, "old_score": old_score, "new_score": new_score, "delta": new_score - old_score})

    changes.sort(key=lambda item: (-abs(int(item["delta"])), item["framework"]))
    return {
        "baseline_snapshot_id": previous_snapshot.get("meta", {}).get("snapshot_id"),
        "signal_delta": int(current_metrics.get("signal_count", 0)) - int(previous_metrics.get("signal_count", 0)),
        "framework_delta": int(current_metrics.get("framework_count", 0)) - int(previous_metrics.get("framework_count", 0)),
        "not_observed_control_delta": int(current_metrics.get("not_observed_control_count", 0))
        - int(previous_metrics.get("not_observed_control_count", 0)),
        "urgent_deadline_delta": int(current_metrics.get("high_or_critical_deadline_count", 0))
        - int(previous_metrics.get("high_or_critical_deadline_count", 0)),
        "framework_score_changes": changes[:12],
    }


def render_markdown(summary: dict[str, Any]) -> str:
    snapshot = summary["snapshot"]
    metrics = summary["metrics"]
    trend = summary["trend"]
    lines = [
        "# Snapshot Store",
        "",
        "| Snapshot | Value |",
        "|---|---|",
        f"| Snapshot ID | `{snapshot['snapshot_id']}` |",
        f"| Created At | `{snapshot['created_at']}` |",
        f"| File | `{snapshot['path']}` |",
        "",
        "## Metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Signals | {metrics['signal_count']} |",
        f"| Candidate frameworks | {metrics['framework_count']} |",
        f"| Not-observed controls | {metrics['not_observed_control_count']} |",
        f"| High/Critical deadlines | {metrics['high_or_critical_deadline_count']} |",
        f"| Structural findings | {metrics['structural_finding_count']} |",
    ]
    top = metrics.get("top_framework")
    if isinstance(top, dict) and top.get("framework"):
        lines.append(f"| Top framework | {markdown_cell(top.get('framework'))} ({top.get('score')}) |")

    lines.extend(["", "## Delta vs Previous Snapshot"])
    if not trend.get("baseline_snapshot_id"):
        lines.append("")
        lines.append("✅ No baseline snapshot found.")
    else:
        lines.extend(
            [
                "",
                "| Metric | Value |",
                "|---|---|",
                f"| Baseline snapshot | `{trend['baseline_snapshot_id']}` |",
                f"| Signal delta | {delta_badge(trend['signal_delta'])} |",
                f"| Framework delta | {delta_badge(trend['framework_delta'])} |",
                f"| Not-observed controls delta | {delta_badge(trend['not_observed_control_delta'])} |",
                f"| High/Critical deadlines delta | {delta_badge(trend['urgent_deadline_delta'])} |",
            ]
        )
        changes = trend.get("framework_score_changes", [])
        if changes:
            lines.extend(["", "### Framework Score Changes", "", "| Framework | Previous | Current | Delta |", "|---|---:|---:|---|"])
            for change in changes[:6]:
                lines.append(
                    f"| {markdown_cell(change['framework'])} | {change['old_score']} | {change['new_score']} | {delta_badge(change['delta'])} |"
                )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    snapshot_dir = Path(args.snapshot_dir)
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    scan = load_json(args.scan)
    applicability = load_json(args.applicability)
    deadlines = load_json(args.deadlines)
    ast_data = load_json(args.ast_path)

    created_at = parse_timestamp(args.timestamp)
    snapshot_id = make_snapshot_id(created_at)
    filename = f"snapshot-{snapshot_id}.json"
    snapshot_path = snapshot_dir / filename
    dedupe = 1
    while snapshot_path.exists():
        dedupe += 1
        filename = f"snapshot-{snapshot_id}-{dedupe}.json"
        snapshot_path = snapshot_dir / filename

    index = load_index(snapshot_dir)
    previous_snapshot = resolve_previous_snapshot(snapshot_dir, index)
    metrics = collect_metrics(scan if isinstance(scan, dict) else None, applicability, deadlines, ast_data)

    snapshot = {
        "meta": {
            "snapshot_id": snapshot_id,
            "created_at": created_at,
            "tag": args.tag,
            "sources": {
                "scan": str(Path(args.scan)),
                "applicability": args.applicability,
                "deadlines": args.deadlines,
                "ast": args.ast_path,
            },
        },
        "scan": scan,
        "applicability": applicability,
        "deadlines": deadlines,
        "ast": ast_data,
        "metrics": metrics,
    }
    with snapshot_path.open("w", encoding="utf-8") as handle:
        json.dump(snapshot, handle, indent=2)
        handle.write("\n")

    entry = {
        "snapshot_id": snapshot_id,
        "created_at": created_at,
        "path": filename,
        "tag": args.tag,
        "metrics": metrics,
    }
    snapshots = [item for item in index.get("snapshots", []) if isinstance(item, dict)]
    snapshots.append(entry)
    snapshots.sort(key=lambda item: str(item.get("created_at", "")))
    index["snapshots"] = snapshots
    save_index(snapshot_dir, index)

    trend = build_trend(snapshot, previous_snapshot)
    output = with_meta(
        "snapshot_store",
        {
            "snapshot": {"snapshot_id": snapshot_id, "created_at": created_at, "path": str(snapshot_path.as_posix())},
            "metrics": metrics,
            "trend": trend,
        },
    )
    if args.format == "markdown":
        sys.stdout.write(render_markdown(output))
    else:
        json.dump(output, sys.stdout, indent=2)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
