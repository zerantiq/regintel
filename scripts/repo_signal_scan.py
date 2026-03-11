#!/usr/bin/env python3
"""Inventory repo signals relevant to software regulatory review."""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

FRAMEWORKS = {
    "eu-ai-act": "EU AI Act",
    "iso-42001": "ISO/IEC 42001",
    "gdpr": "GDPR",
    "uk-gdpr": "UK GDPR",
    "us-state-privacy": "U.S. State Privacy",
    "ccpa-cpra": "CCPA / CPRA",
    "us-va-cdpa": "Virginia CDPA",
    "us-co-cpa": "Colorado Privacy Act",
    "hipaa": "HIPAA",
    "fda-software": "FDA Software / SaMD",
    "pci-dss": "PCI DSS",
    "sec-cyber-disclosure": "SEC Cyber Disclosure",
    "sox": "SOX",
    "dora": "DORA",
    "nis2": "NIS2",
    "nist-ai-rmf": "NIST AI RMF",
}

EXCLUDED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "vendor",
    "dist",
    "build",
    ".next",
    "coverage",
    ".turbo",
    ".cache",
    ".pytest_cache",
    "__pycache__",
    "target",
    "out",
    "tmp",
    "temp",
    "artifacts",
}

EXCLUDED_FILE_NAMES = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "cargo.lock",
    "poetry.lock",
    "podfile.lock",
    "composer.lock",
}

SKIPPED_SUFFIXES = {
    ".lock",
    ".min.js",
    ".min.css",
    ".map",
    ".snap",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".pdf",
    ".zip",
    ".gz",
    ".tar",
    ".jar",
    ".war",
    ".class",
    ".pyc",
}

SCANNABLE_SUFFIXES = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".java",
    ".kt",
    ".swift",
    ".go",
    ".rb",
    ".php",
    ".cs",
    ".rs",
    ".tf",
    ".tfvars",
    ".bicep",
    ".hcl",
    ".sql",
    ".graphql",
    ".gql",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".env",
    ".md",
    ".txt",
    ".html",
    ".css",
    ".sh",
}

SPECIAL_FILENAMES = {
    ".env.example",
    ".env.sample",
    ".env.template",
    "dockerfile",
    "makefile",
    "procfile",
    "justfile",
    "requirements.txt",
    "pipfile",
    "pyproject.toml",
    "package.json",
    "tsconfig.json",
    "next.config.js",
    "next.config.mjs",
    "vite.config.ts",
    "vite.config.js",
    "chart.yaml",
    "chart.yml",
    "values.yaml",
    "values.yml",
    "helmfile.yaml",
    "helmfile.yml",
    "kustomization.yaml",
    "kustomization.yml",
    "template.yaml",
    "template.yml",
    "cloudformation.yaml",
    "cloudformation.yml",
    "docker-compose.yml",
    "docker-compose.yaml",
}

INFRA_SUFFIXES = {".tf", ".tfvars", ".bicep", ".hcl"}

INFRA_FILENAMES = {
    "dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "kustomization.yaml",
    "kustomization.yml",
    "chart.yaml",
    "chart.yml",
    "values.yaml",
    "values.yml",
    "helmfile.yaml",
    "helmfile.yml",
    "template.yaml",
    "template.yml",
    "cloudformation.yaml",
    "cloudformation.yml",
}

INFRA_PATH_MARKERS = {"infra", "terraform", "bicep", "cloudformation", "helm", "charts", "k8s", "kubernetes"}

MAX_FILE_BYTES = 1_000_000
MAX_EVIDENCE_PER_SIGNAL = 6
MAX_SNIPPET_CHARS = 180
DEFERRED_MARKERS = ("todo", "fixme", "tbd", "later", "not implemented", "future work")

# Evidence-class weighting: source code and config are stronger signals than docs/comments
EVIDENCE_WEIGHTS = {
    "source": 1.0,
    "config": 0.9,
    "infra": 0.85,
    "docs": 0.4,
    "comment": 0.3,
}

# Suffixes that indicate documentation or prose rather than executable code
DOC_SUFFIXES = {".md", ".txt", ".rst", ".adoc", ".html"}

# Comment line prefixes by language (used for evidence-class downweighting)
COMMENT_PREFIXES = ("#", "//", "/*", "*", "--", "<!--")


def is_infra_path(path: Path) -> bool:
    """Return True when a path likely points to IaC/deployment configuration."""
    lower_name = path.name.lower()
    if path.suffix.lower() in INFRA_SUFFIXES:
        return True
    if lower_name in INFRA_FILENAMES:
        return True
    return any(part.lower() in INFRA_PATH_MARKERS for part in path.parts)


def classify_evidence(path: Path, line: str) -> str:
    """Classify the evidence class of a match for weighting purposes."""
    suffix = path.suffix.lower()
    stripped = line.strip()
    if suffix in DOC_SUFFIXES:
        return "docs"
    if stripped.startswith(COMMENT_PREFIXES):
        return "comment"
    if is_infra_path(path):
        return "infra"
    if suffix in {".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf", ".env", ".json"}:
        return "config"
    return "source"


