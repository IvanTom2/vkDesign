# Стоимость указана в USD за 1 000 000 токенов.
# gpt-image считает и вход, и выход в токенах (текст + картинки).
PRICING = {
    "gpt-image-1": {
        "text_input": 5.0,  # текстовый промпт
        "image_input": 10.0,  # входные картинки (edits)
        "image_output": 40.0,  # сгенерированное изображение
    },
    "gpt-image-1-mini": {
        "text_input": 2.0,
        "image_input": 2.5,
        "image_output": 8.0,
    },
}


def estimate_cost(response: dict, model: str) -> dict:
    """Считает реальную стоимость запроса по полю usage из ответа OpenAI.

    Возвращает разбивку по типам токенов и итоговую цену в USD.
    """
    rates = PRICING.get(model)
    if not rates:
        return {"error": f"нет ставок для модели {model}"}

    usage = response.get("usage", {})

    # выход — всегда токены изображения
    image_out = usage.get("output_tokens", 0)

    # вход разбит на текст и картинки в input_tokens_details
    details = usage.get("input_tokens_details", {})
    text_in = details.get("text_tokens", 0)
    image_in = details.get("image_tokens", 0)

    # если детализации нет (например, generations без картинок на входе) —
    # считаем весь вход текстовым
    if not details:
        text_in = usage.get("input_tokens", 0)
        image_in = 0

    cost_text_in = text_in / 1_000_000 * rates["text_input"]
    cost_image_in = image_in / 1_000_000 * rates["image_input"]
    cost_image_out = image_out / 1_000_000 * rates["image_output"]
    total = cost_text_in + cost_image_in + cost_image_out

    return {
        "text_input_tokens": text_in,
        "image_input_tokens": image_in,
        "image_output_tokens": image_out,
        "cost_text_input": round(cost_text_in, 5),
        "cost_image_input": round(cost_image_in, 5),
        "cost_image_output": round(cost_image_out, 5),
        "total_usd": round(total, 5),
    }
