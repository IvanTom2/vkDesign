import urllib3
from datetime import datetime
from pathlib import Path

from settings import settings
from src.gemini.client import GeminiClient
from src.gemini.cost import estimate_cost

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def log(msg: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def main():
    log("=== START ===")
    with GeminiClient(
        api_key=settings.GEMINI_API_KEY,
        proxy_url=settings.PROXY_URL,
    ) as gem:
        MODEL = "gemini-3.1-flash-image-preview"
        IMAGE_PATH = Path("/home/ivan/Projects/vkDesign/Макет-2-1.png")
        PROMPT = (
            'Перерисуй это оформление под нишу "Септики и автономные канализации". '
            "Замени весь текст, иконки и изображения на уместные в этой сфере. "
            "Учитывай контекст компании при создании объектов. "
            "Сохрани общую композицию и структуру макета, но измени стилистику, цвета и детали так, чтобы не выглядело как копия исходника."
            "Не описывай изменения текстом. Верни готовое изображение. "
            "ВАЖНО! На обложке показана красная пунктирная линия за которую нельзя чтобы выходил текст и значимые объекты - потому что там они могут обрезаться. Там должен быть только фон. "
            "Контекст:"
            'Название компании: "Септик-Про". '
        )

        log("вызываю edit_image...")
        resp = gem.edit_image_stream(prompt=PROMPT, image_path=IMAGE_PATH, model=MODEL)
        log("edit_image вернул ответ")

        log("текст модели:")
        print(gem.extract_text(resp))

        ok = gem.save_image(resp, "output.png")
        log("saved" if ok else "failed")

        cost = estimate_cost(resp, MODEL)
        log(f"cost: {cost}")

    log("=== END ===")


if __name__ == "__main__":
    main()
