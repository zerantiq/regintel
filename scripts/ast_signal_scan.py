#!/usr/bin/env python3
"""Structured code analysis for regulatory compliance using AST-style scanning.

Complements repo_signal_scan.py with function-level structural analysis across:
  - Python (stdlib AST parsing)
  - TypeScript (function-block structural patterns)
  - Java (method-block structural patterns)
  - Go (function-block structural patterns)
  - .NET/C# (method-block structural patterns)

Detects patterns that regex-only repository scanning cannot reliably find:
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
import concurrent.futures
import json
import os
import re
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from ._contract import with_meta
    from ._markdown import markdown_cell, severity_badge
    from ._scan_cache import (
        default_parallel_workers,
        file_fingerprint,
        load_scan_cache,
        save_scan_cache,
    )
except ImportError:
    from _contract import with_meta  # type: ignore
    from _markdown import markdown_cell, severity_badge  # type: ignore
    from _scan_cache import (  # type: ignore
        default_parallel_workers,
        file_fingerprint,
        load_scan_cache,
        save_scan_cache,
    )

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

# Database write method names that indicate data mutation.
DB_WRITE_METHOD_NAMES: frozenset[str] = frozenset(
    {
        "save",
        "insert",
        "insert_one",
        "insert_many",
        "insertOne",
        "insertMany",
        "create",
        "update",
        "update_one",
        "update_many",
        "updateOne",
        "updateMany",
        "delete",
        "delete_one",
        "delete_many",
        "deleteOne",
        "deleteMany",
        "upsert",
        "bulk_create",
        "bulk_update",
        "bulk_insert",
        "bulkCreate",
        "bulkUpdate",
        "bulkInsert",
        "execute",
        "executemany",
        "exec",
        "commit",
    }
)

# Logging method names that indicate audit or traceability.
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
        "auditLog",
        "audit",
        "printf",
        "println",
    }
)

# File open modes that write data.
STORAGE_WRITE_MODES: frozenset[str] = frozenset({"w", "wb", "a", "ab", "x", "xb"})

# Storage SDK and language runtime method names that upload or write data.
STORAGE_WRITE_METHODS: frozenset[str] = frozenset(
    {
        "put_object",
        "putObject",
        "upload_file",
        "uploadFile",
        "upload_fileobj",
        "uploadFileObj",
        "put",
        "write_file",
        "writeFile",
        "writeFileSync",
        "createWriteStream",
        "WriteFile",
        "WriteAllText",
        "WriteAllBytes",
        "AppendAllText",
        "FileOutputStream",
        "BufferedWriter",
        "PrintWriter",
    }
)

# Encryption-related names that indicate the write is protected.
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
        "cipher",
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

LANGUAGE_SUFFIXES: dict[str, tuple[str, ...]] = {
    "python": (".py",),
    "typescript": (".ts", ".tsx"),
    "java": (".java",),
    "go": (".go",),
    "csharp": (".cs",),
}

LANGUAGE_DISPLAY: dict[str, str] = {
    "python": "Python",
    "typescript": "TypeScript",
    "java": "Java",
    "go": "Go",
    "csharp": ".NET/C#",
}

STRUCTURAL_METHODS: dict[str, str] = {
    "python": "python-ast",
    "typescript": "typescript-brace-patterns",
    "java": "java-brace-patterns",
    "go": "go-brace-patterns",
    "csharp": "csharp-brace-patterns",
}

MAX_FILE_BYTES = 1_000_000
DEFAULT_WORKERS = default_parallel_workers(cap=8)
AST_SCAN_CACHE_VERSION = "ast_signal_scan.v0.9.0"

PII_TOKEN_PATTERN = "|".join(
    sorted((re.escape(name) for name in PII_FIELD_NAMES), key=len, reverse=True)
)
PII_KEY_RE = re.compile(
    rf"(?:['\"](?P<quoted>{PII_TOKEN_PATTERN})['\"]|(?P<plain>{PII_TOKEN_PATTERN}))\s*:",
    re.IGNORECASE,
)
RETURN_EXPR_PII_RE = re.compile(
    rf"\breturn\b[^\n;]*\b(?P<field>{PII_TOKEN_PATTERN})\b",
    re.IGNORECASE,
)
RETURN_OBJECT_PII_RE = re.compile(
    rf"\breturn\b[\s\S]*?\{{[\s\S]*?\b(?P<field>{PII_TOKEN_PATTERN})\b[\s\S]*?\}}",
    re.IGNORECASE,
)
OPEN_WRITE_MODE_RE = re.compile(
    r"""open\s*\([^,\n]+,\s*['"](?:w|wb|a|ab|x|xb)\+?['"]""",
    re.IGNORECASE,
)
CALL_TOKEN_RE = re.compile(r"\b(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\(")
OS_CREATE_RE = re.compile(r"\bos\.Create\s*\(", re.IGNORECASE)
STRING_LITERAL_RE = re.compile(r"""(["'`])(?:\\.|(?!\1).)*\1""")

CONTROL_FLOW_NAMES: frozenset[str] = frozenset(
    {"if", "for", "while", "switch", "catch", "try", "do", "else", "return"}
)

TS_FUNCTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"^\s*(?:export\s+)?(?:async\s+)?function\s+(?P<name>[A-Za-z_$][\w$]*)\s*\([^)]*\)\s*(?::[^{]+)?\{"
    ),
    re.compile(
        r"^\s*(?:export\s+)?(?:const|let|var)\s+(?P<name>[A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\([^)]*\)\s*(?::[^=]+)?=>\s*\{"
    ),
    re.compile(
        r"^\s*(?:public|private|protected)?\s*(?:async\s+)?(?P<name>[A-Za-z_$][\w$]*)\s*\([^)]*\)\s*(?::[^{]+)?\{"
    ),
)

