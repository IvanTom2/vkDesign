"""Реализация репозиториев и Unit of Work поверх SQLAlchemy (PostgreSQL).

Репозитории работают с доменными моделями, маппинг в ORM скрыт внутри.
"""

from __future__ import annotations

from datetime import datetime
from datetime import timezone

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker

from src.domain.interfaces import IJobRepository
from src.domain.interfaces import IMessageRepository
from src.domain.interfaces import IOutboxRepository
from src.domain.interfaces import IUnitOfWork
from src.domain.models import DialogMessage
from src.domain.models import Job
from src.domain.models import JobContext
from src.domain.models import JobStatus
from src.domain.models import MessageDirection
from src.domain.models import OutboxMessage
from src.domain.models import OutboxStatus
from src.infra.db.orm import JobORM
from src.infra.db.orm import MessageORM
from src.infra.db.orm import OutboxORM


def _now() -> datetime:
    return datetime.now(timezone.utc)


# --------------------------------------------------------------------------- #
#  Маппинг ORM -> домен
# --------------------------------------------------------------------------- #
def _to_message(row: MessageORM) -> DialogMessage:
    return DialogMessage(
        id=row.id,
        vk_message_id=row.vk_message_id,
        peer_id=row.peer_id,
        from_id=row.from_id,
        direction=MessageDirection(row.direction),
        text=row.text,
        vk_date=row.vk_date,
        created_at=row.created_at,
    )


def _to_job(row: JobORM) -> Job:
    return Job(
        id=row.id,
        peer_id=row.peer_id,
        from_id=row.from_id,
        trigger_message_id=row.trigger_message_id,
        status=JobStatus(row.status),
        context=JobContext.model_validate(row.context or {}),
        media_path=row.media_path,
        error=row.error,
        attempts=row.attempts,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _to_outbox(row: OutboxORM) -> OutboxMessage:
    return OutboxMessage(
        id=row.id,
        job_id=row.job_id,
        peer_id=row.peer_id,
        text=row.text,
        media_path=row.media_path,
        status=OutboxStatus(row.status),
        attempts=row.attempts,
        error=row.error,
        created_at=row.created_at,
        sent_at=row.sent_at,
    )


class MessageRepository(IMessageRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, message: DialogMessage) -> DialogMessage:
        row = MessageORM(
            vk_message_id=message.vk_message_id,
            peer_id=message.peer_id,
            from_id=message.from_id,
            direction=message.direction.value,
            text=message.text,
            vk_date=message.vk_date,
        )
        self._session.add(row)
        self._session.flush()
        return _to_message(row)

    def recent_by_peer(self, peer_id: int, limit: int) -> list[DialogMessage]:
        stmt = (
            select(MessageORM)
            .where(MessageORM.peer_id == peer_id)
            .order_by(MessageORM.id.desc())
            .limit(limit)
        )
        rows = list(self._session.scalars(stmt))
        rows.reverse()  # от старых к новым
        return [_to_message(r) for r in rows]


class JobRepository(IJobRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, job: Job) -> Job:
        row = JobORM(
            peer_id=job.peer_id,
            from_id=job.from_id,
            trigger_message_id=job.trigger_message_id,
            status=job.status.value,
            context=job.context.model_dump(),
            media_path=job.media_path,
            attempts=job.attempts,
        )
        self._session.add(row)
        self._session.flush()
        return _to_job(row)

    def get(self, job_id: int) -> Job | None:
        row = self._session.get(JobORM, job_id)
        return _to_job(row) if row else None

    def mark_processing(self, job_id: int) -> None:
        row = self._session.get(JobORM, job_id)
        if row is None:
            return
        row.status = JobStatus.PROCESSING.value
        row.attempts += 1

    def mark_done(self, job_id: int, media_path: str | None) -> None:
        row = self._session.get(JobORM, job_id)
        if row is None:
            return
        row.status = JobStatus.DONE.value
        row.media_path = media_path
        row.error = None

    def mark_failed(self, job_id: int, error: str) -> None:
        row = self._session.get(JobORM, job_id)
        if row is None:
            return
        row.status = JobStatus.FAILED.value
        row.error = error[:4000]


class OutboxRepository(IOutboxRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, message: OutboxMessage) -> OutboxMessage:
        row = OutboxORM(
            job_id=message.job_id,
            peer_id=message.peer_id,
            text=message.text,
            media_path=message.media_path,
            status=message.status.value,
        )
        self._session.add(row)
        self._session.flush()
        return _to_outbox(row)

    def get(self, outbox_id: int) -> OutboxMessage | None:
        row = self._session.get(OutboxORM, outbox_id)
        return _to_outbox(row) if row else None

    def mark_sent(self, outbox_id: int) -> None:
        row = self._session.get(OutboxORM, outbox_id)
        if row is None:
            return
        row.status = OutboxStatus.SENT.value
        row.sent_at = _now()
        row.error = None

    def mark_failed(self, outbox_id: int, error: str) -> None:
        row = self._session.get(OutboxORM, outbox_id)
        if row is None:
            return
        row.status = OutboxStatus.FAILED.value
        row.attempts += 1
        row.error = error[:4000]


class SqlAlchemyUnitOfWork(IUnitOfWork):
    """Открывает сессию-транзакцию и отдаёт репозитории, работающие в ней."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self._session: Session | None = None

    def __enter__(self) -> "SqlAlchemyUnitOfWork":
        self._session = self._session_factory()
        self.messages = MessageRepository(self._session)
        self.jobs = JobRepository(self._session)
        self.outbox = OutboxRepository(self._session)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        assert self._session is not None
        if exc_type is not None:
            self._session.rollback()
        self._session.close()
        self._session = None

    def commit(self) -> None:
        assert self._session is not None
        self._session.commit()

    def rollback(self) -> None:
        assert self._session is not None
        self._session.rollback()
