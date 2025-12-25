"""설정 로더 - GitHub Actions용"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List
import os
import yaml


@dataclass
class Settings:
    regions: List[str] = field(default_factory=lambda: ["서울", "인천", "경기"])
    facility_scores: Dict[str, int] = field(default_factory=dict)
    keywords_high_intent: List[str] = field(default_factory=list)
    keywords_facilities: List[str] = field(default_factory=list)
    scoring: Dict[str, int] = field(default_factory=dict)
    api: Dict[str, Any] = field(default_factory=dict)

    def get_api(self, name: str) -> Dict:
        return self.api.get(name, {})


@dataclass
class Env:
    db_path: str = "./data/cybarrier.db"
    data_go_kr_key: str = ""
    telegram_token: str = ""
    telegram_chat_id: str = ""

    @property
    def has_data_go_kr(self) -> bool:
        return bool(self.data_go_kr_key)


def load_settings(path: str = "config.yaml") -> Settings:
    if not Path(path).exists():
        return Settings()
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return Settings(
        regions=raw.get("regions", ["서울", "인천", "경기"]),
        facility_scores=raw.get("facility_scores", {}),
        keywords_high_intent=raw.get("keywords", {}).get("high_intent", []),
        keywords_facilities=raw.get("keywords", {}).get("facilities", []),
        scoring=raw.get("scoring", {}),
        api=raw.get("api", {}),
    )


def load_env() -> Env:
    return Env(
        db_path=os.environ.get("DB_PATH", "./data/cybarrier.db"),
        data_go_kr_key=os.environ.get("DATA_GO_KR_SERVICE_KEY", ""),
        telegram_token=os.environ.get("TELEGRAM_TOKEN", ""),
        telegram_chat_id=os.environ.get("TELEGRAM_CHAT_ID", ""),
    )