JAVA_FUNCTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"^\s*(?:public|private|protected)?\s*(?:static\s+)?(?:final\s+)?(?:synchronized\s+)?[\w<>\[\], ?]+\s+(?P<name>[A-Za-z_]\w*)\s*\([^;]*\)\s*(?:throws[^{]+)?\{"
    ),
)

GO_FUNCTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"^\s*func\s*(?:\([^)]+\)\s*)?(?P<name>[A-Za-z_]\w*)\s*\([^)]*\)\s*(?:\([^)]*\)|[^{\n]+)?\s*\{"
    ),
)

C_SHARP_FUNCTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"^\s*(?:public|private|protected|internal)?\s*(?:static\s+)?(?:async\s+)?(?:[\w<>\[\], ?]+\s+)?(?P<name>[A-Za-z_]\w*)\s*\([^;]*\)\s*(?:\{|$)"
    ),
)

LANGUAGE_FUNCTION_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "typescript": TS_FUNCTION_PATTERNS,
    "java": JAVA_FUNCTION_PATTERNS,
    "go": GO_FUNCTION_PATTERNS,
    "csharp": C_SHARP_FUNCTION_PATTERNS,
}

ENCRYPT_INDICATORS_LOWER: frozenset[str] = frozenset(ind.lower() for ind in ENCRYPT_INDICATORS)


