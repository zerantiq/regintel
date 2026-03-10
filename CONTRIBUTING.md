# Contributing

Thanks for contributing to Regintel.

## What Good Contributions Look Like

- tighter repo-scan heuristics with fewer false positives
- clearer framework applicability rules
- better reference material for software and AI obligations
- validation improvements that make the repo easier to inspect and trust
- documentation updates that help reviewers or contributors move faster

## Before You Open an Issue

- Search existing issues and pull requests first.
- Reproduce the behavior on the latest branch you are targeting.
- Capture the exact command, repo path, and output that led to the problem.
- If the issue is security-sensitive, use the process in `SECURITY.md` instead of a public bug report.

## Local Setup

Requirements:

- Python 3.10+
- GNU `make` or equivalent shell access

Validation:

```bash
make validate
```

Regression tests:

```bash
make test
```

Basic smoke scan:

```bash
python3 scripts/repo_signal_scan.py --path . --scope full > /tmp/regintel-scan.json
python3 scripts/applicability_score.py --signals /tmp/regintel-scan.json --format markdown
```

## Pull Request Guidelines

- Keep changes scoped and explain the regulatory or engineering rationale.
- Prefer evidence-backed heuristics over broad keyword expansion.
- Update references when behavior or assumptions change.
- Add or update validation coverage when you change scripts or repo structure.
- Add or update fixtures when you change heuristics, examples, or thresholds.
- Keep public claims careful: likely gap, likely applicability, or area to review.

## Clean Examination Checklist

Reviewers should be able to answer these quickly:

- What changed in skill behavior?
- What evidence does the scanner use?
- What frameworks became more or less likely?
- How was the change validated locally?
- Does the documentation still match the scripts?

## Commit Style

Use concise, descriptive commit messages such as:

- `Refine AI governance signal thresholds`
- `Add HIPAA repo-scan heuristics`
- `Document local validation workflow`
