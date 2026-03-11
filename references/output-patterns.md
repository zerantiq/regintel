# Output Patterns

Use these patterns to keep responses practical, evidence-backed, and visually scannable.

## Repo Scan Pattern

### Executive Snapshot

| Metric | Value |
|---|---|
| Scope | Full application repo scan across source, config, infra, and compliance-sensitive docs |
| Top frameworks | GDPR, EU AI Act, ISO/IEC 42001 |
| Overall urgency | 🔴 High |
| Confidence | 🟡 Medium: repo evidence is strong, but deployment facts are incomplete |

### Severity Legend

`🚨 Critical` · `🔴 High` · `🟠 Medium` · `🟡 Low` · `🔵 Info`

### Applicability Matrix

| Priority | Framework | Why it triggered | Confirmed repo evidence | Depends on company context |
|---|---|---|---|---|
| 🔴 High | GDPR | Account data, analytics, delete/export language | `apps/api/routes/users.ts`, `src/api/telemetry.ts` | EU-user exposure and controller/processor role |
| 🟠 Elevated | EU AI Act | External model APIs and prompt orchestration | `services/llm/client.py`, prompt templates | Whether the deployed feature set is in-scope and how it is used |
| 🟡 Watch | HIPAA | Healthcare domain terms are present | patient-related schemas or workflow docs | Whether PHI is processed in production and BA/CE status |

### Key Findings

| Severity | Framework | Repo evidence | Why it matters | Owner |
|---|---|---|---|---|
| 🔴 High | GDPR | `src/api/telemetry.ts` logs account-linked events; no retention path observed | Suggests a review gap around storage limitation, deletion, and notice coverage | Engineering + Privacy |
| 🟠 Medium | EU AI Act | `services/llm/client.py` integrates model providers; no model inventory or human-review path observed | Suggests an AI governance and transparency gap to review before broader rollout | Product + Compliance |
| 🟡 Low | ISO/IEC 42001 | AI-related workflows exist but governance artifacts are not visible in-repo | Suggests maturity work, not necessarily an immediate blocker | Leadership + Security |

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
