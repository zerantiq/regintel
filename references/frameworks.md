# Framework Guide

Use this file to decide which frameworks are likely relevant, what must be verified before escalation, and how to talk about milestones.

## Stage Labels

- `proposed`: not yet binding; discuss as planning risk only
- `adopted`: enacted or finalized, but not fully effective
- `effective`: obligations are active
- `enforcement`: supervisory or enforcement activity is live or materially increasing

Keep stage separate from timing. A rule can be effective and still have an upcoming enforcement milestone.

## Frameworks

### EU AI Act

- Likely relevant when the repo shows model integration, ranking, profiling, biometric use, automated decisioning, safety filters, or AI-specific product claims.
- Strong repo signals:
  - OpenAI, Anthropic, Gemini, Hugging Face, LangChain, LlamaIndex, vector DBs, prompt templates, moderation pipelines, model routing, evaluation harnesses
  - AI safety or policy docs, model inventory files, prompt logs, guardrail code
- Likely review areas:
  - model inventory and use-case classification
  - user notice and transparency
  - logging, monitoring, and incident escalation
  - human oversight, safeguards, and abuse prevention
  - vendor controls for third-party AI services
- Avoid high-confidence scope claims for high-risk or prohibited practices unless the repo shows direct evidence.

### GDPR and ePrivacy

- Likely relevant when the software processes personal data for EU users or operators.
- Strong repo signals:
  - user profiles, authentication, analytics, cookies, consent banners, tracking SDKs, marketing tags, data export/delete flows, retention settings
  - privacy docs, DPA references, data subject request endpoints
- Likely review areas:
  - lawful basis and notices
  - consent and cookie handling
  - retention, deletion, and export paths
  - processor and cross-border transfer dependencies
  - security controls and incident handling
- Repo evidence alone cannot confirm geography, controller/processor posture, or legal basis.

### U.S. State Privacy / CPRA-style Obligations

- Likely relevant when the repo suggests consumer-facing data collection, advertising/analytics, sharing with vendors, or user rights workflows.
- Strong repo signals:
  - consumer profiles, analytics/ads SDKs, sale/share language, opt-out flags, cookie or tracking controls
- Likely review areas:
  - notice at collection
  - opt-out and preference management
  - contracts with vendors/service providers
  - rights intake, deletion, and access workflows

### HIPAA

- Likely relevant when the repo clearly handles PHI or supports covered-entity or business-associate workflows.
- Strong repo signals:
  - `phi`, `hipaa`, `patient`, `member`, `ehr`, `fhir`, `hl7`, `clinical`, `encounter`, `diagnosis`, `provider`
  - healthcare integrations, access audit trails, role-based access control, medical record features
- Likely review areas:
  - access controls and least privilege
  - audit logging and monitoring
  - transmission/storage safeguards
  - vendor logging and data-sharing exposure
  - retention and minimum necessary handling
- Treat HIPAA applicability as low confidence unless the repo strongly indicates healthcare use or company context confirms it.

### FDA Software / SaMD

- Likely relevant when the product appears to diagnose, recommend treatment, drive clinical decisions, or interface with regulated medical devices.
- Strong repo signals:
  - device telemetry, diagnostic language, treatment recommendations, clinical scoring, device control, 510(k), SaMD, IEC 62304, FDA references
- Likely review areas:
  - intended use claims
  - clinical decision logic
  - software lifecycle documentation
  - change control, validation, and traceability
- Do not infer FDA scope from general wellness or generic health-tracking terms alone.

### SEC Cyber Disclosure

- Potentially relevant when the company is public or disclosure-sensitive, or when the repo includes incident, materiality, or disclosure workflows.
- Strong repo signals:
  - incident management code, disclosure playbooks, security event escalation, materiality language, board reporting, Form 8-K references
- Likely review areas:
  - incident escalation paths
  - materiality assessment workflows
  - logging and investigation support
  - governance and reporting controls
- Company status is a major gating factor. Mark this as inferred unless public-company context is known.

### SOX / Internal Controls

- Potentially relevant when the repo supports financial reporting, access control to financial systems, approval workflows, or audit evidence retention.
- Strong repo signals:
  - finance systems, ERP integrations, journal approval flows, segregation-of-duties docs, access review automation
- Likely review areas:
  - change management
  - privileged access
  - audit trails
  - approval workflows and evidence retention
- Treat SOX as low confidence without company context.

## Milestone Handling

- Verify dates from current authoritative sources when the user asks for live deadlines or “latest” status.
- Tie warnings to concrete milestones only:
  - effective date
  - enforcement start
  - transition end
  - reporting deadline
- Use `references/warning-thresholds.md` and `scripts/check_deadlines.py` for urgency labeling.
