# Regintel

Regintel scans software repositories for regulatory signals, maps evidence to frameworks, and produces artifacts that teams can use in CI and release checks.

## v0.9 Highlights

- Stable JSON contracts for all machine-readable CLI outputs (`meta.tool`, `meta.schema_version`).
- Pip-installable CLI entry points for every core workflow.
- Full framework coverage tests across all bundled fixture repositories.
- Monitoring and release gates for continuous compliance checks.
- Multi-language structural scanning across Python, TypeScript, Java, Go, and .NET/C#.
- Incremental cache and parallel file scanning for large repository performance.

## Quick Start

```bash
python -m pip install zerantiq-regintel

regintel-scan --path . --scope full > /tmp/scan.json
regintel-applicability --signals /tmp/scan.json --format markdown
```

## Core Workflows

- Repository signal scan: `regintel-scan`
- AST structural scan: `regintel-ast-scan`
- Applicability scoring: `regintel-applicability`
- Deadlines and updates: `regintel-deadlines`, `regintel-feed-sync`
- Continuous monitoring: `regintel-snapshot`, `regintel-trend`, `regintel-dashboard`
- Policy gating: `regintel-gate`
