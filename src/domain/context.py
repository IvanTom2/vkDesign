"""Извлечение контекста задачи из истории диалога (этап 1, сменяемая логика).

Пока реализация простая: сохраняем всю историю в `JobContext.history` и
дополнительно пытаемся достать поля из «размеченных» строк вида
``ниша: септики``. В будущем сюда встанет полноценное извлечение
(LLM/правила) — интерфейс IContextExtractor останется тем же.
"""

from __future__ import annotations

from logger import ILogger
from src.domain.interfaces import IContextExtractor
from src.domain.models import DialogMessage
from src.domain.models import JobContext
from src.domain.models import MessageDirection


class SimpleContextExtractor(IContextExtractor):
    # подпись поля -> атрибут JobContext
    _LABELS: dict[str, str] = {
        "ниша": "niche",
        "сфера": "niche",
        "компания": "company_name",
        "название": "company_name",
        "утп": "utp",
        "оффер": "utp",
        "телефон": "phone",
        "тел": "phone",
        "город": "location",
        "локация": "location",
        "регион": "location",
        "стиль": "style",
        "цвета": "colors",
        "цвет": "colors",
        "шрифт": "fonts",
        "шрифты": "fonts",
    }

    def __init__(self, logger: ILogger) -> None:
        self._log = logger.bind(component="SimpleContextExtractor")

    def extract(self, history: list[DialogMessage]) -> JobContext:
        context = JobContext()
        texts: list[str] = []

        for message in history:
            if not message.text:
                continue
            texts.append(message.text)
            # Контекст задаёт пользователь — парсим только входящие.
            if message.direction == MessageDirection.INCOMING:
                self._apply_labels(message.text, context)

        context.history = texts
        self._log.info(
            "context extracted",
            messages=len(texts),
            niche=context.niche,
            company=context.company_name,
        )
        return context

    def _apply_labels(self, text: str, context: JobContext) -> None:
        for line in text.splitlines():
            if ":" not in line:
                continue
            label, _, value = line.partition(":")
            attr = self._LABELS.get(label.strip().lower())
            value = value.strip()
            if attr and value:
                setattr(context, attr, value)
