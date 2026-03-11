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

### Encryption and Key Management

Example evidence:
- AES-256, TLS configuration, SSL certificates
- KMS, Key Vault, secret manager integrations
- bcrypt, hashing, encryption-at-rest settings

Potential review areas:
- key rotation policies
- encryption at rest and in transit
- certificate management and expiry

### Infrastructure-as-Code and Deployment

Example evidence:
- Terraform, Bicep, CloudFormation, Helm, Kustomize
- Dockerfile, docker-compose configurations
- Kubernetes manifests, deployment pipelines

Potential review areas:
- change management and drift detection
- environment isolation
- secret injection and management

### Financial Reporting and Internal Controls

Example evidence:
- general ledger, journal entries, ERP integrations
- segregation of duties, approval workflows
- financial reports, reconciliation logic

Potential review areas:
- access control and least privilege
- approval evidence and audit trails
- change management

### ICT Risk and Resilience (DORA)

Example evidence:
- ICT risk management policies, resilience testing, disaster recovery plans
- failover, circuit breaker, business continuity
- third-party risk assessments

Potential review areas:
- ICT risk framework completeness
- resilience and penetration testing
- third-party ICT oversight
- incident classification and reporting

### Network Security and Critical Infrastructure (NIS2)

Example evidence:
- firewall rules, WAF configuration, DDoS protection
- intrusion detection, vulnerability scanning, patch management
- supply chain security, SBOM generation

Potential review areas:
- network security policies
- supply chain risk management
- vulnerability handling and disclosure
- incident notification compliance

### AI Risk Management (NIST AI RMF)

Example evidence:
- model cards, dataset cards, bias evaluation
- fairness testing, explainability documentation
- AI impact assessments, AI risk documentation

Potential review areas:
- AI risk assessment and categorization
- bias and fairness evaluation
- model documentation and transparency
- continuous monitoring

## Structural Code Signals (AST-Based)

Run `ast_signal_scan.py` for function-level patterns that regex scanning cannot reliably detect.

### PII in Return Values

Example evidence:
- Function returns a dict literal with keys like `email`, `phone`, `first_name`, `dob`
- Function returns `user.email` or another PII attribute directly
- Function returns a variable whose name is a PII field name

Why it matters:
- Exposes personal data to callers without data minimisation
- Each call site becomes a potential disclosure or logging point
- Relevant to GDPR data minimisation, HIPAA minimum-necessary, and CCPA/state-privacy obligations

### Database Writes Without Audit Logging

Example evidence:
- Function calls `.execute()`, `.save()`, `.delete()`, `.commit()`, or ORM write methods
- No logging call (`.info()`, `.warning()`, `.audit_log()`, etc.) is present in the same function

Why it matters:
- Sensitive data mutations without audit trails are a common HIPAA, SOX, and GDPR gap
- Missing write logs limit incident investigation and compliance reporting

### Storage Writes Without Encryption Indicators

Example evidence:
- `open(path, "w")` or `open(path, "wb")` calls with no encryption context
- S3 `put_object()` or `upload_file()` calls with no `ServerSideEncryption` or KMS key argument

Why it matters:
- Unencrypted file or object writes may violate GDPR, HIPAA, DORA, and NIS2 storage obligations
- Absence of encryption indicators does not confirm a violation, but flags a control gap to verify

### False-Positive Reduction (v0.3+)

The regex scanner skips lines inside Python module, class, and function docstrings. This reduces
false positives when regulatory terms like `email`, `patient`, or `consent` appear only in
documentation prose. String constants that are part of executable code (dict keys, assignments,
return values) are not filtered and continue to score as evidence.

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
