import time
import random
from collections.abc import Iterator

import requests

from logger import ILogger
from src.vk.models.long_poll import VKLongPollResponseDTO
from src.vk.models.long_poll import VKLongPollServerDTO
from src.vk.models.long_poll import VKLongPollUpdateDTO
from src.vk.models.long_poll import VKMessageDTO


class VKResponderGateway:
    def __init__(
        self,
        token: str,
        group_id: int,
        logger: ILogger,
    ) -> None:
        self._token = token
        self._group_id = group_id  # нужен для docs.save и upload-сервера
        self._client = requests.Session()
        self._api = "https://api.vk.com/method"
        self._v = "5.199"
        self._logger = logger

    def _call(self, method: str, **params) -> dict:
        params["access_token"] = self._token
        params["v"] = self._v
        resp = self._client.post(f"{self._api}/{method}", data=params)
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            raise RuntimeError(f"VK API {method}: {data['error']}")
        return data["response"]

    def upload_document_fallback(
        self,
        file_bytes: bytes,
        peer_id: int,
        title: str,
    ) -> str:
        """Загружает документ в диалог, возвращает attachment-строку doc{owner}_{id}."""
        # шаг 1 — получить upload-сервер для документа в сообщениях
        server = self._call(
            "docs.getMessagesUploadServer",
            type="doc",
            peer_id=peer_id,
        )
        upload_url = server["upload_url"]

        # шаг 2 — POST файла на upload_url
        files = {"file": (f"{title}.pdf", file_bytes, "application/pdf")}
        up = self._client.post(upload_url, files=files)
        up.raise_for_status()
        file_token = up.json()["file"]  # строка-токен загруженного файла

        # шаг 3 — сохранить документ
        saved = self._call("docs.save", file=file_token, title=title)
        doc = saved["doc"]
        return f"doc{doc['owner_id']}_{doc['id']}"

    def upload_document(
        self,
        file_bytes: bytes,
        peer_id: int,
        title: str,
    ) -> str:
        """Загружает документ в диалог.

        Раздельно обрабатывает лаги серверов загрузки (Шаг 2) и лаги базы данных (Шаг 3).
        """
        if not file_bytes:
            raise ValueError("file_bytes пустой!")

        safe_title = (
            "".join(c for c in title if c.isalnum() or c in " .-_()").strip()
            or "document"
        )

        # --- КРУГ 1: РЕТРАЙ ВСЕЙ ЗАГРУЗКИ (Если лагает сервер pu.vk.com на Шаге 2) ---
        upload_attempts = 5
        for u_attempt in range(1, upload_attempts + 1):
            try:
                # Шаг 1: Получаем свежий сервер
                server = self._call(
                    "docs.getMessagesUploadServer", type="doc", peer_id=peer_id
                )
                upload_url = server["upload_url"]

                # Шаг 2: POST файла
                files = {"file": (f"{safe_title}.pdf", file_bytes, "application/pdf")}
                headers = {"Connection": "close"}
                up = self._client.post(
                    upload_url, files=files, headers=headers, timeout=20
                )
                up.raise_for_status()

                response_json = up.json()

                # Если сервер загрузки вернул ошибку вместо токена
                if "error" in response_json or "file" not in response_json:
                    raise RuntimeError(f"VK CDN upload error: {response_json}")

                file_token = response_json["file"]
                break  # Файл успешно лег на балансировщик ВК, выходим из цикла загрузки!

            except Exception as e:
                if u_attempt < upload_attempts:
                    self._logger.warning(
                        f"[Лаг CDN ВК] Не удалось залить файл (попытка {u_attempt}/{upload_attempts}). Error: {e}. Пробуем другой сервер..."
                    )
                    time.sleep(2)
                    continue
                raise e  # Если за 3 раза вообще не смогли залить файл — падаем

        # Пауза для синхронизации кэша ВК перед сохранением
        time.sleep(1.0)

        # --- КРУГ 2: РЕТРАЙ ТОЛЬКО СОХРАНЕНИЯ (Если лагает база данных ВК на Шаге 3) ---
        save_attempts = 5
        save_delay = 2
        for s_attempt in range(1, save_attempts + 1):
            try:
                saved = self._call("docs.save", file=file_token, title=safe_title)

                if isinstance(saved, list):
                    doc = saved[0]
                elif "doc" in saved:
                    doc = saved["doc"]
                else:
                    doc = saved

                return f"doc{doc['owner_id']}_{doc['id']}"

            except Exception as e:
                error_str = str(e).lower()
                # Если файл залился, но база ВК его еще "не видит" (ошибка 105 / not saved)
                if (
                    "not saved" in error_str or "105" in error_str
                ) and s_attempt < save_attempts:
                    self._logger.warning(
                        f"[Лаг БД ВК] Файл в кэше, но база еще тупит (попытка {s_attempt}/{save_attempts}). Ждем {save_delay}с..."
                    )
                    time.sleep(save_delay)
                    save_delay = min(8, save_delay * 2)
                    continue
                raise e

        return self.upload_document_fallback(file_bytes, peer_id, title)

    def respond_vk(
        self,
        message: str,
        peer_id: int,
        attachment: str | None = None,
    ) -> None:
        params = {
            "random_id": random.randint(0, 2**31 - 1),
            "message": message,
            "peer_id": peer_id,
        }
        if attachment:
            params["attachment"] = attachment
        self._call("messages.send", **params)


