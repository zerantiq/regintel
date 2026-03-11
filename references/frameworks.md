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

### ISO/IEC 42001 (AI Management System)

- Likely relevant when the repo includes AI governance policy artifacts, management-review evidence, internal-audit language, or AIMS terminology.
- Strong repo signals:
  - `ISO/IEC 42001`, `AI management system`, `AIMS`, `internal audit`, `management review`, `AI policy`, `AI risk treatment`
- Likely review areas:
  - AIMS scope and boundaries
  - governance roles and accountability
  - risk treatment controls
  - internal audit and continuous improvement
- ISO/IEC 42001 is a management-system standard and does not itself determine statutory legal scope.

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

### UK GDPR (DPA 2018 Context)

- Likely relevant when the software processes personal data tied to UK users, UK entities, or UK-hosted operations.
- Strong repo signals:
  - `UK GDPR`, `Data Protection Act 2018`, `ICO`, `IDTA`, UK addendum language
  - UK-specific rights forms and transfer-mechanism references
- Likely review areas:
  - UK privacy notices and lawful basis
  - UK rights handling (access, deletion, correction)
  - UK international-transfer mechanisms
  - security controls and breach handling
- Treat UK GDPR scope as inferred unless UK jurisdiction is confirmed in company context.

### U.S. State Privacy / CPRA-style Obligations

- Likely relevant when the repo suggests consumer-facing data collection, advertising/analytics, sharing with vendors, or user rights workflows.
- Strong repo signals:
  - consumer profiles, analytics/ads SDKs, sale/share language, opt-out flags, cookie or tracking controls
- Likely review areas:
  - notice at collection
  - opt-out and preference management
  - contracts with vendors/service providers
  - rights intake, deletion, and access workflows

### CCPA / CPRA (California)

- Likely relevant when California consumers are in scope and the repo references rights-specific controls.
- Strong repo signals:
  - `Do Not Sell or Share`, `Global Privacy Control`, `sensitive personal information`, `notice at collection`, `service provider`, `contractor`
- Likely review areas:
  - do-not-sell/share controls
  - GPC signal handling
  - sensitive PI limitation and use restrictions
  - service-provider and contractor restrictions

### Virginia CDPA / Colorado Privacy Act Variants

- Likely relevant when jurisdiction evidence points to state-specific obligations beyond California.
- Strong repo signals:
  - state-targeted rights flows, universal opt-out handling, processor contract language, state-specific policy variants
- Likely review areas:
  - state-specific notice and rights handling
  - opt-out mechanisms and consent logic
  - controller/processor contract workflows
- State-by-state applicability is low confidence without confirmed jurisdiction exposure.

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

### PCI DSS

- Likely relevant when the repo handles payment-card data, cardholder records, or PCI control language.
- Strong repo signals:
  - `PCI DSS`, `cardholder data`, `card number`, `CVV/CVC`, `payment card`, `tokenization`, `3D Secure`, SAQ references
- Likely review areas:
  - cardholder-data inventory and minimization
  - encryption and key-management controls
  - access logging and monitoring
  - incident response for payment environments
- Treat PCI scope as inferred unless cardholder-data processing is confirmed by company context.

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

### DORA (Digital Operational Resilience Act)

- Likely relevant when the entity is a financial institution or ICT third-party service provider operating in the EU.
- Strong repo signals:
  - ICT risk management, resilience testing, disaster recovery, failover, circuit breaker, third-party risk management, business continuity
  - incident response with financial context, encryption, key management
- Likely review areas:
  - ICT risk framework and governance
  - resilience and penetration testing
  - third-party ICT service provider oversight
  - incident detection, reporting, and classification
  - information sharing arrangements
- Financial-entity status is a major gating factor. Mark as inferred unless company context confirms.

### NIS2 (Network and Information Security Directive)

- Likely relevant when the entity operates essential or important services in the EU (energy, transport, health, digital infrastructure, ICT services, etc.).
- Strong repo signals:
  - firewall, WAF, DDoS protection, intrusion detection, vulnerability scanning, patch management, supply chain security
  - incident notification, network security policies
- Likely review areas:
  - risk analysis and security policies
  - incident handling and reporting (24h early warning, 72h notification)
  - business continuity and crisis management
  - supply chain security
  - vulnerability handling and disclosure
- Entity classification as essential or important is a major gating factor.

### NIST AI RMF (AI Risk Management Framework)

- Relevant when the organization deploys AI systems and wants to align with the NIST AI Risk Management Framework.
- Strong repo signals:
  - model cards, dataset cards, bias evaluation, fairness testing, explainability, AI impact assessments, AI risk documentation
  - model inventory, evaluation harnesses, human oversight mechanisms
- Likely review areas:
  - AI risk assessment and categorization
  - bias and fairness evaluation
  - model documentation and transparency
  - explainability and interpretability
  - continuous monitoring and governance
- NIST AI RMF is voluntary but increasingly referenced as a baseline by U.S. regulators.

## Milestone Handling

- Verify dates from current authoritative sources when the user asks for live deadlines or “latest” status.
- Tie warnings to concrete milestones only:
  - effective date
  - enforcement start
  - transition end
  - reporting deadline
- Use `references/warning-thresholds.md` and `scripts/check_deadlines.py` for urgency labeling.
