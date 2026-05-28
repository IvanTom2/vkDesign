from typing import Any
import base64
import mimetypes
import time
from datetime import datetime
from pathlib import Path

import requests


def _log(msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


class GeminiClient:
    def __init__(
        self,
        api_key: str,
        proxy_url: str | None = None,
    ) -> None:
        self._api_key = api_key
        self._base_url = "https://generativelanguage.googleapis.com/v1beta/models"
        self._session = requests.Session()
        self._timeout = 180.0
        self._session.verify = False
        if proxy_url:
            self._session.proxies = {
                "http": proxy_url,
                "https": proxy_url,
            }
            _log(f"client init: proxy ON, timeout={self._timeout}s")
        else:
            _log(f"client init: no proxy, timeout={self._timeout}s")

    def _post(self, url: str, params: dict, payload: dict) -> dict[str, Any]:
        """Единая точка отправки запроса — тут весь сетевой лог."""
        _log(f"POST -> {url.split('/models/')[-1]}")
        start = time.monotonic()
        try:
            response = self._session.post(
                url, params=params, json=payload, timeout=self._timeout
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
            _log(f"Error from Google: {response.text[:500]}")
        response.raise_for_status()
        return response.json()

    def request(
        self,
        prompt: str,
        model: str = "gemini-2.5-flash",
        temperature: float = 0.1,
        max_tokens: int = 2048,
        response_json: bool = False,
    ) -> dict[str, Any]:
        _log(f"request: model={model}")
        url = f"{self._base_url}/{model}:generateContent"
        params = {"key": self._api_key}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        if response_json:
            payload["generationConfig"]["response_mime_type"] = "application/json"
        return self._post(url, params, payload)

    def edit_image(
        self,
        prompt: str,
        image_path: Path,
        model: str = "gemini-2.5-flash-image",
    ) -> dict[str, Any]:
        _log(f"edit_image: model={model}, file={image_path}")
        _log("читаю и кодирую картинку...")
        raw = image_path.read_bytes()
        encoded = base64.b64encode(raw).decode("utf-8")
        mime = mimetypes.guess_type(image_path.name)[0] or "image/png"
        _log(f"картинка готова: {len(raw)} байт, mime={mime}")

        url = f"{self._base_url}/{model}:generateContent"
        params = {"key": self._api_key}
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {"inline_data": {"mime_type": mime, "data": encoded}},
                    ]
                }
            ],
            "generationConfig": {
                "responseModalities": ["TEXT", "IMAGE"],
            },
        }
        return self._post(url, params, payload)

    def extract_text(self, response: dict[str, Any]) -> str:
        try:
            parts = response["candidates"][0]["content"]["parts"]
            for part in parts:
                if "text" in part:
                    return part["text"]
            return "No text in response"
        except (KeyError, IndexError):
            if "promptFeedback" in response:
                return f"Blocked by safety: {response['promptFeedback']}"
            return "Empty response from model"

    def save_image(self, response: dict[str, Any], out_path: str | Path) -> bool:
        _log(f"save_image -> {out_path}")
        try:
            parts = response["candidates"][0]["content"]["parts"]
        except (KeyError, IndexError):
            if "promptFeedback" in response:
                _log(f"Blocked by safety: {response['promptFeedback']}")
            return False

        for part in parts:
            data = part.get("inlineData") or part.get("inline_data")
            if data and "data" in data:
                img_bytes = base64.b64decode(data["data"])
                Path(out_path).write_bytes(img_bytes)
                _log(f"картинка сохранена: {len(img_bytes)} байт")
                return True
        _log("No image in response")
        return False

    def close(self) -> None:
        _log("client close")
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
