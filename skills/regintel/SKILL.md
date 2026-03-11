---
name: regintel
description: Regulatory compliance intelligence for software, AI, privacy, security, and disclosure obligations. Use when the user asks for regulatory updates, upcoming compliance deadlines, applicability analysis, or to scan a codebase or repository for potential issues under frameworks such as the EU AI Act, GDPR, HIPAA, SEC cyber disclosure rules, FDA software obligations, SOX, DORA, NIS2, NIST AI RMF, or global privacy regimes. Triggers include "regulatory update", "what changed", "what do we need to fix", "upcoming compliance deadline", "scan this repo", "check this codebase for GDPR", "does this software raise HIPAA issues", "check for DORA compliance", and "what regulatory problems exist in this software".
---

# Regintel

Provide compliance intelligence for software products and engineering organizations. Work in one of two modes: regulatory update mode for current developments and repo scan mode for codebase-specific risk discovery.

## Mode Selection

- Use **repo scan mode** when the user wants to inspect a codebase, repository, application, or product implementation for potential regulatory issues.
- Use **regulatory update mode** when the user wants to understand what changed, what is upcoming, or what deadlines and enforcement milestolds matter.
- Combine both modes when the user wants a repo scan tied to current effective dates or upcoming obligations.

## Repo Scan Mode

When the user asks for a regulatory scan, run the full pipeline automatically. Do not ask the user to run commands.

### Path Resolution

This skill is typically installed outside the repo being scanned. Resolve two paths before starting:

