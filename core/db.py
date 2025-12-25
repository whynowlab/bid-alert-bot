"""DB 모듈"""
from __future__ import annotations
from datetime import datetime
from dataclasses import dataclass
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, Text, DateTime, UniqueConstraint
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()


class BidNotice(Base):
    __tablename__ = "bid_notices"

    id = Column(Integer, primary_key=True)
    endpoint = Column(String(50))
    bid_ntce_no = Column(String(50), index=True)
    bid_ntce_ord = Column(String(10))

    title = Column(String(500))
    org = Column(String(200))
    demand_org = Column(String(200))
    region = Column(String(50))
    category = Column(String(100))

    budget = Column(Float)
    bid_begin_dt = Column(String(30))
    bid_close_dt = Column(String(30))
    open_dt = Column(String(30))

    contact_name = Column(String(100))
    contact_phone = Column(String(50))
    contact_email = Column(String(200))

    score = Column(Float, default=0)
    matched_keywords = Column(Text)
    url = Column(String(500))
    raw_data = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("endpoint", "bid_ntce_no", "bid_ntce_ord", name="uq_bid"),)


class SyncLog(Base):
    __tablename__ = "sync_logs"

    id = Column(Integer, primary_key=True)
    source = Column(String(50), unique=True)
    last_sync = Column(DateTime)
    records_count = Column(Integer)
    status = Column(String(20))
    message = Column(Text)


@dataclass
class DB:
    engine: any
    SessionLocal: any


def open_db(db_path: str) -> DB:
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    SessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    return DB(engine=engine, SessionLocal=SessionLocal)
