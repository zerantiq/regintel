#!/usr/bin/env python3
"""Score likely framework applicability from repo signals and optional company context."""

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

FRAMEWORK_DETAILS = {
    "eu-ai-act": {
        "display_name": "EU AI Act",
        "review_areas": ["AI inventory", "transparency", "logging and monitoring", "human oversight", "vendor controls"],
    },
    "iso-42001": {
        "display_name": "ISO/IEC 42001",
        "review_areas": ["AIMS scope", "roles and accountability", "risk treatment", "internal audit and management review"],
    },
    "gdpr": {
        "display_name": "GDPR",
        "review_areas": ["Notices and lawful basis", "retention", "deletion/export", "vendor controls", "security"],
    },
    "uk-gdpr": {
        "display_name": "UK GDPR",
        "review_areas": [
            "Privacy notices and lawful basis",
            "UK data rights workflows",
            "retention and deletion",
            "international transfers (UK IDTA/addendum)",
        ],
    },
    "us-state-privacy": {
        "display_name": "U.S. State Privacy",
        "review_areas": ["Notice at collection", "opt-out and preferences", "vendor contracts", "delete/access workflows"],
    },
    "ccpa-cpra": {
        "display_name": "CCPA / CPRA",
        "review_areas": [
            "Notice at collection",
            "Do Not Sell/Share controls",
            "Global Privacy Control handling",
            "sensitive PI limitation",
        ],
    },
    "us-va-cdpa": {
        "display_name": "Virginia CDPA",
        "review_areas": ["Privacy notices", "opt-out controls", "rights workflows", "processor contracts"],
    },
    "us-co-cpa": {
        "display_name": "Colorado Privacy Act",
        "review_areas": ["Privacy notices", "universal opt-out mechanisms", "rights workflows", "controller/processor duties"],
    },
    "hipaa": {
        "display_name": "HIPAA",
        "review_areas": ["Access control", "audit logging", "vendor logging exposure", "transmission/storage safeguards"],
    },
    "fda-software": {
        "display_name": "FDA Software / SaMD",
        "review_areas": ["Intended use", "validation", "traceability", "change control"],
    },
    "pci-dss": {
        "display_name": "PCI DSS",
        "review_areas": [
            "cardholder-data inventory",
            "tokenization and storage minimization",
            "encryption and key management",
            "access logging and monitoring",
        ],
    },
    "sec-cyber-disclosure": {
        "display_name": "SEC Cyber Disclosure",
        "review_areas": ["Incident escalation", "materiality support", "logging and evidence preservation", "governance"],
    },
    "sox": {
        "display_name": "SOX",
        "review_areas": ["Change management", "privileged access", "audit trails", "approval evidence"],
    },
    "dora": {
        "display_name": "DORA",
        "review_areas": ["ICT risk framework", "resilience testing", "third-party oversight", "incident reporting"],
    },
    "nis2": {
        "display_name": "NIS2",
        "review_areas": ["Network security", "supply chain risk", "vulnerability management", "incident notification"],
    },
    "nist-ai-rmf": {
        "display_name": "NIST AI RMF",
        "review_areas": ["AI risk assessment", "bias and fairness", "model documentation", "explainability"],
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--signals", required=True, help="Path to repo_signal_scan JSON output.")
    parser.add_argument("--company", help="Optional path to company-context JSON.")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    return parser.parse_args()


def load_json(path_str: str) -> Any:
    path = Path(path_str)
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def company_boosts(company: dict[str, Any] | None) -> tuple[dict[str, int], list[str]]:
    boosts = {key: 0 for key in FRAMEWORK_DETAILS}
    notes: list[str] = []
    if not company:
        notes.append("No company context supplied; public-company, jurisdiction, and deployment assumptions remain unconfirmed.")
        return boosts, notes

    jurisdictions = {value.upper() for value in company.get("jurisdictions", [])}
    customers = {str(value).lower() for value in company.get("customers", [])}
    claims = {str(value).lower() for value in company.get("regulated_claims", [])}
    deployment_model = str(company.get("deployment_model", "")).lower()

    if company.get("uses_ai"):
        boosts["eu-ai-act"] += 16
        boosts["iso-42001"] += 14
        boosts["gdpr"] += 6
        boosts["nist-ai-rmf"] += 12
        notes.append("Company context confirms AI use.")
    if "EU" in jurisdictions or any(value.startswith("EU-") for value in jurisdictions):
        boosts["gdpr"] += 14
        boosts["eu-ai-act"] += 10
        boosts["dora"] += 8
        boosts["nis2"] += 8
        notes.append("Company context includes EU exposure.")
    if "UK" in jurisdictions or any(value.startswith("UK-") for value in jurisdictions):
        boosts["uk-gdpr"] += 14
        notes.append("Company context includes UK exposure.")
    if any(value.startswith("US-") for value in jurisdictions) or "US" in jurisdictions:
        boosts["us-state-privacy"] += 10
    if "US-CA" in jurisdictions:
        boosts["ccpa-cpra"] += 16
    if "US-VA" in jurisdictions:
        boosts["us-va-cdpa"] += 14
    if "US-CO" in jurisdictions:
        boosts["us-co-cpa"] += 14
    if company.get("public_company"):
        boosts["sec-cyber-disclosure"] += 20
        boosts["sox"] += 16
        notes.append("Company context confirms public-company obligations.")
    if "healthcare" in customers or company.get("handles_phi"):
        boosts["hipaa"] += 22
        notes.append("Company context indicates healthcare or PHI handling.")
    if claims or company.get("medical_device") or company.get("clinical_decision_support"):
        boosts["fda-software"] += 20
        notes.append("Company context indicates regulated clinical or device claims.")
    if deployment_model == "hosted-saas":
        boosts["gdpr"] += 6
        boosts["uk-gdpr"] += 4
        boosts["us-state-privacy"] += 6
        boosts["ccpa-cpra"] += 4
        boosts["nis2"] += 4
        notes.append("Hosted SaaS deployment increases direct operational/privacy exposure.")
    if company.get("financial_entity"):
        boosts["dora"] += 20
        boosts["sec-cyber-disclosure"] += 6
        notes.append("Company context indicates financial-entity status (DORA scope).")
    if company.get("essential_service") or company.get("important_entity"):
        boosts["nis2"] += 18
        notes.append("Company context indicates essential or important entity status (NIS2 scope).")
    if company.get("processes_card_payments") or company.get("handles_cardholder_data"):
        boosts["pci-dss"] += 24
        notes.append("Company context indicates cardholder-data processing (PCI DSS scope).")
    return boosts, notes


def normalize_candidates(scan_data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    candidates = {}
    for candidate in scan_data.get("candidate_frameworks", []):
        candidates[candidate["framework"]] = {
            "framework": candidate["framework"],
            "display_name": candidate["display_name"],
            "score": int(candidate.get("score", 0)),
            "confidence": float(candidate.get("confidence", 0.0)),
            "basis": list(candidate.get("reasons", [])),
        }
    for framework, metadata in FRAMEWORK_DETAILS.items():
        candidates.setdefault(
            framework,
            {
                "framework": framework,
                "display_name": metadata["display_name"],
                "score": 0,
                "confidence": 0.2,
                "basis": [],
            },
        )
    return candidates


def likely_review_areas(framework: str, control_observations: list[dict[str, Any]]) -> list[str]:
    areas = list(FRAMEWORK_DETAILS[framework]["review_areas"])
    for observation in control_observations:
        if framework not in observation.get("frameworks", []):
            continue
        if observation.get("status") == "not-observed":
            areas.append(observation["control"].replace("-", " "))
    deduped = []
    seen = set()
    for area in areas:
        key = area.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(area)
    return deduped


def assumptions_for(framework: str, company: dict[str, Any] | None) -> list[str]:
    assumptions = []
    if framework in {"sec-cyber-disclosure", "sox"} and not (company or {}).get("public_company"):
        assumptions.append("Public-company status is not confirmed from repo evidence alone.")
    if framework == "hipaa" and not ((company or {}).get("handles_phi") or "healthcare" in {str(v).lower() for v in (company or {}).get("customers", [])}):
        assumptions.append("Covered-entity or business-associate status is not confirmed.")
    if framework == "fda-software" and not ((company or {}).get("medical_device") or (company or {}).get("regulated_claims")):
        assumptions.append("Device or clinical intended-use claims are not confirmed.")
    if framework in {"gdpr", "eu-ai-act"} and "EU" not in {str(v).upper() for v in (company or {}).get("jurisdictions", [])}:
        assumptions.append("EU establishment or EU-user exposure is inferred from product signals, not confirmed.")
    if framework == "uk-gdpr" and "UK" not in {str(v).upper() for v in (company or {}).get("jurisdictions", [])}:
        assumptions.append("UK establishment or UK-user exposure is inferred from product signals, not confirmed.")
    if framework == "ccpa-cpra" and "US-CA" not in {str(v).upper() for v in (company or {}).get("jurisdictions", [])}:
        assumptions.append("California consumer exposure is not confirmed.")
    if framework == "us-va-cdpa" and "US-VA" not in {str(v).upper() for v in (company or {}).get("jurisdictions", [])}:
        assumptions.append("Virginia consumer exposure is not confirmed.")
    if framework == "us-co-cpa" and "US-CO" not in {str(v).upper() for v in (company or {}).get("jurisdictions", [])}:
        assumptions.append("Colorado consumer exposure is not confirmed.")
    if framework == "iso-42001" and not (company or {}).get("uses_ai"):
        assumptions.append("ISO/IEC 42001 alignment is inferred from repo evidence, not confirmed by company policy.")
    if framework == "dora" and not (company or {}).get("financial_entity"):
        assumptions.append("Financial-entity status under DORA is not confirmed.")
    if framework == "nis2" and not ((company or {}).get("essential_service") or (company or {}).get("important_entity")):
        assumptions.append("Essential or important entity status under NIS2 is not confirmed.")
    if framework == "nist-ai-rmf" and not (company or {}).get("uses_ai"):
        assumptions.append("AI system deployment is inferred from repo signals, not confirmed.")
    if framework == "pci-dss" and not ((company or {}).get("processes_card_payments") or (company or {}).get("handles_cardholder_data")):
        assumptions.append("Cardholder-data environment scope is not confirmed.")
    return assumptions


def build_output(scan_data: dict[str, Any], company: dict[str, Any] | None) -> dict[str, Any]:
    candidates = normalize_candidates(scan_data)
    boosts, confidence_notes = company_boosts(company)
    control_observations = scan_data.get("control_observations", [])

    for framework, boost in boosts.items():
        candidates[framework]["score"] = min(candidates[framework]["score"] + boost, 100)
        if boost:
            candidates[framework]["basis"].append(f"Company context added {boost} points.")

    signals = scan_data.get("signals", [])
    for framework, candidate in candidates.items():
        supporting_signals = [signal["title"] for signal in signals if framework in signal.get("frameworks", [])]
        if supporting_signals:
            candidate["basis"].extend(
                [f"Repo evidence includes {title.lower()}." for title in sorted(set(supporting_signals))]
            )
        if candidate["score"] > 0:
            candidate["confidence"] = round(min(0.3 + (candidate["score"] / 120.0), 0.95), 2)
        candidate["likely_review_areas"] = likely_review_areas(framework, control_observations)
        candidate["assumptions"] = assumptions_for(framework, company)

    applicability = sorted(
        [candidate for candidate in candidates.values() if candidate["score"] >= 20],
        key=lambda item: (-item["score"], item["display_name"]),
    )

    priority_review_areas: list[str] = []
    seen = set()
    for candidate in applicability[:4]:
        for area in candidate["likely_review_areas"]:
            key = area.lower()
            if key in seen:
                continue
            seen.add(key)
            priority_review_areas.append(area)
            if len(priority_review_areas) == 8:
                break
        if len(priority_review_areas) == 8:
            break

    return with_meta(
        "applicability_score",
        {
            "product_profile": scan_data.get("product_profile", {}),
            "applicability": applicability,
            "priority_review_areas": priority_review_areas,
            "confidence_notes": confidence_notes,
        },
    )


def render_markdown(output: dict[str, Any]) -> str:
    lines = ["# Applicability Score", ""]
    profile = output.get("product_profile", {})
    labels = ", ".join(profile.get("labels", [])) or "none"
    lines.append(f"- Product profile: {labels} (confidence {profile.get('confidence', 0)})")
    if profile.get("reasons"):
        lines.append(f"- Profile basis: {' '.join(profile['reasons'])}")
    lines.append("")
    lines.append("## Frameworks")
    for candidate in output.get("applicability", []):
        lines.append(
            f"- {candidate['display_name']}: score {candidate['score']}, confidence {candidate['confidence']}, review areas: {', '.join(candidate['likely_review_areas'][:4])}"
        )
        if candidate.get("assumptions"):
            lines.append(f"  Assumptions: {' '.join(candidate['assumptions'])}")
    if output.get("priority_review_areas"):
        lines.append("")
        lines.append("## Priority Review Areas")
        for area in output["priority_review_areas"]:
            lines.append(f"- {area}")
    if output.get("confidence_notes"):
        lines.append("")
        lines.append("## Confidence Notes")
        for note in output["confidence_notes"]:
            lines.append(f"- {note}")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    scan_data = load_json(args.signals)
    company = load_json(args.company) if args.company else None
    output = build_output(scan_data, company)
    if args.format == "markdown":
        sys.stdout.write(render_markdown(output))
    else:
        json.dump(output, sys.stdout, indent=2)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
