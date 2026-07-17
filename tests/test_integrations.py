import json

import httpx
import pytest

from polypilot.config import Settings
from polypilot.engine import decide
from polypilot.feishu import build_result_card
from polypilot.intent import AilyIntentParser
from polypilot.models import IntentSource, SelectionRequest
from polypilot.repository import load_materials


def aily_settings() -> Settings:
    return Settings(
        feishu_app_id="cli_test",
        feishu_app_secret="test-secret",
        aily_app_id="spring_test__c",
        aily_skill_id="skill_test",
    )


@pytest.mark.asyncio
async def test_aily_contract_accepts_schema_valid_json():
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("tenant_access_token/internal"):
            return httpx.Response(200, json={"code": 0, "tenant_access_token": "t-test"})
        output = {
            "purpose": "户外支架",
            "outdoor_exposure": True,
            "max_use_temperature_c": 80,
            "risk_level": "normal",
            "risk_tags": [],
            "confidence": 0.94,
        }
        return httpx.Response(
            200,
            json={"code": 0, "data": {"status": "success", "output": json.dumps(output)}},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        intent = await AilyIntentParser(aily_settings(), client).parse("户外支架，最高 80℃")
    assert intent.source is IntentSource.AILY
    assert intent.outdoor_exposure is True
    assert intent.max_use_temperature_c == 80
    assert intent.requires_manual_form is False


@pytest.mark.asyncio
async def test_invalid_aily_output_falls_back_without_recommending():
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("tenant_access_token/internal"):
            return httpx.Response(200, json={"tenant_access_token": "t-test"})
        return httpx.Response(
            200,
            json={"code": 0, "data": {"status": "success", "output": "not-json"}},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        intent = await AilyIntentParser(aily_settings(), client).parse("柔性线缆保护套")
    assert intent.source is IntentSource.DETERMINISTIC
    assert intent.requires_manual_form is True
    assert intent.parser_message


def test_feishu_card_contains_top_material_and_audit_versions():
    request = SelectionRequest.model_validate(
        {
            "purpose": "柔性线缆保护套",
            "flexibility_required": True,
            "outdoor_exposure": False,
            "printer": {
                "nozzle_max_c": 230,
                "bed_max_c": 60,
                "has_enclosure": False,
                "has_hardened_nozzle": False,
            },
        }
    )
    result = decide(request, load_materials())
    card = build_result_card(result)
    serialized = json.dumps(card, ensure_ascii=False)
    assert card["schema"] == "2.0"
    assert result.recommendations[0].material_name in serialized
    assert result.dataset_version in serialized
    assert "查看证据" in serialized
