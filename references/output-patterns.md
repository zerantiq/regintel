# Output Patterns

Use these patterns to keep responses practical, evidence-backed, and visually scannable.

## Repo Scan Pattern

### Regulatory Scan Summary

**Scanned:** Full application repo scan across source, config, infra, and compliance-sensitive docs for a SaaS platform that handles user accounts, analytics, model-provider calls, and operational telemetry.

**Overall Risk Picture:** 🔴 High. The repo suggests a mix of personal data handling and AI-enabled workflows, while several governance and lifecycle controls are not clearly visible in-repo, so the immediate risk is around privacy obligations, AI governance, and evidence gaps.

### Executive Snapshot

| Metric | Value |
|---|---|
| Scope | Full application repo scan across source, config, infra, and compliance-sensitive docs |
| Top frameworks | GDPR, EU AI Act, ISO/IEC 42001 |
| Overall urgency | 🔴 High |
| Confidence | 🟡 Medium: repo evidence is strong, but deployment facts are incomplete |

### Severity Legend

`🚨 Critical` · `🔴 High` · `🟠 Medium` · `🟡 Low` · `🔵 Info`

### Applicability

| Framework | Applicability | Confidence |
|---|---|---|
| GDPR / UK GDPR | High: the repo includes account data, analytics, and delete/export-style workflows that suggest personal-data handling | Medium-High |
| EU AI Act | Medium-High: model-provider integrations and prompt orchestration suggest AI governance review is needed | Medium |
| HIPAA | Low-Medium: healthcare-style terminology may indicate sensitivity, but PHI handling is not confirmed from repo evidence alone | Low-Medium |

### Key Findings

| Severity | Regulatory framework | Evidence (where found) | Why it matters |
|---|---|---|---|
| 🔴 High | GDPR | `src/api/telemetry.ts` logs account-linked events; no retention path observed | Suggests a review gap around storage limitation, deletion, and notice coverage |
| 🟠 Medium | EU AI Act | `services/llm/client.py` integrates model providers; no model inventory or human-review path observed | Suggests an AI governance and transparency gap to review before broader rollout |
| 🟡 Low | ISO/IEC 42001 | AI-related workflows exist but governance artifacts are not visible in-repo | Suggests maturity work, not necessarily an immediate blocker |

### Action Plan

| Priority | Team | Action | Evidence trigger |
|---|---|---|---|
| 🔴 High | Engineering | Map retention, deletion, and export behavior across all user-data stores | Telemetry and user-data endpoints are visible |
| 🟠 Medium | Product | Inventory all AI-assisted features and user-facing disclosures | Model-provider integrations are visible |
| 🟠 Medium | Security | Confirm logging, escalation, and vendor-review paths for incidents involving AI or personal data | Disclosure-sensitive and privacy-sensitive signals were detected |
| 🟡 Low | Legal / Compliance | Confirm geography, public-company status, and regulated-data scope | Repo evidence alone cannot confirm legal/entity facts |

### Deadlines & Warnings

| Milestone | Framework | Warning | Urgency | Review trigger |
|---|---|---|---|---|
| 2026-08-01 enforcement milestone | EU AI Act | 🟠 Action Needed Soon | 🔴 High | Validate whether current product workflows fall into the affected category |
| Incident reporting window | DORA / NIS2 | 🚨 Critical Deadline | 🚨 Critical | Confirm whether the business is actually in scope before relying on current incident processes |

### Open Questions / Assumptions

- EU and UK exposure are inferred from product signals, not confirmed from entity or customer facts.
- Healthcare terminology alone does not confirm HIPAA scope.
- No claim of definitive non-compliance should be made from repo evidence alone.

## Regulatory Update Pattern

### Regulatory Update Snapshot

| Metric | Value |
|---|---|
| Framework | EU AI Act |
| Status | 🟠 Adopted, approaching milestone |
| Date to anchor on | August 1, 2026 |
| Operational urgency | 🔴 High |

### Impact Matrix

| Area | What changed | Why it matters |
|---|---|---|
| Engineering | Logging, monitoring, and provider-governance expectations become more immediate | Release plans may need additional controls and evidence |
| Product | User-facing transparency and feature inventory work may need to land sooner | Unclear ownership creates launch risk |
| Compliance | Control mapping and scope triage must happen against exact use cases | Proposed vs effective obligations must stay clearly separated |

### Action Plan

| Priority | Team | Action |
|---|---|---|
| 🔴 High | Compliance | Confirm exact scope category and milestone relevance |
| 🟠 Medium | Engineering | Map deployed AI features, logs, and fallback paths |
| 🟠 Medium | Product | Review user notices and human-escalation paths |

### Open Questions / Assumptions

- Applicability still depends on the deployed feature category and market exposure.
- Use exact dates and adoption/effective status, not relative phrases.
