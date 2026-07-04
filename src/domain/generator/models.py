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


class ComponentsContextDTO(BaseModel):
    menu: list[str] | None = Field(default=None, description="Список пунктов меню")
    widgets: list[str] | None = Field(default=None, description="Список виджетов")


class ImageGenerationContextDTO(BaseModel):
    niche: str
    company_name: str

    company_description: str | None = None
    utp: str | None = None
    phone: str | None = None
    location: str | None = None

    style: StyleContextDTO = StyleContextDTO(
        style=None,
        colors=None,
        fonts=None,
    )
    components: ComponentsContextDTO = ComponentsContextDTO(
        menu=None,
        widgets=None,
    )
