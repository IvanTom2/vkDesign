from typing import ClassVar
from pydantic import SecretStr
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Settings(BaseSettings):
    GEMINI_API_KEY: str
    OPENAI_API_KEY: str = ""
    PROXY_URL: str

    database_url: str = (
        "postgresql+psycopg://vkdesign:vkdesign@localhost:15433/vkdesign"
    )
    rabbitmq_url: str = "amqp://guest:guest@localhost:5673/"
    rabbitmq_queue: str = "vk_design_jobs"
    rabbitmq_max_attempts: int = 3

    poll_ack_delay_seconds: float = 2.0
    poll_peer_cooldown_hours: int = 24

    # sender: отложенная гарантированная доставка результатов из БД.
    # отчёт уходит через report_delay, оффер — через offer_delay (держите
    # offer_delay > report_delay).
    sender_poll_interval_seconds: float = 30.0
    sender_report_delay_minutes: int = 30
    sender_offer_delay_minutes: int = 60
    sender_batch_size: int = 10
    sender_max_attempts: int = 5
    sender_retry_delay_minutes: int = 5

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow",
    )


settings = Settings()  # type: ignore