@dataclass(frozen=True)
class FunctionBlock:
    name: str
    start_line: int
    lines: tuple[str, ...]
    language: str


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def normalize_identifier(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


DB_WRITE_METHOD_KEYS: frozenset[str] = frozenset(
    normalize_identifier(name) for name in DB_WRITE_METHOD_NAMES
)
LOG_METHOD_KEYS: frozenset[str] = frozenset(normalize_identifier(name) for name in LOG_METHOD_NAMES)
STORAGE_WRITE_METHOD_KEYS: frozenset[str] = frozenset(
    normalize_identifier(name) for name in STORAGE_WRITE_METHODS
)


def make_relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def make_finding(
    *,
    finding_id: str,
    severity: str,
    title: str,
    frameworks: list[str],
    rel_path: str,
    line: int,
    function: str,
    detail: str,
) -> dict[str, Any]:
    return {
        "id": finding_id,
        "severity": severity,
        "title": title,
        "frameworks": frameworks,
        "evidence": [
            {
                "path": rel_path,
                "line": line,
                "function": function,
                "detail": detail,
                "finding_class": "ast",
            }
        ],
    }


def strip_strings(line: str) -> str:
    return STRING_LITERAL_RE.sub("", line)


def brace_delta(line: str) -> int:
    cleaned = strip_strings(line)
    return cleaned.count("{") - cleaned.count("}")


def contains_encryption_indicator(text: str) -> bool:
    low = text.lower()
    return any(ind in low for ind in ENCRYPT_INDICATORS_LOWER)


def extract_call_tokens(line: str) -> list[str]:
    return [match.group("name") for match in CALL_TOKEN_RE.finditer(line)]


# ---------------------------------------------------------------------------
# Python AST utilities
# ---------------------------------------------------------------------------


def walk_no_nested_funcs(node: ast.AST) -> Iterator[ast.AST]:
    """Yield all descendant nodes without descending into nested function bodies."""
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
        if isinstance(node, ast.Name) and node.id.lower() in ENCRYPT_INDICATORS_LOWER:
            return True
        if isinstance(node, ast.Attribute) and node.attr.lower() in ENCRYPT_INDICATORS_LOWER:
            return True
        if (
            isinstance(node, ast.keyword)
            and node.arg
            and normalize_identifier(node.arg) in ENCRYPT_INDICATORS_LOWER
        ):
            return True
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            low = node.value.lower()
            if any(ind in low for ind in ENCRYPT_INDICATORS_LOWER):
                return True
    return False


# ---------------------------------------------------------------------------
# Python structural finders
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

        if isinstance(value, ast.Dict):
            pii_keys = dict_pii_keys(value)
            if pii_keys:
                findings.append(
                    make_finding(
                        finding_id="pii-in-return-value",
                        severity="medium",
                        title="PII field returned from function",
                        frameworks=["gdpr", "us-state-privacy", "hipaa"],
                        rel_path=rel_path,
                        line=node.lineno,
                        function=func.name,
                        detail=f"Returns dict with PII keys: {', '.join(sorted(pii_keys))}",
                    )
                )

        elif isinstance(value, ast.Attribute) and value.attr.lower() in PII_FIELD_NAMES:
            findings.append(
                make_finding(
                    finding_id="pii-in-return-value",
                    severity="medium",
                    title="PII field returned from function",
                    frameworks=["gdpr", "us-state-privacy", "hipaa"],
                    rel_path=rel_path,
                    line=node.lineno,
                    function=func.name,
                    detail=f"Returns PII attribute: .{value.attr}",
                )
            )

        elif isinstance(value, ast.Name) and value.id.lower() in PII_FIELD_NAMES:
            findings.append(
                make_finding(
                    finding_id="pii-in-return-value",
                    severity="medium",
                    title="PII field returned from function",
                    frameworks=["gdpr", "us-state-privacy", "hipaa"],
                    rel_path=rel_path,
                    line=node.lineno,
                    function=func.name,
                    detail=f"Returns variable with PII name: {value.id}",
                )
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
        method_key = normalize_identifier(method)
        if method_key in DB_WRITE_METHOD_KEYS:
            db_write_calls.append((node.lineno, method))
        if method_key in LOG_METHOD_KEYS:
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
        make_finding(
            finding_id="unlogged-db-write",
            severity="medium",
            title="Database write without audit logging",
            frameworks=["gdpr", "hipaa", "sox", "sec-cyber-disclosure"],
            rel_path=rel_path,
            line=line_no,
            function=func.name,
            detail=detail,
        )
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

        if method == "open" and obj is None:
            for arg in node.args[1:2]:
                if isinstance(arg, ast.Constant) and arg.value in STORAGE_WRITE_MODES:
                    write_calls.append((node.lineno, "open(write-mode)"))
            for kw in node.keywords:
                if (
                    kw.arg == "mode"
                    and isinstance(kw.value, ast.Constant)
                    and kw.value.value in STORAGE_WRITE_MODES
                ):
                    write_calls.append((node.lineno, "open(write-mode)"))

        if method and normalize_identifier(method) in STORAGE_WRITE_METHOD_KEYS:
            write_calls.append((node.lineno, method))

    if not write_calls:
        return []

    if node_has_encrypt_indicator(all_nodes):
        return []

    line_no, call_desc = write_calls[0]
    return [
        make_finding(
            finding_id="unencrypted-storage-write",
            severity="medium",
            title="Storage write without encryption indicator",
            frameworks=["gdpr", "hipaa", "dora", "nis2"],
            rel_path=rel_path,
            line=line_no,
            function=func.name,
            detail=f"Calls {call_desc} without detected encryption indicator in scope.",
        )
    ]


# ---------------------------------------------------------------------------
# TypeScript/Java/Go/C# structural finders
# ---------------------------------------------------------------------------


def function_name_for_display(block: FunctionBlock) -> str:
    return f"{block.name} [{LANGUAGE_DISPLAY.get(block.language, block.language)}]"


def match_function_name(line: str, language: str) -> str | None:
    for pattern in LANGUAGE_FUNCTION_PATTERNS.get(language, ()):
        match = pattern.match(line)
        if match:
            candidate = match.group("name")
            if candidate.lower() in CONTROL_FLOW_NAMES:
                return None
            return candidate
    return None


def extract_brace_functions(source: str, language: str) -> list[FunctionBlock]:
    lines = source.splitlines()
    functions: list[FunctionBlock] = []
    index = 0

    while index < len(lines):
        line = lines[index]
        name = match_function_name(line, language)
        if name is None:
            index += 1
            continue

        start_line = index + 1
        block_lines = [line]
        depth = brace_delta(line)
        cursor = index + 1

        # Support styles where the opening brace is on a following line.
        if depth <= 0:
            lookahead_limit = min(len(lines), index + 8)
            found_open = False
            while cursor < lookahead_limit:
                candidate = lines[cursor]
                block_lines.append(candidate)
                cleaned = strip_strings(candidate)
                depth += cleaned.count("{") - cleaned.count("}")
                cursor += 1
                if "{" in cleaned:
                    found_open = True
                    break
                if ";" in cleaned:
                    break
            if not found_open or depth <= 0:
                index += 1
                continue

        while depth > 0 and cursor < len(lines):
            candidate = lines[cursor]
            block_lines.append(candidate)
            depth += brace_delta(candidate)
            cursor += 1

        functions.append(
            FunctionBlock(
                name=name,
                start_line=start_line,
                lines=tuple(block_lines),
                language=language,
            )
        )
        index = cursor if cursor > index else index + 1

    return functions


def find_pii_in_return_block(
    block: FunctionBlock,
    path: Path,
    root: Path,
) -> list[dict[str, Any]]:
    rel_path = make_relative(path, root)
    findings: list[dict[str, Any]] = []
    lines = list(block.lines)

    for idx, line in enumerate(lines):
        if "return" not in line.lower():
            continue

        snippet_lines = [line]
        if "{" in line and "}" not in line:
            for next_line in lines[idx + 1 : idx + 9]:
                snippet_lines.append(next_line)
                if "}" in next_line or ";" in next_line:
                    break
        snippet = "\n".join(snippet_lines)

        pii_keys: set[str] = set()
        for match in PII_KEY_RE.finditer(snippet):
            token = match.group("quoted") or match.group("plain")
            if token and token.lower() in PII_FIELD_NAMES:
                pii_keys.add(token.lower())

        token_match = RETURN_EXPR_PII_RE.search(line)
        object_match = RETURN_OBJECT_PII_RE.search(snippet)
        if not pii_keys and token_match is None and object_match is None:
            continue

        if pii_keys:
            detail = f"Returns object/map with PII keys: {', '.join(sorted(pii_keys))}"
        else:
            token = token_match.group("field") if token_match else object_match.group("field")  # type: ignore[union-attr]
            detail = f"Returns expression referencing PII token: {token}"

        findings.append(
            make_finding(
                finding_id="pii-in-return-value",
                severity="medium",
                title="PII field returned from function",
                frameworks=["gdpr", "us-state-privacy", "hipaa"],
                rel_path=rel_path,
                line=block.start_line + idx,
                function=function_name_for_display(block),
                detail=detail,
            )
        )

    return findings


def find_unlogged_db_writes_block(
    block: FunctionBlock,
    path: Path,
    root: Path,
) -> list[dict[str, Any]]:
    rel_path = make_relative(path, root)
    lines = list(block.lines)
    db_write_calls: list[tuple[int, str]] = []
    has_logging = False

    for idx, line in enumerate(lines):
        for method in extract_call_tokens(line):
            method_key = normalize_identifier(method)
            if method_key in DB_WRITE_METHOD_KEYS:
                db_write_calls.append((idx, method))
            if method_key in LOG_METHOD_KEYS:
                has_logging = True

    if not db_write_calls or has_logging:
        return []

    first_idx, first_method = db_write_calls[0]
    extra = len(db_write_calls) - 1
    detail = (
        f"Calls {first_method}() (plus {extra} more DB write(s)) without a logging call."
        if extra
        else f"Calls {first_method}() without a logging call."
    )
    return [
        make_finding(
            finding_id="unlogged-db-write",
            severity="medium",
            title="Database write without audit logging",
            frameworks=["gdpr", "hipaa", "sox", "sec-cyber-disclosure"],
            rel_path=rel_path,
            line=block.start_line + first_idx,
            function=function_name_for_display(block),
            detail=detail,
        )
    ]


def find_unencrypted_storage_writes_block(
    block: FunctionBlock,
    path: Path,
    root: Path,
) -> list[dict[str, Any]]:
    rel_path = make_relative(path, root)
    lines = list(block.lines)
    write_calls: list[tuple[int, str]] = []
    all_text = "\n".join(lines)

    for idx, line in enumerate(lines):
        if OPEN_WRITE_MODE_RE.search(line):
            write_calls.append((idx, "open(write-mode)"))
        if OS_CREATE_RE.search(line):
            write_calls.append((idx, "os.Create"))

        for method in extract_call_tokens(line):
            if normalize_identifier(method) in STORAGE_WRITE_METHOD_KEYS:
                write_calls.append((idx, method))

    if not write_calls:
        return []
    if contains_encryption_indicator(all_text):
        return []

    first_idx, call_desc = write_calls[0]
    return [
        make_finding(
            finding_id="unencrypted-storage-write",
            severity="medium",
            title="Storage write without encryption indicator",
            frameworks=["gdpr", "hipaa", "dora", "nis2"],
            rel_path=rel_path,
            line=block.start_line + first_idx,
            function=function_name_for_display(block),
            detail=f"Calls {call_desc} without detected encryption indicator in scope.",
        )
    ]


# ---------------------------------------------------------------------------
# File and repo scanning
# ---------------------------------------------------------------------------


def scan_python_file(path: Path, root: Path) -> list[dict[str, Any]]:
    """Run all Python AST structural finders over a single file."""
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


def scan_language_file(path: Path, root: Path, language: str) -> list[dict[str, Any]]:
    """Run structural function-block finders for TypeScript/Java/Go/C# files."""
    source = path.read_text(encoding="utf-8", errors="ignore")
    blocks = extract_brace_functions(source, language)
    findings: list[dict[str, Any]] = []
    for block in blocks:
        findings.extend(find_pii_in_return_block(block, path, root))
        findings.extend(find_unlogged_db_writes_block(block, path, root))
        findings.extend(find_unencrypted_storage_writes_block(block, path, root))
    return findings


def collect_structural_files(base_path: Path) -> tuple[dict[str, list[Path]], Path]:
    """Collect scannable source files for all structural languages."""
    root = base_path if base_path.is_dir() else base_path.parent
    files_by_language: dict[str, list[Path]] = {lang: [] for lang in LANGUAGE_SUFFIXES}

    def maybe_add_file(path: Path) -> None:
        if path.stat().st_size > MAX_FILE_BYTES:
            return
        suffix = path.suffix.lower()
        for language, suffixes in LANGUAGE_SUFFIXES.items():
            if suffix in suffixes:
                files_by_language[language].append(path)
                return

    if base_path.is_file():
        maybe_add_file(base_path)
        return files_by_language, root

    for dirpath, dirnames, filenames in os.walk(base_path):
        dirnames[:] = sorted(d for d in dirnames if d not in EXCLUDED_DIRS)
        for filename in sorted(filenames):
            maybe_add_file(Path(dirpath) / filename)
    for language in files_by_language:
        files_by_language[language].sort()
    return files_by_language, root


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------


def render_markdown(findings: list[dict[str, Any]], scan_meta: dict[str, Any]) -> str:
    lines = [
        "## AST Structural Scan",
        "",
        "| Scope | Count |",
        "|---|---:|",
        f"| Python files | {scan_meta['python_files']} |",
        f"| TypeScript files | {scan_meta['typescript_files']} |",
        f"| Java files | {scan_meta['java_files']} |",
        f"| Go files | {scan_meta['go_files']} |",
        f"| .NET/C# files | {scan_meta['csharp_files']} |",
        f"| Structural findings | {scan_meta['finding_count']} |",
        "",
    ]
    if not findings:
        lines.append("✅ No structural findings detected.")
        return "\n".join(lines) + "\n"

    lines.extend(["| Severity | Finding | Frameworks | Evidence | Detail |", "|---|---|---|---|---|"])
    for finding in findings:
        evidence_lines = []
        detail_lines = []
        for evidence in finding["evidence"]:
            evidence_lines.append(f"`{evidence['path']}:{evidence['line']}` in `{evidence['function']}`")
            detail_lines.append(evidence["detail"])
        lines.append(
            "| "
            + " | ".join(
                [
                    severity_badge(finding["severity"]),
                    markdown_cell(finding["title"]),
                    markdown_cell(", ".join(finding["frameworks"])),
                    markdown_cell("<br>".join(evidence_lines)),
                    markdown_cell("<br>".join(detail_lines)),
                ]
            )
            + " |"
        )

    return "\n".join(lines) + "\n"


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
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help=f"Parallel worker count for file scanning (default: {DEFAULT_WORKERS}).",
    )
    parser.add_argument(
        "--cache-dir",
        default=".regintel/cache",
        help="Directory for incremental scanner cache files (default: .regintel/cache).",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable incremental cache reads/writes for this run.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    base_path = Path(args.path)
    if not base_path.exists():
        print(json.dumps({"error": f"Path not found: {base_path}"}))
        return 1

    files_by_language, root = collect_structural_files(base_path)
    all_findings: list[dict[str, Any]] = []

    max_workers = max(1, args.workers)
    use_cache = not args.no_cache
    cache_hits = 0
    cache_misses = 0
    cache_entries: dict[str, dict[str, Any]] = {}
    cache_file = Path(args.cache_dir) / "ast_signal_scan.json"
    if use_cache:
        cache_entries = load_scan_cache(cache_file, version=AST_SCAN_CACHE_VERSION)

    work_items: list[tuple[int, str, Path]] = []
    ordered_languages = ("python", "typescript", "java", "go", "csharp")
    item_index = 0
    for language in ordered_languages:
        for path in files_by_language[language]:
            work_items.append((item_index, language, path))
            item_index += 1

    findings_by_index: dict[int, list[dict[str, Any]]] = {}
    futures: dict[
        concurrent.futures.Future[list[dict[str, Any]]], tuple[int, str, str | None]
    ] = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        for index, language, path in work_items:
            cache_key = f"{root.resolve()}::{path.resolve()}::{language}"
            fingerprint: str | None = None
            try:
                fingerprint = file_fingerprint(path)
            except OSError:
                fingerprint = None

            if use_cache and fingerprint:
                cached = cache_entries.get(cache_key)
                if (
                    isinstance(cached, dict)
                    and cached.get("fingerprint") == fingerprint
                    and isinstance(cached.get("result"), list)
                ):
                    findings_by_index[index] = cached["result"]
                    cache_hits += 1
                    continue

            if language == "python":
                future = executor.submit(scan_python_file, path, root)
            else:
                future = executor.submit(scan_language_file, path, root, language)
            futures[future] = (index, cache_key, fingerprint)
            if use_cache:
                cache_misses += 1

        for future in concurrent.futures.as_completed(futures):
            index, cache_key, fingerprint = futures[future]
            result = future.result()
            findings_by_index[index] = result
            if use_cache and fingerprint:
                cache_entries[cache_key] = {"fingerprint": fingerprint, "result": result}

    if use_cache:
        save_scan_cache(cache_file, version=AST_SCAN_CACHE_VERSION, entries=cache_entries)

    for index, _, _ in work_items:
        all_findings.extend(findings_by_index.get(index, []))

    methods_used = [
        STRUCTURAL_METHODS[language]
        for language in ("python", "typescript", "java", "go", "csharp")
        if files_by_language[language]
    ]
    if not methods_used:
        methods_used = [STRUCTURAL_METHODS["python"]]

    scan_meta: dict[str, Any] = {
        "path": str(base_path),
        "python_files": len(files_by_language["python"]),
        "typescript_files": len(files_by_language["typescript"]),
        "java_files": len(files_by_language["java"]),
        "go_files": len(files_by_language["go"]),
        "csharp_files": len(files_by_language["csharp"]),
        "finding_count": len(all_findings),
        "ast_method": "python-ast",
        "structural_methods": methods_used,
        "parallel_workers": max_workers,
        "cache_enabled": use_cache,
        "cache_hits": cache_hits if use_cache else 0,
        "cache_misses": cache_misses if use_cache else 0,
    }

    if args.format == "markdown":
        print(render_markdown(all_findings, scan_meta))
        return 0

    output: dict[str, Any] = with_meta(
        "ast_signal_scan",
        {
            "scan": scan_meta,
            "structural_findings": all_findings,
        },
    )
    json.dump(output, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
