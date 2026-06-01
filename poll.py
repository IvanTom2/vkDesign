"""Этап 1 — запуск поллера VK (приём сообщений, детект триггера, постановка задач)."""

import urllib3

from logger import logger
from src.bootstrap import build_poller

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def main() -> None:
    poller = build_poller()
    try:
        poller.run()
    except KeyboardInterrupt:
        logger.info("poller stopped by user")


if __name__ == "__main__":
    main()
