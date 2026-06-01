"""Этап 2 — воркер.

Слушает очередь задач, обрабатывает каждую задачу обработчиком (IJobHandler),
сохраняет результат и АТОМАРНО (transactional outbox) фиксирует выполнение
задачи + ставит запись на отправку результата. После коммита публикует
запись outbox в очередь результатов.
"""

from __future__ import annotations

from collections.abc import Callable

from logger import ILogger
from src.domain.interfaces import IJobHandler
from src.domain.interfaces import ITaskConsumer
from src.domain.interfaces import ITaskPublisher
from src.domain.interfaces import IUnitOfWork
from src.domain.models import JobStatus
from src.domain.models import OutboxMessage


class WorkerService:
    def __init__(
        self,
        consumer: ITaskConsumer,
        publisher: ITaskPublisher,
        uow_factory: Callable[[], IUnitOfWork],
        handler: IJobHandler,
        jobs_queue: str,
        results_queue: str,
        logger: ILogger,
        *,
        reply_text: str = "",
    ) -> None:
        self._consumer = consumer
        self._publisher = publisher
        self._uow_factory = uow_factory
        self._handler = handler
        self._jobs_queue = jobs_queue
        self._results_queue = results_queue
        self._log = logger.bind(component="WorkerService")
        self._reply_text = reply_text

    def run(self) -> None:
        self._log.info(
            "worker started", jobs=self._jobs_queue, results=self._results_queue
        )
        self._consumer.consume(self._jobs_queue, self._process)

    def _process(self, payload: dict) -> None:
        job_id = payload.get("job_id")
        log = self._log.bind(job_id=job_id)
        if job_id is None:
            log.error("payload without job_id", payload=payload)
            return

        # 1. Берём задачу в работу (идемпотентно).
        with self._uow_factory() as uow:
            job = uow.jobs.get(job_id)
            if job is None:
                log.error("job not found")
                return
            if job.status in (JobStatus.DONE, JobStatus.PROCESSING):
                log.info("job already handled, skip", status=job.status)
                return
            uow.jobs.mark_processing(job_id)
            uow.commit()

        # 2. Тяжёлая работа — вне транзакции БД.
        try:
            result = self._handler.handle(job)
        except Exception as exc:
            log.exception("job handling failed")
            with self._uow_factory() as uow:
                uow.jobs.mark_failed(job_id, repr(exc))
                uow.commit()
            return

        # 3. Атомарно: задача done + запись в outbox (transactional outbox).
        with self._uow_factory() as uow:
            uow.jobs.mark_done(job_id, result.media_path)
            outbox = uow.outbox.add(
                OutboxMessage(
                    job_id=job_id,
                    peer_id=job.peer_id,
                    text=result.reply_text or self._reply_text,
                    media_path=result.media_path,
                )
            )
            uow.commit()
            outbox_id = outbox.id

        log.info("job done", outbox_id=outbox_id, media=result.media_path)

        # 4. Публикуем результат на отправку.
        self._publisher.publish(self._results_queue, {"outbox_id": outbox_id})
