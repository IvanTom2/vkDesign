import queue
import threading
import time
from dataclasses import dataclass

from logger import ILogger
from src.vk.messages import VKResponderGateway


@dataclass(frozen=True)
class _OutgoingMessage:
    text: str
    peer_id: int


class DelayedVkMessageSender:
    """Очередь исходящих сообщений + один фоновый поток для отправки в VK."""

    def __init__(
        self,
        responder: VKResponderGateway,
        log: ILogger,
        *,
        delay_seconds: float = 2.0,
    ) -> None:
        self._responder = responder
        self._delay = max(0.0, delay_seconds)
        self._log = log.bind(component="DelayedVkMessageSender")
        self._queue: queue.Queue[_OutgoingMessage | None] = queue.Queue()
        self._thread = threading.Thread(
            target=self._worker,
            name="vk-ack",
            daemon=True,
        )
        self._thread.start()

    def schedule(self, message: str, peer_id: int) -> None:
        self._queue.put(_OutgoingMessage(text=message, peer_id=peer_id))
        self._log.debug("ack scheduled", peer_id=peer_id, delay_seconds=self._delay)

    def _worker(self) -> None:
        while True:
            item = self._queue.get()
            try:
                if item is None:
                    return
                if self._delay > 0:
                    time.sleep(self._delay)
                self._responder.respond_vk(item.text, peer_id=item.peer_id)
                self._log.info("ack sent", peer_id=item.peer_id)
            except Exception:
                self._log.exception("ack send failed", peer_id=item.peer_id)
            finally:
                self._queue.task_done()

    def shutdown(self, *, wait: bool = True) -> None:
        self._log.info("ack sender shutting down")
        self._queue.put(None)
        if wait:
            self._thread.join()
