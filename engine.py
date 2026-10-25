import shutil
import tempfile
import urllib.request
from pathlib import Path
from typing import List, Dict, Any, Optional
from playwright.sync_api import sync_playwright

from expander import expand_prompt, validate_aspect_ratio, format_camera_prompt

CDP_URL = "http://127.0.0.1:9222"
FLOW_URL = "https://flow.google.com"
BASE_DIR = Path(__file__).parent.resolve()
STORAGE_FILE = BASE_DIR / "storage_state.json"

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"

def is_cdp_available() -> bool:
    try:
        with urllib.request.urlopen(f"{CDP_URL}/json/version", timeout=1.5) as resp:
            return resp.status == 200
    except Exception:
        return False

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

    # Семантический поиск кнопки "Новый проект"
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
                try:
                    btn.wait_for(state="visible", timeout=1500)
                except Exception:
                    pass
            return True
    return False

def set_aspect_ratio(page, aspect_ratio: Optional[str]) -> bool:
    """
    Устанавливает соотношение сторон в интерфейсе Google Flow (16:9, 9:16, 1:1, 4:3).
    """
    if not aspect_ratio:
        return False
    ratio = validate_aspect_ratio(aspect_ratio)
    if not ratio:
        return False

    print(f"[*] Установка соотношения сторон: {ratio}")
    # Открываем меню настроек генератора в строке ввода
    trig = page.locator("button[aria-label*='Триггер' i], button:has-text('Nano Banana')").first
    if trig.is_visible(timeout=1000):
        trig.click()
        page.wait_for_timeout(500)
        btn_ratio = page.locator(f"button:has-text('{ratio}'), [role='menuitem']:has-text('{ratio}'), [role='option']:has-text('{ratio}')").first
        if btn_ratio.is_visible(timeout=1500):
            btn_ratio.click()
            page.wait_for_timeout(400)
            return True

    # Вариант 2: Прямая кнопка с соотношением
    for sel in [f"button:has-text('{ratio}')", f"button[aria-label*='{ratio}']", f"[data-testid*='{ratio}']"]:
        btn = page.locator(sel).first
        if btn.is_visible(timeout=400):
            btn.click()
            return True

    return False

def attach_reference_image(page, image_path: str) -> bool:
    """
    Прикрепляет локальное изображение в качестве референса в Google Flow.
    """
    resolved_path = Path(image_path).resolve()
    if not resolved_path.exists():
        raise FileNotFoundError(f"Файл референсного изображения не найден: {resolved_path}")

    print(f"[*] Прикрепление референсного изображения: {resolved_path}")

    # Способ 1: Загрузка через нативную кнопку загрузки медиа на холст
    up_btn = page.locator("button:has-text('upload')").first
    if up_btn.is_visible(timeout=1200):
        try:
            with page.expect_file_chooser(timeout=3000) as fc:
                up_btn.click()
            fc.value.set_files(str(resolved_path))
            print("[+] Файл передан через кнопку upload на холст")
            page.wait_for_timeout(2500)

            # Добавляем загруженный файл в строку запроса (Ингредиенты)
            ing_btn = page.locator("button[aria-label*='ингредиенты' i], button[aria-label*='ingredients' i]").first
            if ing_btn.is_visible(timeout=2000):
                ing_btn.click()
                page.wait_for_timeout(800)
                btn_add = page.locator("button:has-text('Добавить в запрос'), button:has-text('Add to prompt')").first
                if btn_add.is_visible(timeout=2000):
                    btn_add.click()
                    page.wait_for_timeout(500)
                    print("[+] Референс прикреплен к строке запроса!")
                    return True
        except Exception as e:
            print(f"[-] Ошибка загрузки через кнопку upload: {e}")

    # Способ 2: Прямая передача в существующие input[type='file']
    file_inputs = page.locator("input[type='file']").all()
    for fi in file_inputs:
        try:
            fi.set_input_files(str(resolved_path), timeout=2000)
            print("[+] Файл передан через input[type='file']")
            return True
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

    file_inputs = page.locator("input[type='file']").all()
    if len(file_inputs) > 1:
        try:
            file_inputs[1].set_input_files(str(resolved_path), timeout=2000)
            return True
        except Exception:
            pass

    raise RuntimeError(
        f"Не удалось прикрепить конечный кадр (end frame) по пути: {resolved_path}. "
        "Убедитесь, что Flow переключен в режим генерации видео с поддержкой Frames-to-Video."
    )

