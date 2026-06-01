import logging
import sys
import structlog
from structlog.stdlib import BoundLogger

type ILogger = BoundLogger


def setup_logging(log_level: int = logging.INFO):
    # 1. Список процессоров, общих для всех режимов
    shared_processors = [
        # Извлекает данные из contextvars (те самые RequestID)
        structlog.contextvars.merge_contextvars,
        # Добавляет уровень лога (info, error, etc.)
        structlog.processors.add_log_level,
        # # Позволяет использовать f-строки внутри логов (опционально)
        # structlog.processors.format_exc_info,
        # Добавляет таймстемп в формате ISO
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    structlog.configure(
        processors=[
            *shared_processors,
            # Этот процессор подготавливает данные для финального рендеринга
            structlog.processors.StackInfoRenderer(),
            # Выбираем формат: если в консоли (tty) — красиво, иначе — JSON
            (
                structlog.dev.ConsoleRenderer()
                if sys.stderr.isatty()
                else structlog.processors.JSONRenderer()
            ),
        ],
        # Настройка обертки логгера
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


setup_logging(log_level=logging.DEBUG)
logger: ILogger = structlog.get_logger()
