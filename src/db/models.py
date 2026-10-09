"""ORM models."""
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class SecurityLog(Base):
    """A processed network record produced by the ETL pipeline."""
    __tablename__ = "security_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(64), index=True, default="etl")
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)


class ModelRun(Base):
    """One training run with its real evaluation metrics."""
    __tablename__ = "model_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_path: Mapped[str] = mapped_column(String(512))
    dataset: Mapped[str] = mapped_column(String(512))
    accuracy: Mapped[float] = mapped_column(Float)
    precision: Mapped[float] = mapped_column(Float)
    recall: Mapped[float] = mapped_column(Float)
    f1_score: Mapped[float] = mapped_column(Float)
    confusion_matrix: Mapped[list] = mapped_column(JSON)
    trained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)


class Detection(Base):
    """One prediction batch (an upload to /api/v1/predict)."""
    __tablename__ = "detections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    records_analyzed: Mapped[int] = mapped_column(Integer)
    threats_detected: Mapped[int] = mapped_column(Integer)
    model_path: Mapped[str] = mapped_column(String(512), default="")
    client: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)


class Alert(Base):
    """Threat alert raised from a detection."""
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    severity: Mapped[str] = mapped_column(String(16), index=True)
    threat_type: Mapped[str] = mapped_column(String(64))
    source_ip: Mapped[str] = mapped_column(String(64), default="n/a")
    status: Mapped[str] = mapped_column(String(32), default="open")
    details: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
