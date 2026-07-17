from __future__ import annotations

import json
import re
from typing import Protocol

import httpx
from pydantic import ValidationError

from .config import Settings
from .models import BudgetLevel, IntentSource, RiskLevel, SelectionIntent


class IntentParser(Protocol):
    async def parse(self, text: str) -> SelectionIntent: ...


def _contains(text: str, terms: tuple[str, ...]) -> bool | None:
    return True if any(term in text for term in terms) else None


class DeterministicIntentParser:
    """Safe fallback: extracts only explicit signals and never invents missing values."""

    async def parse(self, text: str) -> SelectionIntent:
        normalized = text.casefold()
        temperature_match = re.search(r"(?:最高|大约|约|达到|耐|到)?\s*(-?\d{2,3})\s*(?:°\s*)?[c℃度]", normalized)
        temperature = float(temperature_match.group(1)) if temperature_match else None
        outdoor = _contains(normalized, ("户外", "室外", "日晒", "uv", "outdoor"))
        flexible = _contains(normalized, ("柔性", "柔软", "可弯", "软的", "flexible", "tpu"))
        moisture = _contains(normalized, ("潮湿", "水汽", "淋雨", "防水", "moisture", "water"))
        appearance = _contains(normalized, ("外观", "光滑", "摆件", "模型", "颜色", "appearance", "smooth"))
        budget = None
        if any(term in normalized for term in ("便宜", "低成本", "省钱", "economy")):
            budget = BudgetLevel.ECONOMY
        elif any(term in normalized for term in ("预算充足", "性能优先", "premium")):
            budget = BudgetLevel.PREMIUM
        risk_terms = ("医疗", "食品接触", "压力容器", "承重安全", "攀岩", "合规", "medical", "food contact")
        risky = any(term in normalized for term in risk_terms)
        extracted = [
            temperature is not None,
            outdoor is not None,
            flexible is not None,
            moisture is not None,
            appearance is not None,
        ]
        confidence = min(0.85, 0.35 + sum(extracted) * 0.1)
        return SelectionIntent(
            raw_text=text,
            purpose=text.strip(),
            max_use_temperature_c=temperature,
            outdoor_exposure=outdoor,
            flexibility_required=flexible,
            moisture_exposure=moisture,
            appearance_priority=appearance,
            budget_level=budget,
            risk_level=RiskLevel.REGULATED if risky else RiskLevel.NORMAL,
            risk_tags=["keyword_detected"] if risky else [],
            source=IntentSource.DETERMINISTIC,
            confidence=confidence,
            requires_manual_form=True,
            parser_message="Aily 未配置或不可用；只提取了文本中明确出现的条件，请在结构化表单中确认。",
        )


class AilyIntentParser:
    BASE_URL = "https://open.feishu.cn/open-apis"

    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None):
        self.settings = settings
        self.client = client

    async def _tenant_token(self, client: httpx.AsyncClient) -> str:
        response = await client.post(
            f"{self.BASE_URL}/auth/v3/tenant_access_token/internal",
            json={"app_id": self.settings.feishu_app_id, "app_secret": self.settings.feishu_app_secret},
        )
        response.raise_for_status()
        payload = response.json()
        token = payload.get("tenant_access_token")
        if not token:
            raise RuntimeError(f"Feishu token request failed: {payload.get('msg', 'unknown error')}")
        return token

    async def parse(self, text: str) -> SelectionIntent:
        owned_client = self.client is None
        client = self.client or httpx.AsyncClient(timeout=12)
        try:
            token = await self._tenant_token(client)
            response = await client.post(
                f"{self.BASE_URL}/aily/v1/apps/{self.settings.aily_app_id}/skills/{self.settings.aily_skill_id}/start",
                headers={"Authorization": f"Bearer {token}"},
                json={"global_variable": {"query": text}, "input": json.dumps({"text": text}, ensure_ascii=False)},
            )
            response.raise_for_status()
            payload = response.json()
            if payload.get("code") != 0 or payload.get("data", {}).get("status") != "success":
                raise RuntimeError(payload.get("msg") or "Aily skill did not return success")
            output = payload.get("data", {}).get("output", "")
            parsed = json.loads(output) if isinstance(output, str) else output
            parsed.update(
                {
                    "raw_text": text,
                    "purpose": parsed.get("purpose") or text,
                    "source": IntentSource.AILY,
                    "requires_manual_form": False,
                }
            )
            return SelectionIntent.model_validate(parsed)
        except (httpx.HTTPError, RuntimeError, json.JSONDecodeError, ValidationError, TypeError, ValueError):
            return await DeterministicIntentParser().parse(text)
        finally:
            if owned_client:
                await client.aclose()


def intent_parser_for(settings: Settings) -> IntentParser:
    return AilyIntentParser(settings) if settings.aily_configured else DeterministicIntentParser()
