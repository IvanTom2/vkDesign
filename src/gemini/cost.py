PRICING = {
    "gemini-3-pro-image-preview": {
        "input": 2.0,  # промпт + входная картинка
        "text_output": 12.0,  # текстовый ответ + thinking
        "image_output": 120.0,
    },
    "gemini-3.1-flash-image-preview": {
        "input": 0.25,
        "text_output": 1.50,
        "image_output": 60.0,
    },
    "gemini-2.5-flash-image": {
        "input": 0.30,
        "text_output": 2.50,
        "image_output": 30.0,
    },
}


def estimate_cost(response: dict, model: str) -> dict:
    """Считает реальную стоимость запроса по usageMetadata.

    Возвращает разбивку по типам токенов и итоговую цену в USD.
    """
    rates = PRICING.get(model)
    if not rates:
        return {"error": f"нет ставок для модели {model}"}

    usage = response.get("usageMetadata", {})

    # все входные токены (текст промпта + входная картинка)
    input_tokens = usage.get("promptTokenCount", 0)

    # выходные токены изображения — ищем модальность IMAGE в candidatesTokensDetails
    image_out = 0
    for d in usage.get("candidatesTokensDetails", []):
        if d.get("modality") == "IMAGE":
            image_out += d.get("tokenCount", 0)

    # выходные текстовые токены = всё, что не картинка, в candidates
    candidates_total = usage.get("candidatesTokenCount", 0)
    text_out = max(candidates_total - image_out, 0)

    # thinking-токены (у Pro) тарифицируются как текстовый выход
    thoughts = usage.get("thoughtsTokenCount", 0)
    text_out += thoughts

    cost_input = input_tokens / 1_000_000 * rates["input"]
    cost_text = text_out / 1_000_000 * rates["text_output"]
    cost_image = image_out / 1_000_000 * rates["image_output"]
    total = cost_input + cost_text + cost_image

    return {
        "input_tokens": input_tokens,
        "text_output_tokens": text_out,
        "image_output_tokens": image_out,
        "thoughts_tokens": thoughts,
        "cost_input": round(cost_input, 5),
        "cost_text": round(cost_text, 5),
        "cost_image": round(cost_image, 5),
        "total_usd": round(total, 5),
    }
