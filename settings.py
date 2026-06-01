from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Settings(BaseSettings):
    # --- Gemini (генерация изображений) ---
    GEMINI_API_KEY: str
    PROXY_URL: str | None = None
    GEMINI_MODEL: str = "gemini-3-pro-image-preview"
    GEMINI_TEMPERATURE: float = 0.7
    LAYOUT_PATH: str = "Макет-2-1.jpg"

    # --- VK (сообщество) ---
    VK_GROUP_TOKEN: str
    VK_GROUP_ID: int
    VK_API_VERSION: str = "5.199"

    # --- Инфраструктура ---
    DATABASE_URL: str = "postgresql+psycopg://vkaudit:vkaudit@localhost:15433/vkaudit"
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5673/"
    RABBITMQ_JOBS_QUEUE: str = "vk_design_jobs"
    RABBITMQ_RESULTS_QUEUE: str = "vk_design_results"

    # --- Хранилище медиа ---
    MEDIA_DIR: str = "media"

    # --- Поллер (этап 1) ---
    TRIGGER_KEYWORD: str = "Начать"
    HISTORY_LIMIT: int = 50
    POLL_WAIT_SECONDS: int = 25
    POLL_ACK_DELAY_SECONDS: float = 2.0
    ACK_MESSAGE: str = "Принял заявку в работу — скоро пришлю результат 🙌"

    # --- Воркер (этап 2) ---
    WORKER_REPLY_MESSAGE: str = "Готово! Вот ваш дизайн оформления группы 🎨"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()  # type: ignore
