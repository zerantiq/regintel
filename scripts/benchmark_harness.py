#!/usr/bin/env python3
"""Benchmark harness for scan quality metrics over labeled fixture corpora."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from ._contract import with_meta
    from ._markdown import bool_badge, delta_badge, markdown_cell
except ImportError:
    from _contract import with_meta  # type: ignore
    from _markdown import bool_badge, delta_badge, markdown_cell  # type: ignore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--labels",
        default="tests/fixtures/benchmarks/labeled-corpus.json",
        help="Path to labeled benchmark corpus JSON.",
    )
    parser.add_argument(
        "--fixtures-root",
        default="tests/fixtures/repos",
        help="Root directory containing benchmark fixture repos.",
    )
    parser.add_argument(
        "--baseline",
        default="tests/fixtures/benchmarks/baseline-metrics.json",
        help="Path to baseline metrics JSON used for trend deltas.",
    )
    parser.add_argument(
        "--policy",
        default="examples/benchmark-gate-policy.json",
        help="Path to benchmark gate policy JSON.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Worker count passed through to scanner scripts.",
    )
    parser.add_argument(
        "--cache-dir",
        default=".regintel/benchmark-cache",
        help="Cache directory passed through to scanner scripts.",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable scanner cache for benchmark runs.",
    )
    parser.add_argument(
        "--history-file",
        help="Optional path to append benchmark summary history as JSON Lines.",
    )
    parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
        help="Output format (default: json).",
    )
    parser.add_argument(
        "--output",
        help="Optional output path. Defaults to stdout when omitted.",
    )
    return parser.parse_args()


def safe_div(num: float, den: float) -> float:
    if den <= 0:
        return 1.0
    return num / den


def round_metric(value: float) -> float:
    return round(value, 4)


def score_sets(expected: set[str], predicted: set[str]) -> dict[str, Any]:
    tp_ids = sorted(expected & predicted)
    fp_ids = sorted(predicted - expected)
    fn_ids = sorted(expected - predicted)
    tp = len(tp_ids)
    fp = len(fp_ids)
    fn = len(fn_ids)
    precision = safe_div(tp, tp + fp)
    recall = safe_div(tp, tp + fn)
    f1 = safe_div(2 * precision * recall, precision + recall)
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": round_metric(precision),
        "recall": round_metric(recall),
        "f1": round_metric(f1),
        "true_positives": tp_ids,
        "false_positives": fp_ids,
        "false_negatives": fn_ids,
    }


def aggregate_metrics(items: list[dict[str, Any]], key: str) -> dict[str, Any]:
    tp = sum(item[key]["tp"] for item in items)
    fp = sum(item[key]["fp"] for item in items)
    fn = sum(item[key]["fn"] for item in items)
    precision = safe_div(tp, tp + fp)
    recall = safe_div(tp, tp + fn)
    f1 = safe_div(2 * precision * recall, precision + recall)
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": round_metric(precision),
        "recall": round_metric(recall),
        "f1": round_metric(f1),
    }


def run_json_command(command: list[str], cwd: Path) -> dict[str, Any]:
    result = subprocess.run(command, cwd=str(cwd), check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def resolve_path_arg(raw_value: str | None, *, base_dir: Path) -> Path | None:
    if not raw_value:
        return None
    raw_path = Path(raw_value)
    if raw_path.is_absolute():
        return raw_path
    return (base_dir / raw_path).resolve()


def evaluate_fixture(
    fixture: dict[str, Any],
    *,
    scripts_dir: Path,
    execution_root: Path,
    fixtures_root: Path,
    workers: int,
    cache_dir: str,
    no_cache: bool,
) -> dict[str, Any]:
    fixture_id = fixture["id"]
    fixture_rel = fixture["path"]
    fixture_path = (fixtures_root / fixture_rel).resolve()
    if not fixture_path.exists():
        raise FileNotFoundError(f"Fixture path not found for {fixture_id}: {fixture_path}")

    repo_scan_cmd = [
        sys.executable,
        str((scripts_dir / "repo_signal_scan.py").resolve()),
        "--path",
        str(fixture_path),
        "--scope",
        "full",
        "--workers",
        str(workers),
        "--cache-dir",
        cache_dir,
    ]
    ast_scan_cmd = [
        sys.executable,
        str((scripts_dir / "ast_signal_scan.py").resolve()),
        "--path",
        str(fixture_path),
        "--workers",
        str(workers),
        "--cache-dir",
        cache_dir,
    ]
    if no_cache:
        repo_scan_cmd.append("--no-cache")
        ast_scan_cmd.append("--no-cache")

    repo_result = run_json_command(repo_scan_cmd, execution_root)
    ast_result = run_json_command(ast_scan_cmd, execution_root)

    predicted_signal_ids = {item["id"] for item in repo_result.get("signals", [])}
    predicted_ast_ids = {item["id"] for item in ast_result.get("structural_findings", [])}

    expected_signal_ids = set(fixture.get("expected_signal_ids", []))
    expected_ast_ids = set(fixture.get("expected_ast_finding_ids", []))

    signal_metrics = score_sets(expected_signal_ids, predicted_signal_ids)
    ast_metrics = score_sets(expected_ast_ids, predicted_ast_ids)
    return {
        "id": fixture_id,
        "path": fixture_rel,
        "expected_signal_ids": sorted(expected_signal_ids),
        "predicted_signal_ids": sorted(predicted_signal_ids),
        "expected_ast_finding_ids": sorted(expected_ast_ids),
        "predicted_ast_finding_ids": sorted(predicted_ast_ids),
        "signal_metrics": signal_metrics,
        "ast_metrics": ast_metrics,
    }


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def maybe_load_json(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    try:
        return load_json(path)
    except (OSError, json.JSONDecodeError):
        return None


def metric_delta(current: float, baseline: float) -> float:
    return round_metric(current - baseline)


def build_trends(
    overall: dict[str, dict[str, Any]],
    baseline_payload: dict[str, Any] | None,
    baseline_path: Path | None,
) -> dict[str, Any]:
    if not baseline_payload:
        return {
            "baseline_path": str(baseline_path) if baseline_path else None,
            "available": False,
            "deltas": {},
        }
    baseline_overall = baseline_payload.get("overall")
    if not isinstance(baseline_overall, dict):
        return {
            "baseline_path": str(baseline_path) if baseline_path else None,
            "available": False,
            "deltas": {},
        }

    deltas: dict[str, dict[str, float]] = {}
    for group in ("signals", "ast", "combined"):
        current_group = overall.get(group, {})
        baseline_group = baseline_overall.get(group, {})
        if not isinstance(current_group, dict) or not isinstance(baseline_group, dict):
            continue
        group_deltas: dict[str, float] = {}
        for metric in ("precision", "recall", "f1"):
            if metric in current_group and metric in baseline_group:
                group_deltas[metric] = metric_delta(
                    float(current_group[metric]), float(baseline_group[metric])
                )
        if group_deltas:
            deltas[group] = group_deltas

    return {
        "baseline_path": str(baseline_path) if baseline_path else None,
        "available": bool(deltas),
        "deltas": deltas,
    }


def evaluate_policy(
    policy_payload: dict[str, Any] | None,
    overall: dict[str, dict[str, Any]],
    trends: dict[str, Any],
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    policy_name = "none"
    if not policy_payload:
        return {
            "policy_name": policy_name,
            "passed": True,
            "failed_checks": 0,
            "total_checks": 0,
            "checks": checks,
        }

    policy_name = str(policy_payload.get("name", "benchmark-policy"))
    minimum_metrics = policy_payload.get("minimum_metrics", {})
    max_metric_drop = policy_payload.get("max_metric_drop", {})
    deltas = trends.get("deltas", {}) if isinstance(trends, dict) else {}
    deltas_available = bool(trends.get("available")) if isinstance(trends, dict) else False

    if isinstance(minimum_metrics, dict):
        for group, thresholds in minimum_metrics.items():
            if not isinstance(thresholds, dict):
                continue
            current_group = overall.get(group, {})
            if not isinstance(current_group, dict):
                continue
            for metric, threshold in thresholds.items():
                if metric not in current_group:
                    continue
                actual = float(current_group[metric])
                threshold_value = float(threshold)
                passed = actual >= threshold_value
                checks.append(
                    {
                        "check": f"minimum_{group}_{metric}",
                        "status": "pass" if passed else "fail",
                        "threshold": threshold_value,
                        "actual": round_metric(actual),
                        "message": (
                            f"{group}.{metric} meets minimum threshold."
                            if passed
                            else f"{group}.{metric} is below minimum threshold."
                        ),
                    }
                )

    if isinstance(max_metric_drop, dict):
        for group, thresholds in max_metric_drop.items():
            if not isinstance(thresholds, dict):
                continue
            group_deltas = deltas.get(group, {}) if isinstance(deltas, dict) else {}
            for metric, allowed_drop in thresholds.items():
                check_name = f"max_drop_{group}_{metric}"
                if not deltas_available or metric not in group_deltas:
                    checks.append(
                        {
                            "check": check_name,
                            "status": "fail",
                            "threshold": float(allowed_drop),
                            "actual": None,
                            "message": "Baseline trend delta not available for max-drop check.",
                        }
                    )
                    continue
                delta_value = float(group_deltas[metric])
                drop = max(0.0, -delta_value)
                threshold_value = float(allowed_drop)
                passed = drop <= threshold_value
                checks.append(
                    {
                        "check": check_name,
                        "status": "pass" if passed else "fail",
                        "threshold": threshold_value,
                        "actual": round_metric(drop),
                        "message": (
                            f"{group}.{metric} drop is within allowed threshold."
                            if passed
                            else f"{group}.{metric} drop exceeds allowed threshold."
                        ),
                    }
                )

    failed = [check for check in checks if check["status"] == "fail"]
    return {
        "policy_name": policy_name,
        "passed": not failed,
        "failed_checks": len(failed),
        "total_checks": len(checks),
        "checks": checks,
    }


def append_history(history_file: Path, payload: dict[str, Any]) -> None:
    record = {
        "generated_at": payload.get("generated_at"),
        "overall": payload.get("overall"),
        "gate": {
            "policy_name": payload.get("gate", {}).get("policy_name"),
            "passed": payload.get("gate", {}).get("passed"),
            "failed_checks": payload.get("gate", {}).get("failed_checks"),
        },
    }
    history_file.parent.mkdir(parents=True, exist_ok=True)
    with history_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record))
        handle.write("\n")


def render_markdown(payload: dict[str, Any]) -> str:
    overall = payload["overall"]
    gate = payload["gate"]
    trends = payload["trends"]
    fixtures = payload["fixtures"]

    lines = [
        "## Benchmark Quality Report",
        "",
        "| Overview | Value |",
        "|---|---|",
        f"| Generated | `{payload['generated_at']}` |",
        f"| Fixtures evaluated | {len(fixtures)} |",
        f"| Gate passed | {bool_badge(gate['passed'])} |",
        f"| Failed checks | {gate['failed_checks']} / {gate['total_checks']} |",
        "",
        "### Overall Metrics",
        "",
        "| Group | Precision | Recall | F1 | TP | FP | FN |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for group in ("signals", "ast", "combined"):
        metric = overall[group]
        lines.append(
            f"| {group} | {metric['precision']:.4f} | {metric['recall']:.4f} | {metric['f1']:.4f} | {metric['tp']} | {metric['fp']} | {metric['fn']} |"
        )

    lines.extend(["", "### Trend Deltas", ""])
    if trends.get("available"):
        lines.append("| Group | Precision delta | Recall delta | F1 delta |")
        lines.append("|---|---|---|---|")
        deltas = trends.get("deltas", {})
        for group in ("signals", "ast", "combined"):
            group_delta = deltas.get(group, {})
            lines.append(
                f"| {group} | {delta_badge(group_delta.get('precision', 0.0))} | {delta_badge(group_delta.get('recall', 0.0))} | {delta_badge(group_delta.get('f1', 0.0))} |"
            )
    else:
        lines.append("✅ No baseline trend delta available.")

    lines.extend(["", "### Fixture Summary", "", "| Fixture | Signal P/R | AST P/R | Signal FP | AST FP |", "|---|---:|---:|---:|---:|"])
    for fixture in fixtures:
        signal = fixture["signal_metrics"]
        ast_metrics = fixture["ast_metrics"]
        lines.append(
            f"| {markdown_cell(fixture['id'])} | {signal['precision']:.4f}/{signal['recall']:.4f} | {ast_metrics['precision']:.4f}/{ast_metrics['recall']:.4f} | {signal['fp']} | {ast_metrics['fp']} |"
        )
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    execution_root = Path.cwd().resolve()
    scripts_dir = Path(__file__).resolve().parent

    labels_path = resolve_path_arg(args.labels, base_dir=execution_root)
    fixtures_root = resolve_path_arg(args.fixtures_root, base_dir=execution_root)
    baseline_path = resolve_path_arg(args.baseline, base_dir=execution_root)
    policy_path = resolve_path_arg(args.policy, base_dir=execution_root)

    if labels_path is None:
        print(json.dumps({"error": "Invalid labels path."}))
        return 1
    if fixtures_root is None:
        print(json.dumps({"error": "Invalid fixtures-root path."}))
        return 1

    labels_payload = load_json(labels_path)
    fixtures = labels_payload.get("fixtures", [])
    if not isinstance(fixtures, list):
        print(json.dumps({"error": "Invalid labels file: fixtures must be a list."}))
        return 1

    fixture_results: list[dict[str, Any]] = []
    for fixture in fixtures:
        fixture_results.append(
            evaluate_fixture(
                fixture,
                scripts_dir=scripts_dir,
                execution_root=execution_root,
                fixtures_root=fixtures_root,
                workers=max(1, args.workers),
                cache_dir=args.cache_dir,
                no_cache=args.no_cache,
            )
        )

    signals_overall = aggregate_metrics(fixture_results, "signal_metrics")
    ast_overall = aggregate_metrics(fixture_results, "ast_metrics")
    combined_overall = score_sets(
        set(),
        set(),
    )
    combined_overall["tp"] = signals_overall["tp"] + ast_overall["tp"]
    combined_overall["fp"] = signals_overall["fp"] + ast_overall["fp"]
    combined_overall["fn"] = signals_overall["fn"] + ast_overall["fn"]
    precision = safe_div(combined_overall["tp"], combined_overall["tp"] + combined_overall["fp"])
    recall = safe_div(combined_overall["tp"], combined_overall["tp"] + combined_overall["fn"])
    combined_overall["precision"] = round_metric(precision)
    combined_overall["recall"] = round_metric(recall)
    combined_overall["f1"] = round_metric(safe_div(2 * precision * recall, precision + recall))
    combined_overall.pop("true_positives", None)
    combined_overall.pop("false_positives", None)
    combined_overall.pop("false_negatives", None)

    overall = {
        "signals": signals_overall,
        "ast": ast_overall,
        "combined": combined_overall,
    }

    baseline_payload = maybe_load_json(baseline_path)
    trends = build_trends(overall, baseline_payload, baseline_path)
    policy_payload = maybe_load_json(policy_path)
    gate = evaluate_policy(policy_payload, overall, trends)

    payload = with_meta(
        "benchmark_harness",
        {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "labels_path": str(labels_path),
            "fixtures_root": str(fixtures_root),
            "fixture_count": len(fixture_results),
            "fixtures": fixture_results,
            "overall": overall,
            "trends": trends,
            "gate": gate,
        },
    )

    if args.history_file:
        history_path = resolve_path_arg(args.history_file, base_dir=execution_root)
        if history_path is None:
            print(json.dumps({"error": "Invalid history-file path."}))
            return 1
        append_history(history_path, payload)

    if args.format == "markdown":
        text_output = render_markdown(payload)
    else:
        text_output = json.dumps(payload, indent=2)

    if args.output:
        output_path = resolve_path_arg(args.output, base_dir=execution_root)
        if output_path is None:
            print(json.dumps({"error": "Invalid output path."}))
            return 1
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text_output + ("\n" if not text_output.endswith("\n") else ""), encoding="utf-8")
    else:
        print(text_output)

    return 0 if gate["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
