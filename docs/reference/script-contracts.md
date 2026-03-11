# Script Contracts

Regintel v0.7 defines a stable JSON interface contract across all machine-readable script outputs.

## Common Contract Header

Every JSON output starts with:

```json
{
  "meta": {
    "tool": "tool_name",
    "schema_version": "1.0.0"
  }
}
```

`tool` identifies the producer and `schema_version` tracks contract compatibility.

## Covered Scripts

- `repo_signal_scan.py`
- `ast_signal_scan.py`
- `applicability_score.py`
- `check_deadlines.py`
- `change_diff.py`
- `snapshot_store.py`
- `trend_report.py`
- `sync_regulatory_feeds.py`
- `compliance_gate.py`

## Compatibility Rules

- Patch/minor updates keep backward-compatible keys and field meanings.
- Breaking changes require a major `schema_version` update.
- Consumers should validate `meta.tool` and `meta.schema_version` before parsing downstream fields.

## Full Schemas

See [`references/script-schemas.md`](https://github.com/zerantiq/regintel/blob/main/references/script-schemas.md) for per-script payload examples.
