"""Детекторы триггера постановки задачи (этап 1, сменяемая логика)."""

from __future__ import annotations

from logger import ILogger
from src.domain.interfaces import ITriggerDetector


class KeywordTriggerDetector(ITriggerDetector):
    """Срабатывает, если в тексте сообщения встречается ключевое слово.

    Сейчас ключевое слово — «Начать». Регистр игнорируется.
    """

    def __init__(self, keyword: str, logger: ILogger) -> None:
        self._keyword = keyword.strip().lower()
        self._log = logger.bind(component="KeywordTriggerDetector")

    def detect(self, text: str) -> bool:
        triggered = self._keyword in (text or "").lower()
        if triggered:
            self._log.info("trigger matched", keyword=self._keyword)
        return triggered
