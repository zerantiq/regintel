# Repo Scan Signals

Use this file when scanning a software repository for likely regulatory issues.

## Scan Surfaces

Inspect these first:

- source code for APIs, jobs, services, prompts, logging, and data models
- config and manifests such as `package.json`, `pyproject.toml`, Dockerfiles, Helm charts, Terraform, OpenAPI, GraphQL schemas, and env examples
- policy and product docs such as privacy pages, security docs, runbooks, architecture notes, onboarding docs, and release docs

Ignore dependency noise unless first-party code or docs reinforce it.

## Signal Categories

### AI Model Integration

Example evidence:
- OpenAI, Anthropic, Gemini, Bedrock, Vertex AI, Hugging Face
- LangChain, LlamaIndex, semantic search, embeddings, vector stores
- prompt templates, agent routing, evaluation harnesses, moderation pipelines

Potential review areas:
- AI feature inventory
- transparency and notice
- logging and retention of prompts/outputs
- safety guardrails and human oversight
- vendor management

### Personal Data and Tracking

Example evidence:
- user profiles, email, phone, address, device IDs
- analytics SDKs, session replay, advertising IDs, cookies, consent storage
- CRM, email marketing, support tooling, webhook forwarding

Potential review areas:
- privacy notices
- consent and preference management
- data minimization
- vendor disclosures

### User Rights and Lifecycle Controls

Example evidence:
- delete account, export data, DSAR, retention, archival, TTL, purge jobs

Potential review areas:
- deletion completeness
- export coverage
- retention schedule documentation
- controller/processor workflow clarity

### Security, Audit, and Disclosure

Example evidence:
- audit logs, admin actions, incident or breach runbooks, SIEM hooks, materiality language

Potential review areas:
- incident escalation and evidence preservation
- disclosure readiness
- access reviews
- logging around sensitive operations

### Healthcare and Clinical Signals

Example evidence:
- patient or provider entities
- FHIR or HL7 schemas
- diagnosis, treatment, triage, care plan, medical record language
- BAA or HIPAA docs

Potential review areas:
- access control
- audit logging
- data-sharing with vendors
- minimum necessary handling

### Medical Device / SaMD Signals

Example evidence:
- diagnostic scoring
- treatment recommendation language
- device control interfaces
- FDA, SaMD, IEC 62304, validation or traceability terms

Potential review areas:
- intended use claims
- validation evidence
- software lifecycle controls
- change control

## Absence-Based Findings

Use “not observed” findings only when a relevant feature is clearly present.

Good examples:
- AI feature code is present, but no model inventory, AI notice, or safety control evidence is observed.
- User profile and analytics code are present, but no delete/export/retention evidence is observed.
- Patient data structures are present, but no access audit trail or access-control evidence is observed.

Bad examples:
- Declaring a privacy-law violation just because the repo has no privacy policy file.
- Treating a dependency name alone as proof of regulated processing.

## Severity Guidance

- `High`: direct evidence of regulated processing plus missing controls that would likely require near-term review
- `Medium`: credible feature evidence with incomplete control coverage
- `Low`: weak or company-dependent relevance, or a precautionary review item
