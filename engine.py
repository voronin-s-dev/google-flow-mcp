import os
import sys
import io
import time
import base64
import shutil
import tempfile
import urllib.request
from pathlib import Path
from typing import List, Dict, Any, Optional
from playwright.sync_api import sync_playwright

try:
    from PIL import Image, ImageFilter
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

from expander import expand_prompt, validate_aspect_ratio, format_camera_prompt

CDP_URL = "http://127.0.0.1:9222"
FLOW_URL = "https://flow.google.com"
BASE_DIR = Path(__file__).parent.resolve()
STORAGE_FILE = BASE_DIR / "storage_state.json"
PROFILE_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "GoogleFlowAgentProfile"

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"

def is_cdp_available() -> bool:
    try:
        with urllib.request.urlopen(f"{CDP_URL}/json/version", timeout=1.5) as resp:
            return resp.status == 200
    except Exception:
        return False

def get_flow_context(p):
    """
    Создает или подключается к контексту браузера с поддержкой CDP, нативного профиля или сохраненной сессии.
    Возвращает кортеж (context, browser, is_headless).
    """
    if is_cdp_available():
        browser = p.chromium.connect_over_cdp(CDP_URL)
        return browser.contexts[0], browser, False

    if PROFILE_DIR.exists():
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            channel="chrome",
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
            viewport={"width": 1920, "height": 1080}
        )
        return context, None, True

    if STORAGE_FILE.exists():
        browser = p.chromium.launch(
            channel="chrome",
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        context = browser.new_context(
            storage_state=str(STORAGE_FILE),
            user_agent=USER_AGENT,
            viewport={"width": 1920, "height": 1080}
        )
        return context, browser, True

    raise RuntimeError(
        f"Авторизационные данные Google Flow не найдены. "
        "Запустите login.bat для однократного входа в Google-аккаунт."
    )

def get_or_create_page(context):
    for page in context.pages:
        if "flow.google.com" in page.url or "labs.google" in page.url:
            return page
    page = context.new_page()
    page.goto(FLOW_URL, wait_until="domcontentloaded", timeout=25000)
    try:
        page.wait_for_load_state("networkidle", timeout=4000)
    except Exception:
        pass
    return page

def ensure_in_project(page) -> bool:
    if "/project/" in page.url:
        return True

    # Поиск кнопки "Новый проект"
    new_proj_btn = page.get_by_role("button", name="Новый проект").or_(page.get_by_text("Новый проект")).first
    if new_proj_btn.is_visible(timeout=3000):
        new_proj_btn.click()
        try:
            page.wait_for_url("**/project/**", timeout=8000)
            return True
        except Exception:
            pass

    create_btn = page.get_by_role("button", name="New").or_(page.get_by_role("button", name="Создать")).first
    if create_btn.is_visible(timeout=2000):
        create_btn.click()
        try:
            page.wait_for_url("**/project/**", timeout=8000)
            return True
        except Exception:
            pass

    return "/project/" in page.url

def ensure_media_mode(page, media_type: str = "image") -> bool:
    """
    Переключает режим генерации между 'image' и 'video' в интерфейсе Flow.
    """
    target = media_type.lower().strip()
    label = "Video" if target == "video" else "Image"
    ru_label = "Видео" if target == "video" else "Изображение"

    # Способ 1: Прямые кнопки на левой панели или холсте
    mode_selectors = [
        page.get_by_role("button", name=label),
        page.get_by_role("button", name=ru_label),
        page.locator(f"button[aria-label*='{label}' i]"),
        page.locator(f"button[aria-label*='{ru_label}' i]"),
        page.locator(f"[data-testid*='mode-{target}']")
    ]
    for btn_loc in mode_selectors:
        btn = btn_loc.first
        if btn.is_visible(timeout=600):
            is_active = (
                btn.get_attribute("aria-pressed") == "true" or
                btn.get_attribute("aria-selected") == "true" or
                "active" in (btn.get_attribute("class") or "").lower() or
                "selected" in (btn.get_attribute("class") or "").lower()
            )
            if not is_active:
                btn.click()
                page.wait_for_timeout(800)
            return True

    # Способ 2: Через всплывающее меню настроек
    trig = page.locator("button[aria-label*='Триггер' i], button:has-text('Nano Banana')").first
    if trig.is_visible(timeout=1000):
        trig.click()
        page.wait_for_timeout(600)
        mode_btn = page.locator(f"button:has-text('{ru_label}'), button:has-text('{label}')").first
        if mode_btn.is_visible(timeout=1500):
            mode_btn.click()
            page.wait_for_timeout(500)
        page.keyboard.press("Escape")
        return True

    return False

def set_model_family(page, model_name: Optional[str] = None) -> bool:
    """
    Устанавливает модель в Google Flow (Nano Banana 2.1, Nano Banana Pro, Nano Banana 2 Lite).
    """
    if not model_name:
        return False

    name_lower = model_name.lower().strip()
    target_text = "Nano Banana 2.1"
    if "pro" in name_lower:
        target_text = "Nano Banana Pro"
    elif "lite" in name_lower:
        target_text = "Nano Banana 2 Lite"
    elif "2.1" in name_lower or "banana" in name_lower:
        target_text = "Nano Banana 2.1"

    print(f"[*] Выбор семейства модели: {target_text}")
    try:
        trig = page.locator("button[aria-label*='Триггер' i], button:has-text('Nano Banana')").first
        if not trig.is_visible(timeout=1500):
            return False

        trig.click()
        page.wait_for_timeout(600)

        family_btn = page.locator("button[aria-label='Выбрать семейство моделей']").first
        if family_btn.is_visible(timeout=1500):
            family_btn.click()
            page.wait_for_timeout(600)

            choice = page.locator(f".cdk-overlay-pane:last-child button:has-text('{target_text}')").first
            if choice.is_visible(timeout=2000):
                choice.click()
                page.wait_for_timeout(500)
                print(f"[+] Успешно выбрана модель: {target_text}")

        page.keyboard.press("Escape")
        page.wait_for_timeout(300)
        return True
    except Exception as e:
        print(f"[-] Предупреждение: Не удалось переключить модель ({e})")
        try:
            page.keyboard.press("Escape")
        except Exception:
            pass
        return False

def set_aspect_ratio(page, aspect_ratio: Optional[str]) -> bool:
    """
    Устанавливает соотношение сторон в интерфейсе Google Flow (16:9, 9:16, 1:1, 4:3, 3:4).
    """
    if not aspect_ratio:
        return False
    ratio = validate_aspect_ratio(aspect_ratio)
    if not ratio:
        return False

    print(f"[*] Установка соотношения сторон: {ratio}")
    try:
        trig = page.locator("button[aria-label*='Триггер' i], button:has-text('Nano Banana')").first
        if trig.is_visible(timeout=1000):
            trig.click()
            page.wait_for_timeout(500)
            btn_ratio = page.locator(f"button:has-text('{ratio}'), [role='menuitem']:has-text('{ratio}'), [role='option']:has-text('{ratio}')").first
            if btn_ratio.is_visible(timeout=1500):
                btn_ratio.click()
                page.wait_for_timeout(400)
                page.keyboard.press("Escape")
                return True
            page.keyboard.press("Escape")

        # Вариант 2: Прямая кнопка на холсте
        for sel in [f"button:has-text('{ratio}')", f"button[aria-label*='{ratio}']", f"[data-testid*='{ratio}']"]:
            btn = page.locator(sel).first
            if btn.is_visible(timeout=400):
                btn.click()
                return True
    except Exception as e:
        print(f"[-] Ошибка установки соотношения сторон: {e}")
        try:
            page.keyboard.press("Escape")
        except Exception:
            pass
    return False

def set_batch_count(page, batch_count: int = 1) -> bool:
    """
    Устанавливает количество генерируемых вариантов (x1, x2, x3, x4) в Google Flow.
    """
    if batch_count not in (1, 2, 3, 4):
        batch_count = 1

    target = f"x{batch_count}"
    print(f"[*] Установка мультипликатора генерации: {target}")
    try:
        trig = page.locator("button[aria-label*='Триггер' i], button:has-text('Nano Banana')").first
        if trig.is_visible(timeout=1000):
            trig.click()
            page.wait_for_timeout(400)
            btn = page.locator(f".cdk-overlay-pane button:has-text('{target}'), [role='menuitem']:has-text('{target}')").first
            if btn.is_visible(timeout=1200):
                btn.click()
                page.wait_for_timeout(300)
                page.keyboard.press("Escape")
                print(f"[+] Мультипликатор {target} успешно активирован.")
                return True
            page.keyboard.press("Escape")
    except Exception as e:
        print(f"[-] Предупреждение: Не удалось установить мультипликатор {target}: {e}")
        try:
            page.keyboard.press("Escape")
        except Exception:
            pass
    return False

def set_video_audio_mode(page, mute_audio: bool = False) -> bool:
    """
    Управляет звуком видео Veo через меню настроек студии ('Вернуть видео без звука').
    """
    print(f"[*] Настройка аудиорежима видео: mute_audio={mute_audio}")
    try:
        tune_btn = page.locator("button[aria-label='Настройки']").first
        if not tune_btn.is_visible(timeout=1000):
            return False
        tune_btn.click()
        page.wait_for_timeout(500)
        mute_item = page.locator("button:has-text('Вернуть видео без звука'), [role='menuitem']:has-text('Вернуть видео без звука'), [role='switch']:has-text('без звука')").first
        if mute_item.is_visible(timeout=1500):
            is_checked = (
                mute_item.get_attribute("aria-checked") == "true" or
                "checked" in (mute_item.get_attribute("class") or "").lower()
            )
            if is_checked != mute_audio:
                mute_item.click()
                page.wait_for_timeout(300)
                print(f"[+] Переключатель звука Veo обновлен: mute_audio={mute_audio}")
        page.keyboard.press("Escape")
        return True
    except Exception as e:
        print(f"[-] Предупреждение: Не удалось настроить аудиорежим видео ({e})")
        try:
            page.keyboard.press("Escape")
        except Exception:
            pass
        return False

def attach_reference_image(page, image_path: str) -> bool:
    """
    Прикрепляет изображение-референс в качестве ингредиента в строку запроса Google Flow.
    """
    resolved_path = Path(image_path).resolve()
    if not resolved_path.exists():
        raise FileNotFoundError(f"Файл референсного изображения не найден: {resolved_path}")

    filename = resolved_path.name
    print(f"[*] Прикрепление референса ({filename}): {resolved_path}")

    try:
        # Проверяем, не прикреплен ли уже ингредиент
        chips = page.locator("flow-image-ingredient-chip, flow-base-prompt-box img.chip-image, button.chip-container").all()
        for chip in chips:
            chip_text = chip.inner_text().strip() if hasattr(chip, "inner_text") else ""
            if filename.lower() in chip_text.lower():
                print(f"[+] Референс {filename} уже прикреплен в строке запроса.")
                return True

        # Открываем меню добавления ингредиентов
        add_btn = page.locator("flow-base-prompt-box button:has-text('add'), button[aria-label*='Добавить ингредиенты' i]").first
        if not add_btn.is_visible(timeout=2000):
            add_btn = page.locator("button:has(mat-icon:has-text('add'))").last

        add_btn.click()
        page.wait_for_timeout(800)

        # 1. Проверяем, загружен ли уже ассет с таким именем в проекте
        asset_item = page.locator(f"button.asset-item:has(span.asset-title:has-text('{filename}'))").first
        if asset_item.is_visible(timeout=1500):
            asset_item.click()
            page.wait_for_timeout(600)
            btn_add = page.locator("button:has-text('Добавить в запрос')").first
            if btn_add.is_visible(timeout=2000):
                btn_add.click()
                page.wait_for_timeout(600)
                page.keyboard.press("Escape")
                print(f"[+] Существующий ассет {filename} прикреплен к запросу.")
                return True

        # 2. Если файл еще не загружен — загружаем его через кнопку загрузки в popover
        upload_btn = page.locator("button[aria-label*='Загрузить' i], button:has-text('upload'), button:has(mat-icon:has-text('drive_folder_upload'))").first
        if upload_btn.is_visible(timeout=2000):
            with page.expect_file_chooser(timeout=5000) as fc:
                upload_btn.click()
            fc.value.set_files(str(resolved_path))
            print(f"[+] Файл {filename} передан в диалог загрузки Flow, ожидание обработки...")
            page.wait_for_timeout(3500)

            # Выбираем свежезагруженный ассет
            new_item = page.locator(f"button.asset-item:has(span.asset-title:has-text('{filename}'))").first
            if not new_item.is_visible(timeout=3000):
                new_item = page.locator("button.asset-item").first
            new_item.click()
            page.wait_for_timeout(600)

            btn_add = page.locator("button:has-text('Добавить в запрос')").first
            if btn_add.is_visible(timeout=2000):
                btn_add.click()
                page.wait_for_timeout(600)
                page.keyboard.press("Escape")
                print(f"[+] Файл {filename} успешно загружен и прикреплен к запросу.")
                return True

        page.keyboard.press("Escape")
    except Exception as e:
        print(f"[-] Ошибка прикрепления референса через UI: {e}")
        try:
            page.keyboard.press("Escape")
        except Exception:
            pass

    return False

def attach_end_frame(page, image_path: str) -> bool:
    """
    Прикрепляет конечное изображение (end frame) для Veo Frames-to-Video.
    """
    resolved_path = Path(image_path).resolve()
    if not resolved_path.exists():
        raise FileNotFoundError(f"Файл конечного кадра не найден: {resolved_path}")

    print(f"[*] Прикрепление конечного кадра (end frame): {resolved_path}")
    end_frame_selectors = [
        "button[aria-label*='end frame' i]",
        "button[aria-label*='конечный кадр' i]",
        "button[aria-label*='последний кадр' i]",
        "button:has-text('End frame')",
        "button:has-text('Конечный кадр')",
        "[data-testid*='end-frame' i]"
    ]
    for sel in end_frame_selectors:
        btn = page.locator(sel).first
        if btn.is_visible(timeout=800):
            try:
                with page.expect_file_chooser(timeout=3000) as fc_info:
                    btn.click()
                fc_info.value.set_files(str(resolved_path))
                return True
            except Exception:
                pass

    return False

def download_asset_via_browser(page, asset_url: str, dest_file: Path) -> bool:
    """
    Скачивает полноразмерный ассет из Flow напрямую через браузерный fetch.
    Передаются все session cookies, origins и auth-токены Google.
    """
    try:
        b64 = page.evaluate(f'''async () => {{
            const res = await fetch("{asset_url}");
            if (!res.ok) throw new Error("HTTP " + res.status);
            const blob = await res.blob();
            return new Promise((resolve) => {{
                const reader = new FileReader();
                reader.onloadend = () => resolve(reader.result);
                reader.readAsDataURL(blob);
            }});
        }}''')
        if b64 and ',' in b64:
            data = b64.split(',')[1]
            dest_file.write_bytes(base64.b64decode(data))
            return True
    except Exception as e:
        print(f"[-] Ошибка скачивания через браузер: {e}")
    return False

def upscale_image_fast_2k(source_path: Path, dest_path: Path) -> bool:
    """
    Выполняет мгновенный высококачественный 2K апскейл (2048x2048) через Lanczos
    с сохранением микротекстур и адаптивным фильтром резкости (UnsharpMask).
    Занимает 0.05 сек вместо минут CPU-вычислений.
    """
    if not HAS_PIL:
        shutil.copy2(str(source_path), str(dest_path))
        return False

    try:
        im = Image.open(source_path).convert('RGB')
        w, h = im.size
        target_w = max(w * 2, 2048)
        target_h = max(h * 2, 2048)

        # 1. Lanczos High-Fidelity Resampling
        up = im.resize((target_w, target_h), Image.Resampling.LANCZOS)

        # 2. Subtle edge sharpening to maintain crisp micro-details
        up_sharp = up.filter(ImageFilter.UnsharpMask(radius=1.2, percent=110, threshold=3))

        up_sharp.save(dest_path, quality=98)
        return True
    except Exception as e:
        print(f"[-] Ошибка 2K апскейла через PIL: {e}")
        shutil.copy2(str(source_path), str(dest_path))
        return False

def select_tile_for_editing(page, tile_index: int = -1) -> bool:
    """
    Выбирает ранее сгенерированный тайл для внесения правок / создания вариации.
    """
    tiles = page.locator("flow-media-tile, .thumbnail-image, .read-only-image, [class*='tile']").all()
    if not tiles:
        raise RuntimeError("В проекте Google Flow нет плиток для редактирования.")

    try:
        target_tile = tiles[tile_index]
    except IndexError:
        target_tile = tiles[-1]

    print(f"[*] Выбор плитки для редактирования (индекс: {tile_index})...")
    target_tile.scroll_into_view_if_needed()
    target_tile.hover()

    edit_selectors = [
        "button:has-text('Редактировать')",
        "button:has-text('Edit')",
        "button:has-text('Вариация')",
        "button[aria-label*='edit' i]",
        "button[aria-label*='редактировать' i]",
        "button[aria-label*='вариац' i]"
    ]

    for sel in edit_selectors:
        btn = target_tile.locator(sel).first
        if not btn.is_visible(timeout=400):
            btn = page.locator(sel).first
        if btn.is_visible(timeout=400):
            btn.click()
            print(f"[+] Плитка выбрана через: {sel}")
            return True

    return False

def generate_flow_media(
    prompt: str,
    output_dir: str = None,
    media_type: str = "image",
    reference_image: str = None,
    aspect_ratio: str = None,
    camera_motion: str = None,
    batch_count: int = 1,
    mute_audio: bool = False,
    expand_prompt_flag: bool = False,
    upscale_2k: bool = False,
    edit_tile_index: int = None,
    model_name: str = "nano_banana_2.1",
    timeout_sec: int = 90
) -> Dict[str, Any]:
    """
    Основной пайплайн генерации медиа (изображения или видео) в Google Flow.
    """
    out_path = Path(output_dir).resolve() if output_dir else Path.cwd() / "outputs"
    out_path.mkdir(parents=True, exist_ok=True)

    effective_prompt = expand_prompt(
        base_prompt=prompt,
        media_type=media_type,
        camera_motion=camera_motion,
        aspect_ratio=aspect_ratio
    ) if expand_prompt_flag else prompt.strip()

    print(f"\n[*] Google Flow Generation Pipeline: media_type='{media_type}'")
    print(f"[*] Prompt: {effective_prompt}")

    with sync_playwright() as p:
        context, browser, is_headless = get_flow_context(p)

        try:
            page = get_or_create_page(context)
            if not ensure_in_project(page):
                raise RuntimeError("Не удалось открыть проектную область Google Flow.")

            ensure_media_mode(page, media_type=media_type)

            if model_name:
                set_model_family(page, model_name=model_name)

            if aspect_ratio:
                set_aspect_ratio(page, aspect_ratio=aspect_ratio)

            if media_type == "image" and batch_count > 1:
                set_batch_count(page, batch_count=batch_count)

            if media_type == "video":
                set_video_audio_mode(page, mute_audio=mute_audio)

            if edit_tile_index is not None:
                select_tile_for_editing(page, tile_index=edit_tile_index)

            if reference_image:
                attach_reference_image(page, reference_image)

            # Фиксируем существующие изображения на странице до генерации
            before_urls = page.evaluate('''() => {
                return Array.from(document.querySelectorAll('img')).map(i => i.src);
            }''')

            # Ввод промпта в текстовую область ProseMirror
            textbox = page.locator("div.ProseMirror[role='textbox'], div.ProseMirror, [contenteditable='true']").first
            if not textbox.is_visible(timeout=5000):
                raise RuntimeError("Поле ввода ProseMirror не найдено.")

            textbox.click()
            page.keyboard.press("Control+A")
            page.keyboard.press("Backspace")
            page.wait_for_timeout(200)
            textbox.fill(effective_prompt)
            page.wait_for_timeout(400)

            # Нажатие кнопки генерации
            submit_selectors = [
                "button[aria-label*='Начать генерацию' i]",
                "button:has(mat-icon:has-text('arrow_forward'))",
                "button[type='submit']",
                "button:has-text('Generate')",
                "button:has-text('Создать')"
            ]
            submit_btn = None
            for sel in submit_selectors:
                btn = page.locator(sel).last
                if btn.is_visible(timeout=500) and not btn.is_disabled():
                    submit_btn = btn
                    break

            if not submit_btn:
                raise RuntimeError("Кнопка запуска генерации недоступна.")

            submit_btn.click()
            print("[*] Запрос отправлен в Google Flow, ожидание генерации...")

            elapsed = 0
            poll_interval = 2000
            new_assets = []

            while elapsed < (timeout_sec * 1000):
                page.wait_for_timeout(poll_interval)
                elapsed += poll_interval

                after_imgs = page.evaluate('''() => {
                    return Array.from(document.querySelectorAll('img')).map(i => ({
                        src: i.src,
                        w: i.naturalWidth,
                        h: i.naturalHeight
                    }));
                }''')

                # Ищем новые изображения (приоритет полноразмерным flow-content.google)
                full_res_diff = [
                    im['src'] for im in after_imgs
                    if im['src'] not in before_urls and 'flow-content.google/image' in im['src']
                ]
                if full_res_diff:
                    new_assets = full_res_diff
                    if len(new_assets) >= batch_count or elapsed >= (timeout_sec * 800):
                        print(f"\n[+] Обнаружен полноразмерный ассет ({len(new_assets)} шт.)!")
                        break

                # Запасной вариант: /asb/ ассеты
                asb_diff = [
                    im['src'] for im in after_imgs
                    if im['src'] not in before_urls and '/asb/' in im['src']
                ]
                if asb_diff:
                    new_assets = asb_diff
                    if len(new_assets) >= batch_count or elapsed >= (timeout_sec * 800):
                        print(f"\n[+] Обнаружен новый ассет Flow ({len(new_assets)} шт.)!")
                        break

                sys.stdout.write(".")
                sys.stdout.flush()

            if not new_assets:
                raise TimeoutError(f"Ассеты не были сгенерированы в течение {timeout_sec} сек.")

            saved_files = []
            timestamp = int(time.time())

            for idx, asset_url in enumerate(new_assets, 1):
                is_video = "video" in asset_url or media_type == "video"
                ext = ".mp4" if is_video else ".png"

                # Базовый файл оригинального разрешения Flow (1024x1024)
                base_dest = out_path / f"flow_{timestamp}_{idx}{ext}"
                ok = download_asset_via_browser(page, asset_url, base_dest)
                if ok and base_dest.exists() and base_dest.stat().st_size > 0:
                    saved_files.append(str(base_dest))
                    print(f"[SAVED] {base_dest} ({base_dest.stat().st_size} bytes)")

                    # Если запрошен 2K апскейл — создаем 2048x2048 версию мгновенно через Lanczos
                    if upscale_2k and not is_video:
                        dest_2k = out_path / f"flow_2k_{timestamp}_{idx}{ext}"
                        if upscale_image_fast_2k(base_dest, dest_2k):
                            saved_files.append(str(dest_2k))
                            print(f"[SAVED 2K] {dest_2k} (2048x2048)")

            return {
                "success": len(saved_files) > 0,
                "mode": "headless" if is_headless else "cdp",
                "media_type": media_type,
                "model_name": model_name,
                "prompt": effective_prompt,
                "original_prompt": prompt,
                "reference_image": reference_image,
                "aspect_ratio": aspect_ratio,
                "camera_motion": camera_motion,
                "batch_count": batch_count,
                "mute_audio": mute_audio,
                "upscale_2k": upscale_2k,
                "files": saved_files,
                "count": len(saved_files)
            }
        finally:
            if context and not is_cdp_available():
                context.close()
            if browser:
                browser.close()

def generate_frames_to_video(
    start_frame: str,
    end_frame: str,
    prompt: str = "",
    aspect_ratio: str = None,
    output_dir: str = None,
    timeout_sec: int = 180
) -> Dict[str, Any]:
    """
    Генерирует видео через Veo с анимацией между начальным и конечным изображением (Frames to Video).
    """
    out_path = Path(output_dir).resolve() if output_dir else Path.cwd() / "outputs"
    out_path.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        context, browser, is_headless = get_flow_context(p)

        try:
            page = get_or_create_page(context)
            if not ensure_in_project(page):
                raise RuntimeError("Не удалось открыть проектную область Google Flow.")

            ensure_media_mode(page, media_type="video")
            if aspect_ratio:
                set_aspect_ratio(page, aspect_ratio=aspect_ratio)

            attach_reference_image(page, start_frame)
            attach_end_frame(page, end_frame)

            before_videos = page.evaluate('''() => {
                return Array.from(document.querySelectorAll('video')).map(v => v.src);
            }''')

            effective_prompt = prompt.strip() if prompt.strip() else "Smooth cinematic transition between start and end frames"

            textbox = page.locator("div.ProseMirror[role='textbox'], div.ProseMirror, [contenteditable='true']").first
            if textbox.is_visible(timeout=5000):
                textbox.click()
                page.keyboard.press("Control+A")
                page.keyboard.press("Backspace")
                textbox.fill(effective_prompt)

            submit_btn = page.locator("button[aria-label*='Начать генерацию' i], button:has(mat-icon:has-text('arrow_forward'))").last
            if submit_btn.is_visible(timeout=2000) and not submit_btn.is_disabled():
                submit_btn.click()

            elapsed = 0
            poll_interval = 3000
            new_assets = []
            while elapsed < (timeout_sec * 1000):
                page.wait_for_timeout(poll_interval)
                elapsed += poll_interval
                after_videos = page.evaluate('''() => {
                    return Array.from(document.querySelectorAll('video')).map(v => v.src);
                }''')
                diff = [v for v in after_videos if v not in before_videos and v]
                if diff:
                    new_assets = diff
                    break

            if not new_assets:
                raise TimeoutError(f"Frames-to-Video не было сгенерировано за {timeout_sec} сек.")

            saved_files = []
            timestamp = int(time.time())
            for idx, asset_url in enumerate(new_assets, 1):
                dest_file = out_path / f"flow_f2v_{timestamp}_{idx}.mp4"
                ok = download_asset_via_browser(page, asset_url, dest_file)
                if ok and dest_file.exists():
                    saved_files.append(str(dest_file))

            return {
                "success": len(saved_files) > 0,
                "mode": "headless" if is_headless else "cdp",
                "action": "frames_to_video",
                "start_frame": start_frame,
                "end_frame": end_frame,
                "prompt": effective_prompt,
                "files": saved_files,
                "count": len(saved_files)
            }
        finally:
            if context and not is_cdp_available():
                context.close()
            if browser:
                browser.close()

def extend_flow_video(
    tile_index: int = -1,
    prompt: str = "",
    output_dir: str = None,
    timeout_sec: int = 180
) -> Dict[str, Any]:
    """
    Продлевает ранее сгенерированное видео в Google Flow на 5-8 секунд.
    """
    out_path = Path(output_dir).resolve() if output_dir else Path.cwd() / "outputs"
    out_path.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        context, browser, is_headless = get_flow_context(p)

        try:
            page = get_or_create_page(context)
            if not ensure_in_project(page):
                raise RuntimeError("Не удалось открыть проектную область Google Flow.")

            tiles = page.locator("flow-media-tile, video, [class*='tile']").all()
            if not tiles:
                raise RuntimeError("В проекте нет видео для продления.")

            try:
                target_tile = tiles[tile_index]
            except IndexError:
                target_tile = tiles[-1]

            target_tile.scroll_into_view_if_needed()
            target_tile.hover()

            extend_selectors = [
                "button[aria-label*='extend' i]",
                "button[aria-label*='продлить' i]",
                "button:has-text('Extend')",
                "button:has-text('Продлить')",
            ]

            extend_btn = None
            for sel in extend_selectors:
                btn = target_tile.locator(sel).first
                if not btn.is_visible(timeout=400):
                    btn = page.locator(sel).first
                if btn.is_visible(timeout=400):
                    extend_btn = btn
                    break

            if not extend_btn:
                raise RuntimeError("Кнопка 'Extend / Продлить' не найдена для выбранного видео.")

            extend_btn.click()

            if prompt.strip():
                textbox = page.locator("div.ProseMirror[role='textbox'], div.ProseMirror, [contenteditable='true']").first
                if textbox.is_visible(timeout=3000):
                    textbox.click()
                    textbox.fill(prompt)

            submit_btn = page.locator("button[aria-label*='Начать генерацию' i], button:has(mat-icon:has-text('arrow_forward'))").last
            if submit_btn.is_visible(timeout=2000) and not submit_btn.is_disabled():
                submit_btn.click()

            before_videos = page.evaluate('''() => {
                return Array.from(document.querySelectorAll('video')).map(v => v.src);
            }''')

            elapsed = 0
            poll_interval = 3000
            new_assets = []
            while elapsed < (timeout_sec * 1000):
                page.wait_for_timeout(poll_interval)
                elapsed += poll_interval
                after_videos = page.evaluate('''() => {
                    return Array.from(document.querySelectorAll('video')).map(v => v.src);
                }''')
                diff = [v for v in after_videos if v not in before_videos and v]
                if diff:
                    new_assets = diff
                    break

            if not new_assets:
                raise TimeoutError(f"Продленное видео не было сгенерировано за {timeout_sec} сек.")

            saved_files = []
            timestamp = int(time.time())
            for idx, asset_url in enumerate(new_assets, 1):
                dest_file = out_path / f"flow_extended_{timestamp}_{idx}.mp4"
                ok = download_asset_via_browser(page, asset_url, dest_file)
                if ok and dest_file.exists():
                    saved_files.append(str(dest_file))

            return {
                "success": len(saved_files) > 0,
                "mode": "headless" if is_headless else "cdp",
                "action": "video_extend",
                "tile_index": tile_index,
                "prompt": prompt,
                "files": saved_files,
                "count": len(saved_files)
            }
        finally:
            if context and not is_cdp_available():
                context.close()
            if browser:
                browser.close()

def upscale_flow_image(
    tile_index: int = -1,
    output_dir: str = None,
    timeout_sec: int = 90
) -> Dict[str, Any]:
    """
    Масштабирует выбранное изображение из Google Flow до 2K (2048x2048).
    Скачивает полноразмерный исходник из Flow и применяет мгновенный Lanczos-апскейл.
    """
    out_path = Path(output_dir).resolve() if output_dir else Path.cwd() / "outputs"
    out_path.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        context, browser, is_headless = get_flow_context(p)

        try:
            page = get_or_create_page(context)
            if not ensure_in_project(page):
                raise RuntimeError("Не удалось открыть проектную область Google Flow.")

            # Собираем все изображения на странице
            imgs = page.evaluate('''() => {
                return Array.from(document.querySelectorAll('img'))
                    .filter(i => i.src.includes('flow-content.google') || i.src.includes('/asb/'))
                    .map(i => i.src);
            }''')

            if not imgs:
                raise RuntimeError("В проекте Google Flow нет доступных изображений для апскейла.")

            try:
                target_url = imgs[tile_index]
            except IndexError:
                target_url = imgs[-1]

            timestamp = int(time.time())
            temp_file = out_path / f"flow_source_{timestamp}.png"
            dest_file = out_path / f"flow_2k_{timestamp}.png"

            ok = download_asset_via_browser(page, target_url, temp_file)
            if not ok or not temp_file.exists():
                raise RuntimeError("Не удалось скачать исходное изображение из Google Flow.")

            # Мгновенный 2K апскейл
            upscale_image_fast_2k(temp_file, dest_file)

            # Удаляем временный файл источника, если целевой 2K готов
            if dest_file.exists() and dest_file.stat().st_size > 0:
                try:
                    temp_file.unlink()
                except Exception:
                    pass

            return {
                "success": True,
                "mode": "headless" if is_headless else "cdp",
                "action": "upscale_2k",
                "tile_index": tile_index,
                "files": [str(dest_file)],
                "count": 1
            }
        finally:
            if context and not is_cdp_available():
                context.close()
            if browser:
                browser.close()

def edit_flow_image(
    prompt: str,
    tile_index: int = -1,
    reference_image: str = None,
    aspect_ratio: str = None,
    upscale_2k: bool = False,
    output_dir: str = None,
    model_name: str = "nano_banana_2.1",
    timeout_sec: int = 90
) -> Dict[str, Any]:
    """
    Вносит правки в существующее изображение или генерирует вариацию на основе промпта и референса.
    """
    return generate_flow_media(
        prompt=prompt,
        output_dir=output_dir,
        media_type="image",
        reference_image=reference_image,
        aspect_ratio=aspect_ratio,
        upscale_2k=upscale_2k,
        edit_tile_index=tile_index if not reference_image else None,
        model_name=model_name,
        timeout_sec=timeout_sec
    )

def finalize_asset(
    target_path: str,
    source_file: Optional[str] = None,
    tile_index: int = -1,
    upscale_2k: bool = True,
    timeout_sec: int = 90
) -> Dict[str, Any]:
    """
    Финализирует выбранный медиа-ассет (Шаг 3 Staging Pipeline):
    1. Если запрошен upscale_2k для изображения — выполняет быстрый 2K-апскейл.
    2. Атомарно перемещает / сохраняет файл в проектную папку target_path.
    3. Защищен от SameFileError при перезаписи по тому же пути.
    4. Возвращает готовые ссылки (абсолютный путь, относительный путь и markdown).
    """
    resolved_target = Path(target_path).resolve()
    resolved_target.parent.mkdir(parents=True, exist_ok=True)

    is_video = resolved_target.suffix.lower() in [".mp4", ".webm", ".mov"] or (source_file and Path(source_file).suffix.lower() in [".mp4", ".webm"])
    is_2k_applied = False
    chosen_source = None

    # Сценарий 1: Если указан source_file и запрошен 2K
    if source_file and Path(source_file).exists():
        src_path = Path(source_file).resolve()
        if upscale_2k and not is_video:
            if upscale_image_fast_2k(src_path, resolved_target):
                chosen_source = resolved_target
                is_2k_applied = True
        else:
            if resolved_target != src_path:
                shutil.copy2(str(src_path), str(resolved_target))
            chosen_source = resolved_target

    # Сценарий 2: Если source_file не указан, но указан tile_index для Flow
    elif tile_index is not None and not is_video:
        try:
            with tempfile.TemporaryDirectory() as tmp_upscale_dir:
                upscale_res = upscale_flow_image(
                    tile_index=tile_index,
                    output_dir=tmp_upscale_dir,
                    timeout_sec=timeout_sec
                )
                if upscale_res.get("success") and upscale_res.get("files"):
                    tmp_file = Path(upscale_res["files"][0])
                    if tmp_file.exists():
                        shutil.copy2(str(tmp_file), str(resolved_target))
                        chosen_source = resolved_target
                        is_2k_applied = True
        except Exception as e:
            print(f"[-] Апскейл тайла Flow не удался ({e})")

    if not chosen_source and not resolved_target.exists():
        raise FileNotFoundError(
            f"Не удалось найти источник медиа для финализации (source_file={source_file}, tile_index={tile_index})."
        )

    if not resolved_target.exists() or resolved_target.stat().st_size == 0:
        raise IOError(f"Ошибка сохранения файла по пути: {resolved_target}")

    try:
        relative_path = str(resolved_target.relative_to(Path.cwd())).replace("\\", "/")
    except ValueError:
        relative_path = str(resolved_target.name)

    normalized_uri = resolved_target.as_posix()
    markdown_link = f"![{resolved_target.name}](file:///{normalized_uri})"

    return {
        "success": True,
        "target_path": str(resolved_target),
        "relative_path": relative_path,
        "markdown_link": markdown_link,
        "is_2k": is_2k_applied,
        "file_size_bytes": resolved_target.stat().st_size,
        "media_type": "video" if is_video else "image",
        "message": f"Ассет успешно финализирован в {resolved_target}"
    }

def regenerate_flow_tile(
    tile_index: int = -1,
    output_dir: Optional[str] = None,
    timeout_sec: int = 90
) -> Dict[str, Any]:
    """
    Перезапускает генерацию существующей плитки на холсте Google Flow ('Сгенерировать повторно').
    """
    out_path = Path(output_dir).resolve() if output_dir else Path.cwd() / "outputs"
    out_path.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        context, browser, is_headless = get_flow_context(p)
        try:
            page = get_or_create_page(context)
            if not ensure_in_project(page):
                raise RuntimeError("Не удалось открыть проектную область Google Flow.")

            before_urls = page.evaluate('''() => {
                return Array.from(document.querySelectorAll('img')).map(i => i.src);
            }''')

            regen_buttons = page.locator("button[aria-label='Сгенерировать повторно']").all()
            if not regen_buttons:
                raise RuntimeError("Кнопки 'Сгенерировать повторно' не найдены на холсте.")

            idx = len(regen_buttons) - 1 if tile_index < 0 else min(tile_index, len(regen_buttons) - 1)
            target_btn = regen_buttons[idx]
            target_btn.click()
            print(f"[*] Запущен повтор генерации плитки {idx}...")

            elapsed = 0
            poll_interval = 2000
            new_assets = []
            while elapsed < (timeout_sec * 1000):
                page.wait_for_timeout(poll_interval)
                elapsed += poll_interval
                after_imgs = page.evaluate('''() => {
                    return Array.from(document.querySelectorAll('img')).map(i => i.src);
                }''')
                diff = [src for src in after_imgs if src not in before_urls and ('flow-content.google' in src or '/asb/' in src)]
                if diff:
                    new_assets = diff
                    break
                sys.stdout.write(".")
                sys.stdout.flush()

            if not new_assets:
                raise TimeoutError(f"Повторная генерация не завершилась за {timeout_sec} сек.")

            saved_files = []
            timestamp = int(time.time())
            for i, asset_url in enumerate(new_assets, 1):
                dest = out_path / f"flow_regen_{timestamp}_{i}.png"
                if download_asset_via_browser(page, asset_url, dest):
                    saved_files.append(str(dest))

            return {
                "success": len(saved_files) > 0,
                "files": saved_files,
                "tile_index": idx,
                "markdown_embed": f"![regen]({Path(saved_files[0]).as_uri()})" if saved_files else ""
            }
        finally:
            if context and not is_cdp_available():
                context.close()
            if browser:
                browser.close()

def list_flow_projects() -> List[Dict[str, Any]]:
    """
    Получает список существующих проектов пользователя в Google Flow.
    """
    with sync_playwright() as p:
        context, browser, is_headless = get_flow_context(p)
        try:
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(FLOW_URL, wait_until="domcontentloaded", timeout=25000)
            page.wait_for_timeout(3000)

            projects = page.evaluate('''() => {
                const links = Array.from(document.querySelectorAll('a[href*="/project/"]'));
                const seen = new Set();
                const result = [];
                for (const a of links) {
                    const href = a.getAttribute('href') || '';
                    const match = href.match(/\\/project\\/([a-zA-Z0-9_-]+)/);
                    if (match && !seen.has(match[1])) {
                        seen.add(match[1]);
                        const card = a.closest('.project-card, mat-card, div') || a;
                        const titleEl = card.querySelector('h2, h3, .project-title, .title') || a;
                        const title = (titleEl.innerText || a.getAttribute('aria-label') || 'Без названия').trim();
                        result.push({
                            id: match[1],
                            title: title,
                            url: 'https://flow.google.com' + href
                        });
                    }
                }
                return result;
            }''')
            return projects
        finally:
            if context and not is_cdp_available():
                context.close()
            if browser:
                browser.close()

def create_flow_project(name: str = "") -> Dict[str, Any]:
    """
    Создает новый изолированный проект в Google Flow и возвращает его ID и URL.
    """
    with sync_playwright() as p:
        context, browser, is_headless = get_flow_context(p)
        try:
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(FLOW_URL, wait_until="domcontentloaded", timeout=25000)
            page.wait_for_timeout(2500)

            new_btn = page.locator("button:has-text('Новый проект'), [aria-label*='Новый проект' i], button.new-project-btn").first
            if not new_btn.is_visible(timeout=3000):
                raise RuntimeError("Кнопка 'Новый проект' не найдена на главной странице Flow.")

            new_btn.click()
            page.wait_for_url("**/project/**", timeout=12000)
            page.wait_for_timeout(2000)

            url = page.url
            proj_id = url.split("/project/")[-1].split("?")[0].split("/")[0]

            if name:
                try:
                    title_input = page.locator("input.project-name-input, [aria-label*='Название проекта' i]").first
                    if title_input.is_visible(timeout=1500):
                        title_input.click()
                        page.keyboard.press("Control+A")
                        title_input.fill(name)
                        page.keyboard.press("Enter")
                        page.wait_for_timeout(500)
                except Exception:
                    pass

            return {
                "success": True,
                "project_id": proj_id,
                "url": url,
                "name": name if name else "Новый проект"
            }
        finally:
            if context and not is_cdp_available():
                context.close()
            if browser:
                browser.close()
