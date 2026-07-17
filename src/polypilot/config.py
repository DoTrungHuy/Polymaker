from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    app_env: str = "development"
    dataset_mode: str = "official"
    feishu_app_id: str = ""
    feishu_app_secret: str = ""
    feishu_verification_token: str = ""
    feishu_encrypt_key: str = ""
    aily_app_id: str = ""
    aily_skill_id: str = ""
    bitable_app_token: str = ""
    bitable_table_id: str = ""
    feishu_card_template_id: str = ""

    @property
    def aily_configured(self) -> bool:
        return bool(self.feishu_app_id and self.feishu_app_secret and self.aily_app_id and self.aily_skill_id)

    @property
    def bot_configured(self) -> bool:
        return bool(self.feishu_app_id and self.feishu_app_secret)

    @property
    def bitable_configured(self) -> bool:
        return bool(self.bot_configured and self.bitable_app_token and self.bitable_table_id)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        app_env=os.getenv("APP_ENV", "development"),
        dataset_mode=os.getenv("DATASET_MODE", os.getenv("POLYPILOT_DATA_MODE", "official")),
        feishu_app_id=os.getenv("FEISHU_APP_ID", ""),
        feishu_app_secret=os.getenv("FEISHU_APP_SECRET", ""),
        feishu_verification_token=os.getenv("FEISHU_VERIFICATION_TOKEN", ""),
        feishu_encrypt_key=os.getenv("FEISHU_ENCRYPT_KEY", ""),
        aily_app_id=os.getenv("AILY_APP_ID", ""),
        aily_skill_id=os.getenv("AILY_SKILL_ID", ""),
        bitable_app_token=os.getenv("BITABLE_APP_TOKEN", ""),
        bitable_table_id=os.getenv("BITABLE_TABLE_ID", ""),
        feishu_card_template_id=os.getenv("FEISHU_CARD_TEMPLATE_ID", ""),
    )


def clear_settings_cache() -> None:
    get_settings.cache_clear()
