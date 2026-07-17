from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
from uuid import uuid4

import httpx

from .config import Settings
from .models import DecisionResponse, FeedbackRequest, FeedbackResponse, SelectionRequest

ROOT = Path(__file__).resolve().parents[2]


class AuditSink(Protocol):
    async def record_decision(self, request: SelectionRequest, response: DecisionResponse) -> None: ...
    async def record_feedback(self, feedback: FeedbackRequest) -> FeedbackResponse: ...


class LocalSQLiteAuditSink:
    def __init__(self, path: Path | None = None):
        self.path = path or ROOT / ".local" / "polypilot-audit.sqlite3"

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.execute(
            "CREATE TABLE IF NOT EXISTS audit_events (id TEXT PRIMARY KEY, kind TEXT, created_at TEXT, payload TEXT)"
        )
        return connection

    async def record_decision(self, request: SelectionRequest, response: DecisionResponse) -> None:
        payload = {"request": request.model_dump(mode="json"), "response": response.model_dump(mode="json")}
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO audit_events VALUES (?, ?, ?, ?)",
                (
                    response.request_id,
                    "decision",
                    datetime.now(UTC).isoformat(),
                    json.dumps(payload, ensure_ascii=False),
                ),
            )

    async def record_feedback(self, feedback: FeedbackRequest) -> FeedbackResponse:
        feedback_id = f"fb_{uuid4().hex[:16]}"
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO audit_events VALUES (?, ?, ?, ?)",
                (feedback_id, "feedback", datetime.now(UTC).isoformat(), feedback.model_dump_json()),
            )
        return FeedbackResponse(feedback_id=feedback_id, stored_in="local_sqlite")


class FeishuBitableAuditSink:
    BASE_URL = "https://open.feishu.cn/open-apis"

    def __init__(self, settings: Settings):
        self.settings = settings

    async def _token(self, client: httpx.AsyncClient) -> str:
        response = await client.post(
            f"{self.BASE_URL}/auth/v3/tenant_access_token/internal",
            json={"app_id": self.settings.feishu_app_id, "app_secret": self.settings.feishu_app_secret},
        )
        response.raise_for_status()
        token = response.json().get("tenant_access_token")
        if not token:
            raise RuntimeError("Feishu tenant token unavailable")
        return token

    async def _write(self, fields: dict) -> None:
        async with httpx.AsyncClient(timeout=12) as client:
            token = await self._token(client)
            response = await client.post(
                f"{self.BASE_URL}/bitable/v1/apps/{self.settings.bitable_app_token}/tables/{self.settings.bitable_table_id}/records",
                headers={"Authorization": f"Bearer {token}"},
                json={"fields": fields},
            )
            response.raise_for_status()
            if response.json().get("code") != 0:
                raise RuntimeError(response.json().get("msg", "Bitable write failed"))

    async def record_decision(self, request: SelectionRequest, response: DecisionResponse) -> None:
        await self._write(
            {
                "Record ID": response.request_id,
                "Type": "decision",
                "Purpose": request.purpose,
                "State": response.state.value,
                "Top Materials": ", ".join(item.material_name for item in response.recommendations),
                "Ruleset": response.ruleset_version,
                "Dataset": response.dataset_version,
                "Payload": response.model_dump_json(),
            }
        )

    async def record_feedback(self, feedback: FeedbackRequest) -> FeedbackResponse:
        feedback_id = f"fb_{uuid4().hex[:16]}"
        await self._write(
            {
                "Record ID": feedback_id,
                "Type": "feedback",
                "Request ID": feedback.request_id,
                "Helpful": feedback.helpful,
                "Reason": feedback.reason or "",
                "Selected Material": feedback.selected_material_key or "",
            }
        )
        return FeedbackResponse(feedback_id=feedback_id, stored_in="feishu_bitable")


def audit_sink_for(settings: Settings) -> AuditSink:
    return FeishuBitableAuditSink(settings) if settings.bitable_configured else LocalSQLiteAuditSink()
