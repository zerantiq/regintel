from typing import Any

FHIR_ENDPOINT = "/fhir/Patient"


class PatientService:
    def create_encounter(self, patient_id: str, diagnosis: str) -> dict[str, Any]:
        return {
            "patient": patient_id,
            "diagnosis": diagnosis,
            "care_plan": "follow-up",
            "treatment_recommendation": "Schedule clinician review",
        }
