from pathlib import Path
from pydantic import BaseModel
from pydantic import Field


class ImageResultDTO(BaseModel):
    service_name: str
    prompt: str
    image_path: Path


class StyleContextDTO(BaseModel):
    style: str | None = None  # Описание стилистики
    colors: str | None = None  # Описание цветовой гаммы
    fonts: str | None = None  # Описание шрифтов


class ImageGenerationContextDTO(BaseModel):
    niche: str
    company_name: str

    utp: str | None = None
    phone: str | None = None
    location: str | None = None

    style: StyleContextDTO = StyleContextDTO(
        style=None,
        colors=None,
        fonts=None,
    )