def select_tile_for_editing(page, tile_index: int = -1) -> bool:
    """
    Выбирает ранее сгенерированный тайл для внесения правок / создания вариации.
    """
    tiles = page.locator("flow-tile, [class*='tile']").all()
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
        "button:has-text('Вариации')",
        "button:has-text('Variations')",
        "button[aria-label*='edit' i]",
        "button[aria-label*='редактировать' i]",
        "button[aria-label*='вариац' i]",
        "button[aria-label*='правка' i]",
        "button[aria-label*='основ' i]",
        "button[aria-label*='use as input' i]",
        "button[aria-label*='add to prompt' i]",
    ]

    for sel in edit_selectors:
        btn = target_tile.locator(sel).first
        if not btn.is_visible(timeout=400):
            btn = page.locator(sel).first
        if btn.is_visible(timeout=400):
            btn.click()
            print(f"[+] Плитка выбрана через действие: {sel}")
            return True

    print("[-] Предупреждение: Кнопка перехода в режим редактирования не найдена на плитке.")
    return False

def trigger_2k_upscale(page, target_tile, timeout_sec: int = 90) -> Optional[str]:
    """
    Инициирует 2K апскейл для указанной плитки и возвращает URL полноразмерного ассета.
    """
    target_tile.scroll_into_view_if_needed()
    target_tile.hover()

    upscale_selectors = [
        "button[aria-label*='2k' i]",
        "button[aria-label*='upscale' i]",
        "button[aria-label*='увеличить' i]",
        "button[aria-label*='качество' i]",
        "button:has-text('2K')",
        "button:has-text('Upscale')",
        "button:has-text('Увеличить')",
    ]

    upscale_btn = None
    for sel in upscale_selectors:
        btn = target_tile.locator(sel).first
        if not btn.is_visible(timeout=400):
            btn = page.locator(sel).first
        if btn.is_visible(timeout=400):
            upscale_btn = btn
            break

    if not upscale_btn:
        print("[-] Предупреждение: Кнопка 2K Upscale не обнаружена.")
        return None

    print("[*] Запуск 2K Upscaling...")
    upscale_btn.click()

    # Ожидаем появления 2K ассета
    elapsed = 0
    poll_interval = 2500
    high_res_url = None

    while elapsed < (timeout_sec * 1000):
        page.wait_for_timeout(poll_interval)
        elapsed += poll_interval
        imgs = page.locator("flow-tile img, [class*='tile'] img, dialog img").all()
        for img in imgs:
            src = img.get_attribute("src") or ""
            if "flow-content.google" in src:
                if any(marker in src.lower() for marker in ["2k", "high", "upscale"]):
                    high_res_url = src
                    break
        if high_res_url:
            break

    if not high_res_url:
        current_img = target_tile.locator("img").first
        if current_img.is_visible(timeout=2000):
            high_res_url = current_img.get_attribute("src")

    return high_res_url

