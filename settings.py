from typing import ClassVar
from pydantic import SecretStr
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Settings(BaseSettings):
    GEMINI_API_KEY: str
    PROXY_URL: str

    model_config = SettingsConfigDict(
        env_file=".env",
    )


settings = Settings()  # type: ignore
