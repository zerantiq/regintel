# Script Schemas

All scripts use UTF-8 JSON files as input. Dates use `YYYY-MM-DD`.

## `repo_signal_scan.py` Output

```json
{
  "scan": {
    "path": ".",
    "scope": "full",
    "focus": null,
    "scanned_files": 42,
    "excluded_files": 11
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
  "jurisdictions": ["EU", "US-CA"],
  "public_company": false,
  "uses_ai": true,
  "customers": ["enterprise", "healthcare"],
  "deployment_model": "hosted-saas",
  "regulated_claims": [],
  "financial_entity": false,
  "essential_service": false
}
```

## `applicability_score.py` Output

```json
{
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

- `json`: echoes developments with `nearest_milestone`, `warning_label`, `urgency`, and `days_until`
- `markdown`: concise deadline table plus warning notes

## `ast_signal_scan.py` Output

```json
{
  "scan": {
    "path": ".",
    "python_files": 4,
    "finding_count": 3,
    "ast_method": "python-ast"
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
