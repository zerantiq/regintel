#!/usr/bin/env python3
"""Evaluate policy-based compliance gates from Regintel analysis outputs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from ._contract import with_meta
except ImportError:
    from _contract import with_meta  # type: ignore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", required=True, help="Path to gate policy JSON.")
    parser.add_argument("--scan", required=True, help="Path to repo_signal_scan JSON output.")
    parser.add_argument("--deadlines", help="Optional path to check_deadlines JSON output.")
    parser.add_argument("--ast", dest="ast_path", help="Optional path to ast_signal_scan JSON output.")
    parser.add_argument("--trend", help="Optional path to trend_report or snapshot_store summary JSON output.")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    return parser.parse_args()


def load_json(path_str: str | None) -> Any:
    if not path_str:
        return None
    path = Path(path_str)
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def scan_signal_ids(scan: dict[str, Any] | None) -> set[str]:
    if not isinstance(scan, dict):
        return set()
    signal_ids: set[str] = set()
    for signal in scan.get("signals", []):
        if isinstance(signal, dict) and isinstance(signal.get("id"), str):
            signal_ids.add(signal["id"])
    return signal_ids


def scan_framework_scores(scan: dict[str, Any] | None) -> dict[str, int]:
    if not isinstance(scan, dict):
        return {}
    scores: dict[str, int] = {}
    for framework in scan.get("candidate_frameworks", []):
        if not isinstance(framework, dict):
            continue
        key = framework.get("framework")
        if isinstance(key, str):
            scores[key] = int(framework.get("score", 0))
    return scores


def not_observed_control_count(scan: dict[str, Any] | None) -> int | None:
    if not isinstance(scan, dict):
        return None
    controls = scan.get("control_observations")
    if not isinstance(controls, list):
        return None
    return sum(1 for item in controls if isinstance(item, dict) and str(item.get("status", "")).lower() == "not-observed")


def urgent_deadline_count(deadlines: dict[str, Any] | None) -> int | None:
    if not isinstance(deadlines, dict):
        return None
    developments = deadlines.get("developments")
    if not isinstance(developments, list):
        return None
    return sum(
        1
        for item in developments
        if isinstance(item, dict) and str(item.get("urgency", "")).lower() in {"high", "critical"}
    )


def structural_finding_count(ast_data: dict[str, Any] | None) -> int | None:
    if not isinstance(ast_data, dict):
        return None
    findings = ast_data.get("structural_findings")
    if not isinstance(findings, list):
        return None
    return len(findings)


def trend_deltas(trend_data: dict[str, Any] | None) -> dict[str, int] | None:
    if not isinstance(trend_data, dict):
        return None
    # trend_report.py output
    if isinstance(trend_data.get("framework_trends"), list):
        deltas: dict[str, int] = {}
        for item in trend_data["framework_trends"]:
            if not isinstance(item, dict):
                continue
            framework = item.get("framework")
            delta = item.get("delta")
            if isinstance(framework, str):
                deltas[framework] = int(delta or 0)
        return deltas

    # snapshot_store.py summary output
    trend_section = trend_data.get("trend")
    if isinstance(trend_section, dict) and isinstance(trend_section.get("framework_score_changes"), list):
        deltas = {}
        for item in trend_section["framework_score_changes"]:
            if not isinstance(item, dict):
                continue
            framework = item.get("framework")
            delta = item.get("delta")
            if isinstance(framework, str):
                deltas[framework] = int(delta or 0)
        return deltas
    return None


def make_check(
    check: str,
    status: str,
    message: str,
    *,
    threshold: Any = None,
    actual: Any = None,
    framework: str | None = None,
    signal: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"check": check, "status": status, "message": message}
    if threshold is not None:
        payload["threshold"] = threshold
    if actual is not None:
        payload["actual"] = actual
    if framework:
        payload["framework"] = framework
    if signal:
        payload["signal"] = signal
    return payload


def evaluate_policy(
    policy: dict[str, Any],
    scan: dict[str, Any] | None,
    deadlines: dict[str, Any] | None,
    ast_data: dict[str, Any] | None,
    trend_data: dict[str, Any] | None,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    signals = scan_signal_ids(scan)
    scores = scan_framework_scores(scan)
    missing_controls = not_observed_control_count(scan)
    urgent_deadlines = urgent_deadline_count(deadlines)
    structural_findings = structural_finding_count(ast_data)
    deltas = trend_deltas(trend_data)

    max_missing_controls = policy.get("max_not_observed_controls")
    if max_missing_controls is not None:
        if missing_controls is None:
            checks.append(make_check("max_not_observed_controls", "skipped", "Scan control observations unavailable."))
        elif missing_controls <= int(max_missing_controls):
            checks.append(
                make_check(
                    "max_not_observed_controls",
                    "pass",
                    "Not-observed control count is within threshold.",
                    threshold=int(max_missing_controls),
                    actual=missing_controls,
                )
            )
        else:
            checks.append(
                make_check(
                    "max_not_observed_controls",
                    "fail",
                    "Not-observed control count exceeds threshold.",
                    threshold=int(max_missing_controls),
                    actual=missing_controls,
                )
            )

    max_urgent_deadlines = policy.get("max_high_or_critical_deadlines")
    if max_urgent_deadlines is not None:
        if urgent_deadlines is None:
            checks.append(
                make_check("max_high_or_critical_deadlines", "skipped", "Deadline output not supplied or malformed.")
            )
        elif urgent_deadlines <= int(max_urgent_deadlines):
            checks.append(
                make_check(
                    "max_high_or_critical_deadlines",
                    "pass",
                    "High/Critical deadline count is within threshold.",
                    threshold=int(max_urgent_deadlines),
                    actual=urgent_deadlines,
                )
            )
        else:
            checks.append(
                make_check(
                    "max_high_or_critical_deadlines",
                    "fail",
                    "High/Critical deadline count exceeds threshold.",
                    threshold=int(max_urgent_deadlines),
                    actual=urgent_deadlines,
                )
            )

    max_structural = policy.get("max_structural_findings")
    if max_structural is not None:
        if structural_findings is None:
            checks.append(make_check("max_structural_findings", "skipped", "AST output not supplied or malformed."))
        elif structural_findings <= int(max_structural):
            checks.append(
                make_check(
                    "max_structural_findings",
                    "pass",
                    "Structural finding count is within threshold.",
                    threshold=int(max_structural),
                    actual=structural_findings,
                )
            )
        else:
            checks.append(
                make_check(
                    "max_structural_findings",
                    "fail",
                    "Structural finding count exceeds threshold.",
                    threshold=int(max_structural),
                    actual=structural_findings,
                )
            )

    minimum_scores = policy.get("minimum_framework_scores")
    if isinstance(minimum_scores, dict):
        for framework, minimum in minimum_scores.items():
            if framework not in scores:
                checks.append(
                    make_check(
                        "minimum_framework_scores",
                        "fail",
                        "Framework score missing.",
                        threshold=int(minimum),
                        actual=0,
                        framework=str(framework),
                    )
                )
                continue
            actual = int(scores[framework])
            if actual >= int(minimum):
                checks.append(
                    make_check(
                        "minimum_framework_scores",
                        "pass",
                        "Framework score meets minimum threshold.",
                        threshold=int(minimum),
                        actual=actual,
                        framework=str(framework),
                    )
                )
            else:
                checks.append(
                    make_check(
                        "minimum_framework_scores",
                        "fail",
                        "Framework score below minimum threshold.",
                        threshold=int(minimum),
                        actual=actual,
                        framework=str(framework),
                    )
                )

    required_all = policy.get("required_signals_all")
    if isinstance(required_all, list):
        for signal in required_all:
            signal_id = str(signal)
            if signal_id in signals:
                checks.append(make_check("required_signals_all", "pass", "Required signal observed.", signal=signal_id))
            else:
                checks.append(make_check("required_signals_all", "fail", "Required signal missing.", signal=signal_id))

    required_any = policy.get("required_signals_any")
    if isinstance(required_any, list) and required_any:
        required_any_ids = {str(item) for item in required_any}
        observed_any = sorted(required_any_ids & signals)
        if observed_any:
            checks.append(
                make_check(
                    "required_signals_any",
                    "pass",
                    "At least one required-any signal observed.",
                    actual=observed_any,
                    threshold=sorted(required_any_ids),
                )
            )
        else:
            checks.append(
                make_check(
                    "required_signals_any",
                    "fail",
                    "No required-any signals observed.",
                    threshold=sorted(required_any_ids),
                    actual=[],
                )
            )

    forbidden_signals = policy.get("forbidden_signals")
    if isinstance(forbidden_signals, list):
        forbidden_ids = {str(item) for item in forbidden_signals}
        hits = sorted(forbidden_ids & signals)
        if hits:
            checks.append(
                make_check("forbidden_signals", "fail", "Forbidden signals were observed.", threshold=sorted(forbidden_ids), actual=hits)
            )
        else:
            checks.append(
                make_check("forbidden_signals", "pass", "No forbidden signals were observed.", threshold=sorted(forbidden_ids), actual=[])
            )

    max_drop = policy.get("max_framework_score_drop")
    if isinstance(max_drop, dict):
        if deltas is None:
            checks.append(make_check("max_framework_score_drop", "skipped", "Trend output not supplied or malformed."))
        else:
            for framework, allowed in max_drop.items():
                delta = int(deltas.get(str(framework), 0))
                drop = -delta if delta < 0 else 0
                if drop <= int(allowed):
                    checks.append(
                        make_check(
                            "max_framework_score_drop",
                            "pass",
                            "Framework score drop is within threshold.",
                            framework=str(framework),
                            threshold=int(allowed),
                            actual=drop,
                        )
                    )
                else:
                    checks.append(
                        make_check(
                            "max_framework_score_drop",
                            "fail",
                            "Framework score drop exceeds threshold.",
                            framework=str(framework),
                            threshold=int(allowed),
                            actual=drop,
                        )
                    )

    failed = [check for check in checks if check["status"] == "fail"]
    passed = not failed
    return with_meta(
        "compliance_gate",
        {
            "policy_name": str(policy.get("name", "unnamed-policy")),
            "passed": passed,
            "failed_checks": len(failed),
            "total_checks": len(checks),
            "checks": checks,
            "metrics": {
                "signal_count": len(signals),
                "framework_scores": scores,
                "not_observed_controls": missing_controls,
                "high_or_critical_deadlines": urgent_deadlines,
                "structural_findings": structural_findings,
                "trend_deltas": deltas,
            },
        },
    )


def render_markdown(result: dict[str, Any]) -> str:
    lines = ["# Compliance Gate", "", f"- Policy: `{result['policy_name']}`", f"- Passed: `{result['passed']}`"]
    lines.append(f"- Failed checks: {result['failed_checks']} of {result['total_checks']}")
    lines.extend(["", "## Checks"])
    if not result["checks"]:
        lines.append("- No checks defined in policy.")
    for check in result["checks"]:
        suffix = []
        if "framework" in check:
            suffix.append(f"framework={check['framework']}")
        if "signal" in check:
            suffix.append(f"signal={check['signal']}")
        if "actual" in check:
            suffix.append(f"actual={check['actual']}")
        if "threshold" in check:
            suffix.append(f"threshold={check['threshold']}")
        details = f" ({', '.join(suffix)})" if suffix else ""
        lines.append(f"- [{check['status'].upper()}] `{check['check']}`: {check['message']}{details}")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    policy = load_json(args.policy)
    if not isinstance(policy, dict):
        raise ValueError("Policy file must contain a JSON object.")
    scan = load_json(args.scan)
    deadlines = load_json(args.deadlines)
    ast_data = load_json(args.ast_path)
    trend_data = load_json(args.trend)

    result = evaluate_policy(policy, scan if isinstance(scan, dict) else None, deadlines, ast_data, trend_data)
    if args.format == "markdown":
        sys.stdout.write(render_markdown(result))
    else:
        json.dump(result, sys.stdout, indent=2)
        sys.stdout.write("\n")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
