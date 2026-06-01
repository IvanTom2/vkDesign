"""Composition root: сборка прикладных сервисов из настроек.

Здесь — единственное место, где конкретные реализации (PostgreSQL, RabbitMQ,
VK, диск, Gemini) подставляются в порты. Прикладные сервисы об этом не знают.
"""

from __future__ import annotations

from pathlib import Path

from logger import logger
from settings import Settings
from settings import settings as default_settings
from src.domain.context import SimpleContextExtractor
from src.domain.generator.service import ImageGeneratorServiceGeminiDynamicCreativeV5
from src.domain.handlers import DesignJobHandler
from src.domain.interfaces import IUnitOfWork
from src.domain.trigger import KeywordTriggerDetector
from src.gemini.client import GeminiClient
from src.infra.db.engine import create_db_engine
from src.infra.db.engine import create_session_factory
from src.infra.db.engine import init_db
from src.infra.db.repositories import SqlAlchemyUnitOfWork
from src.infra.queue.rabbitmq import RabbitMQClient
from src.infra.storage.disk import DiskMediaStorage
from src.infra.vk.sender import VkMessageSender
from src.services.poller import PollerService
from src.services.sender import ResultSenderService
from src.services.worker import WorkerService
from src.vk.messages import VKLongPollGateway
from src.vk.messages import VKResponderGateway


def _uow_factory(settings: Settings):
    engine = create_db_engine(settings.DATABASE_URL)
    init_db(engine)
    session_factory = create_session_factory(engine)

    def factory() -> IUnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory)

    return factory


def build_poller(settings: Settings = default_settings) -> PollerService:
    uow_factory = _uow_factory(settings)
    rabbit = RabbitMQClient(settings.RABBITMQ_URL, logger)
    media = DiskMediaStorage(settings.MEDIA_DIR, logger)

    responder = VKResponderGateway(
        token=settings.VK_GROUP_TOKEN,
        group_id=settings.VK_GROUP_ID,
        logger=logger,
    )
    long_poll = VKLongPollGateway(
        token=settings.VK_GROUP_TOKEN,
        group_id=settings.VK_GROUP_ID,
    )

    return PollerService(
        long_poll=long_poll,
        uow_factory=uow_factory,
        trigger=KeywordTriggerDetector(settings.TRIGGER_KEYWORD, logger),
        context_extractor=SimpleContextExtractor(logger),
        publisher=rabbit,
        jobs_queue=settings.RABBITMQ_JOBS_QUEUE,
        logger=logger,
        history_limit=settings.HISTORY_LIMIT,
        wait_seconds=settings.POLL_WAIT_SECONDS,
        ack_sender=VkMessageSender(responder, media, logger),
        ack_message=settings.ACK_MESSAGE,
    )


def build_worker(settings: Settings = default_settings) -> WorkerService:
    uow_factory = _uow_factory(settings)
    rabbit = RabbitMQClient(settings.RABBITMQ_URL, logger)
    media = DiskMediaStorage(settings.MEDIA_DIR, logger)

    gemini = GeminiClient(
        api_key=settings.GEMINI_API_KEY,
        proxy_url=settings.PROXY_URL,
    )
    generator = ImageGeneratorServiceGeminiDynamicCreativeV5(
        model=settings.GEMINI_MODEL,
        gemini=gemini,
        name="Gemini Dynamic Creative V5",
        layout_path=Path(settings.LAYOUT_PATH),
        temperature=settings.GEMINI_TEMPERATURE,
        logger=logger,
    )
    handler = DesignJobHandler(
        generator=generator,
        media_storage=media,
        logger=logger,
        reply_text=settings.WORKER_REPLY_MESSAGE,
    )

    return WorkerService(
        consumer=rabbit,
        publisher=rabbit,
        uow_factory=uow_factory,
        handler=handler,
        jobs_queue=settings.RABBITMQ_JOBS_QUEUE,
        results_queue=settings.RABBITMQ_RESULTS_QUEUE,
        logger=logger,
        reply_text=settings.WORKER_REPLY_MESSAGE,
    )


def build_sender(settings: Settings = default_settings) -> ResultSenderService:
    uow_factory = _uow_factory(settings)
    rabbit = RabbitMQClient(settings.RABBITMQ_URL, logger)
    media = DiskMediaStorage(settings.MEDIA_DIR, logger)

    responder = VKResponderGateway(
        token=settings.VK_GROUP_TOKEN,
        group_id=settings.VK_GROUP_ID,
        logger=logger,
    )
    sender = VkMessageSender(responder, media, logger)

    return ResultSenderService(
        consumer=rabbit,
        uow_factory=uow_factory,
        sender=sender,
        results_queue=settings.RABBITMQ_RESULTS_QUEUE,
        logger=logger,
    )
