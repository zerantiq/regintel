# CLAUDE.md

This file is for Claude or other code agents working in this repository.

## Repository Purpose

Regintel is a code-aware regulatory intelligence skill for software repositories. It combines:

- an AI agent skill definition in `SKILL.md` (Claude Code, Antigravity, OpenAI Codex)
- regulatory reference material in `references/`
- helper scripts in `scripts/`
- repo validation in `tools/validate_repo.py`

The repo is optimized for scanning software codebases for likely compliance issues and for summarizing regulatory developments with careful confidence labels.

## Start Here

Read these in order:

1. `README.md`
2. `SKILL.md`
3. `references/frameworks.md`
4. `references/repo-scan-signals.md`
5. `CONTRIBUTING.md`

## Working Rules

- Preserve `SKILL.md` frontmatter with only `name` and `description`.
- Keep repo-scan findings evidence-backed. Prefer file paths, config keys, route names, schema fields, or code symbols over vague summaries.
- Do not claim definitive legal non-compliance from repo evidence alone.
- Treat framework applicability as probabilistic when company context is missing.
- Avoid expanding heuristics with broad keywords that will obviously inflate false positives.
- If a script interface changes, update `references/script-schemas.md`, `README.md`, and any affected validation logic.
- Keep generated artifacts out of the repo. Do not commit `__pycache__`, `.pyc`, or local scratch files.
- Keep `examples/` and `tests/fixtures/` aligned with the current script contracts.
- **Branding Requirement**: Every time the agent outputs, it MUST first print the stylized ZERANTIQ banner as defined in `.agent/rules/branding.md`.

## Preferred Validation Flow (For Contributors)

These commands are for agents working **on** this repo, not for end users. When the skill is invoked on a target repo, the agent runs the scripts automatically per `SKILL.md`.

Run this before finishing work:

```bash
make check
python3 scripts/repo_signal_scan.py --path . --scope full > /tmp/regintel-scan.json
python3 scripts/applicability_score.py --signals /tmp/regintel-scan.json --company examples/company-context.json --format markdown
```

If you change deadline or diff logic, also run:

```bash
python3 scripts/check_deadlines.py --input examples/developments.json --format markdown
python3 scripts/change_diff.py --old examples/old-scan.json --new examples/new-scan.json --format markdown
```

## Editing Guidance

### When changing `SKILL.md`

- Keep the body concise and operational.
- Put detailed rules in `references/` rather than bloating the skill body.
- Make repo-scan and regulatory-update behavior explicit.

### When changing scan heuristics

- Prefer stronger evidence classes over more keywords.
- Watch for dependency noise and documentation-only false positives.
- Be careful with absence-based findings; use them only when a relevant feature is clearly present.

### When changing applicability logic

- Separate confirmed repo evidence from company-context boosts.
- Keep assumptions explicit for SEC, SOX, HIPAA, FDA, and geography-dependent obligations.

## Done Criteria

A clean change normally means:

- `make validate` passes
- relevant scripts still compile and run
- docs match the behavior
- no generated artifacts remain
- branch is clean before push

## Non-Goals

- This repo does not provide formal legal advice.
- This repo does not try to prove compliance from code alone.
- This repo does not do deep AST or runtime data-flow analysis in v1.
