#!/usr/bin/env python3
"""Render a lightweight monitoring dashboard from stored snapshots."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from ._markdown import markdown_cell, score_badge, urgency_badge
    from .trend_report import build_report, load_index, load_snapshot
except ImportError:
    from _markdown import markdown_cell, score_badge, urgency_badge  # type: ignore
    from trend_report import build_report, load_index, load_snapshot  # type: ignore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-dir", default=".regintel/snapshots", help="Directory containing snapshot files and index.json.")
    parser.add_argument("--limit", type=int, default=10, help="Number of recent snapshots to include in trend tables.")
    parser.add_argument("--format", choices=("markdown", "html"), default="markdown")
    parser.add_argument("--output", help="Optional output file path. If omitted, writes to stdout.")
    return parser.parse_args()


def latest_snapshot(snapshot_dir: Path) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    entries = load_index(snapshot_dir)
    if not entries:
        return None, None
    entries.sort(key=lambda item: str(item.get("created_at", "")))
    latest_entry = entries[-1]
    snapshot = load_snapshot(snapshot_dir, latest_entry)
    return latest_entry, snapshot


def top_frameworks(snapshot: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(snapshot, dict):
        return []
    scan = snapshot.get("scan")
    if not isinstance(scan, dict):
        return []
    items = [item for item in scan.get("candidate_frameworks", []) if isinstance(item, dict)]
    items.sort(key=lambda item: (-int(item.get("score", 0)), str(item.get("display_name", ""))))
    return items[:8]


def not_observed_controls(snapshot: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(snapshot, dict):
        return []
    scan = snapshot.get("scan")
    if not isinstance(scan, dict):
        return []
    controls = [item for item in scan.get("control_observations", []) if isinstance(item, dict)]
    return [item for item in controls if str(item.get("status", "")).lower() == "not-observed"]


def render_markdown(report: dict[str, Any], latest_entry: dict[str, Any] | None, snapshot: dict[str, Any] | None) -> str:
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    lines = ["# Regintel Monitoring Dashboard", "", f"- Generated at: `{generated_at}`", ""]
    if not latest_entry or not snapshot:
        lines.append("✅ No snapshots found.")
        return "\n".join(lines) + "\n"

    metrics = snapshot.get("metrics", {}) if isinstance(snapshot.get("metrics"), dict) else {}
    lines.append("## Latest Snapshot")
    lines.extend(
        [
            "| Metric | Value |",
            "|---|---|",
            f"| Snapshot | `{latest_entry.get('snapshot_id')}` |",
            f"| Created at | `{latest_entry.get('created_at')}` |",
            f"| Signals | {metrics.get('signal_count', 0)} |",
            f"| Candidate frameworks | {metrics.get('framework_count', 0)} |",
            f"| Not-observed controls | {metrics.get('not_observed_control_count', 0)} |",
            f"| High/Critical deadlines | {urgency_badge('high' if metrics.get('high_or_critical_deadline_count', 0) else 'low')} ({metrics.get('high_or_critical_deadline_count', 0)}) |",
            "",
        ]
    )

    lines.append("### Top Frameworks")
    lines.append("")
    frameworks = top_frameworks(snapshot)
    if not frameworks:
        lines.append("✅ No framework scores available.")
    else:
        lines.append("| Priority | Framework | Score | Confidence |")
        lines.append("|---|---|---:|---:|")
        for item in frameworks:
            lines.append(
                f"| {score_badge(int(item.get('score', 0)))} | {markdown_cell(item.get('display_name', item.get('framework', '-')))} | {int(item.get('score', 0))} | {float(item.get('confidence', 0.0)):.2f} |"
            )
    lines.append("")

    lines.append("### Not Observed Controls")
    lines.append("")
    missing = not_observed_controls(snapshot)
    if not missing:
        lines.append("✅ No not-observed controls in the latest snapshot.")
    else:
        lines.append("| Control | Rationale |")
        lines.append("|---|---|")
        for item in missing:
            lines.append(f"| `{item.get('control')}` | {markdown_cell(item.get('rationale', ''))} |")
    lines.append("")

    lines.append("## Trend Window")
    lines.append("")
    lines.append("| Snapshot | Signals | Frameworks | Not Observed Controls | High/Critical Deadlines |")
    lines.append("|---|---:|---:|---:|---:|")
    for item in report.get("history", []):
        lines.append(
            f"| {markdown_cell(item.get('snapshot_id'))} | {item.get('signal_count', 0)} | {item.get('framework_count', 0)} | {item.get('not_observed_control_count', 0)} | {item.get('high_or_critical_deadline_count', 0)} |"
        )

    return "\n".join(lines) + "\n"


def render_html(report: dict[str, Any], latest_entry: dict[str, Any] | None, snapshot: dict[str, Any] | None) -> str:
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    if not latest_entry or not snapshot:
        body = "<p>No snapshots found.</p>"
    else:
        metrics = snapshot.get("metrics", {}) if isinstance(snapshot.get("metrics"), dict) else {}
        frameworks = top_frameworks(snapshot)
        missing = not_observed_controls(snapshot)

        framework_rows = "".join(
            f"<tr><td>{item.get('display_name', item.get('framework', '-'))}</td><td>{int(item.get('score', 0))}</td><td>{float(item.get('confidence', 0.0)):.2f}</td></tr>"
            for item in frameworks
        )
        if not framework_rows:
            framework_rows = "<tr><td colspan='3'>No framework scores available.</td></tr>"

        missing_list = "".join(
            f"<li><code>{item.get('control')}</code>: {item.get('rationale', '')}</li>" for item in missing
        ) or "<li>No not-observed controls in the latest snapshot.</li>"

        trend_rows = "".join(
            f"<tr><td>{item.get('snapshot_id')}</td><td>{item.get('signal_count', 0)}</td><td>{item.get('framework_count', 0)}</td><td>{item.get('not_observed_control_count', 0)}</td></tr>"
            for item in report.get("history", [])
        )

        body = f"""
        <section>
          <h2>Latest Snapshot</h2>
          <ul>
            <li><strong>Snapshot:</strong> <code>{latest_entry.get('snapshot_id')}</code></li>
            <li><strong>Created:</strong> <code>{latest_entry.get('created_at')}</code></li>
            <li><strong>Signals:</strong> {metrics.get('signal_count', 0)}</li>
            <li><strong>Candidate frameworks:</strong> {metrics.get('framework_count', 0)}</li>
            <li><strong>Not-observed controls:</strong> {metrics.get('not_observed_control_count', 0)}</li>
            <li><strong>High/Critical deadlines:</strong> {metrics.get('high_or_critical_deadline_count', 0)}</li>
          </ul>
        </section>
        <section>
          <h3>Top Frameworks</h3>
          <table>
            <thead><tr><th>Framework</th><th>Score</th><th>Confidence</th></tr></thead>
            <tbody>{framework_rows}</tbody>
          </table>
        </section>
        <section>
          <h3>Not Observed Controls</h3>
          <ul>{missing_list}</ul>
        </section>
        <section>
          <h2>Trend Window</h2>
          <table>
            <thead><tr><th>Snapshot</th><th>Signals</th><th>Frameworks</th><th>Not Observed Controls</th></tr></thead>
            <tbody>{trend_rows}</tbody>
          </table>
        </section>
        """

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Regintel Monitoring Dashboard</title>
  <style>
    :root {{
      --bg: #f8fafc;
      --panel: #ffffff;
      --text: #1f2937;
      --muted: #6b7280;
      --accent: #0f766e;
      --border: #d1d5db;
    }}
    body {{
      margin: 0;
      font-family: "Segoe UI", "Helvetica Neue", Helvetica, Arial, sans-serif;
      color: var(--text);
      background: linear-gradient(180deg, #ecfeff 0%, var(--bg) 40%);
    }}
    main {{
      max-width: 960px;
      margin: 0 auto;
      padding: 24px;
    }}
    h1, h2, h3 {{
      margin: 0 0 12px;
    }}
    section {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 16px;
      margin-bottom: 16px;
      box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
    }}
    .meta {{
      color: var(--muted);
      margin-bottom: 16px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
    }}
    th, td {{
      border: 1px solid var(--border);
      padding: 8px;
      text-align: left;
      font-size: 14px;
    }}
    th {{
      background: #f0fdfa;
      color: var(--accent);
    }}
    code {{
      background: #f1f5f9;
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 12px;
    }}
  </style>
</head>
<body>
  <main>
    <h1>Regintel Monitoring Dashboard</h1>
    <p class="meta">Generated at <code>{generated_at}</code></p>
    {body}
  </main>
</body>
</html>
"""


def write_output(content: str, output: str | None) -> None:
    if not output:
        print(content, end="")
        return
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    args = parse_args()
    snapshot_dir = Path(args.snapshot_dir)
    report = build_report(snapshot_dir, args.limit)
    latest_entry, snapshot = latest_snapshot(snapshot_dir)
    if args.format == "html":
        write_output(render_html(report, latest_entry, snapshot), args.output)
    else:
        write_output(render_markdown(report, latest_entry, snapshot), args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
