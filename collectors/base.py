"""수집기 베이스 클래스"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from core.db import DB, SyncLog


@dataclass
class CollectResult:
    source: str
    total: int
    inserted: int
    updated: int
    errors: int = 0
    message: str = ""


class BaseCollector(ABC):
    source_name: str = "base"

    def __init__(self, db: DB, settings: Any, env: Any):
        self.db = db
        self.settings = settings
        self.env = env

    @abstractmethod
    def collect(self, **kwargs) -> CollectResult:
        pass

    def update_sync_log(self, result: CollectResult):
        with self.db.SessionLocal() as session:
            log = session.query(SyncLog).filter(SyncLog.source == self.source_name).first()
            if log:
                log.last_sync = datetime.utcnow()
                log.records_count = result.total
                log.status = "error" if result.errors else "success"
                log.message = result.message
            else:
                log = SyncLog(
                    source=self.source_name,
                    last_sync=datetime.utcnow(),
                    records_count=result.total,
                    status="error" if result.errors else "success",
                    message=result.message
                )
                session.add(log)
            session.commit()

    @staticmethod
    def safe_int(val: Any) -> Optional[int]:
        if val is None:
            return None
        try:
            return int(float(str(val).replace(',', '')))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def safe_float(val: Any) -> Optional[float]:
        if val is None:
            return None
        try:
            return float(str(val).replace(',', ''))
        except (ValueError, TypeError):
            return None
