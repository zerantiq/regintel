# Roadmap

This document outlines the planned evolution of Regintel. Priorities may shift based on community feedback and real-world scan results.

## ✅ v0.1 — Initial Release

Status: **complete**

Delivered:
- Core repo-signal scanner with pattern-based heuristics across 7 frameworks
- Applicability scoring with optional company context
- Deadline urgency labeling for regulatory developments
- Snapshot diff tool for tracking changes between scans
- AI-saas, healthcare, and low-risk fixture repos with regression tests
- Claude Code, Antigravity, and OpenAI Codex agent integrations
- CI pipeline with structure validation and test suite
- Reference documentation for frameworks, signals, and schemas

## ✅ v0.2 — Stronger Heuristics and Broader Coverage

Status: **complete**

Delivered:
- Reduced false positives through evidence-class weighting and dependency-noise filtering
- Dismissed documentation-only matches that describe regulatory concepts without implementing regulated processing
- Added new signal categories: encryption and key management, infrastructure-as-code, financial reporting controls
- Expanded framework coverage to include DORA, NIS2, and NIST AI RMF
- Added fintech and IoT fixture repos for broader regression testing
- Enhanced CI with Python version matrix testing (3.10, 3.12, 3.13)
- Published example scan reports for common repo archetypes

## ✅ v0.3 — Structured Code Analysis

Status: **complete**

Delivered:
- New `ast_signal_scan.py` script using Python stdlib `ast` for zero-dependency structural analysis
- Detects three function-level patterns: PII fields in return values, database writes without audit logging, and file/storage writes without encryption indicators
- Each finding cites the function name, file path, and line number for direct inspection
- Python string-literal and docstring filtering added to `repo_signal_scan.py` to reduce false positives from regulatory keywords mentioned only in documentation strings
- Updated `references/repo-scan-signals.md` with structural signal categories and guidance
- Updated `references/script-schemas.md` with `ast_signal_scan.py` JSON output schema
- Updated `SKILL.md` pipeline to run `ast_signal_scan.py` after the signal scan when Python source files are present
- Regression tests covering all three structural findings, field validation, false-positive suppression, and markdown output
- Tree-sitter support for TypeScript deferred to v0.4 (optional dependency; Python stdlib AST covers the primary use case)

## ✅ v0.4 — Extended Framework and Jurisdiction Support

Status: **complete**

Delivered:
- Added new framework mappings: ISO/IEC 42001, UK GDPR, CCPA/CPRA, Virginia CDPA, Colorado Privacy Act, and PCI DSS
- Added dedicated signal categories for ISO 42001 AI management controls, CCPA/CPRA rights controls, and PCI card-data handling
- Added jurisdiction-specific scoring boosts and assumptions in `applicability_score.py` for UK and state-level U.S. privacy variants
- Expanded infrastructure file scanning to include Terraform (`.tf`, `.tfvars`), Bicep (`.bicep`), Helm chart files, and CloudFormation templates
- Improved evidence classification so IaC and deployment templates are consistently labeled as `infra`
- Added language-specific source heuristics for Go, Java, C#, and Rust service code
- Added new control-observation rules for CPRA rights coverage and PCI cardholder-security controls
- Added a polyglot regulated fixture repo and regression tests for new frameworks, language heuristics, infra detection, and applicability scoring

## ✅ v0.5 — Continuous Monitoring and Reporting

Status: **complete**

Delivered:
- Added `snapshot_store.py` to persist timestamped scan snapshots with index management and baseline deltas
- Added `trend_report.py` for snapshot-history trend summaries across signals, controls, deadlines, and framework scores
- Added `dashboard_report.py` to generate lightweight monitoring dashboards in both Markdown and HTML
- Added `sync_regulatory_feeds.py` to ingest JSON/RSS/Atom regulatory feeds into the `developments` schema
- Added scheduled CI workflow (`.github/workflows/monitor.yml`) with nightly scan, snapshot history, trend/dashboard artifact output, and baseline diff generation
- Added monitoring regression tests and feed fixtures covering snapshot storage, trend reporting, dashboard rendering, and feed sync compatibility

## ✅ v0.6 — Policy Gates and Release Quality Controls

Status: **complete**

Delivered:
- Added `compliance_gate.py` for policy-driven pass/fail checks over scan, deadlines, AST findings, and trend outputs
- Added support for minimum framework scores, required/forbidden signals, maximum not-observed controls, urgent deadline limits, structural-finding limits, and trend-based framework-drop limits
- Added default policy template `examples/compliance-gate-policy.json` for CI and release gating
- Integrated policy-gate smoke validation into `.github/workflows/validate.yml`
- Integrated gate-result generation into `.github/workflows/monitor.yml` artifact outputs
- Added regression tests for pass/fail gate behavior and trend-drop detection
- Updated reference schemas and skill instructions to include gate usage

## ✅ v0.7 — Stable Release

Status: **complete**

Delivered:
- Added stable JSON interface metadata across machine-readable scripts via `meta.tool` + `meta.schema_version` (`1.0.0`) and documented semver compatibility rules
- Added release-contract regression coverage (`tests/test_v1_release.py`) for interface headers, full framework coverage across fixture repos, and console-script importability checks
- Upgraded packaging to `1.0.0`, promoted project classifiers to production/stable, and added `project.scripts` entry points for all core workflows
- Added documentation site scaffold (`mkdocs.yml` + `docs/`) with getting-started guidance, CI monitoring tutorial, pip CLI workflow, agent integration notes, and contract reference docs
- Updated reference schemas and README install guidance to reflect pip-based usage and v0.7 interface guarantees

## Non-Goals

These remain explicitly out of scope:
- Formal legal advice or compliance certification
- Deep runtime data-flow analysis or taint tracking
- Replacing human legal and compliance review

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to help with any of these milestones. The most impactful near-term contributions are better heuristics with fewer false positives, new fixture repos, and stronger reference material.
