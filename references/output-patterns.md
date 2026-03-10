# Output Patterns

Use these patterns to keep responses practical and evidence-backed.

## Repo Scan Pattern

### Regulatory Scan Summary
Scanned the application repo for first-party evidence of AI, privacy, healthcare, and disclosure-sensitive obligations. The strongest signals point to GDPR and EU AI Act review, with lower-confidence healthcare obligations that depend on deployment context.

### Applicability
- **GDPR**: likely relevant because the repo includes account data, analytics, cookie handling, and delete/export endpoints.
- **EU AI Act**: likely relevant because the repo integrates third-party model APIs and prompt orchestration.
- **HIPAA**: possible only if the customer environment actually includes PHI; the repo contains healthcare terms but not enough to confirm covered workflows.

### Potential Repo Findings
- **High | GDPR | `apps/api/routes/users.ts`**
  User profile and analytics events appear to collect personal data, but no retention or deletion policy was observed in the scanned repo. This suggests a likely review area around storage limitation and user-rights workflows.
- **Medium | EU AI Act | `services/llm/client.py`**
  The product uses external model providers and prompt templates, but no model inventory, safety review, or AI-specific notice path was observed. This suggests a likely governance gap to review.

### Issues to Address
- Document retention, deletion, and export behavior.
- Review AI feature inventory and user transparency.
- Confirm whether healthcare-related fields process PHI in production.

### Recommended Fixes / Next Actions
- Engineering: map data stores, retention settings, and delete/export code paths.
- Product: inventory AI-assisted features and user-facing disclosures.
- Security: verify logging, incident escalation, and vendor controls.
- Legal/Compliance: confirm geography, public-company status, and HIPAA/FDA exposure.

### Warning
Action Needed Soon: if EU AI Act milestones apply to the deployed feature set, verify current dates before release planning.

### Urgency
High

### Confidence / Assumptions
Medium confidence. The assessment relies on repo evidence and does not confirm production data categories, customer profile, or legal entity status.

## Regulatory Update Pattern

### Regulatory Update
Explain what changed, whether the change is proposed, adopted, effective, or entering enforcement, and what software teams need to revisit.

### Applicability
State who is likely affected and what assumptions drive that view.

### Why It Matters
Connect the change to engineering, product, data governance, security, or disclosure processes.

### Issues to Address
List the main review items.

### Recommended Fixes / Next Actions
Assign actions across legal/compliance, security, engineering, product, and leadership.

### Warning
Use one of: `Monitor`, `Upcoming Change`, `Action Needed Soon`, `High Priority`, `Critical Deadline`.

### Urgency
Use one of: `Low`, `Medium`, `High`, `Critical`.

### Confidence / Assumptions
Explain missing context, deployment unknowns, or unsettled legal interpretation.
