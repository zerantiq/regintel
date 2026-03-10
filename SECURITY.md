# Security Policy

## Supported Scope

This repository contains:

- a Codex skill definition
- regulatory reference material
- helper scripts used for repo scanning and deadline analysis

Security-sensitive reports are especially relevant when they involve:

- unintended disclosure of sensitive data during scanning
- incorrect handling of private repo paths or output
- command execution or path traversal concerns
- logic that could materially mislead users about urgent security obligations

## Reporting a Vulnerability

Do not open a public issue with exploit details.

Preferred process:

1. Use GitHub private vulnerability reporting or a private maintainer channel if available.
2. Include a clear description, impact, affected files, reproduction steps, and any proof of concept.
3. Share the minimum detail needed for triage until a secure conversation is established.

If private reporting is not available, open a minimal public issue without exploit details and request a private contact path.

## Response Expectations

Maintainers should aim to:

- acknowledge receipt within a reasonable time
- confirm whether the report is in scope
- provide a remediation or disposition update when triage is complete

## What Not to Report Publicly

- exploit chains
- sensitive sample data
- internal tokens or credentials
- private repository contents that are not already public
