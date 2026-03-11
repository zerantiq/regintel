#!/usr/bin/env python3
"""Structured code analysis for regulatory compliance using AST-based scanning.

Complements repo_signal_scan.py with function-level analysis of Python source files.
Detects patterns that regex-based scanning cannot reliably find:

  - PII field names used in function return values
  - Database write calls without adjacent audit logging
  - File or storage write calls without encryption indicators

Usage:
  python3 ast_signal_scan.py --path /path/to/repo
  python3 ast_signal_scan.py --path /path/to/repo --format markdown
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PII_FIELD_NAMES: frozenset[str] = frozenset(
    {
        "email",
        "phone",
        "address",
        "first_name",
        "last_name",
        "full_name",
        "dob",
        "birth_date",
        "birthdate",
        "date_of_birth",
        "ip_address",
        "ssn",
        "social_security",
        "passport_number",
        "national_id",
        "tax_id",
        "credit_card",
        "card_number",
    }
)

# Database write method names that indicate data mutation
DB_WRITE_METHOD_NAMES: frozenset[str] = frozenset(
    {
        "save",
        "insert",
        "insert_one",
        "insert_many",
        "create",
        "update",
        "update_one",
        "update_many",
        "delete",
        "delete_one",
        "delete_many",
        "upsert",
        "bulk_create",
        "bulk_update",
        "bulk_insert",
        "execute",
        "executemany",
        "commit",
    }
)

# Logging method names that indicate audit or traceability
LOG_METHOD_NAMES: frozenset[str] = frozenset(
    {
        "log",
        "info",
        "warning",
        "warn",
        "error",
        "debug",
        "critical",
        "audit_log",
        "audit",
    }
)

# File open modes that write data
STORAGE_WRITE_MODES: frozenset[str] = frozenset({"w", "wb", "a", "ab", "x", "xb"})

# Storage SDK method names that upload data
STORAGE_WRITE_METHODS: frozenset[str] = frozenset(
    {"put_object", "upload_file", "upload_fileobj", "put", "write_file"}
)

# Encryption-related names that indicate the write is protected
ENCRYPT_INDICATORS: frozenset[str] = frozenset(
    {
        "ServerSideEncryption",
        "SSEAlgorithm",
        "KMSKeyId",
        "encrypt",
        "encryption",
        "encrypted",
        "sse",
        "aes",
        "kms",
        "fernet",
        "cryptography",
    }
)

EXCLUDED_DIRS: set[str] = {
    ".git",
    "node_modules",
    "vendor",
    "dist",
    "build",
    ".next",
    "__pycache__",
    ".pytest_cache",
    "coverage",
    ".turbo",
    "target",
    "tmp",
    "temp",
}

MAX_FILE_BYTES = 1_000_000

# ---------------------------------------------------------------------------
# AST utilities
# ---------------------------------------------------------------------------


def walk_no_nested_funcs(node: ast.AST) -> Iterator[ast.AST]:
    """Yield all descendant nodes without descending into nested function bodies.

    This ensures patterns are checked at the function level rather than leaking
    context across function boundaries.
    """
    yield node
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        yield from walk_no_nested_funcs(child)


def extract_call_method(call: ast.Call) -> tuple[str | None, str | None]:
    """Return (object_name, method_name) for a Call node, or (None, None) when not resolvable."""
    func = call.func
    if isinstance(func, ast.Attribute):
        obj = func.value.id if isinstance(func.value, ast.Name) else None
        return obj, func.attr
    if isinstance(func, ast.Name):
        return None, func.id
    return None, None


def dict_pii_keys(node: ast.Dict) -> list[str]:
    """Return all string literal keys from a Dict node that match PII field names."""
    result = []
    for key in node.keys:
        if isinstance(key, ast.Constant) and isinstance(key.value, str):
            if key.value.lower() in PII_FIELD_NAMES:
                result.append(key.value)
    return result


def node_has_encrypt_indicator(nodes: list[ast.AST]) -> bool:
    """Return True if any node in the list contains an encryption-related identifier."""
    for node in nodes:
        if isinstance(node, ast.Name) and node.id.lower() in {
            ind.lower() for ind in ENCRYPT_INDICATORS
        }:
            return True
        if isinstance(node, ast.Attribute) and node.attr in ENCRYPT_INDICATORS:
            return True
        if isinstance(node, ast.keyword) and node.arg and node.arg in ENCRYPT_INDICATORS:
            return True
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            low = node.value.lower()
            if any(ind.lower() in low for ind in ENCRYPT_INDICATORS):
                return True
    return False


def make_relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


# ---------------------------------------------------------------------------
# Structural finders
# ---------------------------------------------------------------------------


def find_pii_in_return(
    func: ast.FunctionDef | ast.AsyncFunctionDef,
    path: Path,
    root: Path,
) -> list[dict[str, Any]]:
    """Flag functions that return PII field names in dict literals or attribute access."""
    findings: list[dict[str, Any]] = []
    rel_path = make_relative(path, root)

    for node in walk_no_nested_funcs(func):
        if not isinstance(node, ast.Return) or node.value is None:
            continue
        value = node.value

        # return {"email": x, "phone": y}
        if isinstance(value, ast.Dict):
            pii_keys = dict_pii_keys(value)
            if pii_keys:
                findings.append(
                    {
                        "id": "pii-in-return-value",
                        "severity": "medium",
                        "title": "PII field returned from function",
                        "frameworks": ["gdpr", "us-state-privacy", "hipaa"],
                        "evidence": [
                            {
                                "path": rel_path,
                                "line": node.lineno,
                                "function": func.name,
                                "detail": (
                                    f"Returns dict with PII keys: {', '.join(sorted(pii_keys))}"
                                ),
                                "finding_class": "ast",
                            }
                        ],
                    }
                )

        # return user.email
        elif isinstance(value, ast.Attribute) and value.attr.lower() in PII_FIELD_NAMES:
            findings.append(
                {
                    "id": "pii-in-return-value",
                    "severity": "medium",
                    "title": "PII field returned from function",
                    "frameworks": ["gdpr", "us-state-privacy", "hipaa"],
                    "evidence": [
                        {
                            "path": rel_path,
                            "line": node.lineno,
                            "function": func.name,
                            "detail": f"Returns PII attribute: .{value.attr}",
                            "finding_class": "ast",
                        }
                    ],
                }
            )

        # return email
        elif isinstance(value, ast.Name) and value.id.lower() in PII_FIELD_NAMES:
            findings.append(
                {
                    "id": "pii-in-return-value",
                    "severity": "medium",
                    "title": "PII field returned from function",
                    "frameworks": ["gdpr", "us-state-privacy", "hipaa"],
                    "evidence": [
                        {
                            "path": rel_path,
                            "line": node.lineno,
                            "function": func.name,
                            "detail": f"Returns variable with PII name: {value.id}",
                            "finding_class": "ast",
                        }
                    ],
                }
            )

    return findings


def find_unlogged_db_writes(
    func: ast.FunctionDef | ast.AsyncFunctionDef,
    path: Path,
    root: Path,
) -> list[dict[str, Any]]:
    """Flag functions with database write calls that have no logging call in scope."""
    rel_path = make_relative(path, root)
    db_write_calls: list[tuple[int, str]] = []
    has_logging = False

    for node in walk_no_nested_funcs(func):
        if not isinstance(node, ast.Call):
            continue
        _, method = extract_call_method(node)
        if method is None:
            continue
        if method.lower() in DB_WRITE_METHOD_NAMES:
            db_write_calls.append((node.lineno, method))
        if method.lower() in LOG_METHOD_NAMES:
            has_logging = True

    if not db_write_calls or has_logging:
        return []

    line_no, method_name = db_write_calls[0]
    extra = len(db_write_calls) - 1
    detail = (
        f"Calls .{method_name}() (plus {extra} more DB write(s)) without a logging call."
        if extra
        else f"Calls .{method_name}() without a logging call."
    )
    return [
        {
            "id": "unlogged-db-write",
            "severity": "medium",
            "title": "Database write without audit logging",
            "frameworks": ["gdpr", "hipaa", "sox", "sec-cyber-disclosure"],
            "evidence": [
                {
                    "path": rel_path,
                    "line": line_no,
                    "function": func.name,
                    "detail": detail,
                    "finding_class": "ast",
                }
            ],
        }
    ]


def find_unencrypted_storage_writes(
    func: ast.FunctionDef | ast.AsyncFunctionDef,
    path: Path,
    root: Path,
) -> list[dict[str, Any]]:
    """Flag functions that write to files or storage without encryption indicators."""
    rel_path = make_relative(path, root)
    write_calls: list[tuple[int, str]] = []
    all_nodes = list(walk_no_nested_funcs(func))

    for node in all_nodes:
        if not isinstance(node, ast.Call):
            continue
        obj, method = extract_call_method(node)

        # open() called with a write-mode positional or keyword argument
        if method == "open" and obj is None:
            for arg in node.args[1:2]:  # second positional arg is mode
                if isinstance(arg, ast.Constant) and arg.value in STORAGE_WRITE_MODES:
                    write_calls.append((node.lineno, "open(write-mode)"))
            for kw in node.keywords:
                if (
                    kw.arg == "mode"
                    and isinstance(kw.value, ast.Constant)
                    and kw.value.value in STORAGE_WRITE_MODES
                ):
                    write_calls.append((node.lineno, "open(write-mode)"))

        # Storage SDK write methods (S3, GCS, etc.)
        if method in STORAGE_WRITE_METHODS:
            write_calls.append((node.lineno, method))

    if not write_calls:
        return []

    if node_has_encrypt_indicator(all_nodes):
        return []

    line_no, call_desc = write_calls[0]
    return [
        {
            "id": "unencrypted-storage-write",
            "severity": "medium",
            "title": "Storage write without encryption indicator",
            "frameworks": ["gdpr", "hipaa", "dora", "nis2"],
            "evidence": [
                {
                    "path": rel_path,
                    "line": line_no,
                    "function": func.name,
                    "detail": (
                        f"Calls {call_desc} without detected encryption indicator in scope."
                    ),
                    "finding_class": "ast",
                }
            ],
        }
    ]


# ---------------------------------------------------------------------------
# File and repo scanning
# ---------------------------------------------------------------------------


def scan_python_file(path: Path, root: Path) -> list[dict[str, Any]]:
    """Run all structural finders over a single Python file."""
    try:
        source = path.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return []

    findings: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        findings.extend(find_pii_in_return(node, path, root))
        findings.extend(find_unlogged_db_writes(node, path, root))
        findings.extend(find_unencrypted_storage_writes(node, path, root))
    return findings


def collect_python_files(base_path: Path) -> tuple[list[Path], Path]:
    """Collect scannable Python source files from base_path."""
    root = base_path if base_path.is_dir() else base_path.parent
    files: list[Path] = []
    if base_path.is_file():
        if base_path.suffix == ".py" and base_path.stat().st_size <= MAX_FILE_BYTES:
            files.append(base_path)
        return files, root
    for dirpath, dirnames, filenames in os.walk(base_path):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]
        for filename in filenames:
            path = Path(dirpath) / filename
            if path.suffix == ".py" and path.stat().st_size <= MAX_FILE_BYTES:
                files.append(path)
    return files, root


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------


def render_markdown(findings: list[dict[str, Any]], scan_meta: dict[str, Any]) -> str:
    lines = [
        "## AST Structural Scan",
        "",
        (
            f"Scanned **{scan_meta['python_files']}** Python file(s), "
            f"found **{scan_meta['finding_count']}** structural finding(s)."
        ),
        "",
    ]
    if not findings:
        lines.append("No structural findings detected.")
        return "\n".join(lines)

    for finding in findings:
        lines.append(f"### {finding['title']}")
        lines.append(f"- **Severity**: {finding['severity']}")
        lines.append(f"- **Frameworks**: {', '.join(finding['frameworks'])}")
        for ev in finding["evidence"]:
            lines.append(
                f"- **Location**: `{ev['path']}:{ev['line']}` in `{ev['function']}`"
            )
            lines.append(f"- **Detail**: {ev['detail']}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", required=True, help="Repo root or file to scan.")
    parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
        help="Output format (default: json).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    base_path = Path(args.path)
    if not base_path.exists():
        print(json.dumps({"error": f"Path not found: {base_path}"}))
        return 1

    python_files, root = collect_python_files(base_path)
    all_findings: list[dict[str, Any]] = []
    for path in python_files:
        all_findings.extend(scan_python_file(path, root))

    scan_meta: dict[str, Any] = {
        "path": str(base_path),
        "python_files": len(python_files),
        "finding_count": len(all_findings),
        "ast_method": "python-ast",
    }

    if args.format == "markdown":
        print(render_markdown(all_findings, scan_meta))
        return 0

    output: dict[str, Any] = {
        "scan": scan_meta,
        "structural_findings": all_findings,
    }
    json.dump(output, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
