from polypilot.engine import decide, explain_material
from polypilot.models import DecisionState, RiskLevel, SelectionRequest
from polypilot.repository import load_materials

MATERIALS = load_materials()


def selection(**overrides) -> SelectionRequest:
    payload = {
        "purpose": "general functional bracket",
        "max_use_temperature_c": None,
        "outdoor_exposure": False,
        "flexibility_required": False,
        "impact_priority": 3,
        "stiffness_priority": 3,
        "experience_level": "beginner",
        "printer": {
            "nozzle_max_c": 260,
            "bed_max_c": 100,
            "has_enclosure": True,
            "has_hardened_nozzle": False,
        },
    }
    payload.update(overrides)
    return SelectionRequest.model_validate(payload)


def test_asks_only_one_high_impact_question():
    result = decide(selection(printer={"nozzle_max_c": None, "bed_max_c": None}), MATERIALS)
    assert result.state is DecisionState.NEED_MORE_INFO
    assert result.next_question == "你的打印机喷嘴最高温度是多少摄氏度？"


def test_flexible_case_keeps_only_tpu_candidates():
    result = decide(selection(flexibility_required=True, printer={"nozzle_max_c": 230, "bed_max_c": 60}), MATERIALS)
    assert result.recommendations
    assert all("TPU" in item.family for item in result.recommendations)
    assert any(item.rule_id == "R04_FLEXIBILITY_MINIMUM" for item in result.excluded)


def test_outdoor_high_temperature_prefers_asa_when_equipment_allows():
    result = decide(selection(purpose="户外耐候支架", outdoor_exposure=True, max_use_temperature_c=85), MATERIALS)
    assert result.state in {DecisionState.RECOMMEND, DecisionState.CONDITIONAL}
    assert result.recommendations[0].material_key == "POLYMAKER_ASA"


def test_open_printer_excludes_enclosure_materials():
    result = decide(
        selection(
            printer={
                "nozzle_max_c": 300,
                "bed_max_c": 110,
                "has_enclosure": False,
                "has_hardened_nozzle": True,
            }
        ),
        MATERIALS,
    )
    excluded = {item.material_key: item.rule_id for item in result.excluded}
    assert excluded["POLYMAKER_ASA"] == "R03_ENCLOSURE_REQUIRED"
    assert excluded["POLYMAX_PC"] == "R03_ENCLOSURE_REQUIRED"


def test_composite_requires_hardened_nozzle():
    result = decide(
        selection(printer={"nozzle_max_c": 300, "bed_max_c": 100, "has_enclosure": True, "has_hardened_nozzle": False}),
        MATERIALS,
    )
    assert any(
        item.material_key == "FIBERON_PA6_CF20" and item.rule_id == "R03_HARDENED_NOZZLE_REQUIRED"
        for item in result.excluded
    )


def test_temperature_unknown_is_not_treated_as_pass():
    result = decide(selection(max_use_temperature_c=45), MATERIALS)
    assert any(item.rule_id == "R04_TEMPERATURE_EVIDENCE_MISSING" for item in result.excluded)


def test_safety_critical_request_is_refused_before_ranking():
    result = decide(selection(risk_level=RiskLevel.SAFETY_CRITICAL), MATERIALS)
    assert result.state is DecisionState.REFUSE_OR_ESCALATE
    assert result.recommendations == []


def test_risk_is_detected_from_purpose_text():
    result = decide(selection(purpose="食品接触水杯"), MATERIALS)
    assert result.state is DecisionState.REFUSE_OR_ESCALATE
    assert result.human_escalation is True


def test_response_separates_fit_and_evidence_confidence():
    result = decide(selection(), MATERIALS)
    first = result.recommendations[0]
    assert 0 <= first.fit_score <= 100
    assert first.evidence_confidence == 100
    assert first.evidence_refs


def test_decision_lab_explains_all_equipment_changes_for_target_material():
    material = next(item for item in MATERIALS if item.key == "POLYMAX_PC")
    trace = explain_material(
        selection(
            max_use_temperature_c=80,
            printer={
                "nozzle_max_c": 240,
                "bed_max_c": 80,
                "has_enclosure": False,
                "has_hardened_nozzle": False,
            },
        ),
        material,
    )
    assert trace.status == "change_conditions"
    assert {item.field for item in trace.required_changes} == {
        "printer.nozzle_max_c",
        "printer.bed_max_c",
        "printer.has_enclosure",
    }
    assert trace.feasible_after_changes is True
    assert trace.projected_fit_score is not None


def test_decision_lab_does_not_turn_missing_evidence_into_a_pass():
    material = next(item for item in MATERIALS if item.key == "PANCHROMA_PLA")
    trace = explain_material(selection(max_use_temperature_c=50), material)
    assert trace.status == "evidence_blocked"
    assert trace.feasible_after_changes is False
    assert trace.projected_fit_score is None
