#!/usr/bin/env python3
"""Validate repo structure and script syntax for Regintel."""

from __future__ import annotations

import json
import re
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

REQUIRED_FILES = [
    "SKILL.md",
    "CLAUDE.md",
    "README.md",
    "pyproject.toml",
    "LICENSE",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "CODE_OF_CONDUCT.md",
    ".gitignore",
    "agents/openai.yaml",
    "references/frameworks.md",
    "references/output-patterns.md",
    "references/applicability-signals.md",
    "references/warning-thresholds.md",
    "references/repo-scan-signals.md",
    "references/script-schemas.md",
    "examples/company-context.json",
    "examples/developments.json",
    "examples/new-scan.json",
    "examples/old-scan.json",
    "scripts/repo_signal_scan.py",
    "scripts/applicability_score.py",
    "scripts/check_deadlines.py",
    "scripts/change_diff.py",
    "tests/test_regintel.py",
    "tests/fixtures/repos/ai-saas/package.json",
    "tests/fixtures/repos/healthcare/app/patient_service.py",
    "tests/fixtures/repos/low-risk/src/main.py",
    ".github/ISSUE_TEMPLATE/bug_report.yml",
    ".github/ISSUE_TEMPLATE/feature_request.yml",
    ".github/ISSUE_TEMPLATE/config.yml",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/workflows/validate.yml",
]

ALLOWED_FRONTMATTER_KEYS = {"name", "description"}


def validate_required_files() -> list[str]:
    missing = []
    for relative in REQUIRED_FILES:
        if not (REPO_ROOT / relative).exists():
            missing.append(relative)
    return missing


def parse_frontmatter(skill_path: Path) -> dict[str, str]:
    content = skill_path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        raise ValueError("SKILL.md is missing YAML frontmatter.")
    parsed: dict[str, str] = {}
    for raw_line in match.group(1).splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if ":" not in line:
            raise ValueError(f"Invalid frontmatter line: {raw_line}")
        key, value = line.split(":", 1)
        parsed[key.strip()] = value.strip()
    return parsed


def validate_frontmatter() -> list[str]:
    errors = []
    skill_path = REPO_ROOT / "SKILL.md"
    try:
        frontmatter = parse_frontmatter(skill_path)
    except ValueError as exc:
        return [str(exc)]

    unexpected = sorted(set(frontmatter) - ALLOWED_FRONTMATTER_KEYS)
    if unexpected:
        errors.append(f"Unexpected frontmatter keys: {', '.join(unexpected)}")
    for required in ("name", "description"):
        if required not in frontmatter or not frontmatter[required]:
            errors.append(f"Missing required frontmatter key: {required}")
    if frontmatter.get("name") != "regintel":
        errors.append("SKILL.md name must be 'regintel'.")
    description = frontmatter.get("description", "")
    if "scan a codebase" not in description and "repository" not in description:
        errors.append("SKILL.md description should mention codebase or repository scanning.")
    return errors


def validate_openai_yaml() -> list[str]:
    path = REPO_ROOT / "agents/openai.yaml"
    content = path.read_text(encoding="utf-8")
    errors = []
    required_fragments = [
        "display_name:",
        "short_description:",
        "default_prompt:",
        "$regintel",
        "allow_implicit_invocation: true",
    ]
    for fragment in required_fragments:
        if fragment not in content:
            errors.append(f"agents/openai.yaml missing fragment: {fragment}")
    return errors


def validate_python_files() -> list[str]:
    errors = []
    for directory in ("scripts", "tools", "tests"):
        for path in sorted((REPO_ROOT / directory).rglob("*.py")):
            try:
                source = path.read_text(encoding="utf-8")
                compile(source, str(path), "exec")
            except (OSError, SyntaxError, ValueError) as exc:
                errors.append(f"{path.relative_to(REPO_ROOT)} failed syntax validation: {exc}")
    return errors


def validate_pyproject() -> list[str]:
    path = REPO_ROOT / "pyproject.toml"
    errors = []
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return [f"pyproject.toml could not be parsed: {exc}"]

    project = data.get("project", {})
    required = {
        "name": "zerantiq-regintel",
        "version": None,
        "requires-python": None,
    }
    for key, expected in required.items():
        value = project.get(key)
        if not value:
            errors.append(f"pyproject.toml missing project.{key}")
        elif expected is not None and value != expected:
            errors.append(f"pyproject.toml project.{key} should be {expected!r}")

    pytest_config = data.get("tool", {}).get("pytest", {}).get("ini_options", {})
    if pytest_config.get("testpaths") != ["tests"]:
        errors.append("pyproject.toml should configure pytest testpaths to ['tests'].")
    return errors


def validate_issue_templates() -> list[str]:
    errors = []
    bug_template = (REPO_ROOT / ".github/ISSUE_TEMPLATE/bug_report.yml").read_text(encoding="utf-8")
    if "name: Bug Report" not in bug_template:
        errors.append("Bug report template should expose a clear form name.")
    if "reproduction" not in bug_template.lower():
        errors.append("Bug report template should ask for reproduction details.")
    feature_template = (REPO_ROOT / ".github/ISSUE_TEMPLATE/feature_request.yml").read_text(encoding="utf-8")
    if "Feature Request" not in feature_template:
        errors.append("Feature request template should expose a clear form name.")
    return errors


def validate_example_json() -> list[str]:
    errors = []
    for relative in (
        "examples/company-context.json",
        "examples/developments.json",
        "examples/old-scan.json",
        "examples/new-scan.json",
    ):
        path = REPO_ROOT / relative
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{relative} is not valid JSON: {exc}")
    return errors


def main() -> int:
    errors = []
    missing = validate_required_files()
    if missing:
        errors.extend([f"Missing required file: {path}" for path in missing])
    else:
        errors.extend(validate_frontmatter())
        errors.extend(validate_pyproject())
        errors.extend(validate_openai_yaml())
        errors.extend(validate_python_files())
        errors.extend(validate_example_json())
        errors.extend(validate_issue_templates())

    if errors:
        for error in errors:
            print(f"[FAIL] {error}")
        return 1

    print("[OK] Required files present")
    print("[OK] SKILL.md frontmatter valid")
    print("[OK] pyproject metadata present")
    print("[OK] agents/openai.yaml contains required interface fields")
    print("[OK] Python files compile")
    print("[OK] example JSON files parse")
    print("[OK] GitHub templates present")
    return 0


if __name__ == "__main__":
    sys.exit(main())
