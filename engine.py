import time
import urllib.request
from pathlib import Path
from typing import List, Dict, Any
from playwright.sync_api import sync_playwright

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
    page.goto(FLOW_URL, wait_until="domcontentloaded", timeout=20000)
    time.sleep(3)
    return page

def ensure_in_project(page) -> bool:
    if "/project/" in page.url:
        return True

    # Ищем кнопку "Новый проект"
    new_proj_btn = page.locator("text='Новый проект'").first
    if new_proj_btn.is_visible(timeout=3000):
        new_proj_btn.click()
        time.sleep(4)
        return True

    create_btn = page.locator("button:has-text('New'), button:has-text('Создать')").first
    if create_btn.is_visible(timeout=2000):
        create_btn.click()
        time.sleep(4)
        return True

    return "/project/" in page.url

def generate_flow_media(
    prompt: str,
    output_dir: str = None,
    media_type: str = "image",
    timeout_sec: int = 90
) -> Dict[str, Any]:
    out_path = Path(output_dir).resolve() if output_dir else Path.cwd() / "outputs"
    out_path.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        # Стратегия подключения: если запущен CDP - используем его, иначе тихий headless
        if is_cdp_available():
            browser = p.chromium.connect_over_cdp(CDP_URL)
            context = browser.contexts[0]
            is_headless = False
        else:
            if not STORAGE_FILE.exists():
                raise RuntimeError(
                    f"Файл сессии {STORAGE_FILE} не найден. "
                    "Требуется однократная авторизация для сохранения сессионных cookie."
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

            # Собираем уже имеющиеся ассеты
            existing_urls = set()
            for img in page.locator("flow-tile img, [class*='tile'] img").all():
                src = img.get_attribute("src") or ""
                if "flow-content.google" in src:
                    existing_urls.add(src)
            for v in page.locator("flow-tile video, [class*='tile'] video").all():
                src = v.get_attribute("src") or ""
                if src:
                    existing_urls.add(src)

            # Находим поле ввода ProseMirror
            textbox = page.locator("div.ProseMirror[role='textbox']").first
            if not textbox.is_visible(timeout=5000):
                raise RuntimeError("Поле ввода ProseMirror не найдено.")

            textbox.click()
            time.sleep(0.3)
            textbox.press_sequentially(prompt, delay=15)
            time.sleep(1)

            submit_btn = page.locator("button[aria-label='Начать генерацию'], button[type='submit'].generate-icon-button").first
            if submit_btn.is_disabled():
                raise RuntimeError("Кнопка генерации недоступна (проверьте текст промпта).")

            submit_btn.click()

            # Ждем появления новых элементов
            start_time = time.time()
            new_assets = []

            while time.time() - start_time < timeout_sec:
                time.sleep(3)
                # Проверка новых картинок
                for img in page.locator("flow-tile img, [class*='tile'] img").all():
                    src = img.get_attribute("src") or ""
                    if "flow-content.google" in src and src not in existing_urls and src not in new_assets:
                        new_assets.append(src)

                # Проверка новых видео
                for v in page.locator("flow-tile video, [class*='tile'] video").all():
                    src = v.get_attribute("src") or ""
                    if src and src not in existing_urls and src not in new_assets:
                        new_assets.append(src)

                if len(new_assets) > 0:
                    time.sleep(3)
                    # Подбираем парные генерации
                    for img in page.locator("flow-tile img, [class*='tile'] img").all():
                        src = img.get_attribute("src") or ""
                        if "flow-content.google" in src and src not in existing_urls and src not in new_assets:
                            new_assets.append(src)
                    break

            if not new_assets:
                raise TimeoutError(f"Ассеты не были сгенерированы в течение {timeout_sec} сек.")

            saved_files = []
            timestamp = int(time.time())
            for idx, asset_url in enumerate(new_assets, 1):
                ext = ".mp4" if "video" in asset_url else ".png"
                dest_file = out_path / f"flow_{timestamp}_{idx}{ext}"
                resp = page.request.get(asset_url)
                if resp.status == 200:
                    dest_file.write_bytes(resp.body())
                    saved_files.append(str(dest_file))

            return {
                "success": True,
                "mode": "headless" if is_headless else "cdp",
                "prompt": prompt,
                "files": saved_files,
                "count": len(saved_files)
            }

        finally:
            if is_headless:
                browser.close()
