"""Этап 2 — запуск воркера (обработка задач из очереди, генерация дизайна)."""

import urllib3

from logger import logger
from src.bootstrap import build_worker

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def main() -> None:
    worker = build_worker()
    try:
        worker.run()
    except KeyboardInterrupt:
        logger.info("worker stopped by user")


if __name__ == "__main__":
    main()
