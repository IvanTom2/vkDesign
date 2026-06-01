from typing import Any

from pydantic import Field

from src.vk.models.group import VKBaseModel


class VKMessageDTO(VKBaseModel):
    """Сообщение из Bots Long Poll (message_new)."""

    id: int
    date: int
    peer_id: int
    from_id: int
    text: str = ""
    payload: str | None = None


class VKMessageNewObjectDTO(VKBaseModel):
    message: VKMessageDTO
    client_info: dict[str, Any] | None = None


class VKLongPollUpdateDTO(VKBaseModel):
    type: str
    object: dict[str, Any]
    group_id: int
    event_id: str | None = None
    v: str | None = None

    def incoming_message(self) -> VKMessageDTO | None:
        if self.type != "message_new":
            return None
        raw = self.object
        if "message" in raw:
            return VKMessageNewObjectDTO.model_validate(raw).message
        return VKMessageDTO.model_validate(raw)


class VKLongPollServerDTO(VKBaseModel):
    server: str
    key: str
    ts: int


class VKLongPollResponseDTO(VKBaseModel):
    ts: int
    updates: list[VKLongPollUpdateDTO] = Field(default_factory=list)
