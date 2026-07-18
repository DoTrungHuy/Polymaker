from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from .models import (
    BudgetLevel,
    ConditionChange,
    DecisionLabStatus,
    DecisionResponse,
    DecisionState,
    EvidenceStatus,
    Exclusion,
    ExperienceLevel,
    MaterialDecisionTrace,
    MaterialProfile,
    Recommendation,
    RiskLevel,
    SelectionRequest,
)

SCHEMA_VERSION = "1.1.0"
RULESET_VERSION = "1.1.0"
DATASET_VERSION = "2026.07.17-gold12"

RISK_KEYWORDS = {
    "medical": ("医疗", "植入", "假肢", "medical", "implant"),
    "food_contact": ("食品接触", "餐具", "水杯", "food contact", "food-safe"),
    "pressure": ("压力容器", "高压", "pressure vessel", "compressed gas"),
    "safety_load": ("承重安全", "攀岩", "吊装", "汽车制动", "safety critical", "load bearing"),
    "regulated": ("认证", "合规", "法规", "certified", "regulated"),
}

PURPOSE_CAPABILITIES = {
    "decorative": ("模型", "摆件", "外观", "cosplay", "miniature", "display"),
    "impact": ("防护", "支架", "卡扣", "夹具", "impact", "bracket", "fixture"),
    "flexible": ("柔性", "软", "线缆", "保护壳", "wearable", "cable", "flexible"),
    "stiff": ("刚性", "齿轮", "治具", "结构件", "stiff", "gear", "tooling"),
    "smoothable": ("光滑", "镜面", "透明", "smooth", "glossy"),
}


@dataclass(frozen=True)
class ScorePart:
    value: float
    available: bool = True


def detect_risk_tags(request: SelectionRequest) -> list[str]:
    text = request.purpose.casefold()
    tags = set(request.risk_tags)
    for tag, terms in RISK_KEYWORDS.items():
        if any(term.casefold() in text for term in terms):
            tags.add(tag)
    return sorted(tags)


def _response(state: DecisionState, message: str, **kwargs) -> DecisionResponse:
    return DecisionResponse(
        request_id=f"req_{uuid4().hex[:16]}",
        state=state,
        data_mode="official_structured_facts",
        schema_version=SCHEMA_VERSION,
        ruleset_version=RULESET_VERSION,
        dataset_version=DATASET_VERSION,
        message=message,
        **kwargs,
    )


def _need_more_info(request: SelectionRequest) -> DecisionResponse | None:
    questions = [
        (
            request.printer.nozzle_max_c is None,
            "喷嘴最高温度会直接改变候选范围。",
            "你的打印机喷嘴最高温度是多少摄氏度？",
        ),
        (
            request.printer.bed_max_c is None,
            "热床最高温度会直接改变候选范围。",
            "你的打印机热床最高温度是多少摄氏度？",
        ),
        (
            request.outdoor_exposure is True and request.max_use_temperature_c is None,
            "户外用途需要最高使用温度才能判断热性能底线。",
            "零件预计会遇到的最高使用温度是多少摄氏度？",
        ),
    ]
    for missing, message, question in questions:
        if missing:
            return _response(
                DecisionState.NEED_MORE_INFO,
                message,
                next_question=question,
                triggered_rules=["R01_MISSING_CRITICAL_FIELD"],
            )
    return None


def _exclude(excluded: list[Exclusion], material: MaterialProfile, rule_id: str, reason: str) -> None:
    excluded.append(
        Exclusion(
            material_key=material.key,
            material_name=material.display_name,
            rule_id=rule_id,
            reason=reason,
        )
    )


def _purpose_targets(request: SelectionRequest) -> set[str]:
    text = request.purpose.casefold()
    targets = {
        capability
        for capability, terms in PURPOSE_CAPABILITIES.items()
        if any(term.casefold() in text for term in terms)
    }
    if request.flexibility_required:
        targets.add("flexible")
    if request.appearance_priority:
        targets.add("decorative")
    return targets