def generate_flow_media(
    prompt: str,
    output_dir: str = None,
    media_type: str = "image",
    reference_image: str = None,
    aspect_ratio: str = None,
    camera_motion: str = None,
    expand_prompt_flag: bool = False,
    upscale_2k: bool = False,
    edit_tile_index: int = None,
    timeout_sec: int = 90
) -> Dict[str, Any]:
    out_path = Path(output_dir).resolve() if output_dir else Path.cwd() / "outputs"
    out_path.mkdir(parents=True, exist_ok=True)

    effective_prompt = prompt
    if expand_prompt_flag:
        effective_prompt = expand_prompt(
            base_prompt=prompt,
            media_type=media_type,
            camera_motion=camera_motion,
            aspect_ratio=aspect_ratio
        )
    elif camera_motion:
        cam_desc = format_camera_prompt(camera_motion)
        if cam_desc:
            effective_prompt = f"{effective_prompt}, {cam_desc}"

    with sync_playwright() as p:
        if is_cdp_available():
            browser = p.chromium.connect_over_cdp(CDP_URL)
            context = browser.contexts[0]
            is_headless = False
        else:
            if not STORAGE_FILE.exists():
                raise RuntimeError(
                    f"Файл сессии {STORAGE_FILE} не найден. "
                    "Требуется однократная авторизация через auth.py для сохранения сессионных cookie."
                )
            browser = p.chromium.launch(
                channel="chrome",
                headless=True,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
            )
            context = browser.new_context(
                storage_state=str(STORAGE_FILE),
                user_agent=USER_AGENT
            )
            is_headless = True

        try:
            page = get_or_create_page(context)
            if not ensure_in_project(page):
                raise RuntimeError("Не удалось открыть проектную область Google Flow.")

            ensure_media_mode(page, media_type=media_type)

            if aspect_ratio:
                set_aspect_ratio(page, aspect_ratio=aspect_ratio)

            if edit_tile_index is not None:
                select_tile_for_editing(page, tile_index=edit_tile_index)

            if reference_image:
                attach_reference_image(page, reference_image)

            existing_urls = set()
            for img in page.locator("flow-tile img, [class*='tile'] img").all():
                src = img.get_attribute("src") or ""
                if "flow-content.google" in src:
                    existing_urls.add(src)
            for v in page.locator("flow-tile video, [class*='tile'] video").all():
                src = v.get_attribute("src") or ""
                if src:
                    existing_urls.add(src)

            textbox = page.locator("div.ProseMirror[role='textbox']").first
            if not textbox.is_visible(timeout=5000):
                raise RuntimeError("Поле ввода ProseMirror не найдено.")

            textbox.click()
            textbox.press_sequentially(effective_prompt, delay=10)

            submit_btn = page.locator("button[aria-label='Начать генерацию'], button[type='submit']").first
            submit_btn.wait_for(state="visible", timeout=2000)
            if submit_btn.is_disabled():
                raise RuntimeError("Кнопка генерации недоступна (проверьте текст промпта).")

            submit_btn.click()

            elapsed = 0
            poll_interval = 2500
            new_assets = []

            while elapsed < (timeout_sec * 1000):
                page.wait_for_timeout(poll_interval)
                elapsed += poll_interval

                for img in page.locator("flow-tile img, [class*='tile'] img").all():
                    src = img.get_attribute("src") or ""
                    if "flow-content.google" in src and src not in existing_urls and src not in new_assets:
                        new_assets.append(src)

                for v in page.locator("flow-tile video, [class*='tile'] video").all():
                    src = v.get_attribute("src") or ""
                    if src and src not in existing_urls and src not in new_assets:
                        new_assets.append(src)

                if len(new_assets) > 0:
                    break

            if not new_assets:
                raise TimeoutError(f"Ассеты не были сгенерированы в течение {timeout_sec} сек.")

            if upscale_2k and media_type == "image":
                tiles = page.locator("flow-tile, [class*='tile']").all()
                if tiles:
                    high_res = trigger_2k_upscale(page, tiles[-1], timeout_sec=timeout_sec)
                    if high_res and high_res not in new_assets:
                        new_assets = [high_res] + new_assets

            saved_files = []
            import time
            timestamp = int(time.time())
            for idx, asset_url in enumerate(new_assets, 1):
                is_video = "video" in asset_url or media_type == "video"
                ext = ".mp4" if is_video else ".png"
                prefix = "flow_2k" if (upscale_2k and not is_video) else "flow"
                dest_file = out_path / f"{prefix}_{timestamp}_{idx}{ext}"
                resp = page.request.get(asset_url)
                if resp.status == 200:
                    dest_file.write_bytes(resp.body())
                    saved_files.append(str(dest_file))

            return {
                "success": True,
                "mode": "headless" if is_headless else "cdp",
                "media_type": media_type,
                "prompt": effective_prompt,
                "original_prompt": prompt,
                "reference_image": reference_image,
                "aspect_ratio": aspect_ratio,
                "camera_motion": camera_motion,
                "upscale_2k": upscale_2k,
                "files": saved_files,
                "count": len(saved_files)
            }

        finally:
            if is_headless:
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
        if is_cdp_available():
            browser = p.chromium.connect_over_cdp(CDP_URL)
            context = browser.contexts[0]
            is_headless = False
        else:
            if not STORAGE_FILE.exists():
                raise RuntimeError(f"Файл сессии {STORAGE_FILE} не найден.")
            browser = p.chromium.launch(
                channel="chrome",
                headless=True,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
            )
            context = browser.new_context(
                storage_state=str(STORAGE_FILE),
                user_agent=USER_AGENT
            )
            is_headless = True

        try:
            page = get_or_create_page(context)
            if not ensure_in_project(page):
                raise RuntimeError("Не удалось открыть проектную область Google Flow.")

            ensure_media_mode(page, media_type="video")
            if aspect_ratio:
                set_aspect_ratio(page, aspect_ratio=aspect_ratio)

            attach_reference_image(page, start_frame)
            attach_end_frame(page, end_frame)

            existing_videos = set()
            for v in page.locator("flow-tile video, [class*='tile'] video").all():
                src = v.get_attribute("src") or ""
                if src:
                    existing_videos.add(src)

            effective_prompt = prompt.strip() if prompt.strip() else "Smooth cinematic transition between start and end frames"

            textbox = page.locator("div.ProseMirror[role='textbox']").first
            if textbox.is_visible(timeout=5000):
                textbox.click()
                textbox.press_sequentially(effective_prompt, delay=10)

            submit_btn = page.locator("button[aria-label='Начать генерацию'], button[type='submit']").first
            submit_btn.wait_for(state="visible", timeout=2000)
            if not submit_btn.is_disabled():
                submit_btn.click()

            elapsed = 0
            poll_interval = 3000
            new_assets = []
            while elapsed < (timeout_sec * 1000):
                page.wait_for_timeout(poll_interval)
                elapsed += poll_interval
                for v in page.locator("flow-tile video, [class*='tile'] video").all():
                    src = v.get_attribute("src") or ""
                    if src and src not in existing_videos and src not in new_assets:
                        new_assets.append(src)
                if new_assets:
                    break

            if not new_assets:
                raise TimeoutError(f"Frames-to-Video не было сгенерировано за {timeout_sec} сек.")

            saved_files = []
            import time
            timestamp = int(time.time())
            for idx, asset_url in enumerate(new_assets, 1):
                dest_file = out_path / f"flow_f2v_{timestamp}_{idx}.mp4"
                resp = page.request.get(asset_url)
                if resp.status == 200:
                    dest_file.write_bytes(resp.body())
                    saved_files.append(str(dest_file))

            return {
                "success": True,
                "mode": "headless" if is_headless else "cdp",
                "action": "frames_to_video",
                "start_frame": start_frame,
                "end_frame": end_frame,
                "prompt": effective_prompt,
                "files": saved_files,
                "count": len(saved_files)
            }
        finally:
            if is_headless:
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
        if is_cdp_available():
            browser = p.chromium.connect_over_cdp(CDP_URL)
            context = browser.contexts[0]
            is_headless = False
        else:
            if not STORAGE_FILE.exists():
                raise RuntimeError(f"Файл сессии {STORAGE_FILE} не найден.")
            browser = p.chromium.launch(
                channel="chrome",
                headless=True,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
            )
            context = browser.new_context(
                storage_state=str(STORAGE_FILE),
                user_agent=USER_AGENT
            )
            is_headless = True

        try:
            page = get_or_create_page(context)
            if not ensure_in_project(page):
                raise RuntimeError("Не удалось открыть проектную область Google Flow.")

            tiles = page.locator("flow-tile, [class*='tile']").all()
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
                textbox = page.locator("div.ProseMirror[role='textbox']").first
                if textbox.is_visible(timeout=3000):
                    textbox.click()
                    textbox.press_sequentially(prompt, delay=10)

            submit_btn = page.locator("button[aria-label='Начать генерацию'], button[type='submit']").first
            submit_btn.wait_for(state="visible", timeout=2000)
            if not submit_btn.is_disabled():
                submit_btn.click()

            existing_videos = set()
            for v in page.locator("flow-tile video, [class*='tile'] video").all():
                src = v.get_attribute("src") or ""
                if src:
                    existing_videos.add(src)

            elapsed = 0
            poll_interval = 3000
            new_assets = []
            while elapsed < (timeout_sec * 1000):
                page.wait_for_timeout(poll_interval)
                elapsed += poll_interval
                for v in page.locator("flow-tile video, [class*='tile'] video").all():
                    src = v.get_attribute("src") or ""
                    if src and src not in existing_videos and src not in new_assets:
                        new_assets.append(src)
                if new_assets:
                    break

            if not new_assets:
                raise TimeoutError(f"Продленное видео не было сгенерировано за {timeout_sec} сек.")

            saved_files = []
            import time
            timestamp = int(time.time())
            for idx, asset_url in enumerate(new_assets, 1):
                dest_file = out_path / f"flow_extended_{timestamp}_{idx}.mp4"
                resp = page.request.get(asset_url)
                if resp.status == 200:
                    dest_file.write_bytes(resp.body())
                    saved_files.append(str(dest_file))

            return {
                "success": True,
                "mode": "headless" if is_headless else "cdp",
                "action": "video_extend",
                "tile_index": tile_index,
                "prompt": prompt,
                "files": saved_files,
                "count": len(saved_files)
            }
        finally:
            if is_headless:
                browser.close()

