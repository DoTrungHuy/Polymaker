from pathlib import Path

from fastapi.testclient import TestClient

from polypilot.api import app
from polypilot.audit import LocalSQLiteAuditSink
from polypilot.models import FeedbackRequest

client = TestClient(app)


def request_payload() -> dict:
    return {
        "purpose": "flexible cable guide",
        "outdoor_exposure": False,
        "flexibility_required": True,
        "experience_level": "beginner",
        "impact_priority": 3,
        "printer": {
            "nozzle_max_c": 230,
            "bed_max_c": 60,
            "has_enclosure": False,
            "has_hardened_nozzle": False,
        },
    }


def test_health_endpoint_exposes_versions_and_material_count():
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["materials"] == 12
    assert payload["ruleset_version"]


def test_material_list_and_detail():
    response = client.get("/api/v1/materials")
    assert response.status_code == 200
    assert len(response.json()) == 12
    detail = client.get("/api/v1/materials/POLYMAKER_ASA")
    assert detail.status_code == 200
    assert detail.json()["evidence_status"] == "approved"
    assert client.get("/api/v1/materials/DOES_NOT_EXIST").status_code == 404


def test_recommendation_endpoint_returns_auditable_top_three():
    response = client.post("/api/v1/recommendations", json=request_payload())
    assert response.status_code == 200
    payload = response.json()
    assert payload["recommendations"]
    assert len(payload["recommendations"]) <= 3
    assert payload["recommendations"][0]["fit_score"] >= 0
    assert payload["recommendations"][0]["evidence_refs"]
    assert payload["request_id"].startswith("req_")


def test_intent_endpoint_uses_safe_fallback_without_credentials():
    response = client.post("/api/v1/intent/parse", json={"text": "打印一个户外使用、最高 80℃ 的支架"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "deterministic"
    assert payload["outdoor_exposure"] is True
    assert payload["max_use_temperature_c"] == 80
    assert payload["requires_manual_form"] is True


def test_feedback_is_persisted_locally(tmp_path: Path):
    sink = LocalSQLiteAuditSink(tmp_path / "audit.sqlite3")
    import asyncio

    result = asyncio.run(
        sink.record_feedback(
            FeedbackRequest.model_validate(
                {
                    "request_id": "req_123456",
                    "helpful": True,
                    "reason": "clear",
                }
            )
        )
    )
    assert result.stored_in == "local_sqlite"
    assert (tmp_path / "audit.sqlite3").exists()


def test_feishu_url_verification_contract():
    response = client.post(
        "/api/integrations/feishu/events",
        json={"type": "url_verification", "challenge": "challenge-value", "token": ""},
    )
    assert response.status_code == 200
    assert response.json() == {"challenge": "challenge-value"}


def test_feishu_card_action_contract():
    response = client.post(
        "/api/integrations/feishu/card-actions",
        json={"action": {"value": {"action": "evidence", "request_id": "req_123456"}}},
    )
    assert response.status_code == 200
    assert "证据" in response.json()["toast"]["content"]
