from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from .models import MaterialProfile

ROOT = Path(__file__).resolve().parents[2]
MATERIALS_FILE = ROOT / "data" / "materials" / "materials.v1.json"


@lru_cache(maxsize=1)
def load_materials() -> list[MaterialProfile]:
    payload = json.loads(MATERIALS_FILE.read_text(encoding="utf-8"))
    return [MaterialProfile.model_validate(item) for item in payload["materials"]]


def load_material(material_key: str) -> MaterialProfile | None:
    normalized = material_key.casefold()
    return next((item for item in load_materials() if item.key.casefold() == normalized), None)


def dataset_metadata() -> dict[str, str | int]:
    payload = json.loads(MATERIALS_FILE.read_text(encoding="utf-8"))
    return {
        "version": payload["dataset_version"],
        "status": payload["dataset_status"],
        "updated_at": payload["updated_at"],
        "material_count": len(payload["materials"]),
    }


def clear_repository_cache() -> None:
    load_materials.cache_clear()