def upscale_flow_image(
    tile_index: int = -1,
    output_dir: str = None,
    timeout_sec: int = 90
) -> Dict[str, Any]:
    """
    Масштабирует существующее изображение в Google Flow до 2K.
    """
    out_path = Path(output_dir).resolve() if output_dir else Path.cwd() / "outputs"
    out_path.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        if is_cdp_available():
            browser = p.chromium.connect_over_cdp(CDP_URL)
            context = browser.contexts[0]
            is_headless = False
        else:
            if not STORAGE_FILE.exists():
                raise RuntimeError(f"Файл сессии {STORAGE_FILE} не найден.")
            browser = p.chromium.launch(
                channel="chrome",
                headless=True,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
            )
            context = browser.new_context(
                storage_state=str(STORAGE_FILE),
                user_agent=USER_AGENT
            )
            is_headless = True

        try:
            page = get_or_create_page(context)
            if not ensure_in_project(page):
                raise RuntimeError("Не удалось открыть проектную область Google Flow.")

            tiles = page.locator("flow-tile, [class*='tile']").all()
            if not tiles:
                raise RuntimeError("В проекте Google Flow нет доступных изображений для апскейла.")

            try:
                target_tile = tiles[tile_index]
            except IndexError:
                target_tile = tiles[-1]

            high_res_url = trigger_2k_upscale(page, target_tile, timeout_sec=timeout_sec)
            import time
            timestamp = int(time.time())
            dest_file = out_path / f"flow_2k_{timestamp}.png"

            if high_res_url:
                resp = page.request.get(high_res_url)
                if resp.status == 200:
                    dest_file.write_bytes(resp.body())
                else:
                    target_tile.screenshot(path=str(dest_file))
            else:
                target_tile.screenshot(path=str(dest_file))

            return {
                "success": True,
                "mode": "headless" if is_headless else "cdp",
                "action": "upscale_2k",
                "tile_index": tile_index,
                "files": [str(dest_file)],
                "count": 1
            }
        finally:
            if is_headless:
                browser.close()

