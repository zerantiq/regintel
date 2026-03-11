#!/usr/bin/env python3
"""Sync regulatory feed items into developments JSON schema."""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    from ._contract import with_meta
except ImportError:
    from _contract import with_meta  # type: ignore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="Path to feed-sync config JSON.")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--output", help="Optional path to write output JSON/markdown.")
    return parser.parse_args()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "item"


def parse_date(raw: str | None) -> str | None:
    if not raw:
        return None
    value = raw.strip()
    if not value:
        return None

    candidates = [value]
    if value.endswith("Z"):
        candidates.append(value[:-1] + "+00:00")
    for candidate in candidates:
        try:
            dt = datetime.fromisoformat(candidate)
            if dt.tzinfo is None:
                return dt.date().isoformat()
            return dt.astimezone(timezone.utc).date().isoformat()
        except ValueError:
            pass

    try:
        return parsedate_to_datetime(value).date().isoformat()
    except (TypeError, ValueError):
        pass

    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def get_nested(obj: Any, field: str) -> Any:
    if not isinstance(obj, dict):
        return None
    if "." not in field:
        return obj.get(field)
    current: Any = obj
    for part in field.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def localname(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def load_source_text(source: str, config_dir: Path) -> str:
    parsed = urlparse(source)
    if parsed.scheme in {"http", "https"}:
        with urllib.request.urlopen(source, timeout=15) as response:
            return response.read().decode("utf-8", errors="ignore")
    if parsed.scheme == "file":
        path = Path(parsed.path)
    else:
        raw = Path(source)
        path = raw if raw.is_absolute() else (config_dir / raw)
    return path.read_text(encoding="utf-8")


def detect_format(raw_text: str, explicit: str | None, source: str) -> str:
    if explicit in {"json", "rss", "atom"}:
        return explicit
    text = raw_text.lstrip()
    if text.startswith("{") or text.startswith("["):
        return "json"
    if "<rss" in text.lower():
        return "rss"
    if "<feed" in text.lower():
        return "atom"
    lowered = source.lower()
    if lowered.endswith(".json"):
        return "json"
    if lowered.endswith(".xml") or lowered.endswith(".rss"):
        return "rss"
    return "json"


def json_items(payload: Any, items_path: str | None) -> list[dict[str, Any]]:
    current = payload
    if items_path:
        for part in items_path.split("."):
            if isinstance(current, dict):
                current = current.get(part)
            else:
                current = None
                break
    elif isinstance(payload, dict):
        for key in ("items", "entries", "developments"):
            if isinstance(payload.get(key), list):
                current = payload.get(key)
                break
    if not isinstance(current, list):
        return []
    return [item for item in current if isinstance(item, dict)]


def parse_json_feed(raw_text: str, feed_cfg: dict[str, Any], max_items: int) -> list[dict[str, Any]]:
    payload = json.loads(raw_text)
    items = json_items(payload, str(feed_cfg.get("items_path")) if feed_cfg.get("items_path") else None)
    title_field = str(feed_cfg.get("title_field", "title"))
    date_field = str(feed_cfg.get("date_field", "date"))
    id_field = str(feed_cfg.get("id_field", "id"))
    link_field = str(feed_cfg.get("link_field", "url"))
    normalized: list[dict[str, Any]] = []
    for item in items[:max_items]:
        title = get_nested(item, title_field)
        raw_date = get_nested(item, date_field)
        if not isinstance(title, str):
            continue
        date_iso = parse_date(str(raw_date) if raw_date is not None else "")
        if not date_iso:
            continue
        item_id = get_nested(item, id_field)
        link = get_nested(item, link_field)
        normalized.append(
            {
                "id": str(item_id) if item_id else f"{feed_cfg['id']}::{slugify(title)}::{date_iso}",
                "title": title.strip(),
                "date": date_iso,
                "link": str(link) if link else None,
            }
        )
    return normalized


def first_child_text(node: ET.Element, names: tuple[str, ...]) -> str | None:
    for child in node.iter():
        lname = localname(child.tag).lower()
        if lname in names and child.text and child.text.strip():
            return child.text.strip()
    return None


def parse_xml_feed(raw_text: str, feed_cfg: dict[str, Any], max_items: int) -> list[dict[str, Any]]:
    root = ET.fromstring(raw_text)
    root_name = localname(root.tag).lower()
    candidates: list[ET.Element] = []
    if root_name == "rss":
        for channel in root:
            if localname(channel.tag).lower() == "channel":
                candidates.extend([item for item in channel if localname(item.tag).lower() == "item"])
    elif root_name == "feed":
        candidates = [entry for entry in root if localname(entry.tag).lower() == "entry"]
    else:
        candidates = [node for node in root.iter() if localname(node.tag).lower() in {"item", "entry"}]

    normalized: list[dict[str, Any]] = []
    for node in candidates[:max_items]:
        title = first_child_text(node, ("title",))
        raw_date = first_child_text(node, ("published", "updated", "pubdate", "date"))
        if not title or not raw_date:
            continue
        date_iso = parse_date(raw_date)
        if not date_iso:
            continue

        link_text = None
        for child in node:
            if localname(child.tag).lower() != "link":
                continue
            href = child.attrib.get("href")
            link_text = href or (child.text.strip() if child.text else None)
            if link_text:
                break

        normalized.append(
            {
                "id": f"{feed_cfg['id']}::{slugify(title)}::{date_iso}",
                "title": title,
                "date": date_iso,
                "link": link_text,
            }
        )
    return normalized


def normalize_feed_items(feed_cfg: dict[str, Any], items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    framework = str(feed_cfg.get("framework", "Unknown Framework"))
    stage = str(feed_cfg.get("stage", "adopted"))
    timing = str(feed_cfg.get("timing", "upcoming"))
    milestone_kind = str(feed_cfg.get("milestone_kind", "effective"))
    milestone_label = str(feed_cfg.get("milestone_label", "feed-update"))

    normalized = []
    for item in items:
        normalized.append(
            {
                "id": item["id"],
                "framework": framework,
                "title": item["title"],
                "stage": stage,
                "timing": timing,
                "source": feed_cfg["id"],
                "source_url": item.get("link"),
                "milestones": [{"label": milestone_label, "date": item["date"], "kind": milestone_kind}],
            }
        )
    return normalized


def merge_developments(existing: list[dict[str, Any]], updates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for item in existing:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id", f"{item.get('framework', '')}::{item.get('title', '')}"))
        merged[item_id] = item
    for item in updates:
        item_id = str(item.get("id", f"{item.get('framework', '')}::{item.get('title', '')}"))
        merged[item_id] = item
    return sorted(
        merged.values(),
        key=lambda item: (
            str(item.get("framework", "")),
            str(item.get("title", "")),
            str((item.get("milestones") or [{}])[0].get("date", "")),
        ),
    )


def render_markdown(output: dict[str, Any]) -> str:
    lines = [
        "# Regulatory Feed Sync",
        "",
        f"- Generated at: `{output['generated_at']}`",
        f"- Feeds processed: {output['feed_count']}",
        f"- Developments available: {len(output['developments'])}",
        "",
        "| Framework | Title | Milestone Date | Source |",
        "|---|---|---|---|",
    ]
    for item in output["developments"][:40]:
        milestones = item.get("milestones", [])
        date = milestones[0].get("date") if milestones else "-"
        lines.append(f"| {item.get('framework', '-')} | {item.get('title', '-')} | {date} | {item.get('source', '-')} |")
    if output.get("errors"):
        lines.append("")
        lines.append("## Errors")
        for err in output["errors"]:
            lines.append(f"- {err}")
    return "\n".join(lines) + "\n"


def write_output(content: str, output_path: str | None) -> None:
    if not output_path:
        sys.stdout.write(content)
        return
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    args = parse_args()
    config_path = Path(args.config)
    config = load_json(config_path)
    if not isinstance(config, dict):
        raise ValueError("Feed config must be a JSON object.")

    config_dir = config_path.parent
    feeds = config.get("feeds", [])
    if not isinstance(feeds, list):
        raise ValueError("feeds must be a list.")
    max_items = int(config.get("max_items_per_feed", 25))

    all_updates: list[dict[str, Any]] = []
    errors: list[str] = []
    for raw_feed in feeds:
        if not isinstance(raw_feed, dict):
            continue
        if "id" not in raw_feed or "source" not in raw_feed:
            errors.append("Feed entry missing required fields: id, source.")
            continue
        feed_cfg = dict(raw_feed)
        feed_cfg["id"] = str(feed_cfg["id"])
        feed_cfg["source"] = str(feed_cfg["source"])
        try:
            source_text = load_source_text(feed_cfg["source"], config_dir)
            fmt = detect_format(source_text, str(feed_cfg.get("format")) if feed_cfg.get("format") else None, feed_cfg["source"])
            if fmt == "json":
                raw_items = parse_json_feed(source_text, feed_cfg, max_items)
            else:
                raw_items = parse_xml_feed(source_text, feed_cfg, max_items)
            all_updates.extend(normalize_feed_items(feed_cfg, raw_items))
        except Exception as exc:  # pragma: no cover - defensive, exercised in integration use
            errors.append(f"{feed_cfg['id']}: {exc}")

    merge_with = config.get("merge_with")
    existing: list[dict[str, Any]] = []
    if isinstance(merge_with, str) and merge_with:
        merge_path = Path(merge_with)
        if not merge_path.is_absolute():
            merge_path = config_dir / merge_path
        if merge_path.exists():
            merged_source = load_json(merge_path)
            if isinstance(merged_source, dict) and isinstance(merged_source.get("developments"), list):
                existing = [item for item in merged_source["developments"] if isinstance(item, dict)]
            elif isinstance(merged_source, list):
                existing = [item for item in merged_source if isinstance(item, dict)]

    developments = merge_developments(existing, all_updates)
    output = with_meta(
        "sync_regulatory_feeds",
        {
            "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "feed_count": len([feed for feed in feeds if isinstance(feed, dict)]),
            "item_count": len(all_updates),
            "developments": developments,
            "errors": errors,
        },
    )

    if args.format == "markdown":
        write_output(render_markdown(output), args.output)
    else:
        serialized = json.dumps(output, indent=2) + "\n"
        write_output(serialized, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
