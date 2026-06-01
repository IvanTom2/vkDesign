"""Хранилище медиа на диске. В БД кладётся только имя файла (ключ)."""

from __future__ import annotations

from pathlib import Path

from logger import ILogger
from src.domain.interfaces import IMediaStorage


class DiskMediaStorage(IMediaStorage):
    def __init__(self, base_dir: str | Path, logger: ILogger) -> None:
        self._base = Path(base_dir)
        self._base.mkdir(parents=True, exist_ok=True)
        self._log = logger.bind(component="DiskMediaStorage")

    def resolve(self, name: str) -> Path:
        return self._base / name

    def save(self, data: bytes, name: str) -> str:
        path = self.resolve(name)
        path.write_bytes(data)
        self._log.info("media saved", name=name, size=len(data))
        return name

    def load(self, name: str) -> bytes:
        return self.resolve(name).read_bytes()

    def exists(self, name: str) -> bool:
        return self.resolve(name).exists()
