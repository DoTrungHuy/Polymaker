from __future__ import annotations

import json

import httpx

from .config import Settings
from .models import DecisionResponse


def build_result_card(response: DecisionResponse) -> dict:
    elements: list[dict] = [{"tag": "markdown", "content": f"**状态：** {response.state.value}\n{response.message}"}]
    for index, item in enumerate(response.recommendations, start=1):
        settings = item.print_settings
        elements.append(
            {
                "tag": "markdown",
                "content": (
                    f"### {index}. {item.material_name}\n"
                    f"适配 **{item.fit_score}** · 证据 **{item.evidence_confidence}%**\n"
                    f"喷嘴 {settings.nozzle_c.min_c:g}–{settings.nozzle_c.max_c:g}℃ · "
                    f"热床 {settings.bed_c.min_c:g}–{settings.bed_c.max_c:g}℃\n"
                    f"{item.reasons[0] if item.reasons else ''}"
                ),
            }
        )
    if response.next_question:
        elements.append({"tag": "markdown", "content": f"**需要补充：** {response.next_question}"})
    elements.append(
        {
            "tag": "action",
            "actions": [
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "查看证据"},
                    "type": "primary",
                    "value": {"action": "evidence", "request_id": response.request_id},
                },
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "不符合需求"},
                    "value": {"action": "feedback_negative", "request_id": response.request_id},
                },
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "重新选择"},
                    "value": {"action": "restart", "request_id": response.request_id},
                },
            ],
        }
    )
    return {
        "schema": "2.0",
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": "PolyPilot 选材建议"},
            "subtitle": {
                "tag": "plain_text",
                "content": f"规则 {response.ruleset_version} · 数据 {response.dataset_version}",
            },
            "template": "orange",
        },
        "body": {"elements": elements},
    }


class FeishuGateway:
    BASE_URL = "https://open.feishu.cn/open-apis"

    def __init__(self, settings: Settings):
        self.settings = settings

    async def _tenant_token(self, client: httpx.AsyncClient) -> str:
        response = await client.post(
            f"{self.BASE_URL}/auth/v3/tenant_access_token/internal",
            json={"app_id": self.settings.feishu_app_id, "app_secret": self.settings.feishu_app_secret},
        )
        response.raise_for_status()
        token = response.json().get("tenant_access_token")
        if not token:
            raise RuntimeError("Feishu tenant token unavailable")
        return token

    async def reply_card(self, message_id: str, card: dict) -> None:
        async with httpx.AsyncClient(timeout=12) as client:
            token = await self._tenant_token(client)
            response = await client.post(
                f"{self.BASE_URL}/im/v1/messages/{message_id}/reply",
                headers={"Authorization": f"Bearer {token}"},
                json={"msg_type": "interactive", "content": json.dumps(card, ensure_ascii=False)},
            )
            response.raise_for_status()
            if response.json().get("code") != 0:
                raise RuntimeError(response.json().get("msg", "Feishu reply failed"))


def extract_message_text(payload: dict) -> tuple[str | None, str | None]:
    event = payload.get("event", {})
    message = event.get("message", {})
    message_id = message.get("message_id")
    try:
        content = json.loads(message.get("content", "{}"))
    except json.JSONDecodeError:
        return message_id, None
    return message_id, content.get("text")
