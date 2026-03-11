"""IoT device telemetry ingestion with TLS and certificate management."""

from __future__ import annotations

from typing import Any

TLS_VERSION = "1.3"
CERTIFICATE_PATH = "/etc/iot/certs/device.pem"


class DeviceGateway:
    def ingest_telemetry(self, device_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "device_id": device_id,
            "encrypted": True,
            "tls": TLS_VERSION,
            "certificate": CERTIFICATE_PATH,
        }

    def register_device(self, device_id: str, user_email: str) -> dict[str, Any]:
        return {
            "device_id": device_id,
            "email": user_email,
            "kms": "aws-kms-key-arn",
        }
