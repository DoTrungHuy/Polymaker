from __future__ import annotations

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from .audit import audit_sink_for
from .config import get_settings
from .engine import DATASET_VERSION, RULESET_VERSION, SCHEMA_VERSION, decide, explain_material
from .feishu import FeishuGateway, build_result_card, extract_message_text
from .intent import intent_parser_for
from .models import (
    DecisionResponse,
    FeedbackRequest,
    FeedbackResponse,
    IntegrationStatus,
    IntentParseRequest,
    MaterialDecisionTrace,
    MaterialProfile,
    SelectionIntent,
    SelectionRequest,
)
from .repository import dataset_metadata, load_material, load_materials

app = FastAPI(
    title="PolyPilot Decision API",
    version="1.1.0",
    description=(
        "Auditable material-selection API for the Polymaker challenge. "
        "AI parses intent; deterministic rules own the decision."
    ),
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "product": "PolyPilot",
        "schema_version": SCHEMA_VERSION,
        "ruleset_version": RULESET_VERSION,
        "dataset_version": DATASET_VERSION,
        "materials": dataset_metadata()["material_count"],
        "aily_mode": "configured" if settings.aily_configured else "deterministic_fallback",
    }


@app.get("/api/health")
@app.get("/health", include_in_schema=False)
def health() -> dict:
    return _health()


@app.get("/api/integration-status", response_model=IntegrationStatus)
def integration_status() -> IntegrationStatus:
    settings = get_settings()
    return IntegrationStatus(
        aily_configured=settings.aily_configured,
        feishu_bot_configured=settings.bot_configured,
        bitable_configured=settings.bitable_configured,
        audit_sink="feishu_bitable" if settings.bitable_configured else "local_sqlite",
    )


@app.post("/api/v1/intent/parse", response_model=SelectionIntent)
async def parse_intent(request: IntentParseRequest) -> SelectionIntent:
    return await intent_parser_for(get_settings()).parse(request.text)


@app.get("/api/v1/materials", response_model=list[MaterialProfile])
@app.get("/v1/materials", response_model=list[MaterialProfile], include_in_schema=False)
def list_materials() -> list[MaterialProfile]:
    return load_materials()


@app.get("/api/v1/materials/{material_key}", response_model=MaterialProfile)
def material_detail(material_key: str) -> MaterialProfile:
    material = load_material(material_key)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    return material


@app.post("/api/v1/recommendations", response_model=DecisionResponse)
@app.post("/v1/recommendations", response_model=DecisionResponse, include_in_schema=False)
async def create_recommendation(request: SelectionRequest) -> DecisionResponse:
    response = decide(request, load_materials())
    await audit_sink_for(get_settings()).record_decision(request, response)
    return response


@app.post("/api/v1/decision-lab/{material_key}", response_model=MaterialDecisionTrace)
async def decision_lab(material_key: str, request: SelectionRequest) -> MaterialDecisionTrace:
    material = load_material(material_key)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    return explain_material(request, material)


@app.post("/api/v1/feedback", response_model=FeedbackResponse)
async def create_feedback(feedback: FeedbackRequest) -> FeedbackResponse:
    return await audit_sink_for(get_settings()).record_feedback(feedback)


@app.post("/api/integrations/feishu/events")
async def feishu_events(payload: dict, background_tasks: BackgroundTasks) -> dict:
    settings = get_settings()
    if payload.get("type") == "url_verification":
        if settings.feishu_verification_token and payload.get("token") != settings.feishu_verification_token:
            raise HTTPException(status_code=403, detail="Invalid verification token")
        return {"challenge": payload.get("challenge", "")}
    if payload.get("encrypt"):
        raise HTTPException(
            status_code=501,
            detail=(
                "Encrypted callbacks are not enabled in this MVP; "
                "disable event encryption or add a reviewed decryptor."
            ),
        )
    header_token = payload.get("header", {}).get("token")
    if settings.feishu_verification_token and header_token != settings.feishu_verification_token:
        raise HTTPException(status_code=403, detail="Invalid event token")
    message_id, text = extract_message_text(payload)
    if not message_id or not text:
        return {"status": "ignored", "reason": "not a text message"}

    async def process_message() -> None:
        intent = await intent_parser_for(settings).parse(text)
        request = SelectionRequest(
            purpose=intent.purpose,
            max_use_temperature_c=intent.max_use_temperature_c,
            outdoor_exposure=intent.outdoor_exposure,
            flexibility_required=intent.flexibility_required,
            moisture_exposure=intent.moisture_exposure,
            impact_priority=intent.impact_priority,
            stiffness_priority=intent.stiffness_priority,
            appearance_priority=intent.appearance_priority,
            budget_level=intent.budget_level,
            risk_level=intent.risk_level,
            risk_tags=intent.risk_tags,
            printer={"nozzle_max_c": None, "bed_max_c": None},
        )
        response = decide(request, load_materials())
        await audit_sink_for(settings).record_decision(request, response)
        if settings.bot_configured:
            await FeishuGateway(settings).reply_card(message_id, build_result_card(response))

    background_tasks.add_task(process_message)
    return {"status": "accepted"}


@app.post("/api/integrations/feishu/card-actions")
async def feishu_card_actions(request: Request) -> dict:
    payload = await request.json()
    action = payload.get("action", {}).get("value", {})
    return {
        "toast": {
            "type": "success",
            "content": {
                "evidence": "请在 PolyPilot 网页的证据账本中查看来源。",
                "decision_lab": "请在 PolyPilot 网页的决策实验室中选择被排除材料。",
                "feedback_negative": "已收到反馈，请补充不符合需求的原因。",
                "restart": "请重新发送你的用途和打印机条件。",
            }.get(action.get("action"), "操作已收到。"),
        }
    }
