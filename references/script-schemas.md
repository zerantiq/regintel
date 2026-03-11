# Script Schemas

All scripts use UTF-8 JSON files as input. Dates use `YYYY-MM-DD`.

## v1.0 Contract Header

All machine-readable outputs include a stable contract header:

```json
{
  "meta": {
    "tool": "repo_signal_scan",
    "schema_version": "1.0.0"
  }
}
```

Consumers should validate `meta.tool` and `meta.schema_version` before parsing script-specific fields.

## `repo_signal_scan.py` Output

```json
{
  "meta": {
    "tool": "repo_signal_scan",
    "schema_version": "1.0.0"
  },
  "scan": {
    "path": ".",
    "scope": "full",
    "focus": null,
    "scanned_files": 42,
    "excluded_files": 11,
    "parallel_workers": 8,
    "cache_enabled": true,
    "cache_hits": 30,
    "cache_misses": 12
  },
  "product_profile": {
    "labels": ["ai-enabled-software", "saas-service"],
    "confidence": 0.82,
    "reasons": ["Model API clients and prompt templates were detected."]
  },
  "signals": [
    {
      "id": "ai-model-integration",
      "category": "ai",
      "title": "AI model or agent integration",
      "frameworks": ["eu-ai-act", "gdpr"],
      "confidence": 0.9,
      "evidence": [
        {
          "path": "services/llm/client.py",
          "line": 12,
          "match": "from openai import OpenAI",
          "patterns": ["openai"],
          "evidence_class": "source"
        }
      ],
      "summary": "The repo integrates external model services or orchestration tooling."
    }
  ],
  "control_observations": [
    {
      "control": "privacy-user-controls",
      "status": "not-observed",
      "frameworks": ["gdpr", "us-state-privacy"],
      "confidence": 0.63,
      "rationale": "Personal-data signals were found, but no delete/export/retention evidence was observed.",
      "evidence": []
    }
  ],
  "candidate_frameworks": [
    {
      "framework": "gdpr",
      "display_name": "GDPR",
      "score": 72,
      "confidence": 0.78,
      "reasons": ["Personal-data and analytics signals were detected."]
    }
  ]
}
```

## `applicability_score.py` Inputs

### Signals

Pass the JSON file produced by `repo_signal_scan.py`.

### Company Context

```json
{
  "jurisdictions": ["EU", "UK", "US-CA"],
  "public_company": false,
  "uses_ai": true,
  "customers": ["enterprise", "healthcare"],
  "deployment_model": "hosted-saas",
  "regulated_claims": [],
  "financial_entity": false,
  "essential_service": false,
  "processes_card_payments": false
}
```

## `applicability_score.py` Output

```json
{
  "meta": {
    "tool": "applicability_score",
    "schema_version": "1.0.0"
  },
  "product_profile": { "...": "..." },
  "applicability": [
    {
      "framework": "eu-ai-act",
      "display_name": "EU AI Act",
      "score": 79,
      "confidence": 0.84,
      "basis": ["AI model integration detected in repo.", "Company context confirms AI use in the EU."],
      "likely_review_areas": ["AI inventory", "transparency", "logging and monitoring"],
      "assumptions": ["High-risk classification is not confirmed from repo evidence alone."]
    }
  ],
  "priority_review_areas": ["AI inventory", "retention and deletion", "vendor controls"],
  "confidence_notes": ["SEC and SOX were not elevated because public-company status was not confirmed."]
}
```

## `check_deadlines.py` Input

```json
{
  "developments": [
    {
      "id": "eu-ai-act-gpai",
      "framework": "EU AI Act",
      "title": "General-purpose AI obligations",
      "stage": "adopted",
      "timing": "upcoming",
      "milestones": [
        {
          "label": "obligations-apply",
          "date": "2026-08-02",
          "kind": "effective"
        }
      ]
    }
  ]
}
```

## `check_deadlines.py` Output

- `json`: includes `meta`, then developments with `nearest_milestone`, `warning_label`, `urgency`, and `days_until`
- `markdown`: concise deadline table plus warning notes

## `ast_signal_scan.py` Output

Scans Python, TypeScript, Java, Go, and .NET/C# source files for structural function-level findings.

