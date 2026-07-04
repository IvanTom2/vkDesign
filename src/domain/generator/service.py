import base64
from abc import ABC
from abc import abstractmethod
from pathlib import Path

from src.gemini.client import GeminiClient
from src.gemini.models import GeminiResponseDTO
from src.openai.client import OpenAIImageClient
from src.openai.models import OpenAIImageResponseDTO
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
    ) -> None:
        self._name = name
        self._layout_path = layout_path
        self._temperature = temperature

    @abstractmethod
    def prompt(self, ctx: ImageGenerationContextDTO) -> str:
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
    ) -> None:
        super().__init__(name, layout_path, temperature)
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
            print("Тектовый ответ модели:", text)
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


class ImageGeneratorServiceGeminiDynamicCreativeV6(ImageGeneratorServiceGeminiBase):
    def prompt(self, ctx: ImageGenerationContextDTO) -> str:
        # 1. Базовый системный контекст
        prompt_blocks = [
            "You are a senior UI/UX production designer.",
            "Your primary constraint is to treat the provided image as an EXACT pixel-perfect layout grid (blueprint).",
            "You must NEVER change the positions, boundaries, shapes, or scale of the visual blocks.",
            "Your creative freedom applies ONLY to replacing the inner content, assets, and stylistic execution to match the brand parameters.",
            f'\nBUSINESS DOMAIN / NICHE: "{ctx.niche}"',
        ]

        # 2. Динамический блок стилистики
        sctx = ctx.style
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
            "- MENU BUTTONS BACKGROUND: All 4 horizontal buttons MUST share the EXACT SAME identical background texture, pattern, and color. "
            "Do not vary the backgrounds between buttons. They must look like a unified set.",
            "- THREE BOTTOM WIDGET CARDS BACKGROUND: Their backgrounds must create a unified continuous panorama "
            "(a single seamless abstract theme or texture split across 3 vertical panels), maintaining coherent lighting.",
        ]
        prompt_blocks.append("\n".join(unification_rules))

        # 5. Детальная проработка контента (Сборка с защитой от None)
        utp_part = ""
        if ctx.utp:
            utp_part = f' Below it, the UTP sub-text "{ctx.utp}" must be rendered in a smaller, clean, highly legible font size so it looks balanced and professional.'

        content_rules = [
            f'\nDETAILED CONTENT FIXES (Strictly customized for "{ctx.niche}"):',
            "\n- MAIN BANNER (DESKTOP COVER):",
            "  * Completely wipe out the original house and septic tanks. Render a completely new, visually stunning environment "
            "and premium 3D objects/assets on the right side that instantly symbolize the niche.",
            f'  * TYPOGRAPHY HIERARCHY: On the left, print the company name "{ctx.company_name}" in a prominent, large, bold typography.{utp_part}',
        ]

        # Добавляем телефон только если он передан в DTO
        if ctx.phone:
            content_rules.append(
                f'  * PHONE NUMBER CAPSULE: The phone number "{ctx.phone}" must be placed at the bottom of the text block and enclosed inside a beautiful, '
                "stylized graphic container (like a rounded pill-badge or contrasting accent plate) to stand out elegantly."
            )

        content_rules.append(
            "  * THE RED DASHED LINE (CRITICAL TECHNICAL RULE): Keep the thin red dashed line exactly in the same position as the original blueprint. "
            "This is a technical safe-zone marker. Everything ABOVE this red dashed line must be clean, empty background (sky or clean abstract texture). "
            "Absolutely NO text, NO logos, and NO parts/tops of the main 3D objects are allowed to cross or exist above this red line."
        )
        prompt_blocks.append("\n".join(content_rules))

        if ctx.components.menu:
            menu_icons_text = (
                "Text for menu icons based on provided menu items: "
                + ", ".join(ctx.components.menu)
            )
        else:
            menu_icons_text = ""

        # 6. НАСТРОЙКА ДИНАМИЧЕСКИХ ИКОНОК МЕНЮ
        menu_icons = [
            "\n- DYNAMIC 3D MENU ICONS & LABELS (Variety rule):",
            f"  * Inside the 4 horizontal menu buttons, completely replace the original icons with 4 entirely different, "
            f'highly detailed 3D objects that directly represent standard corporate sections for "{ctx.niche}".',
            "  * CRITICAL REQUIRED TEXT: Each button MUST contain clear, readable Russian text labels below or next to its 3D icon, "
            # 'exactly following the original layout positions (e.g., "КАТАЛОГ", "О НАС", "ОТЗЫВЫ", "КОНСУЛЬТАЦИЯ"). Do not erase the text.',
            "  * Each of the 4 icons must be a unique, distinct volumetric 3D object with clear shapes, textures, and shading.",
            menu_icons_text,
        ]
        prompt_blocks.append("\n".join(menu_icons))

        if ctx.components.widgets:
            widget_icons_text = (
                "Text for widget icons based on provided widget items: "
                + ", ".join(ctx.components.widgets)
            )
        else:
            widget_icons_text = ""

        # 7. Правило для динамических 3D-форм виджетов (С фиксацией текста)
        widget_shapes = [
            "\n- DYNAMIC 3D WIDGET ICONS & LABELS (Form variety rule):",
            "  * Inside the 3 bottom vertical cards, you must render distinct, custom-shaped high-quality 3D icons ",
            "(traditionally a Question Mark, a Calculator, and a Currency/Ruble symbol).",
            f"  * CRITICAL REQUIRED TEXT: Each of the 3 cards MUST contain its large, bold text label at the bottom, exactly matching the positions in the blueprint ",
            # f'(e.g., "ЗАДАТЬ ВОПРОС", "УЗНАТЬ СТОИМОСТЬ", "ЦЕНЫ НА УЧАСТКИ" or equivalents adapted for "{ctx.niche}").',
            f"  * Do NOT copy the standard generic shapes from the original image. ",
            f'Dynamically redesign and morph the geometry of these three 3D shapes to integrate elements of "{ctx.niche}". ',
            "Give them unique volumetric shapes, custom glossy/matte textures, and unique thematic framing, while keeping the clear text labels legible.",
            widget_icons_text,
        ]
        prompt_blocks.append("\n".join(widget_shapes))

        # 8. Адаптив под смартфон и финальный стиль
        final_blocks = [
            "\n- SMARTPHONE DISPLAY (MOBILE COVER):",
            f'  * The screen of the smartphone must display a dedicated Mobile Cover version for "{ctx.niche}" with vertically optimized framing. It must feature the same branding style, colors, and typography, with the main 3D object centrally framed.',
            f"\nStyle: Clean commercial digital art, professional color grading matching the chosen niche theme, coherent studio lighting across all blocks, flawless execution of text elements and specific custom generated assets.",
        ]
        prompt_blocks.append("\n".join(final_blocks))

        return "\n".join(prompt_blocks)


