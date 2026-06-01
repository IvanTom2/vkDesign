"""Интерфейсы (порты) основных сервисов.

Цель — низкая связанность: прикладные сервисы (поллер/воркер/отправщик)
зависят только от этих абстракций, а конкретные реализации (PostgreSQL,
RabbitMQ, VK, диск, Gemini) подставляются в composition root (bootstrap).

Стек БД (PostgreSQL) и очереди (RabbitMQ) — постоянный. Меняться задуманы
лишь: метод обработки сообщений (ITriggerDetector / IContextExtractor /
IJobHandler), генерация изображений (IImageGeneratorService) и отправка
сообщений (IMessageSender).
"""

from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from collections.abc import Callable

from src.domain.models import DialogMessage
from src.domain.models import Job
from src.domain.models import JobContext
from src.domain.models import JobResult
from src.domain.models import OutboxMessage


# --------------------------------------------------------------------------- #
#  Обработка сообщений (этап 1) — сменяемая логика
# --------------------------------------------------------------------------- #
class ITriggerDetector(ABC):
    """Определяет, является ли сообщение триггером постановки задачи."""

    @abstractmethod
    def detect(self, text: str) -> bool: ...


class IContextExtractor(ABC):
    """Формирует контекст задачи из истории диалога."""

    @abstractmethod
    def extract(self, history: list[DialogMessage]) -> JobContext: ...


# --------------------------------------------------------------------------- #
#  Обработчик задачи (этап 2) — сменяемая логика
# --------------------------------------------------------------------------- #
class IJobHandler(ABC):
    """Выполняет задачу и возвращает результат (медиа + текст ответа)."""

    @abstractmethod
    def handle(self, job: Job) -> JobResult: ...


# --------------------------------------------------------------------------- #
#  Отправка сообщений (этап 3) — сменяемая логика
# --------------------------------------------------------------------------- #
class IMessageSender(ABC):
    """Отправляет сообщение (опционально с медиа) получателю."""

    @abstractmethod
    def send(self, peer_id: int, text: str, media_path: str | None = None) -> None: ...


# --------------------------------------------------------------------------- #
#  Хранилище медиа (постоянное — диск/БД)
# --------------------------------------------------------------------------- #
class IMediaStorage(ABC):
    """Абстракция над хранилищем медиа. Ключ (`name`) кладётся в БД."""

    @abstractmethod
    def resolve(self, name: str):
        """Локальный путь, куда генератор может записать файл напрямую."""
        ...

    @abstractmethod
    def save(self, data: bytes, name: str) -> str: ...

    @abstractmethod
    def load(self, name: str) -> bytes: ...

    @abstractmethod
    def exists(self, name: str) -> bool: ...


# --------------------------------------------------------------------------- #
#  Очередь задач (RabbitMQ) — постоянная
# --------------------------------------------------------------------------- #
class ITaskPublisher(ABC):
    @abstractmethod
    def publish(self, queue: str, payload: dict) -> None: ...


class ITaskConsumer(ABC):
    @abstractmethod
    def consume(self, queue: str, handler: Callable[[dict], None]) -> None:
        """Блокирующий цикл: на каждое сообщение вызывает handler.

        ack — при успехе handler, nack без requeue — при исключении
        (источник правды — БД, повтор делается через outbox/relay).
        """
        ...


# --------------------------------------------------------------------------- #
#  Репозитории + Unit of Work (PostgreSQL) — постоянные
# --------------------------------------------------------------------------- #
class IMessageRepository(ABC):
    @abstractmethod
    def add(self, message: DialogMessage) -> DialogMessage: ...

    @abstractmethod
    def recent_by_peer(self, peer_id: int, limit: int) -> list[DialogMessage]: ...


class IJobRepository(ABC):
    @abstractmethod
    def create(self, job: Job) -> Job: ...

    @abstractmethod
    def get(self, job_id: int) -> Job | None: ...

    @abstractmethod
    def mark_processing(self, job_id: int) -> None: ...

    @abstractmethod
    def mark_done(self, job_id: int, media_path: str | None) -> None: ...

    @abstractmethod
    def mark_failed(self, job_id: int, error: str) -> None: ...


class IOutboxRepository(ABC):
    @abstractmethod
    def add(self, message: OutboxMessage) -> OutboxMessage: ...

    @abstractmethod
    def get(self, outbox_id: int) -> OutboxMessage | None: ...

    @abstractmethod
    def mark_sent(self, outbox_id: int) -> None: ...

    @abstractmethod
    def mark_failed(self, outbox_id: int, error: str) -> None: ...


class IUnitOfWork(ABC):
    """Единица работы: репозитории, разделяющие одну транзакцию.

    Обеспечивает атомарность transactional outbox (обновление задачи +
    вставка записи на отправку в одной транзакции).
    """

    messages: IMessageRepository
    jobs: IJobRepository
    outbox: IOutboxRepository

    @abstractmethod
    def __enter__(self) -> IUnitOfWork: ...

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb) -> None: ...

    @abstractmethod
    def commit(self) -> None: ...

    @abstractmethod
    def rollback(self) -> None: ...
