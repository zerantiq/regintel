---
name: regintel
description: Regulatory compliance intelligence for software, AI, privacy, security, and disclosure obligations. Use when the user asks for regulatory updates, upcoming compliance deadlines, applicability analysis, or to scan a codebase or repository for potential issues under frameworks such as the EU AI Act, ISO/IEC 42001, GDPR, UK GDPR, CCPA/CPRA, HIPAA, PCI DSS, SEC cyber disclosure rules, FDA software obligations, SOX, DORA, NIS2, NIST AI RMF, or global privacy regimes. Triggers include "regulatory update", "what changed", "what do we need to fix", "upcoming compliance deadline", "scan this repo", "check this codebase for GDPR", "does this software raise HIPAA issues", "check for DORA compliance", and "what regulatory problems exist in this software".
---

# Regintel

Provide compliance intelligence for software products and engineering organizations. Work in three modes: repo scan mode for codebase-specific risk discovery, regulatory update mode for current developments, and continuous monitoring mode for recurring tracking.

## Mode Selection

- Use **repo scan mode** when the user wants to inspect a codebase, repository, application, or product implementation for potential regulatory issues.
- Use **regulatory update mode** when the user wants to understand what changed, what is upcoming, or what deadlines and enforcement milestolds matter.
- Use **continuous monitoring mode** when the user wants recurring snapshots, trend tracking, dashboards, or scheduled CI monitoring.
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

### 3. Run the AST Structural Scanner

When the scan path contains Python, TypeScript, Java, Go, or .NET/C# source files, run the structural scanner to detect function-level patterns that regex scanning cannot reliably find:

```bash
python3 SKILL_DIR/scripts/ast_signal_scan.py --path TARGET_REPO > /tmp/regintel-ast.json
```

- Read `structural_findings` in the output for PII-in-return-value, unlogged-db-write, and unencrypted-storage-write findings.
- Each finding includes the function name, file path, and line number for direct inspection.
- Python analysis uses stdlib AST parsing; TypeScript/Java/Go/.NET analysis uses structural function-block parsing.
- Incorporate these findings into the agent review step alongside regex-based signal evidence.

### 4. Run the Applicability Scorer

Run the scorer automatically to compute framework-level priorities:

```bash
python3 SKILL_DIR/scripts/applicability_score.py --signals /tmp/regintel-scan.json --format json > /tmp/regintel-applicability.json
```

- If the user provides company context (jurisdictions, public-company status, healthcare customers, etc.), save it as JSON and pass `--company <path>`.
- Read the resulting JSON for scored frameworks, review areas, and confidence notes.

### 5. Review Evidence with Agent Judgment

The script output is a starting point. Refine it with your own code reading:

- For each high-scoring signal, open the cited files in TARGET_REPO and verify the match is meaningful, not a keyword coincidence.
- Dismiss signals that come only from documentation describing regulatory concepts rather than implementing regulated processing.
- Look for patterns the scripts may miss: implicit data flows, third-party integrations, deployment configurations, and architectural decisions.
- Add findings the scripts cannot detect: missing controls, architectural gaps, and business-logic risks.
- Use `SKILL_DIR/references/repo-scan-signals.md` and `SKILL_DIR/references/applicability-signals.md` to guide your review.

This agent review step is what separates Regintel from a raw keyword scan.

### 6. Draft Findings Carefully

- Cite concrete repo evidence for every finding. Include file paths and, when possible, the exact symbol, setting, schema, or log/event name that triggered the concern.
- Allow absence-based findings only when the repo clearly implements a relevant feature and the expected control is not observed anywhere in the in-scope evidence.
- Describe issues as likely gaps, missing controls, or areas to review. Do not claim definitive non-compliance from repo evidence alone.
- Separate confirmed facts from inference. Mark company-level or deployment-level assumptions explicitly.

### 7. Map to Frameworks and Deadlines

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

## Continuous Monitoring Mode

### 1. Build Current Monitoring Inputs

- Run `repo_signal_scan.py`, `ast_signal_scan.py`, and `applicability_score.py` for the target repo.
- If feed sync is configured, run `sync_regulatory_feeds.py` and pass the result to `check_deadlines.py`.

### 2. Store Snapshot History

- Run `snapshot_store.py` with the current scan outputs and a stable snapshot directory.
- Use `--tag nightly` (or equivalent) for scheduled runs.
- Use the returned `trend` section to identify baseline movement from the previous snapshot.

### 3. Generate Trend and Dashboard Artifacts

- Run `trend_report.py` over the snapshot directory to summarize score/control movement over time.
- Run `dashboard_report.py` to produce markdown or HTML monitoring views.
- Use `change_diff.py` between the two latest snapshots for concise baseline deltas in CI logs.

### 4. Enforce Policy Gates

- Run `compliance_gate.py` with a policy JSON to enforce acceptable risk thresholds in CI.
- Use gate checks for not-observed controls, urgent deadlines, structural findings, required/forbidden signals, and framework-score trends.
- Treat non-zero exit as a release/merge gate failure unless explicitly running in report-only mode.

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

## Script Execution

The agent runs these scripts automatically as part of the skill workflow. The user does not need to run any commands. All script paths are relative to `SKILL_DIR`.

| Script | When to Run | Command |
|---|---|---|
| `repo_signal_scan.py` | Always, as the first step of every repo scan | `python3 SKILL_DIR/scripts/repo_signal_scan.py --path TARGET_REPO --scope full` |
| `ast_signal_scan.py` | After the signal scan, when the repo contains Python/TypeScript/Java/Go/.NET-C# source files | `python3 SKILL_DIR/scripts/ast_signal_scan.py --path TARGET_REPO` |
| `applicability_score.py` | Always, immediately after the signal scan | `python3 SKILL_DIR/scripts/applicability_score.py --signals <scan.json> --format json` |
| `check_deadlines.py` | When regulatory developments with dates are available | `python3 SKILL_DIR/scripts/check_deadlines.py --input <developments.json> --format markdown` |
| `change_diff.py` | When comparing two snapshots (before/after scans or regulatory updates) | `python3 SKILL_DIR/scripts/change_diff.py --old <old.json> --new <new.json> --format markdown` |
| `sync_regulatory_feeds.py` | When external feed-based development updates are needed | `python3 SKILL_DIR/scripts/sync_regulatory_feeds.py --config <feed-config.json> --format json` |
| `snapshot_store.py` | When persisting a monitoring snapshot | `python3 SKILL_DIR/scripts/snapshot_store.py --scan <scan.json> --snapshot-dir <snapshot-dir>` |
| `trend_report.py` | When summarising movement across snapshots | `python3 SKILL_DIR/scripts/trend_report.py --snapshot-dir <snapshot-dir> --format markdown` |
| `dashboard_report.py` | When rendering a monitoring dashboard | `python3 SKILL_DIR/scripts/dashboard_report.py --snapshot-dir <snapshot-dir> --format html --output <dashboard.html>` |
| `compliance_gate.py` | When enforcing policy thresholds in CI/release workflows | `python3 SKILL_DIR/scripts/compliance_gate.py --policy <policy.json> --scan <scan.json> --format markdown` |

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
