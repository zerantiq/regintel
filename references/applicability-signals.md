# Applicability Signals

Use these heuristics to convert repo evidence and company facts into a product profile and likely framework exposure.

## Product Profile Heuristics

### AI-Enabled Software

Strong signals:
- model API clients
- embeddings, retrieval, vector DBs
- prompt templates, agent orchestration, evals, moderation
- AI feature names in docs or UI copy

Implications:
- EU AI Act review likely
- privacy review likely if prompts, outputs, or user context are logged

### SaaS / Cloud Service

Strong signals:
- auth flows, multi-tenant config, billing, REST or GraphQL APIs, web dashboards, deployment manifests

Implications:
- GDPR and U.S. privacy review usually relevant when personal data is present
- security and disclosure controls matter more for public or enterprise vendors

### Healthcare / Clinical Software

Strong signals:
- patient, provider, encounter, FHIR, HL7, diagnosis, treatment, medical record, care plan

Implications:
- HIPAA review likely
- FDA review may be relevant if the product makes clinical or diagnostic claims

### Financial Reporting / Public Company Support

Strong signals:
- SEC, 8-K, materiality, disclosure committee, ERP controls, journal approvals, segregation of duties

Implications:
- SEC cyber disclosure and SOX controls may be relevant

## Company Context Signals

Increase confidence when company facts confirm:

- `jurisdictions`
  - EU or UK presence increases privacy and AI-governance relevance
  - California or broad U.S. consumer operations increase state privacy relevance
- `public_company`
  - raises SEC cyber disclosure and SOX relevance
- `customers`
  - healthcare providers, payers, or health-tech vendors raise HIPAA relevance
- `deployment_model`
  - hosted SaaS increases direct operational/privacy exposure
  - on-prem changes some operational assumptions but not all obligations
- `uses_ai`
  - raises EU AI Act and privacy review
- `regulated_claims`
  - diagnostic, treatment, or device-control claims raise FDA relevance

## Codebase Signals by Theme

### Personal Data

- account/profile models
- analytics events with user identifiers
- marketing tags
- file upload or support ticket features
- CRM or email integrations

### User Rights and Transparency

- privacy policy pages
- delete account endpoints
- export/download user data flows
- consent and preference storage

### Security and Incident Handling

- audit logs
- SIEM or alerting hooks
- breach or incident runbooks
- privileged admin actions

### AI Governance

- moderation, safety filters, red-team docs, evaluation harnesses
- model/version inventory
- human review or fallback paths

### Healthcare Safeguards

- RBAC for patient data
- access audit trails
- encryption config
- BAA or HIPAA docs

## Confidence Rules

- High confidence: direct feature evidence plus confirming company context.
- Medium confidence: strong repo evidence without confirming business context.
- Low confidence: generic terms, dependency names, or sparse docs without supporting implementation evidence.
