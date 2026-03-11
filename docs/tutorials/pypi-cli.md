# Pip CLI Workflow

The v0.8 package exposes stable CLI entry points for all major workflows.

## Install

```bash
python -m pip install zerantiq-regintel
```

## Scan and Score

```bash
regintel-scan --path tests/fixtures/repos/ai-saas --scope full > /tmp/scan.json
regintel-applicability --signals /tmp/scan.json --format markdown
```

## Compare Snapshots

```bash
regintel-diff --old examples/old-scan.json --new examples/new-scan.json --format markdown
```

## Feed Sync and Deadlines

```bash
regintel-feed-sync --config examples/regulatory-feed-config.json --format json > /tmp/developments.json
regintel-deadlines --input /tmp/developments.json --format markdown
```

## Contract Compatibility

Machine-readable outputs include:

```json
{
  "meta": {
    "tool": "repo_signal_scan",
    "schema_version": "1.0.0"
  }
}
```

Treat `schema_version` as the API contract version for JSON consumers.