class ImageGeneratorServiceGeminiDynamicCreativeV7(ImageGeneratorServiceGeminiBase):
    def prompt(self, ctx: ImageGenerationContextDTO) -> str:
        if not ctx.components.menu or not ctx.components.widgets:
            raise ValueError(
                "Menu and widget components must be provided for GeminiDynamicCreativeV7"
            )
        menu_section = "\n".join([f"- {item}" for item in ctx.components.menu])
        widget_section = "\n".join([f"- {item}" for item in ctx.components.widgets])
        txt = f"""
        You are a senior UI/UX production designer.
        Constraint: Treat the provided image ONLY as an abstract pixel-perfect spatial layout grid (blueprint) for positions, shapes, and boundaries.

        CRITICAL VISUAL RESET:
        * ABSOLUTE ASSET REPLACEMENT: You must COMPLETELY ERASE and WIPE OUT all background art, environment details, textures, plants, leaves, birds, or specific decorative objects from the original blueprint image.
        * DO NOT copy any illustrative style or content from the reference image. Generate entirely brand-new, original backgrounds and environmental elements from scratch tailored EXCLUSIVELY to the "{ctx.niche}" domain.

        BUSINESS DOMAIN: "{ctx.niche}"
        COMPANY NAME: "{ctx.company_name}"
        {f'UTP: "{ctx.utp}"' if ctx.utp else ''}
        {f'PHONE: "{ctx.phone}"' if ctx.phone else ''}

        STYLE & COLORS:
        - Style: {ctx.style.style if ctx.style.style else 'Modern premium commercial 3D style matching the niche.'}
        - Colors: {ctx.style.colors if ctx.style.colors else 'Professional color palette selected automatically.'}
        - Fonts: {ctx.style.fonts if ctx.style.fonts else 'Flawless modern typography matching the niche and style.'}

        CRITICAL LAYOUT & UNIFICATION RULES:
        * THE RED DASHED LINE (CRITICAL TECHNICAL RULE): The thin red dashed line must be positioned exactly in the same place as on the original blueprint. This is a technical safe-zone marker. Everything ABOVE this red dashed line MUST strictly remain a clean, empty background (sky or clean abstract texture). It is CATEGORICALLY FORBIDDEN to place any text, logos, or upper parts of the main 3D objects across or above this red line.
        * MENU BACKGROUND UNITY: All 4 horizontal menu buttons MUST share the EXACT SAME brand-new identical background texture, pattern, and color for absolute visual integrity.
        * WIDGET PANORAMA UNITY: The 3 bottom vertical cards MUST share a single, seamless continuous background landscape/panorama split across the 3 panels, generated completely new for "{ctx.niche}".
        * SIGNATURE: Keep the exact watermark text "Зарипов SMM Графический Дизайнер" in the bottom-left corner.

        DETAILED CONTENT REPLACEMENT:

        - MAIN BANNER:
          * Left side: Large bold company name "{ctx.company_name}". Below it, smaller UTP font. Phone number enclosed inside a stylized pill-badge.
          * Right side: Render completely new premium 3D assets representing "{ctx.niche}". No old assets or background details allowed.
          * Bottom Right: Keep the action button containing the exact text "НАПИСАТЬ".

        - AVATAR: Clean circular logo icon for "{ctx.company_name}" inside the circle, with a brand-new background.

        - MENU BUTTONS (Render exactly 4 horizontal items following the blueprint):
        {menu_section}

        - WIDGET CARDS (Render exactly 3 vertical cards following the blueprint):
        {widget_section}

        - SMARTPHONE Mockup: Screen must display a vertically optimized mobile cover mirroring the main banner theme, style, and typography, built entirely on the new visual assets.
        """
        return txt