def _hard_blockers(material: MaterialProfile, request: SelectionRequest) -> list[Exclusion]:
    """Return every deterministic blocker for one material in rule priority order."""
    blockers: list[Exclusion] = []

    def block(rule_id: str, reason: str) -> None:
        _exclude(blockers, material, rule_id, reason)

    if material.evidence_status is not EvidenceStatus.APPROVED:
        block("R00_UNAPPROVED_DATA", "材料数据尚未审核，不进入正式推荐。")
    if (
        request.printer.nozzle_max_c is not None
        and request.printer.nozzle_max_c < material.print_settings.nozzle_c.min_c
    ):
        block("R02_NOZZLE_LIMIT", "喷嘴温度上限低于官方最低打印温度。")
    if (
        request.printer.bed_max_c is not None
        and request.printer.bed_max_c < material.print_settings.bed_c.min_c
    ):
        block("R02_BED_LIMIT", "热床温度上限低于官方最低打印温度。")
    if material.requires_enclosure and request.printer.has_enclosure is not True:
        block("R03_ENCLOSURE_REQUIRED", "官方条件要求封闭仓，当前设备未确认具备。")
    if material.requires_hardened_nozzle and request.printer.has_hardened_nozzle is not True:
        block("R03_HARDENED_NOZZLE_REQUIRED", "材料具有磨蚀性，官方建议或要求耐磨喷嘴。")
    if request.flexibility_required and "flexible" not in material.capabilities:
        block("R04_FLEXIBILITY_MINIMUM", "用户把柔性设为最低要求，该材料不满足。")
    if request.outdoor_exposure and "outdoor" not in material.capabilities:
        block("R04_OUTDOOR_MINIMUM", "官方资料未确认该材料适合户外使用。")
    if request.max_use_temperature_c is not None:
        if material.heat_reference_c is None:
            block("R04_TEMPERATURE_EVIDENCE_MISSING", "缺少可审核的热性能参考值，不能默认满足。")
        elif material.heat_reference_c < request.max_use_temperature_c:
            block("R04_TEMPERATURE_MINIMUM", "官方热性能参考值低于用户明确的环境温度。")
    return blockers


