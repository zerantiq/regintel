# Regintel

> Code-aware regulatory intelligence for software repositories.

Regintel helps teams inspect a software repo for likely regulatory issues, map the findings to frameworks such as the EU AI Act, GDPR, HIPAA, FDA software obligations, SEC cyber disclosure, and SOX, and turn those signals into practical next actions.

## Why This Repo Exists

This repository packages `regintel` as a Codex skill with:

- a repo scan workflow for software codebases
- a regulatory update workflow for current developments and deadlines
- bundled references for applicability and warning logic
- Python helpers for signal detection, applicability scoring, deadline checks, and change diffs

## What Regintel Does

| Mode | Purpose | Core Output |
|---|---|---|
| Repo scan | Inspect source, config, schemas, infra, and docs for likely compliance signals | Evidence-backed findings, candidate frameworks, missing-control observations |
| Regulatory update | Track current or upcoming regulatory changes | Applicability summary, warnings, next actions, deadline urgency |

```mermaid
flowchart LR
    A["Software Repo"] --> B["repo_signal_scan.py"]
    B --> C["applicability_score.py"]
    C --> D["Evidence-backed Findings"]
    E["Regulatory Developments"] --> F["check_deadlines.py"]
    E --> G["change_diff.py"]
    F --> H["Warnings / Urgency"]
    G --> I["What's Changed"]
```

## Repository Layout

```text
.
├── SKILL.md
├── CLAUDE.md
├── agents/
├── examples/
├── references/
├── scripts/
├── tests/
├── tools/
├── .github/
├── CONTRIBUTING.md
├── SECURITY.md
├── CODE_OF_CONDUCT.md
├── LICENSE
└── README.md
```

## Quick Start

### 1. Validate the repo

```bash
make validate
```

### 2. Run the regression suite

```bash
make test
```

### 3. Run a repo scan on the sample AI SaaS fixture

```bash
python3 scripts/repo_signal_scan.py --path tests/fixtures/repos/ai-saas --scope full > /tmp/regintel-scan.json
python3 scripts/applicability_score.py --signals /tmp/regintel-scan.json --company examples/company-context.json --format markdown
```

### 4. Check milestone urgency

```bash
python3 scripts/check_deadlines.py --input examples/developments.json --format markdown
```

### 5. Compare two snapshots

```bash
python3 scripts/change_diff.py --old examples/old-scan.json --new examples/new-scan.json --format markdown
```

## Clean Examination Workflow

Use this sequence when reviewing the repo:

1. Read [README.md](README.md) and [SKILL.md](SKILL.md).
2. Read [CLAUDE.md](CLAUDE.md) if you are using an AI coding agent to work in the repo.
3. Review the domain references in [references/frameworks.md](references/frameworks.md) and [references/repo-scan-signals.md](references/repo-scan-signals.md).
4. Run `make check` to verify structure and regression behavior.
5. Run `repo_signal_scan.py` against a target repo or this repo itself.
6. Use `applicability_score.py` to turn raw signals into framework-specific review priorities.
7. Use `examples/` when you want deterministic deadline and diff demonstrations.

## Script Overview

| Script | Purpose |
|---|---|
| `scripts/repo_signal_scan.py` | Scans a repo and inventories evidence-backed regulatory signals |
| `scripts/applicability_score.py` | Scores likely framework relevance from scan output and optional company context |
| `scripts/check_deadlines.py` | Labels milestone urgency for regulatory developments |
| `scripts/change_diff.py` | Compares old and new regulatory or scan snapshots |
| `tools/validate_repo.py` | Repo-native validation for structure, frontmatter, and Python syntax |

## Examples and Tests

- `examples/` contains ready-to-run JSON inputs for deadline checks, applicability scoring, and snapshot diffs.
- `tests/fixtures/repos/` contains three regression fixture repos:
  - `ai-saas`
  - `healthcare`
  - `low-risk`
- `tests/test_regintel.py` asserts expected framework detection, diff-scan behavior, deadline labels, and example diff output.

## Contributing

Start with [CONTRIBUTING.md](CONTRIBUTING.md). Good contributions usually include one or more of:

- better repo-scan heuristics with reduced false positives
- clearer applicability logic for framework-specific edge cases
- stronger reference material for software and AI obligations
- tighter test and validation coverage for the helper scripts

## Reporting Bugs

Use the GitHub bug report template for normal issues. For security-sensitive findings, follow [SECURITY.md](SECURITY.md) instead of opening a public issue with exploit details.

## License

This repository is licensed under the MIT License. See [LICENSE](LICENSE).
