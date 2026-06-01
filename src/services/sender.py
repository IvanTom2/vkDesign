"""Этап 3 — отправщик результатов.

Слушает очередь результатов, берёт запись outbox, отправляет результат в VK
через IMessageSender и фиксирует выполнение (outbox -> sent).
"""

from __future__ import annotations

from collections.abc import Callable

from logger import ILogger
from src.domain.interfaces import IMessageSender
from src.domain.interfaces import ITaskConsumer
from src.domain.interfaces import IUnitOfWork
from src.domain.models import OutboxStatus


class ResultSenderService:
    def __init__(
        self,
        consumer: ITaskConsumer,
        uow_factory: Callable[[], IUnitOfWork],
        sender: IMessageSender,
        results_queue: str,
        logger: ILogger,
    ) -> None:
        self._consumer = consumer
        self._uow_factory = uow_factory
        self._sender = sender
        self._results_queue = results_queue
        self._log = logger.bind(component="ResultSenderService")

    def run(self) -> None:
        self._log.info("sender started", queue=self._results_queue)
        self._consumer.consume(self._results_queue, self._process)

    def _process(self, payload: dict) -> None:
        outbox_id = payload.get("outbox_id")
        log = self._log.bind(outbox_id=outbox_id)
        if outbox_id is None:
            log.error("payload without outbox_id", payload=payload)
            return

        with self._uow_factory() as uow:
            outbox = uow.outbox.get(outbox_id)
            if outbox is None:
                log.error("outbox record not found")
                return
            if outbox.status == OutboxStatus.SENT:
                log.info("already sent, skip")
                return
            peer_id = outbox.peer_id
            text = outbox.text
            media_path = outbox.media_path

        try:
            self._sender.send(peer_id, text, media_path)
        except Exception as exc:
            # Фиксируем неудачу в outbox (источник правды для будущего relay/повтора)
            # и подтверждаем сообщение, чтобы не уйти в poison-loop.
            log.exception("send failed")
            with self._uow_factory() as uow:
                uow.outbox.mark_failed(outbox_id, repr(exc))
                uow.commit()
            return

        with self._uow_factory() as uow:
            uow.outbox.mark_sent(outbox_id)
            uow.commit()
        log.info("result delivered", peer_id=peer_id)
