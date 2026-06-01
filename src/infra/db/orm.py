"""SQLAlchemy ORM-модели (PostgreSQL). Маппинг в доменные модели — в
repositories.py. Схема создаётся через Base.metadata (см. engine.init_db).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from src.domain.models import JobStatus
from src.domain.models import MessageDirection
from src.domain.models import OutboxStatus


class Base(DeclarativeBase):
    pass


class MessageORM(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    vk_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    peer_id: Mapped[int] = mapped_column(BigInteger)
    from_id: Mapped[int] = mapped_column(BigInteger)
    direction: Mapped[str] = mapped_column(
        String(16), default=MessageDirection.INCOMING.value
    )
    text: Mapped[str] = mapped_column(Text, default="")
    vk_date: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (Index("ix_messages_peer_id", "peer_id"),)


class JobORM(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    peer_id: Mapped[int] = mapped_column(BigInteger)
    from_id: Mapped[int] = mapped_column(BigInteger)
    trigger_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default=JobStatus.PENDING.value)
    context: Mapped[dict] = mapped_column(JSONB, default=dict)
    media_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("ix_jobs_peer_id", "peer_id"),
        Index("ix_jobs_status", "status"),
    )


class OutboxORM(Base):
    __tablename__ = "outbox"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("jobs.id", ondelete="CASCADE")
    )
    peer_id: Mapped[int] = mapped_column(BigInteger)
    text: Mapped[str] = mapped_column(Text, default="")
    media_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default=OutboxStatus.PENDING.value)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (Index("ix_outbox_status", "status"),)