def _score_material(
    material: MaterialProfile, request: SelectionRequest
) -> tuple[int, int, dict[str, int], list[str], list[str]]:
    targets = _purpose_targets(request)
    reasons: list[str] = []
    conditions: list[str] = []
    parts: dict[str, tuple[ScorePart, int]] = {}

    if targets:
        matched = targets & material.capabilities
        ratio = len(matched) / len(targets)
        parts["functional_fit"] = (ScorePart(100 * ratio), 35)
        if matched:
            reasons.append(f"功能标签匹配：{', '.join(sorted(matched))}。")
    else:
        parts["functional_fit"] = (ScorePart(50), 35)
        reasons.append("通过设备硬约束，可作为通用候选继续比较。")

    environment_specified = any(
        value is not None
        for value in (
            request.outdoor_exposure,
            request.max_use_temperature_c,
            request.moisture_exposure,
        )
    )
    if environment_specified:
        values: list[float] = []
        if request.outdoor_exposure is not None:
            values.append(100 if (not request.outdoor_exposure or "outdoor" in material.capabilities) else 0)
        if request.moisture_exposure is not None:
            values.append(
                100 if (not request.moisture_exposure or "moisture_resistant" in material.capabilities) else 0
            )
        if request.max_use_temperature_c is not None:
            if material.heat_reference_c is None:
                values.append(0)
            else:
                headroom = material.heat_reference_c - request.max_use_temperature_c
                values.append(max(0, min(100, 60 + headroom * 2)))
                conditions.append(
                    f"热性能比较采用官方 {material.heat_reference_type} "
                    f"{material.heat_reference_c:g}℃ 参考值，不等于成品安全工作温度。"
                )
        parts["environment_fit"] = (ScorePart(sum(values) / len(values)), 20)

    mechanical_values: list[float] = []
    if request.impact_priority and request.impact_priority >= 3:
        mechanical_values.append(100 if "impact" in material.capabilities else 35)
    if request.stiffness_priority and request.stiffness_priority >= 4:
        mechanical_values.append(100 if "stiff" in material.capabilities else 30)
    if mechanical_values:
        parts["mechanical_fit"] = (ScorePart(sum(mechanical_values) / len(mechanical_values)), 15)

    nozzle_margin = request.printer.nozzle_max_c - material.print_settings.nozzle_c.min_c
    bed_margin = request.printer.bed_max_c - material.print_settings.bed_c.min_c
    hardware_score = min(100, 55 + max(0, nozzle_margin) + max(0, bed_margin) / 2)
    if material.requires_enclosure:
        hardware_score -= 10
    if material.requires_hardened_nozzle:
        hardware_score -= 10
    parts["printer_margin"] = (ScorePart(max(0, hardware_score)), 15)
    reasons.append(
        f"设备满足最低打印条件：喷嘴 ≥ {material.print_settings.nozzle_c.min_c:g}℃，"
        f"热床 ≥ {material.print_settings.bed_c.min_c:g}℃。"
    )

    experience_penalty = {
        ExperienceLevel.BEGINNER: 15,
        ExperienceLevel.INTERMEDIATE: 8,
        ExperienceLevel.ADVANCED: 3,
    }[request.experience_level]
    printability = max(0, 100 - (material.print_difficulty - 1) * experience_penalty)
    parts["printability"] = (ScorePart(printability), 10)

    if request.budget_level is not None:
        allowed = {
            BudgetLevel.ECONOMY: 1,
            BudgetLevel.STANDARD: 2,
            BudgetLevel.PREMIUM: 3,
        }[request.budget_level]
        parts["budget"] = (ScorePart(100 if material.cost_tier <= allowed else 20), 5)

    active_weight = sum(weight for _, weight in parts.values())
    weighted = sum(part.value * weight for part, weight in parts.values()) / active_weight
    breakdown = {name: round(part.value) for name, (part, _) in parts.items()}

    required_evidence = ["nozzle", "bed", "enclosure"]
    if material.requires_hardened_nozzle:
        required_evidence.append("hardened_nozzle")
    if request.max_use_temperature_c is not None:
        required_evidence.append("heat_reference")
    covered = sum(1 for key in required_evidence if material.field_evidence.get(key))
    confidence = round(100 * covered / len(required_evidence))
    return round(weighted), confidence, breakdown, reasons, conditions


def decide(request: SelectionRequest, materials: list[MaterialProfile]) -> DecisionResponse:
    risk_tags = detect_risk_tags(request)
    if request.risk_level is not RiskLevel.NORMAL or risk_tags:
        tags = ", ".join(risk_tags) if risk_tags else request.risk_level.value
        return _response(
            DecisionState.REFUSE_OR_ESCALATE,
            f"检测到高风险或受监管用途（{tags}）。系统只提供信息整理，不能给出确定性材料或合规结论。",
            triggered_rules=["R06_HIGH_RISK_ESCALATION"],
            human_escalation=True,
        )

    question = _need_more_info(request)
    if question:
        return question

    excluded: list[Exclusion] = []
    recommendations: list[Recommendation] = []
    triggered_rules: set[str] = set()

    for material in materials:
        blockers = _hard_blockers(material, request)
        if blockers:
            excluded.append(blockers[0])
            triggered_rules.add(blockers[0].rule_id)
            continue

        score, confidence, breakdown, reasons, conditions = _score_material(material, request)
        if request.printer.nozzle_max_c == material.print_settings.nozzle_c.min_c:
            conditions.append("喷嘴能力恰好处于官方最低边界，没有温度余量。")
            triggered_rules.add("R05_BOUNDARY_CONDITION")
        recommendations.append(
            Recommendation(
                material_key=material.key,
                material_name=material.display_name,
                family=material.family,
                fit_score=score,
                evidence_confidence=confidence,
                evidence_status=material.evidence_status,
                reasons=reasons,
                tradeoffs=material.tradeoffs,
                conditions=conditions,
                print_settings=material.print_settings,
                postprocessing=material.postprocessing,
                evidence_refs=material.source_refs,
                score_breakdown=breakdown,
            )
        )

    if not recommendations:
        return _response(
            DecisionState.NO_COMPATIBLE_MATERIAL,
            "当前设备、用途和证据条件下没有可靠候选。请调整条件、升级设备或转人工复核。",
            excluded=excluded,
            triggered_rules=sorted(triggered_rules),
            human_escalation=True,
        )

    recommendations.sort(key=lambda item: (item.fit_score, item.evidence_confidence), reverse=True)
    top_three = recommendations[:3]
    conditional = any(item.conditions for item in top_three)
    return _response(
        DecisionState.CONDITIONAL if conditional else DecisionState.RECOMMEND,
        "候选已通过硬约束过滤，并按用户已提供的维度归一化排序。适配得分不是安全概率。",
        recommendations=top_three,
        excluded=excluded,
        triggered_rules=sorted(triggered_rules),
    )


