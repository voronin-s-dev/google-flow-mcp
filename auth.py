"""
Скрипт первоначальной авторизации в Google Flow.
Открывает браузер для ручного входа в ваш Google-аккаунт
и сохраняет сессионные токены локально в storage_state.json.
"""

import sys
import time
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

STORAGE_FILE = Path(__file__).parent / "storage_state.json"

def is_cdp_available() -> bool:
    try:
        with urllib.request.urlopen("http://127.0.0.1:9222/json/version", timeout=1.0) as resp:
            return resp.status == 200
    except Exception:
        return False

def login():
    print("==================================================================")
    print("  Google Flow MCP: Первоначальная авторизация")
    print("==================================================================")

    with sync_playwright() as p:
        if is_cdp_available():
            print("[*] Обнаружен активный Chrome на порту 9222 (CDP).")
            browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            context = browser.contexts[0]
            print("[*] Экспорт сессионных cookie из открытого Chrome в storage_state.json...")
            context.storage_state(path=str(STORAGE_FILE))
            print(f"[+] УСПЕХ! Сессия сохранена: {STORAGE_FILE}")
            print("[+] Теперь Google Flow готов к скрытой фоновой работе.")
            return

        print("Сейчас откроется окно браузера.")
        print("1. Войдите в свой Google-аккаунт с подпиской Google AI Pro.")
        print("2. Убедитесь, что открылась главная страница Google Flow.")
        print("3. Вернитесь в эту консоль и нажмите ENTER для сохранения сессии.")
        print("==================================================================\n")

        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-first-run",
            "--no-default-browser-check"
        ]
        try:
            browser = p.chromium.launch(
                channel="chrome",
                headless=False,
                args=launch_args,
                ignore_default_args=["--enable-automation"]
            )
        except Exception:
            browser = p.chromium.launch(
                headless=False,
                args=launch_args,
                ignore_default_args=["--enable-automation"]
            )

        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()
        page.goto("https://flow.google.com", wait_until="domcontentloaded")

        input("\n>>> После успешного входа в аккаунт нажмите ENTER здесь в консоли... ")

        print("\n[*] Сохранение сессионных cookie в storage_state.json...")
        context.storage_state(path=str(STORAGE_FILE))
        print(f"[+] Готово! Файл сохранен: {STORAGE_FILE}")
        print("[+] Теперь MCP-сервер сможет работать полностью в скрытом headless-режиме.")
        browser.close()

if __name__ == "__main__":
    login()
