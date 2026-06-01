"""Обработчики задач (этап 2).

Сейчас единственный обработчик — создание дизайна оформления группы.
Он принимает контекст задачи, генерирует изображение через сменяемый
IImageGeneratorService, сохраняет медиа в IMediaStorage и возвращает
результат (путь к медиа + текст ответа).
"""

from __future__ import annotations

from uuid import uuid4

from logger import ILogger
from src.domain.generator.service import IImageGeneratorService
from src.domain.interfaces import IJobHandler
from src.domain.interfaces import IMediaStorage
from src.domain.models import Job
from src.domain.models import JobResult


class DesignJobHandler(IJobHandler):
    def __init__(
        self,
        generator: IImageGeneratorService,
        media_storage: IMediaStorage,
        logger: ILogger,
        reply_text: str,
    ) -> None:
        self._generator = generator
        self._media = media_storage
        self._log = logger.bind(component="DesignJobHandler")
        self._reply_text = reply_text

    def handle(self, job: Job) -> JobResult:
        log = self._log.bind(job_id=job.id, peer_id=job.peer_id)
        context = job.context.to_generation_context()
        media_name = f"design_job_{job.id}_{uuid4().hex}.png"
        save_path = self._media.resolve(media_name)

        log.info("generation started", niche=context.niche)
        result = self._generator.generate(context, save_path)
        log.info(
            "generation finished",
            media=media_name,
            service=result.service_name,
        )
        return JobResult(media_path=media_name, reply_text=self._reply_text)
