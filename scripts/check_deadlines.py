#!/usr/bin/env python3
"""Annotate regulatory developments with milestone urgency and warning labels."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

try:
    from ._contract import with_meta
    from ._markdown import markdown_cell, urgency_badge, warning_badge
except ImportError:
    from _contract import with_meta  # type: ignore
    from _markdown import markdown_cell, urgency_badge, warning_badge  # type: ignore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Path to developments JSON.")
    parser.add_argument("--as-of", dest="as_of", help="Override the reference date (YYYY-MM-DD).")
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    return parser.parse_args()


def load_json(path_str: str) -> Any:
    path = Path(path_str)
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def parse_iso_date(raw: str) -> date:
    return datetime.strptime(raw, "%Y-%m-%d").date()


def classify_warning(days_until: int, kind: str, stage: str) -> tuple[str, str]:
    if days_until < 0:
        return "Critical Deadline", "Critical"
    if kind == "reporting" and days_until <= 14:
        return "Critical Deadline", "Critical"
    if days_until <= 30:
        return "Critical Deadline", "Critical"
    if days_until <= 60:
        return "High Priority", "High"
    if days_until <= 120 or stage == "effective":
        return "Action Needed Soon", "High"
    if days_until <= 270 or stage == "adopted":
        return "Upcoming Change", "Medium"
    return "Monitor", "Low"


def annotate_developments(data: Any, as_of: date) -> dict[str, Any]:
    developments = data["developments"] if isinstance(data, dict) and "developments" in data else data
    annotated = []
    for development in developments:
        milestones = development.get("milestones", [])
        if not milestones:
            annotated.append(
                {
                    **development,
                    "nearest_milestone": None,
                    "warning_label": "Monitor",
                    "urgency": "Low",
                    "days_until": None,
                }
            )
            continue
        nearest = None
        for milestone in milestones:
            milestone_date = parse_iso_date(milestone["date"])
            days_until = (milestone_date - as_of).days
            enriched = {**milestone, "days_until": days_until}
            if nearest is None or abs(days_until) < abs(nearest["days_until"]):
                nearest = enriched
        assert nearest is not None
        warning_label, urgency = classify_warning(
            nearest["days_until"],
            nearest.get("kind", ""),
            development.get("stage", ""),
        )
        annotated.append(
            {
                **development,
                "nearest_milestone": nearest,
                "warning_label": warning_label,
                "urgency": urgency,
                "days_until": nearest["days_until"],
            }
        )
    return with_meta(
        "check_deadlines",
        {"as_of": as_of.isoformat(), "developments": annotated},
    )


def render_markdown(output: dict[str, Any]) -> str:
    urgent_count = sum(
        1 for development in output["developments"] if development.get("urgency") in {"Critical", "High"}
    )
    lines = [
        f"# Deadline Check ({output['as_of']})",
        "",
        "| Summary | Value |",
        "|---|---|",
        f"| Developments tracked | {len(output['developments'])} |",
        f"| High/Critical items | {urgent_count} |",
        "",
        "| Framework | Title | Milestone | Days | Warning | Urgency |",
        "|---|---|---|---:|---|---|",
    ]
    for development in output["developments"]:
        nearest = development.get("nearest_milestone")
        if nearest:
            milestone_label = f"{nearest.get('label', 'milestone')} ({nearest.get('date')})"
            days = str(nearest["days_until"])
        else:
            milestone_label = "No milestone"
            days = "-"
        lines.append(
            "| "
            + " | ".join(
                [
                    markdown_cell(development.get("framework", "-")),
                    markdown_cell(development.get("title", "-")),
                    markdown_cell(milestone_label),
                    days,
                    warning_badge(development["warning_label"]),
                    urgency_badge(development["urgency"]),
                ]
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    as_of = parse_iso_date(args.as_of) if args.as_of else date.today()
    data = load_json(args.input)
    output = annotate_developments(data, as_of)
    if args.format == "markdown":
        sys.stdout.write(render_markdown(output))
    else:
        json.dump(output, sys.stdout, indent=2)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
