import base64
from abc import ABC
from abc import abstractmethod
from pathlib import Path

from logger import ILogger
from logger import logger as _default_logger
from src.gemini.client import GeminiClient
from src.gemini.models import GeminiResponseDTO
from src.domain.generator.models import ImageResultDTO
from src.domain.generator.models import ImageGenerationContextDTO


class ImageNotSaved(Exception):
    pass


class IImageGeneratorService(ABC):
    def __init__(
        self,
        name: str,
        layout_path: Path,
        temperature: float | None = None,
        logger: ILogger | None = None,
    ) -> None:
        self._name = name
        self._layout_path = layout_path
        self._temperature = temperature
        self._logger = (logger or _default_logger).bind(component=name)

    @abstractmethod
    def prompt(self, context: ImageGenerationContextDTO) -> str:
        pass

    @abstractmethod
    def generate(
        self,
        context: ImageGenerationContextDTO,
        save_path: Path,
    ) -> ImageResultDTO:
        pass


class ImageGeneratorServiceGeminiBase(IImageGeneratorService):
    def __init__(
        self,
        model: str,
        gemini: GeminiClient,
        name: str,
        layout_path: Path,
        temperature: float | None = None,
        logger: ILogger | None = None,
    ) -> None:
        super().__init__(name, layout_path, temperature, logger)
        self._model = model
        self._gemini = gemini

    def extract_text(
        self,
        response: GeminiResponseDTO,
    ) -> str | None:
        raw_json = response.raw_json
        try:
            parts = raw_json["candidates"][0]["content"]["parts"]
            for part in parts:
                if "text" in part:
                    return part["text"]
            return None
        except (KeyError, IndexError):
            if "promptFeedback" in raw_json:
                return f"Blocked by safety: {raw_json['promptFeedback']}"
            return None

    def save_image(
        self,
        response: GeminiResponseDTO,
        save_path: Path,
    ) -> bool:
        # _log(f"save_image -> {save_path}")
        try:
            parts = response.raw_json["candidates"][0]["content"]["parts"]
        except (KeyError, IndexError):
            # if "promptFeedback" in response:
            #     _log(f"Blocked by safety: {response['promptFeedback']}")
            return False

        for part in parts:
            data = part.get("inlineData") or part.get("inline_data")
            if data and "data" in data:
                img_bytes = base64.b64decode(data["data"])
                Path(save_path).write_bytes(img_bytes)
                # _log(f"картинка сохранена: {len(img_bytes)} байт")
                return True
        # _log("No image in response")
        return False

    def prompt(self, ctx: ImageGenerationContextDTO) -> str:
        sctx = ctx.style
        utp_str = f'Чуть ниже добавь УТП: "{ctx.utp}". ' if ctx.utp else ""
        phone_str = f'В самом низу укажи телефон: "{ctx.phone}"' if ctx.phone else ""
        style_str = f"Стиль: {sctx.style}" if sctx.style else ""
        colors_str = f"Цвета: {sctx.colors}" if sctx.colors else ""
        fonts_str = f"Шрифты: {sctx.fonts}" if sctx.fonts else ""
        return f"""
            Используй исходное изображение исключительно как композиционный шаблон (Layout) для презентации графического дизайна. Сделай ПОЛНОСТЬЮ НОВОЕ оформление группы ВК на тему: "{ctx.niche}".

            1. СТРУКТУРА (Сохранить):
            - Верхний текст «ОФОРМЛЕНИЕ ГРУППЫ», плашка «вконтакте», горизонтальный баннер со скругленными углами, 4 кнопки меню, круглая аватарка, 3 вертикальные 3D-карточки, смартфон справа и оригинальный вотермарк «Зарипов SMM» в левом углу.

            2. ОБНОВЛЕНИЕ ПОД НИШУ:
            - ОБЛОЖКА: Полностью удали объекты старой ниши (дома/септики). Нарисуй один главный, крупный, фотореалистичный объект, идеально отражающий сферу "{ctx.niche}", и расположи его в правой части баннера.
            - ТЕКСТ НА ОБЛОЖКЕ: Слева крупно напиши название компании: "{ctx.company_name}". {utp_str} {phone_str}.
            - ПРАВИЛО ОБРЕЗКИ: На обложке сохраняется красная пунктирная линия. Выше этой линии — только чистый фон (небо или абстракция). Никакой текст и объекты туда не заходят.
            - КНОПКИ МЕНЮ И КАРТОЧКИ: Замени все старые иконки и тексты на новые, логически подходящие под сферу "{ctx.niche}".
            - СМАРТФОН: Дублирует стиль и главный объект новой обложки.

            {style_str}
            {colors_str}
            {fonts_str}
            """

    def generate(
        self,
        context: ImageGenerationContextDTO,
        save_path: Path,
    ) -> ImageResultDTO:
        prompt = self.prompt(context)
        data = self._gemini.edit_image(
            prompt=prompt,
            image_path=self._layout_path,
            model=self._model,
            temperature=self._temperature,
        )
        resp = GeminiResponseDTO(raw_json=data)
        text = self.extract_text(resp)
        if text:
            self._logger.info("model text response", text=text)
        saved = self.save_image(resp, save_path)
        if not saved:
            raise ImageNotSaved("Не удалось сохранить изображение")
        return ImageResultDTO(
            service_name=self._name,
            prompt=prompt,
            image_path=save_path,
        )

    def close(self) -> None:
        self._gemini._session.close()

    def __enter__(self):
        self._gemini.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._gemini.__exit__(exc_type, exc_val, exc_tb)
        self.close()


