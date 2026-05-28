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
        IMAGE_PATH = Path("/home/ivan/Projects/vkDesign/Макет-1.jpg")
        IMAGE_PATH = Path("/home/ivan/Projects/vkDesign/Дизайн-Темный.png")
        # PROMPT = (
        #     'Перерисуй это оформление для ВК под тематику "Септики и автономные канализации". '
        #     "Замени текст, иконки и изображения на уместные в этой сфере. "
        #     'Название компании — "Септики Урала". Надпись "Зарипов SMM" оставь без изменений. '
        #     "Измени стилистику и цвета, чтобы не выглядело как копия исходника. "
        #     "Верни готовое изображение."
        # )
        # PROMPT = "Дан макет дизайна ВК. Улучши его с точки зрения дизайна. Сделай более привлекательные и детализированные компоненты. Можешь менять шрифт, но не меняй сами значение текста. Создай и верни изображение."
        PROMPT = "Удалить фон у изображения. Удали фон и верни изображение на прозрачном фоне. Верни изображение в формате PNG."

        log("вызываю edit_image...")
        resp = gem.edit_image(prompt=PROMPT, image_path=IMAGE_PATH, model=MODEL)
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