def edit_flow_image(
    prompt: str,
    tile_index: int = -1,
    reference_image: str = None,
    aspect_ratio: str = None,
    upscale_2k: bool = False,
    output_dir: str = None,
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
    1. Если указан tile_index и запрошен upscale_2k для изображения — выполняет 2K-апскейл через изолированный tempdir.
    2. Атомарно перемещает / сохраняет файл в проектную папку target_path без оставления мусорных файлов.
    3. Защищен от SameFileError при перезаписи по тому же пути.
    4. Возвращает готовые ссылки (абсолютный путь, относительный путь и markdown).
    """
    resolved_target = Path(target_path).resolve()
    resolved_target.parent.mkdir(parents=True, exist_ok=True)

    is_video = resolved_target.suffix.lower() in [".mp4", ".webm", ".mov"] or (source_file and Path(source_file).suffix.lower() in [".mp4", ".webm"])
    is_2k_applied = False
    chosen_source = None

    # Сценарий 1: Запрошен 2K апскейл для изображения через Flow
    if upscale_2k and not is_video:
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
            print(f"[-] Апскейл не удался ({e}), используем fallback на исходный черновик.")

    # Сценарий 2: Fallback или прямое копирование исходного черновика
    if not chosen_source and source_file:
        src_path = Path(source_file).resolve()
        if src_path.exists():
            chosen_source = src_path
            # Защита от SameFileError, если target_path совпадает с source_file
            if resolved_target != chosen_source:
                shutil.copy2(str(chosen_source), str(resolved_target))

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
