"""Network infrastructure configuration for IoT hub."""

FIREWALL_RULES = {
    "ingress": [
        {"port": 8883, "protocol": "mqtt+tls", "source": "device-subnet"},
        {"port": 443, "protocol": "https", "source": "admin-subnet"},
    ],
    "egress": [
        {"port": 443, "protocol": "https", "destination": "cloud-api"},
    ],
}

WAF_CONFIG = {
    "enabled": True,
    "rules": ["sql-injection", "xss", "rate-limit"],
}

VULNERABILITY_SCANNING = {
    "schedule": "weekly",
    "patch_management": "automated",
    "supply_chain": "sbom-generated",
}

INTRUSION_DETECTION = {
    "enabled": True,
    "ddos_protection": "cloud-native",
}
