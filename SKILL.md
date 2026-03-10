---
name: regintel
description: Regulatory compliance intelligence for software, AI, privacy, security, and disclosure obligations. Use when the user asks for regulatory updates, upcoming compliance deadlines, applicability analysis, or to scan a codebase or repository for potential issues under frameworks such as the EU AI Act, GDPR, HIPAA, SEC cyber disclosure rules, FDA software obligations, SOX, or global privacy regimes. Triggers include "regulatory update", "what changed", "what do we need to fix", "upcoming compliance deadline", "scan this repo", "check this codebase for GDPR", "does this software raise HIPAA issues", and "what regulatory problems exist in this software".
---

# Regintel

Provide compliance intelligence for software products and engineering organizations. Work in one of two modes: regulatory update mode for current developments and repo scan mode for codebase-specific risk discovery.

## Mode Selection

- Use **repo scan mode** when the user wants to inspect a codebase, repository, application, or product implementation for potential regulatory issues.
- Use **regulatory update mode** when the user wants to understand what changed, what is upcoming, or what deadlines and enforcement milestones matter.
- Combine both modes when the user wants a repo scan tied to current effective dates or upcoming obligations.

## Repo Scan Mode

### 1. Determine Scope

- Default to the current repo root.
- Support `diff` scope when the user wants to inspect only changed files.
- Support a user-specified file or directory when the request is narrow.
- Treat first-party source, configuration, schemas, infrastructure definitions, and compliance-relevant docs as in scope.

### 2. Discover Evidence

- Prefer `rg --files` and `rg -n` style discovery over broad manual browsing.
- Exclude `.git`, `node_modules`, `dist`, `build`, `.next`, coverage folders, generated artifacts, vendored code, snapshots, minified assets, and lockfiles unless a lockfile is the only plausible source of a first-party compliance signal.
- Prioritize files such as application code, API routes, OpenAPI schemas, GraphQL schemas, deployment manifests, IaC files, environment templates, policy docs, privacy docs, architecture notes, and onboarding docs.
- Use `scripts/repo_signal_scan.py` to inventory evidence before drafting conclusions when the repo is more than a few files or the regulatory surface is mixed.

### 3. Infer Product and Obligation Signals

- Use `references/repo-scan-signals.md` to map code and config patterns to likely obligations.
- Use `references/applicability-signals.md` to infer product profile, geography, sector, data sensitivity, AI usage, and reporting posture.
- Use `scripts/applicability_score.py` with repo-scan output and optional company context when the applicability picture is mixed or disputed.

### 4. Draft Findings Carefully

- Cite concrete repo evidence for every finding. Include file paths and, when possible, the exact symbol, setting, schema, or log/event name that triggered the concern.
- Allow absence-based findings only when the repo clearly implements a relevant feature and the expected control is not observed anywhere in the in-scope evidence.
- Describe issues as likely gaps, missing controls, or areas to review. Do not claim definitive non-compliance from repo evidence alone.
- Separate confirmed facts from inference. Mark company-level or deployment-level assumptions explicitly.

### 5. Map to Frameworks and Deadlines

- Use `references/frameworks.md` for obligation framing and applicability boundaries.
- Use `scripts/check_deadlines.py` when current developments have concrete milestone dates.
- If the user asks for live dates, current enforcement posture, or recent changes, verify them with authoritative web sources before finalizing. Distinguish proposed, adopted, effective, and enforcement states.

## Regulatory Update Mode

### 1. Identify the Development

- Pin down the framework, jurisdiction, and development stage.
- Confirm whether the item is proposed, adopted, effective, entering enforcement, or subject to a reporting deadline.

### 2. Explain Practical Impact

- Translate the development into software, product, data governance, security, disclosure, or operational consequences.
- Tie the analysis to the user’s product profile if it is known. Otherwise, state the key assumptions.

### 3. Surface Time-Sensitive Warnings

- Use `references/warning-thresholds.md` to label the urgency.
- Use `scripts/change_diff.py` when comparing a new summary to a prior snapshot.
- Use visible warnings when a transition window is ending, enforcement is near, or a reporting deadline is approaching.

## Output Format

For repo scans, use this structure:

### Regulatory Scan Summary
State what was scanned and the overall risk picture.

### Applicability
Explain which frameworks appear relevant, what is confirmed by evidence, and what still depends on company context.

### Potential Repo Findings
List evidence-backed findings. For each finding, include severity, framework, file/path evidence, and why it matters.

### Issues to Address
List likely gaps or controls to review.

### Recommended Fixes / Next Actions
Group actions by engineering, product, security, legal/compliance, and leadership when relevant.

### Warning
Highlight near-term dates, enforcement milestones, or immediate review triggers.

### Urgency
Use `Low`, `Medium`, `High`, or `Critical`.

### Confidence / Assumptions
State what is inferred, what is missing, and how that affects confidence.

For regulatory updates, use the same structure but rename the first section `Regulatory Update`.

## Script Usage

- Use `scripts/repo_signal_scan.py --path . --scope full` for default repo scans.
- Use `scripts/repo_signal_scan.py --path . --scope diff` for changed-file analysis in a git repo.
- Use `scripts/repo_signal_scan.py --path path/to/file_or_dir --scope path` for narrow scans.
- Use `scripts/applicability_score.py --signals scan.json --company company.json` when company context is available.
- Use `scripts/check_deadlines.py --input developments.json` to annotate milestone urgency.
- Use `scripts/change_diff.py --old old.json --new new.json` to summarize what changed between regulatory snapshots or scan outputs.

## Bundled References

Load only the references needed for the task.

- `references/frameworks.md` for framework scope, gating assumptions, and milestone handling.
- `references/output-patterns.md` for response examples.
- `references/applicability-signals.md` for company and codebase heuristics.
- `references/warning-thresholds.md` for warning labels and urgency rules.
- `references/repo-scan-signals.md` for evidence patterns to inspect in software repos.
- `references/script-schemas.md` for JSON contracts used by the scripts.

## Guardrails

- Provide compliance intelligence and operational guidance, not formal legal advice.
- Never present proposed rules as active obligations.
- Never collapse jurisdiction-specific duties into a universal rule.
- Never over-weight third-party dependency names when first-party code and configuration are silent.
- Mark low-confidence frameworks clearly when applicability depends on business model, public-company status, regulated-data handling, or deployment facts not visible in the repo.
