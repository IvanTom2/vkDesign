from enum import IntEnum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field
from pydantic import field_validator


# ---------- Перечисления ----------


class IsClosed(IntEnum):
    OPEN = 0
    CLOSED = 1
    PRIVATE = 2


class AdminLevel(IntEnum):
    MODERATOR = 1
    EDITOR = 2
    ADMIN = 3


class AgeLimits(IntEnum):
    NONE_ = 1
    AGE_16 = 2
    AGE_18 = 3


class MainSection(IntEnum):
    NONE_ = 0
    PHOTOS = 1
    TOPICS = 2
    AUDIOS = 3
    VIDEOS = 4
    PRODUCTS = 5


class MemberStatus(IntEnum):
    NOT_MEMBER = 0
    MEMBER = 1
    UNSURE = 2
    DECLINED = 3
    REQUESTED = 4
    INVITED = 5


class WallStatus(IntEnum):
    DISABLED = 0
    OPEN = 1
    RESTRICTED = 2
    CLOSED = 3


# ---------- Базовый класс ----------


class VKBaseModel(BaseModel):
    """Базовый класс: разрешаем лишние поля, чтобы API не ломал парсинг."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)


# ---------- Вложенные объекты ----------


class City(VKBaseModel):
    id: int
    title: str


class Country(VKBaseModel):
    id: int
    title: str


class Place(VKBaseModel):
    id: Optional[int] = None
    title: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    type: Optional[str] = None
    country: Optional[int] = None
    city: Optional[int] = None
    address: Optional[str] = None


class Contact(VKBaseModel):
    user_id: Optional[int] = None
    desc: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class Link(VKBaseModel):
    id: int
    url: str
    name: Optional[str] = None
    desc: Optional[str] = None
    photo_50: Optional[str] = None
    photo_100: Optional[str] = None


class Counters(VKBaseModel):
    # posts: Optional[int] = None
    photos: Optional[int] = None
    albums: Optional[int] = None
    audios: Optional[int] = None
    videos: Optional[int] = None
    topics: Optional[int] = None
    docs: Optional[int] = None
    clips: Optional[int] = None
    market: Optional[int] = None
    market_services: Optional[int] = None


class BanInfo(VKBaseModel):
    end_date: Optional[int] = None
    comment: Optional[str] = None


class Addresses(VKBaseModel):
    is_enabled: Optional[bool] = None
    main_address_id: Optional[int] = None


class CoverImage(VKBaseModel):
    url: str
    width: int
    height: int


class Cover(VKBaseModel):
    enabled: int
    images: Optional[list[CoverImage]] = None


class CropRect(VKBaseModel):
    x: float
    y: float
    x2: float
    y2: float


class PhotoSize(VKBaseModel):
    """Элемент массива photo.sizes."""

    type: str  # 's','m','x','o','p','q','r','y','z','w','a','b','c','d','e',
    # 'i','j','k','n','g','h','f','max','temp' — список расширяется
    url: Optional[str] = None
    src: Optional[str] = None  # старое название поля до v5.77
    width: int
    height: int


class PhotoImage(VKBaseModel):
    """Элемент массива photo.images (используется в некоторых ответах)."""

    type: str
    url: str
    width: int
    height: int


class Photo(VKBaseModel):
    """
    Объект фотографии ВКонтакте.
    Используется, в частности, в crop_photo.photo сообщества.
    Набор полей зависит от метода — обязательны только id и owner_id.
    """

    id: int
    owner_id: int
    album_id: Optional[int] = None
    user_id: Optional[int] = None
    text: Optional[str] = None
    date: Optional[int] = None  # unixtime

    width: Optional[int] = None
    height: Optional[int] = None

    sizes: Optional[list[PhotoSize]] = None
    images: Optional[list[PhotoImage]] = None

    # Прямые URL-поля (встречаются в старых форматах ответа и в attachments)
    photo_75: Optional[str] = None
    photo_130: Optional[str] = None
    photo_256: Optional[str] = None
    photo_604: Optional[str] = None
    photo_807: Optional[str] = None
    photo_1280: Optional[str] = None
    photo_2560: Optional[str] = None

    access_key: Optional[str] = None
    post_id: Optional[int] = None
    can_comment: Optional[int] = None
    has_tags: Optional[bool] = None

    # Геометки
    lat: Optional[float] = None
    long: Optional[float] = None
    place: Optional[str] = None


class CropPhoto(VKBaseModel):
    photo: Optional[Photo] = None
    crop: Optional[CropRect] = None
    rect: Optional[CropRect] = None


class Currency(VKBaseModel):
    id: int
    name: str


class Market(VKBaseModel):
    enabled: int
    type: Optional[str] = None
    price_min: Optional[int] = None
    price_max: Optional[int] = None
    main_album_id: Optional[int] = None
    contact_id: Optional[int] = None
    currency: Optional[Currency] = None
    currency_text: Optional[str] = None


class VKTicket(VKBaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    is_onboarding_enabled: Optional[bool] = False


# ---------- Главная модель ----------


class VKGroupInfoDTO(VKBaseModel):
    """
    Объект сообщества ВКонтакте.
    Все поля, кроме базовых идентификационных, опциональны.
    """

    # --- Базовые поля ---
    id: int
    name: Optional[str] = None
    screen_name: Optional[str] = None
    is_closed: Optional[IsClosed] = None
    deactivated: Optional[str] = None  # 'deleted' | 'banned'
    type: Optional[str] = None  # 'group' | 'page' | 'event'
    photo_50: Optional[str] = None
    photo_100: Optional[str] = None
    photo_200: Optional[str] = None

    # Поля, требующие scope=groups
    is_admin: Optional[int] = None
    admin_level: Optional[AdminLevel] = None
    is_member: Optional[int] = None
    is_advertiser: Optional[int] = None
    invited_by: Optional[int] = None
    member_status: Optional[MemberStatus] = None

    # --- Опциональные A–K ---
    activity: Optional[str] = None
    addresses: Optional[Addresses] = None
    age_limits: Optional[AgeLimits] = None
    ban_info: Optional[BanInfo] = None

    can_create_topic: Optional[int] = None
    can_message: Optional[int] = None
    can_post: Optional[int] = None
    can_see_all_posts: Optional[int] = None
    can_upload_doc: Optional[int] = None
    can_upload_story: Optional[int] = None
    can_upload_video: Optional[int] = None

    city: Optional[City] = None
    contacts: Optional[list[Contact]] = None
    counters: Counters = Field(default_factory=Counters)
    country: Optional[Country] = None
    cover: Optional[Cover] = None
    crop_photo: Optional[CropPhoto] = None

    description: Optional[str] = None
    fixed_post: Optional[int] = None
    has_photo: Optional[int] = None
    is_favorite: Optional[int] = None
    is_hidden_from_feed: Optional[int] = None
    is_messages_blocked: Optional[int] = None

    # --- Опциональные L–W ---
    links: Optional[list[Link]] = None
    main_album_id: Optional[int] = None
    main_section: Optional[int] = None
    market: Optional[Market] = None
    members_count: Optional[int] = None
    place: Optional[Place] = None
    public_date_label: Optional[str] = None
    site: Optional[str] = None

    # Для встреч — unixtime, для публичных страниц start_date — YYYYMMDD
    start_date: Optional[int] = None
    finish_date: Optional[int] = None

    status: Optional[str] = None
    trending: Optional[int] = None
    verified: Optional[int] = None
    vk_ticket: Optional[VKTicket] = None
    wall: Optional[WallStatus] = None
    wiki_page: Optional[str] = None


class VKGroupOnlineStatusDTO(VKBaseModel):
    status: Optional[str] = None
    minutes: Optional[int] = None

    @field_validator("status", mode="after")
    @classmethod
    def normalize_status(cls, value: Optional[str]) -> Optional[str]:
        if value == "none":
            return None
        return value