```json
{
  "meta": {
    "tool": "ast_signal_scan",
    "schema_version": "1.0.0"
  },
  "scan": {
    "path": ".",
    "python_files": 4,
    "typescript_files": 2,
    "java_files": 1,
    "go_files": 1,
    "csharp_files": 1,
    "finding_count": 3,
    "ast_method": "python-ast",
    "structural_methods": [
      "python-ast",
      "typescript-brace-patterns",
      "java-brace-patterns",
      "go-brace-patterns",
      "csharp-brace-patterns"
    ],
    "parallel_workers": 8,
    "cache_enabled": true,
    "cache_hits": 6,
    "cache_misses": 2
  },
  "structural_findings": [
    {
      "id": "pii-in-return-value",
      "severity": "medium",
      "title": "PII field returned from function",
      "frameworks": ["gdpr", "us-state-privacy", "hipaa"],
      "evidence": [
        {
          "path": "services/user_service.py",
          "line": 25,
          "function": "get_user_profile",
          "detail": "Returns dict with PII keys: dob, email, first_name, last_name, phone",
          "finding_class": "ast"
        }
      ]
    },
    {
      "id": "unlogged-db-write",
      "severity": "medium",
      "title": "Database write without audit logging",
      "frameworks": ["gdpr", "hipaa", "sox", "sec-cyber-disclosure"],
      "evidence": [
        {
          "path": "services/user_service.py",
          "line": 35,
          "function": "delete_user_account",
          "detail": "Calls .execute() (plus 1 more DB write(s)) without a logging call.",
          "finding_class": "ast"
        }
      ]
    },
    {
      "id": "unencrypted-storage-write",
      "severity": "medium",
      "title": "Storage write without encryption indicator",
      "frameworks": ["gdpr", "hipaa", "dora", "nis2"],
      "evidence": [
        {
          "path": "services/user_service.py",
          "line": 43,
          "function": "export_user_data",
          "detail": "Calls open(write-mode) without detected encryption indicator in scope.",
          "finding_class": "ast"
        }
      ]
    }
  ]
}
```

### Finding IDs

| ID | Severity | Description | Frameworks |
|---|---|---|---|
| `pii-in-return-value` | medium | Function returns a dict with PII key names, a PII attribute, or a PII-named variable | gdpr, us-state-privacy, hipaa |
| `unlogged-db-write` | medium | Function contains DB write calls (save, insert, execute, commit, etc.) with no logging call in scope | gdpr, hipaa, sox, sec-cyber-disclosure |
| `unencrypted-storage-write` | medium | Function writes to a file or storage SDK without encryption indicators present | gdpr, hipaa, dora, nis2 |

## `change_diff.py` Inputs

Accept any two JSON files containing one or more of:

- `developments`
- `signals`
- `candidate_frameworks`
- `applicability`

Items should expose `id` where possible. If `id` is absent, the script falls back to composite keys such as `framework + title`.

## `snapshot_store.py` Input

- `--scan` (required): JSON output from `repo_signal_scan.py`
- `--applicability` (optional): JSON output from `applicability_score.py`
- `--deadlines` (optional): JSON output from `check_deadlines.py`
- `--ast` (optional): JSON output from `ast_signal_scan.py`
- `--snapshot-dir` (optional): directory to store snapshots (default: `.regintel/snapshots`)
- `--tag` (optional): snapshot tag (`nightly`, `baseline`, etc.)

## `snapshot_store.py` Output

```json
{
  "meta": {
    "tool": "snapshot_store",
    "schema_version": "1.0.0"
  },
  "snapshot": {
    "snapshot_id": "20260311120000",
    "created_at": "2026-03-11T12:00:00Z",
    "path": ".regintel/snapshots/snapshot-20260311120000.json"
  },
  "metrics": {
    "signal_count": 11,
    "framework_count": 7,
    "applicability_count": 6,
    "structural_finding_count": 3,
    "observed_control_count": 2,
    "not_observed_control_count": 1,
    "high_or_critical_deadline_count": 2,
    "top_framework": { "framework": "gdpr", "display_name": "GDPR", "score": 92 }
  },
  "trend": {
    "baseline_snapshot_id": "20260310120000",
    "signal_delta": 1,
    "framework_delta": 0,
    "not_observed_control_delta": -1,
    "urgent_deadline_delta": 0,
    "framework_score_changes": [
      { "framework": "gdpr", "old_score": 90, "new_score": 92, "delta": 2 }
    ]
  }
}
```

## `trend_report.py` Output

```json
{
  "meta": {
    "tool": "trend_report",
    "schema_version": "1.0.0"
  },
  "snapshot_count": 12,
  "window": 10,
  "history": [
    {
      "snapshot_id": "20260311120000",
      "created_at": "2026-03-11T12:00:00Z",
      "signal_count": 11,
      "framework_count": 7,
      "not_observed_control_count": 1,
      "high_or_critical_deadline_count": 2,
      "structural_finding_count": 3,
      "top_framework": { "framework": "gdpr", "display_name": "GDPR", "score": 92 }
    }
  ],
  "framework_trends": [
    { "framework": "gdpr", "first_score": 84, "latest_score": 92, "delta": 8, "direction": "up" }
  ],
  "latest_snapshot": { "...": "..." }
}
```

## `dashboard_report.py` Output

- `markdown`: text dashboard with latest snapshot metrics, top frameworks, not-observed controls, and trend window table
- `html`: lightweight single-file dashboard with the same sections

## `sync_regulatory_feeds.py` Config

```json
{
  "max_items_per_feed": 15,
  "feeds": [
    {
      "id": "nist-ai-rmf-feed",
      "source": "https://www.nist.gov/news-events/news/rss.xml",
      "format": "rss",
      "framework": "NIST AI RMF",
      "stage": "adopted",
      "timing": "upcoming",
      "milestone_kind": "effective"
    }
  ],
  "merge_with": "examples/developments.json"
}
```

## `sync_regulatory_feeds.py` Output