class ImageGeneratorServiceGeminiDynamicCreativeV3(ImageGeneratorServiceGeminiBase):
    def prompt(self, ctx: ImageGenerationContextDTO) -> str:
        sctx = ctx.style
        if ctx.utp:
            utp_str = f'Below it, the UTP sub-text "{ctx.utp}" must be rendered in a smaller, clean, highly legible font size so it looks balanced and professional.'
        else:
            utp_str = ""
        if ctx.phone:
            phone_str = f'* PHONE NUMBER CAPSULE: The phone number "{ctx.phone}" must be placed at the bottom of the text block and enclosed inside a beautiful, stylized graphic container (like a rounded pill-badge or contrasting accent plate) to stand out elegantly.'
        else:
            phone_str = ""

        if sctx.style:
            style_str = (
                "Style: "
                + sctx.style
                + f' matching the "{ctx.niche}" domain, coherent studio lighting across all blocks'
            )
        else:
            style_str = f'Style: Clean commercial digital art, professional color grading matching the "{ctx.niche}" domain, coherent studio lighting across all blocks'

        if sctx.colors:
            colors_str = "Colors: " + sctx.colors
        else:
            colors_str = ""

        if sctx.fonts:
            fonts_str = "Fonts: " + " " + sctx.fonts
        else:
            fonts_str = "Fonts: flawless modern typography"

        return f"""
            You are a senior UI/UX production designer. Your primary constraint is to treat the provided image as an EXACT pixel-perfect layout grid (blueprint). You must NEVER change the positions, boundaries, shapes, or scale of the visual blocks. Your creative freedom applies ONLY to replacing the inner content, assets, and color palette to match the new business niche: "{ctx.niche}".

            STRICT LAYOUT & CONSISTENCY RULES:
            1. COMPOSITION RETENTION (Do NOT alter the layout):
            - Top center: White text "ОФОРМЛЕНИЕ ГРУППЫ" and the VK logo badge.
            - Main banner: Horizontal rounded rectangle (Desktop Cover).
            - Menu bar: 4 horizontal buttons right under the banner.
            - Avatar: Large circle on the right.
            - Bottom area: 3 large vertical cards with 3D depth effect (Widgets).
            - Device: A modern smartphone on the right mirroring the layout.
            - Bottom-left corner: Keep the exact watermark signature text "Зарипов SMM Графический Дизайнер".

            2. FIXED MENUS & THEME UNIFICATION:
            - MENU BUTTONS BACKGROUND: All 4 horizontal buttons MUST share the EXACT SAME identical background texture, pattern, and color. Do not vary the backgrounds between buttons. They must look like a unified set. Inside them, place relevant 3D icons tailored to "{ctx.niche}".
            - THREE BOTTOM WIDGET CARDS: Their backgrounds must create a unified continuous panorama (a single seamless abstract theme or texture split across 3 vertical panels), maintaining coherent lighting.

            3. DETAILED CONTENT & COMPONENT FIXES (Strictly customized for "{ctx.niche}"):

            - MAIN BANNER (DESKTOP COVER): 
            * Completely wipe out the original house and septic tanks. Render a completely new, visually stunning environment and premium 3D objects/assets on the right side that instantly symbolize "{ctx.niche}".
            * TYPOGRAPHY HIERARCHY: On the left, print the company name "{ctx.company_name}" in a prominent, large, bold commercial typography. {utp_str}
            {phone_str}
            * THE RED DASHED LINE (CRITICAL TECHNICAL RULE): Keep the thin red dashed line exactly in the same position as the original blueprint. This is a technical safe-zone marker. Everything ABOVE this red dashed line must be clean, empty background (sky or clean abstract texture). Absolutely NO text, NO logos, and NO parts/tops of the main 3D objects are allowed to cross or exist above this red line.

            - SMARTPHONE DISPLAY (MOBILE COVER):
            * The screen of the smartphone must display a dedicated Mobile Cover version for "{ctx.niche}" with vertically optimized framing. It must feature the same branding style and colors, with the main 3D object centrally framed and clean typography adapted for a vertical smartphone screen.

            {style_str}
            {fonts_str}
            {colors_str}
            """