class VKLongPollGateway:
    """Bots Long Poll API: приём событий сообщества (в т.ч. входящие сообщения)."""

    def __init__(self, token: str, group_id: int) -> None:
        self._token = token
        self._group_id = group_id
        self._client = requests.Session()
        self._api = "https://api.vk.com/method"
        self._v = "5.199"

    def _call(self, method: str, **params) -> dict:
        params["access_token"] = self._token
        params["v"] = self._v
        resp = self._client.post(f"{self._api}/{method}", data=params)
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            raise RuntimeError(f"VK API {method}: {data['error']}")
        return data["response"]

    def enable_long_poll(self, *, message_new: bool = True) -> None:
        """Включает Bots Long Poll API и типы событий в сообществе."""
        params: dict[str, int] = {
            "group_id": self._group_id,
            "enabled": 1,
        }
        if message_new:
            params["message_new"] = 1
        self._call("groups.setLongPollSettings", **params)

    def _get_server(self, *, auto_enable: bool = True) -> VKLongPollServerDTO:
        try:
            raw = self._call("groups.getLongPollServer", group_id=self._group_id)
        except RuntimeError as exc:
            if not auto_enable or "longpoll for this group is not enabled" not in str(
                exc
            ):
                raise
            self.enable_long_poll()
            raw = self._call("groups.getLongPollServer", group_id=self._group_id)
        return VKLongPollServerDTO.model_validate(raw)

    def _poll(
        self,
        server: VKLongPollServerDTO,
        *,
        wait: int = 25,
    ) -> tuple[VKLongPollServerDTO, VKLongPollResponseDTO]:
        while True:
            resp = self._client.get(
                server.server,
                params={
                    "act": "a_check",
                    "key": server.key,
                    "ts": server.ts,
                    "wait": wait,
                },
                timeout=wait + 10,
            )
            resp.raise_for_status()
            data = resp.json()

            if "failed" in data:
                failed = data["failed"]
                if failed == 1:
                    server = VKLongPollServerDTO(
                        server=server.server,
                        key=server.key,
                        ts=int(data["ts"]),
                    )
                    continue
                server = self._get_server()
                continue

            parsed = VKLongPollResponseDTO.model_validate(data)
            server = VKLongPollServerDTO(
                server=server.server,
                key=server.key,
                ts=parsed.ts,
            )
            return server, parsed

    def poll_once(
        self,
        server: VKLongPollServerDTO,
        *,
        wait: int = 25,
    ) -> tuple[VKLongPollServerDTO, list[VKLongPollUpdateDTO]]:
        server, response = self._poll(server, wait=wait)
        return server, response.updates

    def listen(
        self,
        *,
        wait: int = 25,
    ) -> Iterator[VKLongPollUpdateDTO]:
        """Бесконечный цикл Long Poll; отдаёт все события из updates."""
        server = self._get_server()
        while True:
            server, response = self._poll(server, wait=wait)
            yield from response.updates

    def incoming_messages(
        self,
        *,
        wait: int = 25,
    ) -> Iterator[VKMessageDTO]:
        """Только входящие сообщения (type == message_new)."""
        for update in self.listen(wait=wait):
            msg = update.incoming_message()
            if msg is not None:
                yield msg
