from typing import Any

from pydantic import BaseModel
from pydantic import Field


class GeminiResponseDTO(BaseModel):
    json: dict[str, Any] = Field(default_factory=dict)
