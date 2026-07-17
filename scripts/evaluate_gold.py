"""Run the fixed 30-scenario contest benchmark."""

from __future__ import annotations

import json
from pathlib import Path

from polypilot.engine import decide
from polypilot.models import SelectionRequest
from polypilot.repository import load_materials

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = ROOT / "data" / "evaluation" / "gold-scenarios.v1.json"


def evaluate() -> tuple[int, int, list[str]]:
    payload = json.loads(SCENARIOS.read_text(encoding="utf-8"))
    passed = 0
    failures: list[str] = []
    materials = load_materials()
    for scenario in payload["scenarios"]:
        result = decide(SelectionRequest.model_validate(scenario["request"]), materials)
        top_keys = {item.material_key for item in result.recommendations}
        ok = True
        if expected_state := scenario.get("expected_state"):
            ok = result.state.value == expected_state
        if expected := set(scenario.get("expected_top_keys", [])):
            ok = ok and bool(top_keys & expected)
        if forbidden := set(scenario.get("forbidden_top_keys", [])):
            ok = ok and not bool(top_keys & forbidden)
        if ok:
            passed += 1
        else:
            failures.append(f"{scenario['id']}: state={result.state.value}, top={sorted(top_keys)}")
    return passed, len(payload["scenarios"]), failures


def main() -> int:
    passed, total, failures = evaluate()
    rate = passed / total
    print(f"Gold benchmark: {passed}/{total} ({rate:.1%})")
    for failure in failures:
        print(f"FAIL {failure}")
    return 0 if rate >= 0.80 else 1


if __name__ == "__main__":
    raise SystemExit(main())