- **SKILL_DIR**: the directory containing this `SKILL.md` file (where `scripts/`, `references/`, and `examples/` live)
- **TARGET_REPO**: the repo the user wants scanned (usually the user's current working directory)

All script commands below use `SKILL_DIR` for tool paths and `TARGET_REPO` for scan targets.

### 1. Determine Scope

- Default to the current repo root.
- Support `diff` scope when the user wants to inspect only changed files.
- Support a user-specified file or directory when the request is narrow.
- Treat first-party source, configuration, schemas, infrastructure definitions, and compliance-relevant docs as in scope.

### 2. Run the Signal Scan

Run the scanner automatically to inventory repo-level evidence:

```bash
python3 SKILL_DIR/scripts/repo_signal_scan.py --path TARGET_REPO --scope full > /tmp/regintel-scan.json
```

- Use `--scope diff` when the user wants to inspect only changed files.
- Use `--scope path` with a specific file or directory for narrow scans.
- Use `--focus <framework>` to filter signals to a single framework when the user asks about a specific one.
- Read the resulting JSON to understand what signals, frameworks, and control observations were found.

### 3. Run the Applicability Scorer

Run the scorer automatically to compute framework-level priorities:

```bash
python3 SKILL_DIR/scripts/applicability_score.py --signals /tmp/regintel-scan.json --format json > /tmp/regintel-applicability.json
```

- If the user provides company context (jurisdictions, public-company status, healthcare customers, etc.), save it as JSON and pass `--company <path>`.
- Read the resulting JSON for scored frameworks, review areas, and confidence notes.

### 4. Review Evidence with Agent Judgment

The script output is a starting point. Refine it with your own code reading:

- For each high-scoring signal, open the cited files in TARGET_REPO and verify the match is meaningful, not a keyword coincidence.
- Dismiss signals that come only from documentation describing regulatory concepts rather than implementing regulated processing.
- Look for patterns the scripts may miss: implicit data flows, third-party integrations, deployment configurations, and architectural decisions.
- Add findings the scripts cannot detect: missing controls, architectural gaps, and business-logic risks.
- Use `SKILL_DIR/references/repo-scan-signals.md` and `SKILL_DIR/references/applicability-signals.md` to guide your review.

This agent review step is what separates Regintel from a raw keyword scan.

### 5. Draft Findings Carefully

- Cite concrete repo evidence for every finding. Include file paths and, when possible, the exact symbol, setting, schema, or log/event name that triggered the concern.
- Allow absence-based findings only when the repo clearly implements a relevant feature and the expected control is not observed anywhere in the in-scope evidence.
- Describe issues as likely gaps, missing controls, or areas to review. Do not claim definitive non-compliance from repo evidence alone.
- Separate confirmed facts from inference. Mark company-level or deployment-level assumptions explicitly.

### 6. Map to Frameworks and Deadlines

- Use `SKILL_DIR/references/frameworks.md` for obligation framing and applicability boundaries.
- If regulatory developments with milestone dates are available, run `python3 SKILL_DIR/scripts/check_deadlines.py --input <developments.json> --format markdown` automatically to annotate urgency.
- If the user asks for live dates, current enforcement posture, or recent changes, verify them with authoritative web sources before finalizing. Distinguish proposed, adopted, effective, and enforcement states.

## Regulatory Update Mode

### 1. Identify the Development

- Pin down the framework, jurisdiction, and development stage.
- Confirm whether the item is proposed, adopted, effective, entering enforcement, or subject to a reporting deadline.

### 2. Explain Practical Impact

- Translate the development into software, product, data governance, security, disclosure, or operational consequences.
- Tie the analysis to the user's product profile if it is known. Otherwise, state the key assumptions.

### 3. Surface Time-Sensitive Warnings

- Use `SKILL_DIR/references/warning-thresholds.md` to label the urgency.
- Use `SKILL_DIR/scripts/change_diff.py` when comparing a new summary to a prior snapshot.
- Use visible warnings when a transition window is ending, enforcement is near, or a reporting deadline is approaching.

## Output Format

Begin every full response with this exact banner in a fenced `text` block:

```text
███████╗███████╗██████╗  █████╗ ███╗   ██╗████████╗██╗ ██████╗ 
╚══███╔╝██╔════╝██╔══██╗██╔══██╗████╗  ██║╚══██╔══╝██║██╔═══██╗
  ███╔╝ █████╗  ██████╔╝███████║██╔██╗ ██║   ██║   ██║██║▄▄▄██║
 ███╔╝  ██╔══╝  ██╔══██╗██╔══██║██║╚██╗██║   ██║   ██║██║██╗██║
███████╗███████╗██║  ██║██║  ██║██║ ╚████║   ██║   ██║╚██████╔╝
╚══════╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝   ╚═╝ ╚══▀▀╚═╝
```

For repo scans, prefer this richer markdown structure:

### Regulatory Scan Summary
Start with 2 short prose lines:

- `Scanned:` what was scanned, including the repo path/scope and a plain-English description of the product or platform.
- `Overall Risk Picture:` the current risk level and a concrete summary of the sensitive data/processes or missing controls driving that view.

### Executive Snapshot
Use a 2-column table for scope, top frameworks, overall urgency, and confidence.

### Severity Legend
Use these badges consistently: `🚨 Critical`, `🔴 High`, `🟠 Medium`, `🟡 Low`, `🔵 Info`.

### Applicability
Use a markdown table with: framework, applicability, and confidence. The applicability cell should say why the framework is relevant in plain English, not just a score.

### Key Findings
Use a markdown table with these required columns: severity badge, regulatory framework, evidence (where it is found), and why it matters. Add owner/team only if it improves the clarity.

### Action Plan
Use a markdown table with: priority, team, action, and evidence trigger.

### Deadlines & Warnings
When dates exist, use a markdown table with: date/milestone, framework, warning badge, urgency, and what needs review.

### Open Questions / Assumptions
Use short bullets for missing deployment facts, jurisdiction assumptions, or company-context unknowns.

Formatting rules:

- Default to tables when comparing frameworks, findings, or actions.
- Make the opening scan summary concrete and repo-specific; avoid generic statements like "several issues were found."
- Put the most important 3-6 findings in the primary findings table; move lower-signal items to a short `Additional Observations` list only if needed.
- Avoid empty sections and generic filler text.
- Use emoji badges for severity, urgency, warnings, pass/fail status, and trend direction when relevant.
- Keep evidence concrete: file paths, symbols, routes, config keys, schema fields, or log/event names.

For regulatory updates, keep the same visual style but rename the first section `Regulatory Update Snapshot` and include stage/status plus exact dates in the snapshot table.

## Script Execution

The agent runs these scripts automatically as part of the skill workflow. The user does not need to run any commands. All script paths are relative to `SKILL_DIR`.

| Script | When to Run | Command |
|---|---|---|
| `repo_signal_scan.py` | Always, as the first step of every repo scan | `python3 SKILL_DIR/scripts/repo_signal_scan.py --path TARGET_REPO --scope full` |
| `applicability_score.py` | Always, immediately after the signal scan | `python3 SKILL_DIR/scripts/applicability_score.py --signals <scan.json> --format json` |
| `check_deadlines.py` | When regulatory developments with dates are available | `python3 SKILL_DIR/scripts/check_deadlines.py --input <developments.json> --format markdown` |
| `change_diff.py` | When comparing two snapshots (before/after scans or regulatory updates) | `python3 SKILL_DIR/scripts/change_diff.py --old <old.json> --new <new.json> --format markdown` |

## Bundled References

Load only the references needed for the task. All paths are relative to `SKILL_DIR`.

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
