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

## v0.3 — Structured Code Analysis

Goals:
- Add optional AST-based scanning for Python and TypeScript to detect data flows, not just keywords
- Detect function-level patterns: PII field usage in return values, unlogged database writes, unencrypted storage calls
- Support Tree-sitter or Semgrep rule integration for language-agnostic structural matching
- Reduce false positives from comments, docstrings, and string literals that match signal patterns

## v0.4 — Extended Framework and Jurisdiction Support

Goals:
- Add ISO 42001 (AI management system), CCPA/CPRA detailed rules, PCI DSS software signals
- Support jurisdiction-specific rule variants (e.g., GDPR vs. UK GDPR, state-by-state U.S. privacy)
- Add infrastructure scanning for Terraform, Bicep, Helm, and CloudFormation templates
- Support Go, Java, C#, and Rust source scanning with language-specific heuristics

## v0.5 — Continuous Monitoring and Reporting

Goals:
- Track scan results over time with snapshot storage and trend reporting
- Support scheduled scans via CI integration with baseline comparison
- Add a lightweight HTML/Markdown dashboard for scan result browsing
- Integrate with regulatory data feeds for automatic deadline updates

## v1.0 — Stable Release

Goals:
- Stable script interfaces with semantic versioning guarantees
- Comprehensive test coverage across all supported frameworks and languages
- Published to PyPI for `pip install` adoption
- Full documentation site with tutorials and integration guides

## Non-Goals

These remain explicitly out of scope:
- Formal legal advice or compliance certification
- Deep runtime data-flow analysis or taint tracking
- Replacing human legal and compliance review

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to help with any of these milestones. The most impactful near-term contributions are better heuristics with fewer false positives, new fixture repos, and stronger reference material.