```json
{
  "meta": {
    "tool": "sync_regulatory_feeds",
    "schema_version": "1.0.0"
  },
  "generated_at": "2026-03-11T12:00:00Z",
  "feed_count": 2,
  "item_count": 8,
  "developments": [
    {
      "id": "nist-ai-rmf-feed::item::2026-03-01",
      "framework": "NIST AI RMF",
      "title": "NIST AI guidance update",
      "stage": "adopted",
      "timing": "upcoming",
      "source": "nist-ai-rmf-feed",
      "source_url": "https://example.org/item",
      "milestones": [{ "label": "feed-update", "date": "2026-03-01", "kind": "effective" }]
    }
  ],
  "errors": []
}
```

## `compliance_gate.py` Input

- `--policy` (required): policy JSON with threshold checks
- `--scan` (required): JSON output from `repo_signal_scan.py`
- `--deadlines` (optional): JSON output from `check_deadlines.py`
- `--ast` (optional): JSON output from `ast_signal_scan.py`
- `--trend` (optional): JSON output from `trend_report.py` or `snapshot_store.py` summary

## `compliance_gate.py` Output

```json
{
  "meta": {
    "tool": "compliance_gate",
    "schema_version": "1.0.0"
  },
  "policy_name": "balanced-default-gate",
  "passed": true,
  "failed_checks": 0,
  "total_checks": 8,
  "checks": [
    {
      "check": "max_not_observed_controls",
      "status": "pass",
      "message": "Not-observed control count is within threshold.",
      "threshold": 3,
      "actual": 2
    }
  ],
  "metrics": {
    "signal_count": 6,
    "framework_scores": { "gdpr": 81, "dora": 75 },
    "not_observed_controls": 2,
    "high_or_critical_deadlines": 2,
    "structural_findings": 0,
    "trend_deltas": { "gdpr": -4, "dora": 2 }
  }
}
```

- Exit code `0`: gate passed
- Exit code `1`: one or more gate checks failed

## `benchmark_harness.py` Inputs

- `--labels` (optional): labeled corpus JSON (default: `tests/fixtures/benchmarks/labeled-corpus.json`)
- `--fixtures-root` (optional): fixture repo root (default: `tests/fixtures/repos`)
- `--baseline` (optional): baseline metrics JSON used for trend deltas (default: `tests/fixtures/benchmarks/baseline-metrics.json`)
- `--policy` (optional): benchmark gate policy JSON with minimum-metric and max-drop checks (default: `examples/benchmark-gate-policy.json`)
- `--workers` (optional): worker count forwarded to scanner runs
- `--cache-dir` (optional): cache directory forwarded to scanner runs
- `--no-cache` (optional): disable scanner cache for benchmark runs
- `--history-file` (optional): append run summaries as JSON Lines

## `benchmark_harness.py` Output

```json
{
  "meta": {
    "tool": "benchmark_harness",
    "schema_version": "1.0.0"
  },
  "generated_at": "2026-03-11T12:00:00Z",
  "labels_path": "tests/fixtures/benchmarks/labeled-corpus.json",
  "fixtures_root": "tests/fixtures/repos",
  "fixture_count": 7,
  "fixtures": [
    {
      "id": "ai-saas",
      "path": "ai-saas",
      "expected_signal_ids": ["ai-model-integration", "analytics-and-tracking", "personal-data-processing"],
      "predicted_signal_ids": ["ai-model-integration", "analytics-and-tracking", "personal-data-processing"],
      "expected_ast_finding_ids": ["pii-in-return-value", "unencrypted-storage-write", "unlogged-db-write"],
      "predicted_ast_finding_ids": ["pii-in-return-value", "unencrypted-storage-write", "unlogged-db-write"],
      "signal_metrics": { "tp": 3, "fp": 0, "fn": 0, "precision": 1.0, "recall": 1.0, "f1": 1.0 },
      "ast_metrics": { "tp": 3, "fp": 0, "fn": 0, "precision": 1.0, "recall": 1.0, "f1": 1.0 }
    }
  ],
  "overall": {
    "signals": { "tp": 29, "fp": 0, "fn": 0, "precision": 1.0, "recall": 1.0, "f1": 1.0 },
    "ast": { "tp": 7, "fp": 0, "fn": 0, "precision": 1.0, "recall": 1.0, "f1": 1.0 },
    "combined": { "tp": 36, "fp": 0, "fn": 0, "precision": 1.0, "recall": 1.0, "f1": 1.0 }
  },
  "trends": {
    "baseline_path": "tests/fixtures/benchmarks/baseline-metrics.json",
    "available": true,
    "deltas": {
      "signals": { "precision": 0.0, "recall": 0.0, "f1": 0.0 },
      "ast": { "precision": 0.0, "recall": 0.0, "f1": 0.0 },
      "combined": { "precision": 0.0, "recall": 0.0, "f1": 0.0 }
    }
  },
  "gate": {
    "policy_name": "default-benchmark-gate",
    "passed": true,
    "failed_checks": 0,
    "total_checks": 12
  }
}
```

- Exit code `0`: benchmark gate passed (or no policy checks configured)
- Exit code `1`: one or more benchmark gate checks failed
