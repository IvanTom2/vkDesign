"""
Pydantic-модели для ответа метода wall.get.
Pydantic v2. extra='allow' — чтобы новые поля API не ломали парсинг.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


# Переиспользуем тот же базовый класс, что и в vk_group.py
class VKBaseModel(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)


# ---------- Вспомогательные объекты ----------


class PhotoSize(VKBaseModel):
    type: str
    width: int
    height: int
    url: Optional[str] = None


class OrigPhoto(VKBaseModel):
    type: Optional[str] = None
    url: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None


class Photo(VKBaseModel):
    id: int
    owner_id: int
    album_id: Optional[int] = None
    user_id: Optional[int] = None
    date: Optional[int] = None
    text: Optional[str] = None
    access_key: Optional[str] = None
    web_view_token: Optional[str] = None
    has_tags: Optional[bool] = None
    sizes: Optional[list[PhotoSize]] = None
    orig_photo: Optional[OrigPhoto] = None
    width: Optional[int] = None
    height: Optional[int] = None


class LinkAttachment(VKBaseModel):
    url: str
    title: Optional[str] = None
    caption: Optional[str] = None
    description: Optional[str] = None
    is_favorite: Optional[bool] = None
    # photo, product, button — добавишь по мере необходимости


class Attachment(VKBaseModel):
    """
    Универсальный аттачмент. Поле `type` определяет, какое из под-полей
    заполнено (photo / video / link / doc / audio / poll / album / ...).
    Сейчас типизированы только реально встречающиеся в твоём ответе.
    """

    type: str
    photo: Optional[Photo] = None
    link: Optional[LinkAttachment] = None
    # video, doc, audio, poll, market, sticker, wall, ... — Any, чтобы не падать
    video: Optional[dict[str, Any]] = None
    doc: Optional[dict[str, Any]] = None
    audio: Optional[dict[str, Any]] = None
    poll: Optional[dict[str, Any]] = None
    market: Optional[dict[str, Any]] = None
    sticker: Optional[dict[str, Any]] = None
    album: Optional[dict[str, Any]] = None
    wall: Optional[dict[str, Any]] = None


class Comments(VKBaseModel):
    count: int = 0
    can_post: Optional[int] = None
    can_view: Optional[int] = None
    groups_can_post: Optional[bool] = None
    can_close: Optional[bool] = None
    can_open: Optional[bool] = None


class Likes(VKBaseModel):
    count: int = 0
    user_likes: Optional[int] = None
    can_like: Optional[int] = None
    can_publish: Optional[int] = None
    repost_disabled: Optional[bool] = None  # не из доки, но реально приходит


class Reposts(VKBaseModel):
    count: int = 0
    user_reposted: Optional[int] = None


class Views(VKBaseModel):
    count: int = 0


class PostSource(VKBaseModel):
    type: Optional[str] = None  # 'vk', 'api', 'widget', 'mvk', ...
    platform: Optional[str] = None
    data: Optional[str] = None
    url: Optional[str] = None


class Donut(VKBaseModel):
    is_donut: bool = False
    paid_duration: Optional[int] = None
    placeholder: Optional[dict[str, Any]] = None
    can_publish_free_copy: Optional[bool] = None
    edit_mode: Optional[str] = None  # 'all' | 'duration'


class Geo(VKBaseModel):
    type: Optional[str] = None
    coordinates: Optional[str] = None
    place: Optional[dict[str, Any]] = None


class Copyright(VKBaseModel):
    id: Optional[int] = None
    link: Optional[str] = None
    name: Optional[str] = None
    type: Optional[str] = None


# ---------- Пост ----------


class VKWallPostDTO(VKBaseModel):
    id: int
    owner_id: int  # в API < 5.7 называлось to_id
    from_id: int
    date: int  # unixtime
    text: str = ""
    post_type: Optional[str] = None  # 'post', 'copy', 'reply', 'postpone', 'suggest'
    inner_type: Optional[str] = None
    hash: Optional[str] = None

    # Автор/публикатор
    created_by: Optional[int] = (
        None  # админ, опубликовавший запись (< 24ч, нужен токен админа)
    )
    signer_id: Optional[int] = (
        None  # подпись пользователя при посте от имени сообщества
    )

    # Ответ на другую запись
    reply_owner_id: Optional[int] = None
    reply_post_id: Optional[int] = None
    friends_only: Optional[int] = None

    # Вложения и счётчики
    attachments: list[Attachment] = []
    comments: Optional[Comments] = None
    likes: Optional[Likes] = None
    reposts: Optional[Reposts] = None
    views: Optional[Views] = None
    post_source: Optional[PostSource] = None
    donut: Optional[Donut] = None
    geo: Optional[Geo] = None
    copyright: Optional[Copyright] = None

    # Права текущего пользователя над записью
    can_pin: Optional[int] = None
    can_delete: Optional[int] = None
    can_edit: Optional[int] = None

    # Состояние записи
    is_favorite: Optional[bool] = None
    is_pinned: Optional[int] = None
    marked_as_ads: Optional[int] = None
    postponed_id: Optional[int] = None  # id отложенной записи, если стояла на таймере
    reaction_set_id: Optional[str] = None  # не из доки, но реально приходит

    # История репостов: массив таких же записей. Возвращается, только если
    # текущая запись — репост.
    # copy_history: Optional[list["WallPost"]] = None

    # to_id — алиас owner_id для совместимости со старыми версиями API (< 5.7)
    to_id: Optional[int] = None


# ---------- Корневой ответ wall.get ----------


class VKWallResponseDTO(VKBaseModel):
    """
    То, что лежит в response["response"] для wall.get.
    Именно эту модель нужно валидировать.
    """

    count: int
    items: list[VKWallPostDTO]
    # reaction_sets — большая структура с картинками реакций; нам в аудите
    # она не нужна, поэтому оставляем сырыми словарями.
    reaction_sets: Optional[list[dict[str, Any]]] = None
