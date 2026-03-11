"""Incident response and security escalation procedures."""

INCIDENT_RESPONSE_PLAN = {
    "severity_levels": ["P1", "P2", "P3"],
    "escalation_path": ["on-call engineer", "security lead", "disclosure committee"],
    "breach_notification_sla_hours": 72,
    "materiality_threshold": "determined by legal and CFO",
    "business_continuity": {
        "failover": "active-passive",
        "disaster_recovery": "RPO 1h, RTO 4h",
        "resilience_testing": "quarterly",
    },
}

THIRD_PARTY_RISK = {
    "payment_processor": "Stripe",
    "cloud_provider": "AWS",
    "ict_risk_assessment": "annual",
}
