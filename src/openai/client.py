import base64
import mimetypes
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from src.openai.models import OpenAIImageResponseDTO


def _log(msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


class OpenAIImageClient:
    """Клиент для генерации/редактирования изображений через OpenAI Images API.

    Работает с моделями семейства gpt-image (по умолчанию gpt-image-1).
    Стилистически повторяет GeminiClient: тот же голый requests, тот же
    подробный сетевой лог, прокси и context manager.
    """

    DEFAULT_MODEL = "gpt-image-1"

    def __init__(
        self,
        api_key: str,
        proxy_url: str | None = None,
        base_url: str = "https://api.openai.com/v1",
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._session = requests.Session()
        self._timeout = 180.0
        self._session.verify = False
        self._session.headers.update(
            {"Authorization": f"Bearer {self._api_key}"}
        )
        if proxy_url:
            self._session.proxies = {
                "http": proxy_url,
                "https": proxy_url,
            }
            _log(f"openai client init: proxy ON, timeout={self._timeout}s")
        else:
            _log(f"openai client init: no proxy, timeout={self._timeout}s")

    def _request(
        self,
        url: str,
        *,
        json: dict | None = None,
        data: dict | None = None,
        files: dict | None = None,
    ) -> dict[str, Any]:
        """Единая точка отправки запроса — тут весь сетевой лог."""
        endpoint = url.split("/v1/")[-1]
        _log(f"POST -> {endpoint}")
        start = time.monotonic()
        try:
            response = self._session.post(
                url,
                json=json,
                data=data,
                files=files,
                timeout=self._timeout,
            )
        except requests.exceptions.Timeout:
            elapsed = time.monotonic() - start
            _log(f"TIMEOUT после {elapsed:.1f}s (лимит {self._timeout}s)")
            raise
        except requests.exceptions.ProxyError as e:
            _log(f"PROXY ERROR: {e}")
            raise
        except requests.exceptions.ConnectionError as e:
            _log(f"CONNECTION ERROR: {e}")
            raise

        elapsed = time.monotonic() - start
        _log(f"ответ {response.status_code} за {elapsed:.1f}s")
        if response.status_code != 200:
            _log(f"Error from OpenAI: {response.text[:500]}")
        response.raise_for_status()
        return response.json()

    def generate_image(
        self,
        prompt: str,
        model: str = DEFAULT_MODEL,
        size: str = "auto",
        quality: str = "auto",
        n: int = 1,
        background: str | None = None,
        output_format: str | None = None,
    ) -> OpenAIImageResponseDTO:
        """Генерация изображения с нуля (POST /images/generations)."""
        _log(f"generate_image: model={model}, size={size}, quality={quality}")
        url = f"{self._base_url}/images/generations"
        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "size": size,
            "quality": quality,
            "n": n,
        }
        if background is not None:
            payload["background"] = background
        if output_format is not None:
            payload["output_format"] = output_format
        raw = self._request(url, json=payload)
        return OpenAIImageResponseDTO(raw_json=raw)

    def edit_image(
        self,
        prompt: str,
        image_path: Path | list[Path],
        model: str = DEFAULT_MODEL,
        size: str = "auto",
        quality: str = "auto",
        n: int = 1,
        background: str | None = None,
        output_format: str | None = None,
    ) -> OpenAIImageResponseDTO:
        """Редактирование изображения на основе исходника (POST /images/edits).

        image_path — путь к картинке или список путей (gpt-image-1 умеет
        принимать несколько референсов одним запросом).
        """
        paths = [image_path] if isinstance(image_path, Path) else list(image_path)
        _log(f"edit_image: model={model}, files={[str(p) for p in paths]}")

        files: list[tuple[str, tuple[str, bytes, str]]] = []
        for p in paths:
            raw = p.read_bytes()
            mime = mimetypes.guess_type(p.name)[0] or "image/png"
            # gpt-image-1 принимает несколько изображений через поле image[]
            field = "image[]" if len(paths) > 1 else "image"
            files.append((field, (p.name, raw, mime)))
            _log(f"картинка готова: {len(raw)} байт, mime={mime}")

        data: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "size": size,
            "quality": quality,
            "n": str(n),
        }
        if background is not None:
            data["background"] = background
        if output_format is not None:
            data["output_format"] = output_format

        url = f"{self._base_url}/images/edits"
        raw = self._request(url, data=data, files=files)
        return OpenAIImageResponseDTO(raw_json=raw)

    def save_image(
        self,
        response: OpenAIImageResponseDTO,
        save_path: Path,
        index: int = 0,
    ) -> bool:
        """Сохраняет index-е изображение из ответа в save_path."""
        _log(f"save_image -> {save_path}")
        data = response.raw_json.get("data") or []
        if index >= len(data):
            _log("No image in response")
            return False

        item = data[index]
        b64 = item.get("b64_json")
        if b64:
            img_bytes = base64.b64decode(b64)
            Path(save_path).write_bytes(img_bytes)
            _log(f"картинка сохранена: {len(img_bytes)} байт")
            return True

        # На случай, если модель вернула url вместо base64
        url = item.get("url")
        if url:
            _log(f"ответ содержит url, скачиваю: {url[:80]}")
            img = self._session.get(url, timeout=self._timeout)
            img.raise_for_status()
            Path(save_path).write_bytes(img.content)
            _log(f"картинка сохранена: {len(img.content)} байт")
            return True

        _log("No image in response")
        return False

    def close(self) -> None:
        _log("openai client close")
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
