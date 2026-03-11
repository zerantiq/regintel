"""Shared interface contract metadata for Regintel CLI JSON outputs."""

from __future__ import annotations

from typing import Any

SCHEMA_VERSION = "1.0.0"


def script_meta(tool: str) -> dict[str, str]:
    return {
        "tool": tool,
        "schema_version": SCHEMA_VERSION,
    }


def with_meta(tool: str, payload: dict[str, Any]) -> dict[str, Any]:
    output = {"meta": script_meta(tool)}
    output.update(payload)
    return output

