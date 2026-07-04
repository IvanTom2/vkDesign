from typing import Any

from pydantic import BaseModel
from pydantic import Field


class OpenAIImageResponseDTO(BaseModel):
    raw_json: dict[str, Any] = Field(default_factory=dict)
