"""Доменные модели сервиса: сущности, которые ходят между этапами
(поллер → воркер → отправщик) и сохраняются в БД.

Это чистый домен — без знаний о SQLAlchemy, pika или VK. ORM-модели и
маппинг живут в src/infra/db.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel
from pydantic import Field

from src.domain.generator.models import ImageGenerationContextDTO
from src.domain.generator.models import StyleContextDTO


class MessageDirection(StrEnum):
    INCOMING = "incoming"
    OUTGOING = "outgoing"


class JobStatus(StrEnum):
    PENDING = "pending"  # создана, ждёт обработки
    PROCESSING = "processing"  # воркер взял в работу
    DONE = "done"  # обработана, результат готов
    FAILED = "failed"  # обработка упала


class OutboxStatus(StrEnum):
    PENDING = "pending"  # ждёт отправки в VK
    SENT = "sent"  # отправлено
    FAILED = "failed"  # отправка упала


class DialogMessage(BaseModel):
    """Сообщение из диалога (история). Хранится для извлечения контекста."""

    id: int | None = None
    vk_message_id: int | None = None
    peer_id: int
    from_id: int
    direction: MessageDirection = MessageDirection.INCOMING
    text: str = ""
    vk_date: int | None = None
    created_at: datetime | None = None


class JobContext(BaseModel):
    """Контекст задачи. Формируется на этапе 1 из истории диалога.

    Пока извлечение примитивное (см. SimpleContextExtractor), но структура
    рассчитана на будущее обогащение из истории сообщений (`history`).
    """

    niche: str | None = None
    company_name: str | None = None
    utp: str | None = None
    phone: str | None = None
    location: str | None = None

    style: str | None = None
    colors: str | None = None
    fonts: str | None = None

    # Сырая история диалога (от старых к новым) — источник контекста.
    history: list[str] = Field(default_factory=list)

    def to_generation_context(self) -> ImageGenerationContextDTO:
        """Маппинг доменного контекста в DTO сервиса генерации."""
        return ImageGenerationContextDTO(
            niche=self.niche or "Не указана",
            company_name=self.company_name or "Не указано",
            utp=self.utp,
            phone=self.phone,
            location=self.location,
            style=StyleContextDTO(
                style=self.style,
                colors=self.colors,
                fonts=self.fonts,
            ),
        )


class Job(BaseModel):
    """Задача на обработку (сейчас единственный тип — создание дизайна)."""

    id: int | None = None
    peer_id: int
    from_id: int
    trigger_message_id: int | None = None
    status: JobStatus = JobStatus.PENDING
    context: JobContext = Field(default_factory=JobContext)
    media_path: str | None = None
    error: str | None = None
    attempts: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


class OutboxMessage(BaseModel):
    """Запись transactional outbox — результат, который надо отправить в VK."""

    id: int | None = None
    job_id: int
    peer_id: int
    text: str = ""
    media_path: str | None = None
    status: OutboxStatus = OutboxStatus.PENDING
    attempts: int = 0
    error: str | None = None
    created_at: datetime | None = None
    sent_at: datetime | None = None


class JobResult(BaseModel):
    """Результат работы обработчика задачи."""

    media_path: str | None = None
    reply_text: str = ""