SIGNAL_DEFINITIONS = [
    {
        "id": "ai-model-integration",
        "category": "ai",
        "title": "AI model or agent integration",
        "summary": "The repo integrates external model services or orchestration tooling.",
        "patterns": [
            r"\bopenai\b",
            r"\banthropic\b",
            r"\bgemini\b",
            r"\bvertex ai\b",
            r"\bbedrock\b",
            r"\bhuggingface\b",
            r"\blangchain\b",
            r"\bllamaindex\b",
            r"\bembeddings?\b",
            r"\bvector\s*(db|store|search)\b",
            r"\bprompt(_template|s)?\b",
            r"\bchat\.completions\b",
        ],
        "framework_weights": {
            "eu-ai-act": 9,
            "iso-42001": 8,
            "gdpr": 4,
            "uk-gdpr": 3,
            "us-state-privacy": 3,
            "ccpa-cpra": 2,
            "nist-ai-rmf": 6,
        },
        "product_labels": ["ai-enabled-software"],
        "base_confidence": 0.9,
        "review_areas": ["AI inventory", "transparency", "logging and monitoring", "vendor controls"],
    },
    {
        "id": "ai-governance-controls",
        "category": "ai-controls",
        "title": "AI governance or safety controls",
        "summary": "The repo includes AI governance, moderation, evaluation, or safety evidence.",
        "patterns": [
            r"\bmoderat(e|ion)\b",
            r"\bguardrail(s)?\b",
            r"\bsafety\b",
            r"\bred[- ]team\b",
            r"\beval(s|uation)?\b",
            r"\bhuman[- ]in[- ]the[- ]loop\b",
            r"\bmodel inventory\b",
        ],
        "framework_weights": {"eu-ai-act": 5, "iso-42001": 8, "nist-ai-rmf": 4, "gdpr": 2, "uk-gdpr": 1},
        "product_labels": [],
        "base_confidence": 0.72,
        "review_areas": ["Safety controls", "model governance"],
        "skip_deferred": True,
    },
    {
        "id": "ai-management-system",
        "category": "ai-controls",
        "title": "AI management system (ISO 42001 style) evidence",
        "summary": "The repo includes policy, governance, or audit terms aligned with ISO/IEC 42001.",
        "patterns": [
            r"\biso[ /-]?iec 42001\b",
            r"\biso 42001\b",
            r"\bai management system\b",
            r"\baims\b",
            r"\bmanagement review\b",
            r"\binternal audit\b",
            r"\bai policy\b",
            r"\bai risk treatment\b",
        ],
        "framework_weights": {"iso-42001": 10, "eu-ai-act": 4, "nist-ai-rmf": 4},
        "product_labels": ["ai-enabled-software"],
        "base_confidence": 0.79,
        "review_areas": ["AIMS scope", "roles and accountability", "risk treatment", "internal audit and review"],
        "skip_deferred": True,
    },
    {
        "id": "web-api-service",
        "category": "service",
        "title": "Web application or API service",
        "summary": "The repo looks like a hosted application or API service.",
        "patterns": [
            r"\bexpress\b",
            r"\bfastapi\b",
            r"\bflask\b",
            r"\bnextauth\b",
            r"\bgraphql\b",
            r"\brouter\b",
            r"\bapi[_/-]?key\b",
            r"\bauth0\b",
            r"\bclerk\b",
            r"\bmultitenant\b",
            r"\bbilling\b",
        ],
        "framework_weights": {
            "gdpr": 4,
            "uk-gdpr": 3,
            "us-state-privacy": 4,
            "ccpa-cpra": 3,
            "us-va-cdpa": 2,
            "us-co-cpa": 2,
            "sec-cyber-disclosure": 2,
        },
        "product_labels": ["saas-service"],
        "base_confidence": 0.68,
        "review_areas": ["Data inventory", "access control", "vendor management"],
    },
    {
        "id": "go-backend-service",
        "category": "service",
        "title": "Go backend service patterns",
        "summary": "The repo includes Go-specific backend/API implementation patterns.",
        "patterns": [
            r"\bpackage main\b",
            r"\bnet/http\b",
            r"\bhttp\.HandleFunc\b",
            r"\bgin\.Default\(\)\b",
            r"\bfiber\.New\(\)\b",
            r"\becho\.New\(\)\b",
        ],
        "framework_weights": {"gdpr": 2, "uk-gdpr": 2, "us-state-privacy": 2, "ccpa-cpra": 2, "nis2": 1},
        "product_labels": ["saas-service"],
        "base_confidence": 0.62,
        "review_areas": ["API data handling", "authentication and logging", "service hardening"],
        "skip_deferred": True,
    },
    {
        "id": "java-backend-service",
        "category": "service",
        "title": "Java backend service patterns",
        "summary": "The repo includes Java-specific backend/API implementation patterns.",
        "patterns": [
            r"@RestController",
            r"@RequestMapping",
            r"\bSpringApplication\.run\b",
            r"\bjakarta\.persistence\b",
            r"\bjavax\.persistence\b",
        ],
        "framework_weights": {"gdpr": 2, "uk-gdpr": 2, "us-state-privacy": 2, "ccpa-cpra": 2, "nis2": 1},
        "product_labels": ["saas-service"],
        "base_confidence": 0.62,
        "review_areas": ["API data handling", "retention and deletion paths", "service hardening"],
        "skip_deferred": True,
    },
    {
        "id": "csharp-backend-service",
        "category": "service",
        "title": "C# backend service patterns",
        "summary": "The repo includes C#/.NET-specific backend/API implementation patterns.",
        "patterns": [
            r"\bWebApplication\.CreateBuilder\b",
            r"\bMapGet\(",
            r"\bMapPost\(",
            r"\b\[ApiController\]\b",
            r"\bIActionResult\b",
        ],
        "framework_weights": {"gdpr": 2, "uk-gdpr": 2, "us-state-privacy": 2, "ccpa-cpra": 2, "nis2": 1},
        "product_labels": ["saas-service"],
        "base_confidence": 0.62,
        "review_areas": ["API data handling", "consent/rights endpoints", "service hardening"],
        "skip_deferred": True,
    },
    {
        "id": "rust-backend-service",
        "category": "service",
        "title": "Rust backend service patterns",
        "summary": "The repo includes Rust-specific backend/API implementation patterns.",
        "patterns": [
            r"\bactix_web\b",
            r"\baxum::Router\b",
            r"\bwarp::Filter\b",
            r"\bhyper::Server\b",
            r"\btokio::main\b",
        ],
        "framework_weights": {"gdpr": 2, "uk-gdpr": 2, "us-state-privacy": 2, "ccpa-cpra": 2, "nis2": 1},
        "product_labels": ["saas-service"],
        "base_confidence": 0.62,
        "review_areas": ["API data handling", "security controls", "service hardening"],
        "skip_deferred": True,
    },
    {
        "id": "personal-data-processing",
        "category": "privacy",
        "title": "Personal-data processing",
        "summary": "The repo handles user or customer personal data fields.",
        "patterns": [
            r"\bemail\b",
            r"\bphone\b",
            r"\baddress\b",
            r"\buser(_id| id|profile)\b",
            r"\bcustomer(_id| id|profile)\b",
            r"\bfirst_name\b",
            r"\blast_name\b",
            r"\bdob\b",
            r"\bbirth(date)?\b",
            r"\bip address\b",
        ],
        "framework_weights": {
            "gdpr": 8,
            "uk-gdpr": 8,
            "us-state-privacy": 8,
            "ccpa-cpra": 8,
            "us-va-cdpa": 7,
            "us-co-cpa": 7,
            "hipaa": 2,
        },
        "product_labels": ["personal-data-processing"],
        "base_confidence": 0.77,
        "review_areas": ["Lawful basis", "retention", "data subject rights", "security controls"],
    },
    {
        "id": "uk-data-protection-regime",
        "category": "privacy",
        "title": "UK GDPR and DPA 2018 indicators",
        "summary": "The repo contains UK-specific privacy language and governance references.",
        "patterns": [
            r"\buk gdpr\b",
            r"\bdata protection act 2018\b",
            r"\bico\b",
            r"\bidta\b",
            r"\binternational data transfer agreement\b",
            r"\buk addendum\b",
        ],
        "framework_weights": {"uk-gdpr": 10, "gdpr": 3},
        "product_labels": [],
        "base_confidence": 0.82,
        "review_areas": ["UK data rights", "ICO-facing accountability", "UK transfer mechanisms"],
        "skip_deferred": True,
    },
    {
        "id": "analytics-and-tracking",
        "category": "privacy",
        "title": "Analytics or tracking stack",
        "summary": "The repo includes analytics, tracking, or session replay integrations.",
        "patterns": [
            r"\bsegment\b",
            r"\bmixpanel\b",
            r"\bamplitude\b",
            r"\bposthog\b",
            r"\bgoogle analytics\b",
            r"\bgtag\b",
            r"\bhotjar\b",
            r"\bfullstory\b",
            r"\bsentry\b",
            r"\bsession replay\b",
            r"\bcookie(s)?\b",
        ],
        "framework_weights": {
            "gdpr": 7,
            "uk-gdpr": 7,
            "us-state-privacy": 7,
            "ccpa-cpra": 8,
            "us-va-cdpa": 6,
            "us-co-cpa": 6,
            "sec-cyber-disclosure": 2,
        },
        "product_labels": ["tracked-user-behavior"],
        "base_confidence": 0.8,
        "review_areas": ["Consent", "vendor disclosures", "notice at collection"],
    },
    {
        "id": "privacy-notice",
        "category": "privacy-controls",
        "title": "Privacy notice or policy evidence",
        "summary": "The repo contains privacy policy or disclosure content.",
        "patterns": [
            r"\bprivacy policy\b",
            r"\bdata processing\b",
            r"\bcookie policy\b",
            r"\bnotice at collection\b",
            r"\bprivacy notice\b",
        ],
        "framework_weights": {
            "gdpr": 4,
            "uk-gdpr": 4,
            "us-state-privacy": 4,
            "ccpa-cpra": 5,
            "us-va-cdpa": 3,
            "us-co-cpa": 3,
        },
        "product_labels": [],
        "base_confidence": 0.7,
        "review_areas": ["Transparency"],
        "skip_deferred": True,
    },
    {
        "id": "consent-management",
        "category": "privacy-controls",
        "title": "Consent or preference controls",
        "summary": "The repo includes consent, cookie banner, or preference-management logic.",
        "patterns": [
            r"\bconsent\b",
            r"\bcookie banner\b",
            r"\bpreference center\b",
            r"\bopt[- ]in\b",
            r"\bopt[- ]out\b",
            r"\bdo not sell\b",
            r"\btracking preference\b",
        ],
        "framework_weights": {
            "gdpr": 6,
            "uk-gdpr": 6,
            "us-state-privacy": 7,
            "ccpa-cpra": 9,
            "us-va-cdpa": 7,
            "us-co-cpa": 7,
        },
        "product_labels": [],
        "base_confidence": 0.78,
        "review_areas": ["Consent", "preference management"],
        "skip_deferred": True,
    },
    {
        "id": "cpra-privacy-rights",
        "category": "privacy-controls",
        "title": "CCPA/CPRA rights and opt-out implementation",
        "summary": "The repo includes California-specific rights terms and preference-control patterns.",
        "patterns": [
            r"\bdo not sell or share\b",
            r"\bglobal privacy control\b",
            r"\bdo_not_sell_or_share\b",
            r"\blimit (the )?use of sensitive personal information\b",
            r"\bsensitive personal information\b",
            r"\bcross[- ]context behavioral advertising\b",
            r"\bservice provider\b",
            r"\bcontractor\b",
        ],
        "framework_weights": {"ccpa-cpra": 10, "us-state-privacy": 7, "us-va-cdpa": 4, "us-co-cpa": 4},
        "product_labels": [],
        "base_confidence": 0.83,
        "review_areas": [
            "Do Not Sell/Share controls",
            "Global Privacy Control support",
            "sensitive PI limitation handling",
            "service-provider restrictions",
        ],
        "skip_deferred": True,
    },
    {
        "id": "user-rights-controls",
        "category": "privacy-controls",
        "title": "Deletion, export, or access-request controls",
        "summary": "The repo includes user-rights or DSAR-style functionality.",
        "patterns": [
            r"\bdelete account\b",
            r"\bdelete user\b",
            r"\bexport data\b",
            r"\bdownload my data\b",
            r"\bdata subject\b",
            r"\bdsar\b",
            r"\bright to delete\b",
            r"\bright to access\b",
        ],
        "framework_weights": {
            "gdpr": 7,
            "uk-gdpr": 7,
            "us-state-privacy": 7,
            "ccpa-cpra": 8,
            "us-va-cdpa": 7,
            "us-co-cpa": 7,
        },
        "product_labels": [],
        "base_confidence": 0.82,
        "review_areas": ["Deletion", "access requests", "export coverage"],
        "skip_deferred": True,
    },
    {
        "id": "retention-controls",
        "category": "privacy-controls",
        "title": "Retention or purge controls",
        "summary": "The repo contains retention, archival, or data-purge logic.",
        "patterns": [
            r"\bretention\b",
            r"\bttl\b",
            r"\bexpire(s|d)?\b",
            r"\bpurge\b",
            r"\barchive\b",
            r"\bdelete after\b",
        ],
        "framework_weights": {
            "gdpr": 7,
            "uk-gdpr": 7,
            "us-state-privacy": 5,
            "ccpa-cpra": 4,
            "us-va-cdpa": 4,
            "us-co-cpa": 4,
            "hipaa": 3,
            "sox": 2,
        },
        "product_labels": [],
        "base_confidence": 0.76,
        "review_areas": ["Storage limitation", "records management"],
        "skip_deferred": True,
    },
    {
        "id": "audit-logging",
        "category": "security",
        "title": "Audit logging or traceability",
        "summary": "The repo includes audit logging or sensitive-action traceability.",
        "patterns": [
            r"\baudit log\b",
            r"\baudit trail\b",
            r"\badmin action\b",
            r"\bsecurity event\b",
            r"\bimmutable log\b",
            r"\bwho did what\b",
        ],
        "framework_weights": {"hipaa": 6, "sec-cyber-disclosure": 5, "sox": 5, "gdpr": 3},
        "product_labels": [],
        "base_confidence": 0.74,
        "review_areas": ["Traceability", "investigation support"],
        "skip_deferred": True,
    },
    {
        "id": "incident-response",
        "category": "security",
        "title": "Incident, breach, or disclosure workflow",
        "summary": "The repo contains incident response, breach, or disclosure process evidence.",
        "patterns": [
            r"\bincident response\b",
            r"\bsecurity incident\b",
            r"\bbreach\b",
            r"\bmateriality\b",
            r"\b8-k\b",
            r"\bdisclosure committee\b",
            r"\bsecurity escalation\b",
        ],
        "framework_weights": {
            "sec-cyber-disclosure": 8,
            "pci-dss": 4,
            "gdpr": 4,
            "uk-gdpr": 3,
            "hipaa": 3,
            "sox": 4,
        },
        "product_labels": ["disclosure-sensitive-operations"],
        "base_confidence": 0.76,
        "review_areas": ["Escalation", "investigation support", "disclosure readiness"],
        "skip_deferred": True,
    },
    {
        "id": "healthcare-data",
        "category": "healthcare",
        "title": "Healthcare, PHI, or clinical data handling",
        "summary": "The repo appears to support healthcare workflows or PHI-like data.",
        "patterns": [
            r"\bhipaa\b",
            r"\bphi\b",
            r"\bpatient\b",
            r"\bhealthcare provider\b",
            r"\bfhir\b",
            r"\bhl7\b",
            r"\bmedical record\b",
            r"\bcare plan\b",
            r"\bencounter\b",
            r"\bdiagnosis\b",
        ],
        "framework_weights": {"hipaa": 10, "fda-software": 5, "gdpr": 3},
        "product_labels": ["healthcare-software"],
        "base_confidence": 0.9,
        "review_areas": ["Access control", "audit trails", "vendor logging", "minimum necessary"],
    },
    {
        "id": "medical-device-claims",
        "category": "medical-device",
        "title": "Diagnostic, treatment, or device-control claims",
        "summary": "The repo suggests software that may fall into regulated medical-device review.",
        "patterns": [
            r"\bsamd\b",
            r"\bmedical device\b",
            r"\bdiagnostic\b",
            r"\btreatment recommendation\b",
            r"\bclinical decision\b",
            r"\b510\(k\)\b",
            r"\biec 62304\b",
            r"\bmedical.{0,20}telemetry\b",
        ],
        "framework_weights": {"fda-software": 10, "hipaa": 4},
        "product_labels": ["clinical-or-device-software"],
        "base_confidence": 0.88,
        "review_areas": ["Intended use", "validation", "traceability", "change control"],
    },
    {
        "id": "encryption-key-management",
        "category": "security",
        "title": "Encryption or key management",
        "summary": "The repo includes encryption configuration, certificate handling, or key management.",
        "patterns": [
            r"\baes[- ]?256\b",
            r"\btls\b",
            r"\bssl\b",
            r"\bcertificate\b",
            r"\bkms\b",
            r"\bkey[- ]?vault\b",
            r"\bencrypt(ion|ed)?\b",
            r"\bhash(ing|ed)?\b",
            r"\bbcrypt\b",
            r"\bsecret[- ]?manager\b",
        ],
        "framework_weights": {
            "gdpr": 3,
            "uk-gdpr": 3,
            "ccpa-cpra": 2,
            "hipaa": 4,
            "dora": 4,
            "nis2": 4,
            "pci-dss": 7,
            "sec-cyber-disclosure": 2,
        },
        "product_labels": [],
        "base_confidence": 0.7,
        "review_areas": ["Key rotation", "encryption at rest and in transit", "certificate management"],
        "skip_deferred": True,
    },
    {
        "id": "iac-deployment",
        "category": "infra",
        "title": "Infrastructure-as-code or deployment config",
        "summary": "The repo includes infrastructure definitions, container configs, or deployment manifests.",
        "patterns": [
            r"\bterraform\b",
            r"\bbicep\b",
            r"\bcloudformation\b",
            r"\bhelm\b",
            r"\bkustomize\b",
            r"\bkubernetes\b",
            r"\bdockerfile\b",
            r"\bdocker-compose\b",
            r"\bawstemplateformatversion\b",
            r"\bresources:\b",
            r"\bapiVersion:\s*v2\b",
            r"\bresource\s+\"[^\"]+\"\s+\"[^\"]+\"\b",
            r"\bresource\s+\w+\s+'[^']+'\s*=",
        ],
        "framework_weights": {"dora": 3, "nis2": 3, "pci-dss": 2, "sec-cyber-disclosure": 2},
        "product_labels": [],
        "base_confidence": 0.65,
        "review_areas": ["Change management", "environment isolation", "secret injection"],
        "skip_deferred": True,
    },
    {
        "id": "payment-card-processing",
        "category": "finance",
        "title": "Payment-card processing or PCI evidence",
        "summary": "The repo includes cardholder-data handling or PCI DSS control references.",
        "patterns": [
            r"\bpci[- ]?dss\b",
            r"\bcardholder data\b",
            r"\bprimary account number\b",
            r"\bcard[_ -]?number\b",
            r"\bcvv\b",
            r"\bcvc\b",
            r"\btokeni[sz]ation\b",
            r"\bpayment card\b",
            r"\b3d[- ]?secure\b",
            r"\bsaq[- ]?(a|b|c|d|p2pe)\b",
        ],
        "framework_weights": {"pci-dss": 10, "sec-cyber-disclosure": 3, "sox": 2},
        "product_labels": ["disclosure-sensitive-operations", "payment-processing-software"],
        "base_confidence": 0.86,
        "review_areas": [
            "Cardholder-data inventory",
            "tokenization and storage minimization",
            "encryption and key management",
            "access monitoring",
        ],
    },
    {
        "id": "financial-reporting",
        "category": "finance",
        "title": "Financial reporting or controls",
        "summary": "The repo includes financial systems, reporting, or internal-controls evidence.",
        "patterns": [
            r"\bgeneral ledger\b",
            r"\bjournal entr(y|ies)\b",
            r"\berp\b",
            r"\bsegregation of duties\b",
            r"\bapproval workflow\b",
            r"\bfinancial report\b",
            r"\breconciliation\b",
        ],
        "framework_weights": {"sox": 8, "sec-cyber-disclosure": 4, "dora": 3},
        "product_labels": ["disclosure-sensitive-operations"],
        "base_confidence": 0.78,
        "review_areas": ["Access control", "approval evidence", "audit trails", "change management"],
    },
    {
        "id": "ict-risk-management",
        "category": "resilience",
        "title": "ICT risk management or resilience controls",
        "summary": "The repo includes ICT risk management, resilience testing, or third-party ICT oversight.",
        "patterns": [
            r"\bdora\b",
            r"\bict[_ -]?risk\b",
            r"\bresilience[_ -]?test(ing)?\b",
            r"\bbusiness[_ -]?continuity\b",
            r"\bdisaster[_ -]?recovery\b",
            r"\bfailover\b",
            r"\bcircuit[_ -]?breaker\b",
            r"\bthird[_ -]?party[_ -]?risk\b",
        ],
        "framework_weights": {"dora": 9, "nis2": 5, "sec-cyber-disclosure": 3},
        "product_labels": [],
        "base_confidence": 0.74,
        "review_areas": ["ICT risk framework", "resilience testing", "third-party oversight", "incident reporting"],
    },
    {
        "id": "network-critical-infra",
        "category": "resilience",
        "title": "Network security or critical infrastructure controls",
        "summary": "The repo includes network security, supply-chain risk, or essential-service controls.",
        "patterns": [
            r"\bnis2\b",
            r"\bfirewall\w*\b",
            r"\bwaf\w*\b",
            r"\bddos\b",
            r"\bintrusion[_ -]?detect(ion)?\b",
            r"\bsupply[_ -]?chain\b",
            r"\bvulnerability[_ -]?scan(ning)?\b",
            r"\bpatch[_ -]?management\b",
        ],
        "framework_weights": {"nis2": 9, "dora": 5, "sec-cyber-disclosure": 3},
        "product_labels": [],
        "base_confidence": 0.72,
        "review_areas": ["Network security", "supply chain risk", "vulnerability management", "incident notification"],
    },
    {
        "id": "ai-risk-management",
        "category": "ai-controls",
        "title": "AI risk management framework alignment",
        "summary": "The repo includes evidence of AI risk management practices aligned with NIST AI RMF.",
        "patterns": [
            r"\bnist ai\b",
            r"\bai rmf\b",
            r"\bmodel card(s)?\b",
            r"\bdata(set)? card(s)?\b",
            r"\bbias\b",
            r"\bfairness\b",
            r"\bexplainab(le|ility)\b",
            r"\bai impact\b",
            r"\bai risk\b",
        ],
        "framework_weights": {"nist-ai-rmf": 9, "iso-42001": 6, "eu-ai-act": 5, "gdpr": 2, "uk-gdpr": 1},
        "product_labels": ["ai-enabled-software"],
        "base_confidence": 0.73,
        "review_areas": ["AI risk assessment", "bias and fairness", "model documentation", "explainability"],
        "skip_deferred": True,
    },
]

