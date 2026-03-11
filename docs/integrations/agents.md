# Agent Integrations

Regintel supports agent-first workflows and also ships standalone CLI entry points.

## Claude Code

- Marketplace plugin via `conductor.json` and `.claude-plugin/plugin.json`
- Local skill install via `skills/regintel/SKILL.md`

## OpenAI Codex

- Agent manifest: `agents/openai.yaml`
- Implicit skill invocation enabled for repository scans and follow-up checks

## Integration Pattern

1. Agent runs `regintel-scan` and `regintel-applicability`.
2. Optional follow-up tools run based on context (`regintel-ast-scan`, `regintel-deadlines`, `regintel-diff`).
3. Monitoring and release pipelines run (`regintel-snapshot`, `regintel-trend`, `regintel-gate`).

Use the JSON `meta` block as the compatibility check for tool-chain integrations.