def explain_material(request: SelectionRequest, material: MaterialProfile) -> MaterialDecisionTrace:
    """Explain why a target material is unavailable and the smallest explicit changes needed."""
    risk_tags = detect_risk_tags(request)
    if request.risk_level is not RiskLevel.NORMAL or risk_tags:
        return MaterialDecisionTrace(
            material_key=material.key,
            material_name=material.display_name,
            status=DecisionLabStatus.SAFETY_BLOCKED,
            message="高风险或受监管用途不能通过调整参数自动解除人工复核。",
            feasible_after_changes=False,
            evidence_refs=material.source_refs,
            ruleset_version=RULESET_VERSION,
            dataset_version=DATASET_VERSION,
        )

    missing = _need_more_info(request)
    if missing:
        return MaterialDecisionTrace(
            material_key=material.key,
            material_name=material.display_name,
            status=DecisionLabStatus.CHANGE_CONDITIONS,
            message=missing.next_question or missing.message,
            feasible_after_changes=False,
            evidence_refs=material.source_refs,
            ruleset_version=RULESET_VERSION,
            dataset_version=DATASET_VERSION,
        )

    blockers = _hard_blockers(material, request)
    if not blockers:
        score, confidence, _, _, _ = _score_material(material, request)
        return MaterialDecisionTrace(
            material_key=material.key,
            material_name=material.display_name,
            status=DecisionLabStatus.COMPATIBLE,
            message="该材料已通过当前全部硬约束；若未进入 Top 3，原因是综合排序而不是设备不兼容。",
            feasible_after_changes=True,
            projected_fit_score=score,
            projected_evidence_confidence=confidence,
            evidence_refs=material.source_refs,
            ruleset_version=RULESET_VERSION,
            dataset_version=DATASET_VERSION,
        )

    changes: list[ConditionChange] = []
    projected = request.model_copy(deep=True)
    evidence_blocked = False
    for blocker in blockers:
        if blocker.rule_id == "R00_UNAPPROVED_DATA":
            evidence_blocked = True
            changes.append(
                ConditionChange(
                    field="evidence_status",
                    label="完成数据审核",
                    current_value=material.evidence_status.value,
                    required_value=EvidenceStatus.APPROVED.value,
                    rationale="未经审核的数据不能通过用户设置变更进入正式推荐。",
                    user_controllable=False,
                )
            )
        elif blocker.rule_id == "R02_NOZZLE_LIMIT":
            changes.append(
                ConditionChange(
                    field="printer.nozzle_max_c",
                    label="提高喷嘴温度能力",
                    current_value=request.printer.nozzle_max_c,
                    required_value=material.print_settings.nozzle_c.min_c,
                    rationale="达到该材料官方最低喷嘴温度。",
                )
            )
            projected.printer.nozzle_max_c = material.print_settings.nozzle_c.min_c
        elif blocker.rule_id == "R02_BED_LIMIT":
            changes.append(
                ConditionChange(
                    field="printer.bed_max_c",
                    label="提高热床温度能力",
                    current_value=request.printer.bed_max_c,
                    required_value=material.print_settings.bed_c.min_c,
                    rationale="达到该材料官方最低热床温度。",
                )
            )
            projected.printer.bed_max_c = material.print_settings.bed_c.min_c
        elif blocker.rule_id == "R03_ENCLOSURE_REQUIRED":
            changes.append(
                ConditionChange(
                    field="printer.has_enclosure",
                    label="增加封闭仓",
                    current_value=request.printer.has_enclosure,
                    required_value=True,
                    rationale="该材料的官方打印条件要求封闭仓。",
                )
            )
            projected.printer.has_enclosure = True
        elif blocker.rule_id == "R03_HARDENED_NOZZLE_REQUIRED":
            changes.append(
                ConditionChange(
                    field="printer.has_hardened_nozzle",
                    label="更换耐磨喷嘴",
                    current_value=request.printer.has_hardened_nozzle,
                    required_value=True,
                    rationale="纤维填充材料会磨损普通喷嘴。",
                )
            )
            projected.printer.has_hardened_nozzle = True
        elif blocker.rule_id == "R04_FLEXIBILITY_MINIMUM":
            changes.append(
                ConditionChange(
                    field="flexibility_required",
                    label="重新确认柔性是否为硬要求",
                    current_value=True,
                    required_value=False,
                    rationale="该材料本身不能满足柔性底线；只有需求改变时才可进入候选。",
                    user_controllable=False,
                )
            )
            projected.flexibility_required = False
        elif blocker.rule_id == "R04_OUTDOOR_MINIMUM":
            changes.append(
                ConditionChange(
                    field="outdoor_exposure",
                    label="仅限非户外场景",
                    current_value=True,
                    required_value=False,
                    rationale="官方资料未确认户外适用，不能用偏好设置绕过。",
                    user_controllable=False,
                )
            )
            projected.outdoor_exposure = False
        elif blocker.rule_id == "R04_TEMPERATURE_EVIDENCE_MISSING":
            evidence_blocked = True
            changes.append(
                ConditionChange(
                    field="heat_reference_c",
                    label="补齐热性能证据",
                    current_value=None,
                    required_value="approved official reference",
                    rationale="缺少经审核热性能数据，不能推算安全温度。",
                    user_controllable=False,
                )
            )
        elif blocker.rule_id == "R04_TEMPERATURE_MINIMUM":
            changes.append(
                ConditionChange(
                    field="max_use_temperature_c",
                    label="验证更低的实际环境温度",
                    current_value=request.max_use_temperature_c,
                    required_value=material.heat_reference_c,
                    rationale="只有实际最高温度不超过官方热性能参考值时，才可能进入候选。",
                    user_controllable=False,
                )
            )
            projected.max_use_temperature_c = material.heat_reference_c

    remaining = _hard_blockers(material, projected)
    feasible = not evidence_blocked and not remaining
    score: int | None = None
    confidence: int | None = None
    if feasible:
        score, confidence, _, _, _ = _score_material(material, projected)

    return MaterialDecisionTrace(
        material_key=material.key,
        material_name=material.display_name,
        status=DecisionLabStatus.EVIDENCE_BLOCKED if evidence_blocked else DecisionLabStatus.CHANGE_CONDITIONS,
        message=(
            "证据缺口不能由用户设置自动绕过，需要先完成资料审核。"
            if evidence_blocked
            else "以下是让该材料进入候选所需的最小条件变化；涉及用途变化的项目必须按真实场景确认。"
        ),
        blocking_rules=blockers,
        required_changes=changes,
        feasible_after_changes=feasible,
        projected_fit_score=score,
        projected_evidence_confidence=confidence,
        evidence_refs=material.source_refs,
        ruleset_version=RULESET_VERSION,
        dataset_version=DATASET_VERSION,
    )
