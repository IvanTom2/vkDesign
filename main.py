import urllib3
from datetime import datetime
from pathlib import Path

from settings import settings
from src.gemini.client import GeminiClient
from src.gemini.cost import estimate_cost

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def log(msg: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def simple_prompt_v1(
    niche: str,
    company_name: str,
    utp: str,
    phone: str,
) -> str:
    return f"""
        Используй исходное изображение исключительно как композиционный шаблон (Layout) для презентации графического дизайна. Сделай ПОЛНОСТЬЮ НОВОЕ оформление группы ВК на тему: "{niche}".

        1. СТРУКТУРА (Сохранить):
        - Верхний текст «ОФОРМЛЕНИЕ ГРУППЫ», плашка «вконтакте», горизонтальный баннер со скругленными углами, 4 кнопки меню, круглая аватарка, 3 вертикальные 3D-карточки, смартфон справа и оригинальный вотермарк «Зарипов SMM» в левом углу.

        2. ОБНОВЛЕНИЕ ПОД НИШУ:
        - ОБЛОЖКА: Полностью удали объекты старой ниши (дома/септики). Нарисуй один главный, крупный, фотореалистичный объект, идеально отражающий сферу "{niche}", и расположи его в правой части баннера.
        - ТЕКСТ НА ОБЛОЖКЕ: Слева крупно напиши название компании: "{company_name}". Чуть ниже добавь УТП: "{utp}". В самом низу укажи телефон: "{phone}".
        - ПРАВИЛО ОБРЕЗКИ: На обложке сохраняется красная пунктирная линия. Выше этой линии — только чистый фон (небо или абстракция). Никакой текст и объекты туда не заходят.
        - КНОПКИ МЕНЮ И КАРТОЧКИ: Замени все старые иконки и тексты на новые, логически подходящие под сферу "{niche}".
        - СМАРТФОН: Дублирует стиль и главный объект новой обложки.

        Стиль: современный коммерческий веб-дизайн, сочные цвета, чистый рендер.
        """


def dynamic_creative_prompt_v1(
    niche: str,
    company_name: str,
    utp: str,
    phone: str,
) -> str:
    return f"""
        You are an award-winning UI/UX and graphic designer with absolute creative freedom. Use the provided image ONLY as a structural blueprint (Layout wireframe) for positioning blocks. 

        CRITICAL RULE - CREATIVE FREEDOM & NICHE ADAPTATION:
        - Visually redesign everything from scratch. Do NOT copy the color palette, grass, sky, or materials from the original image unless it perfectly fits the new niche.
        - Automatically select the most professional, high-converting, and modern visual style, background texture, and color scheme that perfectly matches the business domain: "{niche}". 
        - Be creative: invent new appropriate 3D objects, backgrounds, shapes, and lighting that represent "{niche}" in the best commercial way. Give it a fresh, unique look.

        1. COMPOSITION STRUCTURE (Keep element boundaries and positions only):
        - Top center: White text "ОФОРМЛЕНИЕ ГРУППЫ" and the VK logo badge.
        - Main banner: Horizontal rounded rectangle.
        - Menu bar: 4 horizontal icon buttons right under the banner.
        - Avatar: Large circle on the right.
        - Bottom area: 3 large vertical cards with 3D depth effect.
        - Device: A modern smartphone on the right displaying the responsive mobile layout.
        - Bottom-left corner: Keep the original watermark signature text "Зарипов SMM Графический Дизайнер".

        2. CONTENT & RE-RENDERING (Strictly customized for "{niche}"):
        - MAIN BANNER BACKGROUND & OBJECTS: Completely wipe out the original house and septic tanks. Render a completely new, visually stunning environment and premium 3D objects/assets on the right side that instantly symbolize "{niche}".
        - TEXT ON BANNER: On the left, print the company name "{company_name}" in large clean typography. Below it, add the UTP sub-text: "{utp}". At the bottom, place the contact phone: "{phone}".
        - SAFE ZONE RULE: The red dashed line marks the adaptive crop zone. Everything ABOVE this line on the banner must be a clean, empty background or sky. No text, logos, or main object tops should cross above this line.
        - BUTTONS & WIDGET CARDS: Replace all old icons and texts. Design completely new, highly relevant 3D icons inside the 4 buttons and 3 lower cards, specifically tailored to the services of "{niche}". 
        - SMARTPHONE: Strictly mirrors the newly generated banner layout, colors, and assets in a mobile view.

        Style: Clean commercial digital art, professional color grading, coherent lighting across all blocks, flawless modern typography.
        """


def dynamic_creative_prompt_v2(
    niche: str,
    company_name: str,
    utp: str,
    phone: str,
) -> str:
    return f"""
        You are an award-winning UI/UX and senior graphic designer with absolute creative freedom. Use the provided image ONLY as a structural layout blueprint (wireframe) for positioning blocks. 

        CRITICAL RULE - CREATIVE FREEDOM & NICHE ADAPTATION:
        - Visually redesign everything from scratch. Do NOT copy the color palette, grass, sky, or materials from the original image.
        - Automatically select the most professional, high-converting, and modern visual style, background texture, and color scheme that perfectly matches the business domain: "{niche}". 
        - Give the entire presentation a coherent, premium studio-shot showcase feel.

        1. COMPOSITION STRUCTURE (Keep element boundaries and positions only):
        - Top center: White text "ОФОРМЛЕНИЕ ГРУППЫ" and the VK logo badge.
        - Main banner: Horizontal rounded rectangle (Desktop Cover, 16:9 aspect ratio context).
        - Menu bar: 4 horizontal icon buttons right under the banner.
        - Avatar: Large circle on the right.
        - Bottom area: 3 large vertical cards with 3D depth effect (Widgets).
        - Device: A modern smartphone on the right displaying the mobile cover layout.
        - Bottom-left corner: Keep the original watermark signature text "Зарипов SMM Графический Дизайнер".

        2. DETAILED CONTENT & COMPONENT FIXES (Strictly customized for "{niche}"):

        - MAIN BANNER (DESKTOP COVER): 
        * Completely wipe out the original house and septic tanks. Render a completely new, visually stunning environment and premium 3D objects/assets on the right side that instantly symbolize "{niche}".
        * TYPOGRAPHY HIERARCHY: On the left, print the company name "{company_name}" in a prominent, large, bold commercial typography. Below it, the UTP sub-text "{utp}" must be rendered in a smaller, clean, highly legible font size so it looks balanced and professional, not oversized.
        * PHONE NUMBER CAPSULE: The phone number "{phone}" must be placed at the bottom of the text block and enclosed inside a beautiful, stylized graphic container (like a rounded pill-badge or contrasting accent plate) to make it stand out elegantly from the background.
        * SAFE ZONE RULE: The red dashed line marks the cutting edge. Everything ABOVE this line on the banner must be a clean, empty background or sky. No text, logos, or main object tops should cross above this line.

        - SMARTPHONE DISPLAY (MOBILE COVER 9:16):
        * The screen of the smartphone must NOT display a squished version of the desktop banner. It must show a dedicated Mobile Cover version for "{niche}". It should feature the same branding style, but the layout is vertically optimized: the main 3D object from the banner is centrally framed, with clean typography adapted for a vertical smartphone screen.

        - MENU BUTTONS FONS:
        * The 4 horizontal buttons must NOT have flat, boring solid backgrounds. Add subtle, high-quality design variety to their backgrounds (such as abstract geometric micro-patterns, soft gradients, or translucent frosted-glass blur textures) that match the chosen theme. Replace all old icons and texts with new 3D icons tailored to "{niche}".

        - THREE BOTTOM WIDGET CARDS (PANORAMIC BACKGROUND EFFECT):
        * The 3 large vertical cards stand together. Their backgrounds must create a unified composition: design a beautiful, continuous abstract background theme or landscape texture that seamlessly flows from the 1st card through the 2nd and into the 3rd card (a horizontal continuous flow split into 3 vertical panels).
        * Inside each card, place a distinct, high-quality 3D icon (e.g., Question Mark, Calculator, Currency Symbol) rendered with beautiful volume, lighting, and matching accent colors.

        Style: Clean commercial digital art, professional color grading, coherent studio lighting across all blocks, flawless modern typography, completely custom generated assets for "{niche}".
        """


def dynamic_creative_prompt_v3(
    niche: str,
    company_name: str,
    utp: str,
    phone: str,
) -> str:
    return f"""
        You are a senior UI/UX production designer. Your primary constraint is to treat the provided image as an EXACT pixel-perfect layout grid (blueprint). You must NEVER change the positions, boundaries, shapes, or scale of the visual blocks. Your creative freedom applies ONLY to replacing the inner content, assets, and color palette to match the new business niche: "{niche}".

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
        - MENU BUTTONS BACKGROUND: All 4 horizontal buttons MUST share the EXACT SAME identical background texture, pattern, and color. Do not vary the backgrounds between buttons. They must look like a unified set. Inside them, place relevant 3D icons tailored to "{niche}".
        - THREE BOTTOM WIDGET CARDS: Their backgrounds must create a unified continuous panorama (a single seamless abstract theme or texture split across 3 vertical panels), maintaining coherent lighting.

        3. DETAILED CONTENT & COMPONENT FIXES (Strictly customized for "{niche}"):

        - MAIN BANNER (DESKTOP COVER): 
        * Completely wipe out the original house and septic tanks. Render a completely new, visually stunning environment and premium 3D objects/assets on the right side that instantly symbolize "{niche}".
        * TYPOGRAPHY HIERARCHY: On the left, print the company name "{company_name}" in a prominent, large, bold commercial typography. Below it, the UTP sub-text "{utp}" must be rendered in a smaller, clean, highly legible font size so it looks balanced and professional.
        * PHONE NUMBER CAPSULE: The phone number "{phone}" must be placed at the bottom of the text block and enclosed inside a beautiful, stylized graphic container (like a rounded pill-badge or contrasting accent plate) to stand out elegantly.
        * THE RED DASHED LINE (CRITICAL TECHNICAL RULE): Keep the thin red dashed line exactly in the same position as the original blueprint. This is a technical safe-zone marker. Everything ABOVE this red dashed line must be clean, empty background (sky or clean abstract texture). Absolutely NO text, NO logos, and NO parts/tops of the main 3D objects are allowed to cross or exist above this red line.

        - SMARTPHONE DISPLAY (MOBILE COVER):
        * The screen of the smartphone must display a dedicated Mobile Cover version for "{niche}" with vertically optimized framing. It must feature the same branding style and colors, with the main 3D object centrally framed and clean typography adapted for a vertical smartphone screen.

        Style: Clean commercial digital art, professional color grading matching the "{niche}" domain, coherent studio lighting across all blocks, flawless modern typography, completely custom generated assets.
        """


def main():
    log("=== START ===")
    with GeminiClient(
        api_key=settings.GEMINI_API_KEY,
        proxy_url=settings.PROXY_URL,
    ) as gem:
        # MODEL = "gemini-3.1-flash-image-preview" # NANO BANANA 2
        MODEL = "gemini-3-pro-image-preview"  # NANO BANANA PRO

        TEMPERATURE = 0.1
        # TEMPERATURE = 0.4
        # TEMPERATURE = 0.7
        # TEMPERATURE = 1.0

        # IMAGE_PATH = Path("/home/ivan/Projects/vkDesign/Макет-2-1.png")
        IMAGE_PATH = Path("/home/ivan/Projects/vkDesign/Макет-2-1.jpg")

        # PROMPT = simple_prompt_v1(
        #     "Строительство домов",
        #     "СК Дом и Дача",
        #     "Строим дома из газобетона за 1 месяц от фундамента до крыши",
        #     "+7 (495) 123-45-67",
        # )
        # PROMPT = dynamic_creative_prompt_v1(
        #     "Строительство домов",
        #     "СК Дом и Дача",
        #     "Строим дома из газобетона за 1 месяц от фундамента до крыши",
        #     "+7 (495) 123-45-67",
        # )
        # PROMPT = dynamic_creative_prompt_v2(
        #     "Строительство домов",
        #     "СК Дом и Дача",
        #     "Строим дома из газобетона за 1 месяц от фундамента до крыши",
        #     "+7 (495) 123-45-67",
        # )
        PROMPT = dynamic_creative_prompt_v3(
            "Строительство домов",
            "СК Дом и Дача",
            "Строим дома из газобетона за 1 месяц от фундамента до крыши",
            "+7 (495) 123-45-67",
        )

        log("вызываю edit_image...")
        resp = gem.edit_image(
            prompt=PROMPT,
            image_path=IMAGE_PATH,
            model=MODEL,
            temperature=TEMPERATURE,
        )
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
