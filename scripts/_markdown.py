"""Shared helpers for polished markdown report rendering."""

from __future__ import annotations


SEVERITY_EMOJI = {
    "critical": "🚨",
    "high": "🔴",
    "medium": "🟠",
    "low": "🟡",
    "info": "🔵",
}

URGENCY_EMOJI = {
    "critical": "🚨",
    "high": "🔴",
    "medium": "🟠",
    "low": "🟢",
}

WARNING_EMOJI = {
    "critical deadline": "🚨",
    "high priority": "🔴",
    "action needed soon": "🟠",
    "upcoming change": "🟡",
    "monitor": "🟢",
}

STATUS_EMOJI = {
    "pass": "✅",
    "passed": "✅",
    "success": "✅",
    "ok": "✅",
    "fail": "❌",
    "failed": "❌",
    "error": "❌",
    "warn": "⚠️",
    "warning": "⚠️",
    "changed": "✏️",
    "added": "➕",
    "removed": "➖",
    "unknown": "⚪",
}


def _clean_label(value: str) -> str:
    return value.replace("-", " ").replace("_", " ").strip().title()


def markdown_cell(value: object) -> str:
    if value is None:
        return "-"
    text = str(value).replace("\n", "<br>")
    return text.replace("|", "\\|")


def severity_badge(level: str) -> str:
    normalized = str(level or "").strip().lower()
    return f"{SEVERITY_EMOJI.get(normalized, '⚪')} {_clean_label(normalized or 'unknown')}"


def urgency_badge(level: str) -> str:
    normalized = str(level or "").strip().lower()
    return f"{URGENCY_EMOJI.get(normalized, '⚪')} {_clean_label(normalized or 'unknown')}"


def warning_badge(label: str) -> str:
    normalized = str(label or "").strip().lower()
    return f"{WARNING_EMOJI.get(normalized, '⚪')} {_clean_label(normalized or 'unknown')}"


def status_badge(status: str) -> str:
    normalized = str(status or "").strip().lower()
    return f"{STATUS_EMOJI.get(normalized, '⚪')} {_clean_label(normalized or 'unknown')}"


def bool_badge(value: bool) -> str:
    return "✅ Yes" if value else "❌ No"


def score_badge(score: int | float) -> str:
    numeric = float(score)
    if numeric >= 80:
        return "🔴 High"
    if numeric >= 60:
        return "🟠 Elevated"
    if numeric >= 40:
        return "🟡 Watch"
    return "🟢 Low"


def confidence_badge(confidence: int | float) -> str:
    numeric = float(confidence)
    if numeric >= 0.8:
        return f"🟢 {numeric:.2f}"
    if numeric >= 0.6:
        return f"🟡 {numeric:.2f}"
    return f"🟠 {numeric:.2f}"


def delta_badge(delta: int | float) -> str:
    numeric = float(delta)
    if numeric.is_integer():
        label = f"{numeric:+.0f}"
    else:
        label = f"{numeric:+.2f}"
    if numeric > 0:
        return f"⬆️ {label}"
    if numeric < 0:
        return f"⬇️ {label}"
    return "➖ 0"
