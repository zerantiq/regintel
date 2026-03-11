#!/usr/bin/env python3
"""Compare two regulatory summaries or scan outputs and report meaningful changes."""

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

COLLECTION_KEYS = ("developments", "signals", "candidate_frameworks", "applicability")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old", required=True, help="Path to the older JSON file.")
    parser.add_argument("--new", required=True, help="Path to the newer JSON file.")
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    return parser.parse_args()


def load_json(path_str: str) -> Any:
    path = Path(path_str)
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def item_key(item: dict[str, Any]) -> str:
    if item.get("id"):
        return str(item["id"])
    if item.get("framework") and item.get("title"):
        return f"{item['framework']}::{item['title']}"
    if item.get("framework") and item.get("display_name"):
        return f"{item['framework']}::{item['display_name']}"
    if item.get("framework"):
        return str(item["framework"])
    if item.get("title"):
        return str(item["title"])
    return json.dumps(item, sort_keys=True)


def canonicalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: canonicalize(val) for key, val in sorted(value.items())}
    if isinstance(value, list):
        return [canonicalize(item) for item in value]
    return value


def summarize_delta(collection: str, old_item: dict[str, Any], new_item: dict[str, Any]) -> str | None:
    if collection == "developments":
        changes = []
        for field in ("stage", "timing", "warning_label", "urgency"):
            if old_item.get(field) != new_item.get(field):
                changes.append(f"{field} {old_item.get(field)!r} -> {new_item.get(field)!r}")
        old_milestone = (old_item.get("nearest_milestone") or {}).get("date")
        new_milestone = (new_item.get("nearest_milestone") or {}).get("date")
        if old_milestone != new_milestone:
            changes.append(f"nearest milestone {old_milestone!r} -> {new_milestone!r}")
        return "; ".join(changes) or None
    if collection in {"candidate_frameworks", "applicability"}:
        changes = []
        old_score = int(old_item.get("score", 0))
        new_score = int(new_item.get("score", 0))
        if abs(new_score - old_score) >= 5:
            changes.append(f"score {old_score} -> {new_score}")
        old_conf = float(old_item.get("confidence", 0.0))
        new_conf = float(new_item.get("confidence", 0.0))
        if abs(new_conf - old_conf) >= 0.05:
            changes.append(f"confidence {old_conf:.2f} -> {new_conf:.2f}")
        old_areas = set(old_item.get("likely_review_areas", []))
        new_areas = set(new_item.get("likely_review_areas", []))
        added = sorted(new_areas - old_areas)
        removed = sorted(old_areas - new_areas)
        if added:
            changes.append(f"review areas added: {', '.join(added)}")
        if removed:
            changes.append(f"review areas removed: {', '.join(removed)}")
        return "; ".join(changes) or None
    if collection == "signals":
        changes = []
        old_evidence = len(old_item.get("evidence", []))
        new_evidence = len(new_item.get("evidence", []))
        if old_evidence != new_evidence:
            changes.append(f"evidence count {old_evidence} -> {new_evidence}")
        old_frameworks = set(old_item.get("frameworks", []))
        new_frameworks = set(new_item.get("frameworks", []))
        if old_frameworks != new_frameworks:
            changes.append("framework mapping changed")
        return "; ".join(changes) or None
    if canonicalize(old_item) != canonicalize(new_item):
        return "item changed"
    return None


def compare_collection(collection: str, old_items: list[dict[str, Any]], new_items: list[dict[str, Any]]) -> dict[str, Any]:
    old_map = {item_key(item): item for item in old_items}
    new_map = {item_key(item): item for item in new_items}
    added_keys = sorted(new_map.keys() - old_map.keys())
    removed_keys = sorted(old_map.keys() - new_map.keys())
    changed = []
    for key in sorted(old_map.keys() & new_map.keys()):
        delta = summarize_delta(collection, old_map[key], new_map[key])
        if delta:
            changed.append({"key": key, "summary": delta})
    return {
        "added": [{"key": key, "item": new_map[key]} for key in added_keys],
        "removed": [{"key": key, "item": old_map[key]} for key in removed_keys],
        "changed": changed,
    }


def extract_collections(data: Any) -> dict[str, list[dict[str, Any]]]:
    if isinstance(data, dict):
        collections = {}
        for key in COLLECTION_KEYS:
            value = data.get(key)
            if isinstance(value, list):
                collections[key] = [item for item in value if isinstance(item, dict)]

        # Snapshot payload compatibility (v0.5+):
        # snapshot files store these collections under nested keys:
        # - scan.signals / scan.candidate_frameworks
        # - applicability.applicability
        # - deadlines.developments
        scan = data.get("scan")
        if isinstance(scan, dict):
            for key in ("signals", "candidate_frameworks"):
                if key in collections:
                    continue
                value = scan.get(key)
                if isinstance(value, list):
                    collections[key] = [item for item in value if isinstance(item, dict)]

        applicability = data.get("applicability")
        if "applicability" not in collections and isinstance(applicability, dict):
            value = applicability.get("applicability")
            if isinstance(value, list):
                collections["applicability"] = [item for item in value if isinstance(item, dict)]

        deadlines = data.get("deadlines")
        if "developments" not in collections and isinstance(deadlines, dict):
            value = deadlines.get("developments")
            if isinstance(value, list):
                collections["developments"] = [item for item in value if isinstance(item, dict)]
        return collections
    return {}


def build_diff(old_data: Any, new_data: Any) -> dict[str, Any]:
    old_collections = extract_collections(old_data)
    new_collections = extract_collections(new_data)
    collections = {}
    for key in COLLECTION_KEYS:
        collections[key] = compare_collection(
            key,
            old_collections.get(key, []),
            new_collections.get(key, []),
        )
    return with_meta("change_diff", {"collections": collections})


def render_markdown(diff: dict[str, Any]) -> str:
    lines = ["# Change Diff", ""]
    for collection, changes in diff["collections"].items():
        total = len(changes["added"]) + len(changes["removed"]) + len(changes["changed"])
        if total == 0:
            continue
        lines.append(f"## {collection.replace('_', ' ').title()}")
        for item in changes["added"]:
            lines.append(f"- Added `{item['key']}`")
        for item in changes["removed"]:
            lines.append(f"- Removed `{item['key']}`")
        for item in changes["changed"]:
            lines.append(f"- Changed `{item['key']}`: {item['summary']}")
        lines.append("")
    if len(lines) == 2:
        lines.append("No changes detected.")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    old_data = load_json(args.old)
    new_data = load_json(args.new)
    diff = build_diff(old_data, new_data)
    if args.format == "markdown":
        sys.stdout.write(render_markdown(diff))
    else:
        json.dump(diff, sys.stdout, indent=2)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
