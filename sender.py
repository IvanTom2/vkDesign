"""Этап 3 — запуск отправщика результатов (отправка готовых дизайнов в VK)."""

import urllib3

from logger import logger
from src.bootstrap import build_sender

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def main() -> None:
    sender = build_sender()
    try:
        sender.run()
    except KeyboardInterrupt:
        logger.info("sender stopped by user")


if __name__ == "__main__":
    main()
