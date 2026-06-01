"""Клиент RabbitMQ: публикация и потребление задач (pika, blocking)."""

from __future__ import annotations

import json
import time
from collections.abc import Callable

import pika
import pika.exceptions

from logger import ILogger
from src.domain.interfaces import ITaskConsumer
from src.domain.interfaces import ITaskPublisher


class RabbitMQClient(ITaskPublisher, ITaskConsumer):
    """Публикация и потребление через одно (лениво открываемое) соединение.

    Сообщения и очереди — durable, доставка — persistent, подтверждения
    ручные. Publisher confirms включены. При обрыве соединения consume
    переподключается.
    """

    def __init__(self, url: str, logger: ILogger, *, reconnect_delay: float = 3.0) -> None:
        self._url = url
        self._log = logger.bind(component="RabbitMQClient")
        self._reconnect_delay = reconnect_delay
        self._connection: pika.BlockingConnection | None = None
        self._channel: pika.adapters.blocking_connection.BlockingChannel | None = None

    def _ensure_channel(self):
        if self._connection is None or self._connection.is_closed:
            params = pika.URLParameters(self._url)
            params.heartbeat = 60
            params.blocked_connection_timeout = 30
            self._connection = pika.BlockingConnection(params)
            self._channel = self._connection.channel()
            self._channel.confirm_delivery()
            self._log.info("amqp connected")
        return self._channel

    def publish(self, queue: str, payload: dict) -> None:
        channel = self._ensure_channel()
        channel.queue_declare(queue=queue, durable=True)
        channel.basic_publish(
            exchange="",
            routing_key=queue,
            body=json.dumps(payload).encode("utf-8"),
            properties=pika.BasicProperties(
                delivery_mode=2,  # persistent
                content_type="application/json",
            ),
        )
        self._log.info("task published", queue=queue, payload=payload)

    def consume(self, queue: str, handler: Callable[[dict], None]) -> None:
        while True:
            try:
                channel = self._ensure_channel()
                channel.queue_declare(queue=queue, durable=True)
                channel.basic_qos(prefetch_count=1)

                def _on_message(ch, method, _properties, body):
                    try:
                        payload = json.loads(body)
                    except json.JSONDecodeError:
                        self._log.error("invalid payload, dropping", body=body[:200])
                        ch.basic_nack(method.delivery_tag, requeue=False)
                        return
                    try:
                        handler(payload)
                        ch.basic_ack(method.delivery_tag)
                    except Exception:
                        self._log.exception("handler failed", payload=payload)
                        ch.basic_nack(method.delivery_tag, requeue=False)

                channel.basic_consume(queue=queue, on_message_callback=_on_message)
                self._log.info("consuming", queue=queue)
                channel.start_consuming()
            except (
                pika.exceptions.AMQPConnectionError,
                pika.exceptions.StreamLostError,
                pika.exceptions.ChannelClosedByBroker,
            ) as exc:
                self._log.error("amqp lost, reconnecting", error=str(exc))
                self._connection = None
                self._channel = None
                time.sleep(self._reconnect_delay)

    def close(self) -> None:
        if self._connection is not None and self._connection.is_open:
            self._connection.close()
        self._connection = None
        self._channel = None
