"""Validate the public material dataset and its evidence contract."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from polypilot.models import EvidenceStatus, MaterialProfile

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data" / "materials" / "materials.v1.json"

REQUIRED_FIELDS = {"nozzle", "bed", "enclosure"}


def main() -> int:
    payload = json.loads(DATASET.read_text(encoding="utf-8"))
    raw_materials = payload.get("materials", [])
    if len(raw_materials) < 12:
        print(f"FAIL expected at least 12 gold materials; found {len(raw_materials)}")
        return 1
    try:
        materials = [MaterialProfile.model_validate(item) for item in raw_materials]
    except ValidationError as exc:
        print(f"FAIL schema validation\n{exc}")
        return 1

    keys = [item.key for item in materials]
    if len(keys) != len(set(keys)):
        print("FAIL duplicate material keys")
        return 1
    for item in materials:
        if item.evidence_status is not EvidenceStatus.APPROVED:
            print(f"FAIL gold material is not approved: {item.key}")
            return 1
        source_ids = {source.source_id for source in item.source_refs}
        if not source_ids:
            print(f"FAIL no source reference: {item.key}")
            return 1
        missing = REQUIRED_FIELDS - set(item.field_evidence)
        if missing:
            print(f"FAIL missing field evidence for {item.key}: {', '.join(sorted(missing))}")
            return 1
        dangling = set(item.field_evidence.values()) - source_ids
        if dangling:
            print(f"FAIL dangling evidence refs for {item.key}: {', '.join(sorted(dangling))}")
            return 1
        if any(not source.url.startswith("https://") for source in item.source_refs):
            print(f"FAIL non-HTTPS source URL: {item.key}")
            return 1

    print(f"PASS {len(materials)} approved materials; schema and evidence links are valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
