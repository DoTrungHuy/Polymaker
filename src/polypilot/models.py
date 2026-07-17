from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class DecisionState(StrEnum):
    NEED_MORE_INFO = "NEED_MORE_INFO"
    RECOMMEND = "RECOMMEND"
    CONDITIONAL = "CONDITIONAL"
    NO_COMPATIBLE_MATERIAL = "NO_COMPATIBLE_MATERIAL"
    REFUSE_OR_ESCALATE = "REFUSE_OR_ESCALATE"


class EvidenceStatus(StrEnum):
    APPROVED = "approved"
    REVIEW_PENDING = "review_pending"
    CONFLICTING = "conflicting"
    DEMO_ONLY = "demo_only"


class ExperienceLevel(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class RiskLevel(StrEnum):
    NORMAL = "normal"
    SAFETY_CRITICAL = "safety_critical"
    REGULATED = "regulated"


class BudgetLevel(StrEnum):
    ECONOMY = "economy"
    STANDARD = "standard"
    PREMIUM = "premium"


class IntentSource(StrEnum):
    AILY = "aily"
    DETERMINISTIC = "deterministic"
    MANUAL = "manual"


class ReviewStatus(StrEnum):
    APPROVED = "approved"
    REVIEW_PENDING = "review_pending"
    CONFLICTING = "conflicting"


class PrinterProfile(BaseModel):
    nozzle_max_c: float | None = Field(default=None, ge=0, le=500)
    bed_max_c: float | None = Field(default=None, ge=0, le=250)
    has_enclosure: bool | None = None
    has_hardened_nozzle: bool | None = None
    direct_drive: bool | None = None


class SelectionIntent(BaseModel):
    raw_text: str = Field(min_length=3, max_length=1000)
    purpose: str
    max_use_temperature_c: float | None = Field(default=None, ge=-50, le=300)
    outdoor_exposure: bool | None = None
    flexibility_required: bool | None = None
    moisture_exposure: bool | None = None
    impact_priority: int | None = Field(default=None, ge=1, le=5)
    stiffness_priority: int | None = Field(default=None, ge=1, le=5)
    appearance_priority: bool | None = None
    budget_level: BudgetLevel | None = None
    risk_level: RiskLevel = RiskLevel.NORMAL
    risk_tags: list[str] = Field(default_factory=list)
    source: IntentSource
    confidence: float = Field(ge=0, le=1)
    requires_manual_form: bool = False
    parser_message: str | None = None


class SelectionRequest(BaseModel):
    purpose: str = Field(min_length=3, max_length=500)
    max_use_temperature_c: float | None = Field(default=None, ge=-50, le=300)
    outdoor_exposure: bool | None = None
    flexibility_required: bool | None = None
    moisture_exposure: bool | None = None
    impact_priority: int | None = Field(default=None, ge=1, le=5)
    stiffness_priority: int | None = Field(default=None, ge=1, le=5)
    appearance_priority: bool | None = None
    experience_level: ExperienceLevel = ExperienceLevel.BEGINNER
    budget_level: BudgetLevel | None = None
    risk_level: RiskLevel = RiskLevel.NORMAL
    risk_tags: list[str] = Field(default_factory=list)
    printer: PrinterProfile

    @model_validator(mode="after")
    def normalize_priorities(self) -> SelectionRequest:
        if self.impact_priority is None:
            self.impact_priority = 3
        if self.stiffness_priority is None:
            self.stiffness_priority = 3
        return self


class SourceRef(BaseModel):
    source_id: str
    url: str
    title: str
    document_version: str | None = None
    accessed_at: str
    page_or_section: str | None = None
    applicability: str
    sha256: str | None = None


class MaterialField(BaseModel):
    value: Any
    unit: str | None = None
    condition: str | None = None
    evidence_ref: str
    review_status: ReviewStatus


class TemperatureRange(BaseModel):
    min_c: float
    max_c: float


class PrintSettings(BaseModel):
    nozzle_c: TemperatureRange
    bed_c: TemperatureRange
    speed_mm_s: str | None = None
    cooling: str | None = None
    drying: str | None = None
    annealing: str | None = None


class MaterialProfile(BaseModel):
    key: str
    display_name: str
    series: str
    family: str
    summary: str
    print_settings: PrintSettings
    requires_enclosure: bool
    requires_hardened_nozzle: bool
    requires_all_metal_hotend: bool = False
    capabilities: set[str]
    print_difficulty: int = Field(ge=1, le=5)
    cost_tier: int = Field(ge=1, le=3)
    heat_reference_c: float | None = None
    heat_reference_type: str | None = None
    tradeoffs: list[str] = Field(default_factory=list)
    postprocessing: list[str] = Field(default_factory=list)
    evidence_status: EvidenceStatus
    source_refs: list[SourceRef]
    field_evidence: dict[str, str]


class Exclusion(BaseModel):
    material_key: str
    material_name: str
    rule_id: str
    reason: str


class Recommendation(BaseModel):
    material_key: str
    material_name: str
    family: str
    fit_score: int = Field(ge=0, le=100)
    evidence_confidence: int = Field(ge=0, le=100)
    evidence_status: EvidenceStatus
    reasons: list[str]
    tradeoffs: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    print_settings: PrintSettings
    postprocessing: list[str] = Field(default_factory=list)
    evidence_refs: list[SourceRef] = Field(default_factory=list)
    score_breakdown: dict[str, int] = Field(default_factory=dict)

    @property
    def score(self) -> int:
        """Compatibility alias for early clients."""
        return self.fit_score


class DecisionResponse(BaseModel):
    request_id: str
    state: DecisionState
    data_mode: str
    schema_version: str
    ruleset_version: str
    dataset_version: str
    message: str
    next_question: str | None = None
    recommendations: list[Recommendation] = Field(default_factory=list)
    excluded: list[Exclusion] = Field(default_factory=list)
    triggered_rules: list[str] = Field(default_factory=list)
    human_escalation: bool = False


class FeedbackRequest(BaseModel):
    request_id: str = Field(min_length=6, max_length=100)
    helpful: bool
    reason: str | None = Field(default=None, max_length=1000)
    selected_material_key: str | None = Field(default=None, max_length=100)


class FeedbackResponse(BaseModel):
    feedback_id: str
    stored_in: str
    status: str = "accepted"


class IntentParseRequest(BaseModel):
    text: str = Field(min_length=3, max_length=1000)


class IntegrationStatus(BaseModel):
    aily_configured: bool
    feishu_bot_configured: bool
    bitable_configured: bool
    audit_sink: str
