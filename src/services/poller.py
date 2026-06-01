"""Этап 1 — поллер VK.

Слушает Long Poll сообщества, сохраняет каждое входящее сообщение в историю,
детектит триггер и при срабатывании: собирает контекст из истории, создаёт
задачу в БД и публикует её в очередь задач. Опционально шлёт пользователю ack.
"""

from __future__ import annotations

from collections.abc import Callable

from logger import ILogger
from src.domain.interfaces import IContextExtractor
from src.domain.interfaces import IMessageSender
from src.domain.interfaces import ITaskPublisher
from src.domain.interfaces import ITriggerDetector
from src.domain.interfaces import IUnitOfWork
from src.domain.models import DialogMessage
from src.domain.models import Job
from src.domain.models import MessageDirection
from src.vk.messages import VKLongPollGateway
from src.vk.models.long_poll import VKMessageDTO


class PollerService:
    def __init__(
        self,
        long_poll: VKLongPollGateway,
        uow_factory: Callable[[], IUnitOfWork],
        trigger: ITriggerDetector,
        context_extractor: IContextExtractor,
        publisher: ITaskPublisher,
        jobs_queue: str,
        logger: ILogger,
        *,
        history_limit: int = 50,
        wait_seconds: int = 25,
        ack_sender: IMessageSender | None = None,
        ack_message: str = "",
    ) -> None:
        self._long_poll = long_poll
        self._uow_factory = uow_factory
        self._trigger = trigger
        self._context_extractor = context_extractor
        self._publisher = publisher
        self._jobs_queue = jobs_queue
        self._log = logger.bind(component="PollerService")
        self._history_limit = history_limit
        self._wait_seconds = wait_seconds
        self._ack_sender = ack_sender
        self._ack_message = ack_message

    def run(self) -> None:
        self._log.info("poller started", queue=self._jobs_queue)
        for message in self._long_poll.incoming_messages(wait=self._wait_seconds):
            try:
                self._handle(message)
            except Exception:
                self._log.exception(
                    "failed to handle message",
                    peer_id=message.peer_id,
                    vk_message_id=message.id,
                )

    def _handle(self, message: VKMessageDTO) -> None:
        log = self._log.bind(peer_id=message.peer_id, vk_message_id=message.id)
        log.info("incoming message", text=message.text[:200])

        # 1. Всегда сохраняем сообщение в историю.
        with self._uow_factory() as uow:
            uow.messages.add(self._to_dialog_message(message))
            uow.commit()

        # 2. Триггер?
        if not self._trigger.detect(message.text):
            return

        # 3. Контекст из истории + создание задачи (атомарно), затем публикация.
        with self._uow_factory() as uow:
            history = uow.messages.recent_by_peer(
                message.peer_id, self._history_limit
            )
            context = self._context_extractor.extract(history)
            job = uow.jobs.create(
                Job(
                    peer_id=message.peer_id,
                    from_id=message.from_id,
                    trigger_message_id=message.id,
                    context=context,
                )
            )
            uow.commit()
            job_id = job.id

        log.info("job created", job_id=job_id)
        self._publisher.publish(self._jobs_queue, {"job_id": job_id})

        # 4. Подтверждение пользователю (best-effort).
        if self._ack_sender and self._ack_message:
            try:
                self._ack_sender.send(message.peer_id, self._ack_message)
            except Exception:
                log.exception("failed to send ack", job_id=job_id)

    @staticmethod
    def _to_dialog_message(message: VKMessageDTO) -> DialogMessage:
        return DialogMessage(
            vk_message_id=message.id,
            peer_id=message.peer_id,
            from_id=message.from_id,
            direction=MessageDirection.INCOMING,
            text=message.text,
            vk_date=message.date,
        )