CONTROL_RULES = [
    {
        "control": "privacy-user-controls",
        "frameworks": ["gdpr", "uk-gdpr", "us-state-privacy", "ccpa-cpra", "us-va-cdpa", "us-co-cpa"],
        "required_if_any": ["personal-data-processing", "analytics-and-tracking"],
        "satisfied_by_any": [
            "privacy-notice",
            "consent-management",
            "cpra-privacy-rights",
            "user-rights-controls",
            "retention-controls",
        ],
        "missing_rationale": "Personal-data or tracking signals were found, but no privacy-notice, consent, deletion/export, or retention evidence was observed.",
        "observed_rationale": "Privacy-facing control evidence was observed alongside personal-data or tracking signals.",
        "confidence": 0.64,
    },
    {
        "control": "ai-governance-controls",
        "frameworks": ["eu-ai-act", "iso-42001"],
        "required_if_any": ["ai-model-integration"],
        "satisfied_by_any": ["ai-governance-controls", "ai-management-system", "ai-risk-management"],
        "missing_rationale": "AI model integration was found, but no moderation, guardrail, evaluation, or model-inventory evidence was observed.",
        "observed_rationale": "AI governance or safety-control evidence was observed.",
        "confidence": 0.69,
    },
    {
        "control": "cpra-consumer-rights",
        "frameworks": ["ccpa-cpra"],
        "required_if_any": ["personal-data-processing", "analytics-and-tracking"],
        "satisfied_by_any": ["cpra-privacy-rights", "consent-management", "user-rights-controls", "privacy-notice"],
        "missing_rationale": "California-facing data or tracking signals were found, but no Do Not Sell/Share, GPC, rights workflow, or notice-at-collection evidence was observed.",
        "observed_rationale": "California rights or opt-out control evidence was observed.",
        "confidence": 0.66,
    },
    {
        "control": "healthcare-safeguards",
        "frameworks": ["hipaa"],
        "required_if_any": ["healthcare-data"],
        "satisfied_by_any": ["audit-logging", "incident-response"],
        "missing_rationale": "Healthcare-like data signals were found, but little evidence of audit logging or incident workflow support was observed.",
        "observed_rationale": "Healthcare-relevant logging or incident evidence was observed.",
        "confidence": 0.67,
    },
    {
        "control": "disclosure-readiness",
        "frameworks": ["sec-cyber-disclosure", "sox"],
        "required_if_any": ["incident-response", "audit-logging"],
        "satisfied_by_any": ["incident-response", "audit-logging"],
        "missing_rationale": "",
        "observed_rationale": "Disclosure-sensitive logging or escalation evidence was observed.",
        "confidence": 0.58,
    },
    {
        "control": "ict-resilience",
        "frameworks": ["dora"],
        "required_if_any": ["ict-risk-management", "financial-reporting"],
        "satisfied_by_any": ["ict-risk-management", "encryption-key-management", "incident-response"],
        "missing_rationale": "Financial or ICT-risk signals were found, but no resilience testing, disaster recovery, or encryption evidence was observed.",
        "observed_rationale": "ICT resilience or risk management evidence was observed.",
        "confidence": 0.62,
    },
    {
        "control": "pci-cardholder-controls",
        "frameworks": ["pci-dss"],
        "required_if_any": ["payment-card-processing"],
        "satisfied_by_any": ["encryption-key-management", "audit-logging", "incident-response"],
        "missing_rationale": "Payment-card processing evidence was found, but no clear encryption, audit logging, or incident-response controls were observed.",
        "observed_rationale": "Payment-related security controls were observed alongside card-data processing signals.",
        "confidence": 0.7,
    },
    {
        "control": "network-security-controls",
        "frameworks": ["nis2"],
        "required_if_any": ["network-critical-infra", "web-api-service"],
        "satisfied_by_any": ["network-critical-infra", "encryption-key-management", "incident-response"],
        "missing_rationale": "Network or web service signals were found, but no firewall, vulnerability scanning, or supply-chain security evidence was observed.",
        "observed_rationale": "Network security or vulnerability management evidence was observed.",
        "confidence": 0.60,
    },
    {
        "control": "ai-risk-governance",
        "frameworks": ["nist-ai-rmf"],
        "required_if_any": ["ai-model-integration"],
        "satisfied_by_any": ["ai-risk-management", "ai-governance-controls"],
        "missing_rationale": "AI model integration was found, but no model cards, bias evaluation, fairness testing, or AI risk management evidence was observed.",
        "observed_rationale": "AI risk management or governance evidence was observed.",
        "confidence": 0.65,
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", required=True, help="Repo root or explicit file/directory to scan.")
    parser.add_argument(
        "--scope",
        choices=("full", "diff", "path"),
        default="full",
        help="Scan the full path, only changed files in a git repo, or the explicit path only.",
    )
    parser.add_argument(
        "--focus",
        choices=tuple(FRAMEWORKS.keys()),
        help="Filter output to signals relevant to a single framework.",
    )
    return parser.parse_args()


def make_relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def should_skip_file(path: Path) -> bool:
    lower_name = path.name.lower()
    if lower_name in EXCLUDED_FILE_NAMES:
        return True
    suffix = "".join(path.suffixes[-2:]).lower()
    if suffix in SKIPPED_SUFFIXES or path.suffix.lower() in SKIPPED_SUFFIXES:
        return True
    if path.stat().st_size > MAX_FILE_BYTES:
        return True
    if lower_name in SPECIAL_FILENAMES:
        return False
    if lower_name.startswith(".env"):
        return False
    if path.suffix.lower() in SCANNABLE_SUFFIXES:
        return False
    return "." in path.name


def is_probably_text(path: Path) -> bool:
    try:
        chunk = path.read_bytes()[:4096]
    except OSError:
        return False
    return b"\x00" not in chunk


def iter_full_scope(base_path: Path) -> tuple[list[Path], int]:
    files: list[Path] = []
    excluded = 0
    if base_path.is_file():
        return ([base_path] if not should_skip_file(base_path) and is_probably_text(base_path) else []), 0
    for root, dirnames, filenames in os.walk(base_path):
        dirnames[:] = [name for name in dirnames if name not in EXCLUDED_DIRS]
        root_path = Path(root)
        for filename in filenames:
            candidate = root_path / filename
            if should_skip_file(candidate) or not is_probably_text(candidate):
                excluded += 1
                continue
            files.append(candidate)
    return files, excluded


def git_changed_files(repo_root: Path) -> list[Path]:
    candidates: list[Path] = []
    commands = [
        ["git", "-C", str(repo_root), "diff", "--name-only", "--diff-filter=ACMRTUXB", "HEAD"],
        ["git", "-C", str(repo_root), "status", "--porcelain"],
    ]
    for command in commands:
        try:
            result = subprocess.run(command, check=False, capture_output=True, text=True)
        except OSError:
            continue
        if result.returncode != 0:
            continue
        for raw_line in result.stdout.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if command[-1] == "--porcelain":
                line = line[3:].strip()
            path = (repo_root / line).resolve()
            if path.exists():
                candidates.append(path)
        if candidates:
            break
    unique: list[Path] = []
    seen = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
    return unique


def collect_files(base_path: Path, scope: str) -> tuple[list[Path], Path, int]:
    scan_root = base_path.resolve()
    if scope == "diff":
        repo_root = scan_root if scan_root.is_dir() else scan_root.parent
        files = [path for path in git_changed_files(repo_root) if path.is_file()]
        filtered = [path for path in files if not should_skip_file(path) and is_probably_text(path)]
        return filtered, repo_root, max(len(files) - len(filtered), 0)
    if scope == "path":
        if not scan_root.exists():
            raise FileNotFoundError(scan_root)
        files, excluded = iter_full_scope(scan_root)
        root = scan_root.parent if scan_root.is_file() else scan_root
        return files, root, excluded
    files, excluded = iter_full_scope(scan_root)
    root = scan_root.parent if scan_root.is_file() else scan_root
    return files, root, excluded


def build_compiled_signal_definitions() -> list[dict[str, Any]]:
    compiled: list[dict[str, Any]] = []
    for definition in SIGNAL_DEFINITIONS:
        compiled.append(
            {
                **definition,
                "compiled_patterns": [re.compile(pattern, re.IGNORECASE) for pattern in definition["patterns"]],
            }
        )
    return compiled


def get_python_docstring_lines(path: Path) -> set[int]:
    """Return line numbers that fall inside module, class, or function docstrings.

    Only targets true docstrings — the first string expression in a module, class,
    or function body — not general string literals such as dict keys or assignments.
    Regex matches on docstring lines are skipped to avoid false positives from
    regulatory keywords that appear only in documentation prose.
    Returns an empty set if the file cannot be parsed.
    """
    try:
        source = path.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return set()

    docstring_lines: set[int] = set()

    def record_docstring(body: list[ast.stmt]) -> None:
        if not body:
            return
        first = body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            node = first.value
            start = getattr(node, "lineno", None)
            end = getattr(node, "end_lineno", start)
            if start is not None:
                for lineno in range(start, (end or start) + 1):
                    docstring_lines.add(lineno)

    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            record_docstring(getattr(node, "body", []))

    return docstring_lines


def scan_files(files: list[Path], root: Path, focus: str | None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    compiled_definitions = build_compiled_signal_definitions()
    signals: dict[str, dict[str, Any]] = {}
    framework_scores: dict[str, float] = defaultdict(float)
    label_reasons: dict[str, list[str]] = defaultdict(list)

    for definition in compiled_definitions:
        if focus and focus not in definition["framework_weights"]:
            continue
        signals[definition["id"]] = {
            "id": definition["id"],
            "category": definition["category"],
            "title": definition["title"],
            "frameworks": sorted(definition["framework_weights"].keys()),
            "confidence": definition["base_confidence"],
            "summary": definition["summary"],
            "review_areas": definition["review_areas"],
            "evidence": [],
            "_matched_terms": set(),
        }

    python_docstring_lines_cache: dict[str, set[int]] = {}

    for file_path in files:
        try:
            lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue

        # For Python source files, skip lines that fall inside module, class, or function
        # docstrings. This reduces false positives from regulatory keywords that appear
        # only in documentation prose rather than in executable code or configuration.
        is_python_source = file_path.suffix.lower() == ".py"
        docstring_lines: set[int] = set()
        if is_python_source:
            cache_key = str(file_path)
            if cache_key not in python_docstring_lines_cache:
                python_docstring_lines_cache[cache_key] = get_python_docstring_lines(file_path)
            docstring_lines = python_docstring_lines_cache[cache_key]

        for line_number, line in enumerate(lines, start=1):
            if not line.strip():
                continue
            if is_python_source and line_number in docstring_lines:
                continue
            snippet = line.strip()
            if len(snippet) > MAX_SNIPPET_CHARS:
                snippet = snippet[: MAX_SNIPPET_CHARS - 3] + "..."
            for definition in compiled_definitions:
                if definition["id"] not in signals:
                    continue
                lowered_line = line.lower()
                if definition.get("skip_deferred") and any(marker in lowered_line for marker in DEFERRED_MARKERS):
                    continue
                matches = []
                for pattern in definition["compiled_patterns"]:
                    found = pattern.search(line)
                    if found:
                        matches.append(found.group(0))
                if not matches:
                    continue
                signal = signals[definition["id"]]
                if len(signal["evidence"]) >= MAX_EVIDENCE_PER_SIGNAL:
                    signal["_matched_terms"].update(matches)
                    continue
                evidence_class = classify_evidence(file_path, line)
                signal["evidence"].append(
                    {
                        "path": make_relative(file_path, root),
                        "line": line_number,
                        "match": snippet,
                        "patterns": sorted({match.lower() for match in matches}),
                        "evidence_class": evidence_class,
                    }
                )
                signal["_matched_terms"].update(matches)

    materialized_signals: list[dict[str, Any]] = []
    for definition in compiled_definitions:
        signal = signals.get(definition["id"])
        if not signal or not signal["evidence"]:
            continue
        matched_terms = sorted({term.lower() for term in signal.pop("_matched_terms")})
        signal["matched_terms"] = matched_terms
        materialized_signals.append(signal)
        evidence_factor = min(len(signal["evidence"]) / 3.0, 1.0)
        # Weight by strongest evidence class — source/config evidence counts more than docs/comments
        class_weights = [EVIDENCE_WEIGHTS.get(ev.get("evidence_class", "source"), 1.0) for ev in signal["evidence"]]
        best_class_weight = max(class_weights) if class_weights else 1.0
        for framework, weight in definition["framework_weights"].items():
            framework_scores[framework] += weight * (0.6 + 0.4 * evidence_factor) * best_class_weight
        for label in definition["product_labels"]:
            label_reasons[label].append(definition["title"])

    product_profile = infer_product_profile(materialized_signals, label_reasons)
    candidate_frameworks = build_candidate_frameworks(materialized_signals, framework_scores, focus)
    control_observations = build_control_observations(materialized_signals, focus)
    return materialized_signals, {
        "product_profile": product_profile,
        "candidate_frameworks": candidate_frameworks,
        "control_observations": control_observations,
    }


def infer_product_profile(signals: list[dict[str, Any]], label_reasons: dict[str, list[str]]) -> dict[str, Any]:
    label_order = [
        "ai-enabled-software",
        "saas-service",
        "personal-data-processing",
        "tracked-user-behavior",
        "payment-processing-software",
        "healthcare-software",
        "clinical-or-device-software",
        "disclosure-sensitive-operations",
    ]
    labels = [label for label in label_order if label in label_reasons]
    if not labels and any(signal["id"] == "web-api-service" for signal in signals):
        labels.append("software-service")
        label_reasons["software-service"].append("Web application or API service")
    confidence = 0.25
    if labels:
        confidence = min(0.45 + (len(labels) * 0.08), 0.92)
    reasons = [f"{label.replace('-', ' ')} inferred from: {', '.join(sorted(set(label_reasons[label])))}." for label in labels]
    return {"labels": labels, "confidence": round(confidence, 2), "reasons": reasons}


def build_candidate_frameworks(
    signals: list[dict[str, Any]], framework_scores: dict[str, float], focus: str | None
) -> list[dict[str, Any]]:
    reasons_by_framework: dict[str, list[str]] = defaultdict(list)
    for signal in signals:
        for framework in signal["frameworks"]:
            if focus and framework != focus:
                continue
            reasons_by_framework[framework].append(signal["title"])

    candidates = []
    for framework, score in framework_scores.items():
        if focus and framework != focus:
            continue
        display_name = FRAMEWORKS[framework]
        normalized = min(int(round(score * 5)), 100)
        confidence = round(min(0.35 + (normalized / 120.0), 0.95), 2)
        candidates.append(
            {
                "framework": framework,
                "display_name": display_name,
                "score": normalized,
                "confidence": confidence,
                "reasons": [f"{title} evidence was detected." for title in sorted(set(reasons_by_framework[framework]))],
            }
        )
    return sorted(candidates, key=lambda item: (-item["score"], item["display_name"]))


def build_control_observations(signals: list[dict[str, Any]], focus: str | None) -> list[dict[str, Any]]:
    signal_map = {signal["id"]: signal for signal in signals}
    observations = []
    for rule in CONTROL_RULES:
        if focus and focus not in rule["frameworks"]:
            continue
        if not any(signal_id in signal_map for signal_id in rule["required_if_any"]):
            continue
        satisfied = [signal_map[signal_id] for signal_id in rule["satisfied_by_any"] if signal_id in signal_map]
        gating = [signal_map[signal_id] for signal_id in rule["required_if_any"] if signal_id in signal_map]
        if satisfied:
            evidence = flatten_evidence(satisfied)
            observations.append(
                {
                    "control": rule["control"],
                    "status": "observed",
                    "frameworks": rule["frameworks"],
                    "confidence": rule["confidence"],
                    "rationale": rule["observed_rationale"],
                    "evidence": evidence,
                }
            )
            continue
        if not rule["missing_rationale"]:
            continue
        observations.append(
            {
                "control": rule["control"],
                "status": "not-observed",
                "frameworks": rule["frameworks"],
                "confidence": rule["confidence"],
                "rationale": rule["missing_rationale"],
                "evidence": flatten_evidence(gating),
            }
        )
    return observations


def flatten_evidence(signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    for signal in signals:
        merged.extend(signal["evidence"][:2])
    return merged[:4]


def main() -> int:
    args = parse_args()
    base_path = Path(args.path)
    if not base_path.exists():
        print(json.dumps({"error": f"Path not found: {base_path}"}))
        return 1

    try:
        files, root, excluded_files = collect_files(base_path, args.scope)
    except FileNotFoundError:
        print(json.dumps({"error": f"Path not found: {base_path}"}))
        return 1

    signals, derived = scan_files(files, root, args.focus)
    output = {
        "scan": {
            "path": str(base_path),
            "scope": args.scope,
            "focus": args.focus,
            "scanned_files": len(files),
            "excluded_files": excluded_files,
        },
        "product_profile": derived["product_profile"],
        "signals": signals,
        "control_observations": derived["control_observations"],
        "candidate_frameworks": derived["candidate_frameworks"],
    }
    json.dump(output, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
