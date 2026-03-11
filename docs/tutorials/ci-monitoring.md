# CI Monitoring Pipeline

This tutorial runs the same monitoring flow used in scheduled CI.

## 1. Run Baseline Scan and Snapshot

```bash
regintel-scan --path . --scope full > /tmp/scan.json
regintel-applicability --signals /tmp/scan.json --format json > /tmp/applicability.json
regintel-ast-scan --path . --format json > /tmp/ast.json
regintel-deadlines --input examples/developments.json --format json > /tmp/deadlines.json

regintel-snapshot \
  --scan /tmp/scan.json \
  --applicability /tmp/applicability.json \
  --deadlines /tmp/deadlines.json \
  --ast /tmp/ast.json \
  --snapshot-dir .regintel/snapshots \
  --tag baseline \
  --format json
```

## 2. Run Follow-Up Snapshot and Trends

```bash
regintel-snapshot \
  --scan /tmp/scan.json \
  --snapshot-dir .regintel/snapshots \
  --tag nightly \
  --format json

regintel-trend --snapshot-dir .regintel/snapshots --format markdown
regintel-dashboard --snapshot-dir .regintel/snapshots --format html --output /tmp/regintel-dashboard.html
```

## 3. Enforce Gate in CI

```bash
regintel-gate \
  --policy examples/compliance-gate-policy.json \
  --scan /tmp/scan.json \
  --deadlines /tmp/deadlines.json \
  --ast /tmp/ast.json \
  --format json
```

If gate checks fail, the command exits with code `1`.
