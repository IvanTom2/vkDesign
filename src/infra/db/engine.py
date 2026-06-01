"""Создание engine / фабрики сессий и инициализация схемы."""

from __future__ import annotations

from sqlalchemy import Engine
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker

from logger import logger
from src.infra.db.orm import Base


def create_db_engine(database_url: str) -> Engine:
    return create_engine(database_url, pool_pre_ping=True, future=True)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


def init_db(engine: Engine) -> None:
    """Идемпотентно создаёт таблицы (CREATE TABLE IF NOT EXISTS)."""
    Base.metadata.create_all(engine)
    logger.info("db schema ensured")
