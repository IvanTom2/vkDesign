"""Отправка сообщений в VK (реализация IMessageSender, сменяемая логика)."""

from __future__ import annotations

from logger import ILogger
from src.domain.interfaces import IMediaStorage
from src.domain.interfaces import IMessageSender
from src.vk.messages import VKResponderGateway


class VkMessageSender(IMessageSender):
    def __init__(
        self,
        responder: VKResponderGateway,
        media_storage: IMediaStorage,
        logger: ILogger,
    ) -> None:
        self._responder = responder
        self._media = media_storage
        self._log = logger.bind(component="VkMessageSender")

    def send(self, peer_id: int, text: str, media_path: str | None = None) -> None:
        attachment: str | None = None
        if media_path:
            data = self._media.load(media_path)
            attachment = self._responder.upload_photo(
                data, peer_id=peer_id, filename=media_path
            )
            self._log.info("media uploaded", peer_id=peer_id, attachment=attachment)
        self._responder.respond_vk(text, peer_id=peer_id, attachment=attachment)
        self._log.info("message sent", peer_id=peer_id, has_media=bool(attachment))