class ImageGeneratorServiceGeminiDynamicCreativeV5(ImageGeneratorServiceGeminiBase):
    def prompt(self, ctx: ImageGenerationContextDTO) -> str:
        # 1. Базовый системный контекст
        prompt_blocks = [
            "You are a senior UI/UX production designer.",
            "Your primary constraint is to treat the provided image as an EXACT pixel-perfect layout grid (blueprint).",
            "You must NEVER change the positions, boundaries, shapes, or scale of the visual blocks.",
            "Your creative freedom applies ONLY to replacing the inner content, assets, and stylistic execution to match the brand parameters.",
            f'\nBUSINESS DOMAIN / NICHE: "{ctx.niche}"',
        ]

        sctx = ctx.style
        # 2. Динамический блок стилистики (добавляется только при наличии данных)
        style_section = []
        if sctx.style:
            style_section.append(f"- VISUAL STYLE: {sctx.style}")
        else:
            style_section.append(
                f"- VISUAL STYLE: Automatically select the most professional, high-converting modern visual style that perfectly matches the business domain of {ctx.niche}."
            )

        if sctx.colors:
            style_section.append(
                f"- COLOR PALETTE: Strict compliance with colors: {sctx.colors}"
            )

        if sctx.fonts:
            style_section.append(f"- TYPOGRAPHY STYLE: {sctx.fonts}")

        prompt_blocks.append(
            "\nBRAND STYLISTS & PARAMETERS:\n" + "\n".join(style_section)
        )

        # 3. Жесткие правила сохранения композиции
        layout_rules = [
            "\nSTRICT LAYOUT RETENTION RULES (Do NOT alter the framework):",
            '- Top center: White text "ОФОРМЛЕНИЕ ГРУППЫ" and the VK logo badge.',
            "- Main banner: Horizontal rounded rectangle (Desktop Cover).",
            "- Menu bar: 4 horizontal buttons right under the banner.",
            "- Avatar: Large circle on the right.",
            "- Bottom area: 3 large vertical cards with 3D depth effect (Widgets).",
            "- Device: A modern smartphone on the right mirroring the layout.",
            '- Bottom-left corner: Keep the exact watermark signature text "Зарипов SMM Графический Дизайнер".',
        ]
        prompt_blocks.append("\n".join(layout_rules))

        # 4. Правила унификации интерфейса (меню и виджеты)
        unification_rules = [
            "\nINTERFACE UNIFICATION RULES:",
            "- MENU BUTTONS BACKGROUND: All 4 horizontal buttons MUST share the EXACT SAME identical background texture, pattern, and color. Do not vary the backgrounds between buttons. They must look like a unified set. Inside them, place relevant 3D icons tailored to the niche.",
            "- THREE BOTTOM WIDGET CARDS BACKGROUND: Their backgrounds must create a unified continuous panorama (a single seamless abstract theme or texture split across 3 vertical panels), maintaining coherent lighting.",
        ]
        prompt_blocks.append("\n".join(unification_rules))

        if ctx.utp:
            utp_str = f'Below it, the UTP sub-text "{ctx.utp}" must be rendered in a smaller, clean, highly legible font size so it looks balanced and professional.'
        else:
            utp_str = ""

        if ctx.phone:
            phone_str = f'  * PHONE NUMBER CAPSULE: The phone number "{ctx.phone}" must be placed at the bottom of the text block and enclosed inside a beautiful, stylized graphic container (like a rounded pill-badge or contrasting accent plate) to stand out elegantly.'
        else:
            phone_str = ""

        # 5. Детальная проработка контента (Текст, телефон, капсула, красная линия)
        content_rules = [
            f'\nDETAILED CONTENT FIXES (Strictly customized for "{ctx.niche}"):',
            "\n- MAIN BANNER (DESKTOP COVER):",
            "  * Completely wipe out the original house and septic tanks. Render a completely new, visually stunning environment and premium 3D objects/assets on the right side that instantly symbolize the niche.",
            f'  * TYPOGRAPHY HIERARCHY: On the left, print the company name "{ctx.company_name}" in a prominent, large, bold typography. {utp_str}',
            phone_str,
            "  * THE RED DASHED LINE (CRITICAL TECHNICAL RULE): Keep the thin red dashed line exactly in the same position as the original blueprint. This is a technical safe-zone marker. Everything ABOVE this red dashed line must be clean, empty background (sky or clean abstract texture). Absolutely NO text, NO logos, and NO parts/tops of the main 3D objects are allowed to cross or exist above this red line.",
        ]
        prompt_blocks.append("\n".join(content_rules))

        # 6. Правило для динамических 3D-форм виджетов
        widget_shapes = [
            "\n- DYNAMIC 3D WIDGET ICONS (Form variety rule):",
            "  * Inside the 3 bottom vertical cards, you must render distinct, custom-shaped high-quality 3D icons (traditionally a Question Mark, a Calculator, and a Currency/Ruble symbol).",
            f'  * CRITICAL: Do NOT copy the standard generic shapes from the original image. Dynamically redesign and morph the geometry of these three 3D shapes to integrate elements of "{ctx.niche}". (For example: if niche is auto-repair, merge the question mark with a wrench texture; if niche is real estate, make the calculator look like a stylized modern building blueprint). Give them unique volumetric shapes, custom glossy/matte textures, and unique thematic framing.',
        ]
        prompt_blocks.append("\n".join(widget_shapes))

        # 7. Адаптив под смартфон и финальный стиль
        final_blocks = [
            "\n- SMARTPHONE DISPLAY (MOBILE COVER):",
            f'  * The screen of the smartphone must display a dedicated Mobile Cover version for "{ctx.niche}" with vertically optimized framing. It must feature the same branding style, colors, and typography, with the main 3D object centrally framed.',
            f"\nStyle: Clean commercial digital art, professional color grading matching the chosen niche theme, coherent studio lighting across all blocks, flawless execution of specific custom generated assets.",
        ]
        prompt_blocks.append("\n".join(final_blocks))

        # Собираем всё в один финальный промпт через перенос строки
        return "\n".join(prompt_blocks)