class ImageGeneratorServiceGeminiFixedPrompt(ImageGeneratorServiceGeminiBase):
    def __init__(
        self,
        prompt: str,
        model: str,
        gemini: GeminiClient,
        name: str,
        layout_path: Path,
        temperature: float | None = None,
    ) -> None:
        super().__init__(model, gemini, name, layout_path, temperature)
        self._prompt = prompt

    def prompt(self, ctx: ImageGenerationContextDTO) -> str:
        return self._prompt


class ImageGeneratorServiceOpenAIBase(IImageGeneratorService):
    def __init__(
        self,
        model: str,
        openai: OpenAIImageClient,
        name: str,
        layout_path: Path,
        temperature: float | None = None,
        size: str = "auto",
        quality: str = "auto",
    ) -> None:
        super().__init__(name, layout_path, temperature)
        self._model = model
        self._openai = openai
        self._size = size
        self._quality = quality

    def prompt(self, ctx: ImageGenerationContextDTO) -> str:
        sctx = ctx.style
        utp_str = f'Чуть ниже добавь УТП: "{ctx.utp}". ' if ctx.utp else ""
        phone_str = f'В самом низу укажи телефон: "{ctx.phone}"' if ctx.phone else ""
        style_str = f"Стиль: {sctx.style}" if sctx.style else ""
        colors_str = f"Цвета: {sctx.colors}" if sctx.colors else ""
        fonts_str = f"Шрифты: {sctx.fonts}" if sctx.fonts else ""
        return """
У меня есть оформление группы ВК - макет на изображении. Необходимо полностью изменить тематику и стилистику. Поменять иконки, текст, картинки для тематики "Строительство кирпичных домов". Соблюдай структуру и размеры исходного макета - измени полностью фон и прочее. 

Название компании "ЭлитСтрой". 

Виджеты (3 картинки на макете):
"Задать вопрос"
"Рассчитать стоимость"
"Специальные предложения"

Меню (4 картинки на макете):
"Отзывы"
"Наши дома"
"Гарантия"
"Пример договора"
"""

        # return f"""
        #     Используй исходное изображение исключительно как композиционный шаблон (Layout) для презентации графического дизайна. Сделай ПОЛНОСТЬЮ НОВОЕ оформление группы ВК на тему: "{ctx.niche}".

        #     1. СТРУКТУРА (Сохранить):
        #     - Верхний текст «ОФОРМЛЕНИЕ ГРУППЫ», плашка «вконтакте», горизонтальный баннер со скругленными углами, 4 кнопки меню, круглая аватарка, 3 вертикальные 3D-карточки, смартфон справа и оригинальный вотермарк «Зарипов SMM» в левом углу.

        #     2. ОБНОВЛЕНИЕ ПОД НИШУ:
        #     - ОБЛОЖКА: Полностью удали объекты старой ниши (дома/септики). Нарисуй один главный, крупный, фотореалистичный объект, идеально отражающий сферу "{ctx.niche}", и расположи его в правой части баннера.
        #     - ТЕКСТ НА ОБЛОЖКЕ: Слева крупно напиши название компании: "{ctx.company_name}". {utp_str} {phone_str}.
        #     - ПРАВИЛО ОБРЕЗКИ: На обложке сохраняется красная пунктирная линия. Выше этой линии — только чистый фон (небо или абстракция). Никакой текст и объекты туда не заходят.
        #     - КНОПКИ МЕНЮ И КАРТОЧКИ: Замени все старые иконки и тексты на новые, логически подходящие под сферу "{ctx.niche}".
        #     - СМАРТФОН: Дублирует стиль и главный объект новой обложки.

        #     {style_str}
        #     {colors_str}
        #     {fonts_str}
        #     """

    def save_image(
        self,
        response: OpenAIImageResponseDTO,
        save_path: Path,
    ) -> bool:
        return self._openai.save_image(response, save_path)

    def generate(
        self,
        context: ImageGenerationContextDTO,
        save_path: Path,
    ) -> ImageResultDTO:
        prompt = self.prompt(context)
        response = self._openai.edit_image(
            prompt=prompt,
            image_path=self._layout_path,
            model=self._model,
            size=self._size,
            quality=self._quality,
        )
        saved = self.save_image(response, save_path)
        if not saved:
            raise ImageNotSaved("Не удалось сохранить изображение")
        return ImageResultDTO(
            service_name=self._name,
            prompt=prompt,
            image_path=save_path,
        )

    def close(self) -> None:
        self._openai._session.close()

    def __enter__(self):
        self._openai.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._openai.__exit__(exc_type, exc_val, exc_tb)
        self.close()
