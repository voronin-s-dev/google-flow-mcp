"""
Google Flow MCP - Интерактивный мастер авторизации (Zero-Error Login)
Обходит защиту Google 'Небезопасный браузер' через двухэтапный нативный запуск.
"""

import os
import sys
import time
import subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent
STORAGE_FILE = BASE_DIR / "storage_state.json"
PROFILE_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "GoogleFlowAgentProfile"

def find_chrome():
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None

def clean_locks(profile_path: Path):
    for lock_name in ["lockfile", "SingletonLock", "SingletonCookie", "SingletonSocket"]:
        lock_file = profile_path / lock_name
        if lock_file.exists():
            try:
                lock_file.unlink()
            except Exception:
                pass

def main():
    print("=" * 66)
    print("  Google Flow MCP: Вход в аккаунт Google")
    print("=" * 66)

    chrome_bin = find_chrome()
    if not chrome_bin:
        print("[ОШИБКА] Браузер Google Chrome не найден на компьютере!")
        input("\nНажмите Enter для выхода...")
        sys.exit(1)

    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    clean_locks(PROFILE_DIR)

    print("\n[ЭТАП 1] Запуск чистого Chrome...")
    print("1. Сейчас откроется обычный Chrome без каких-либо отладочных флагов.")
    print("2. Google примет его как на 100% безопасный ваш личный браузер.")
    print("3. Войдите в свой аккаунт Google и убедитесь, что открылась страница Google Flow.")
    print("4. После этого просто ЗАКРОЙТЕ окно Chrome.\n")

    # Этап 1: Чистый запуск без флагов отладки (Google не ругается на безопасность)
    subprocess.run([
        chrome_bin,
        f"--user-data-dir={PROFILE_DIR}",
        "https://flow.google.com"
    ])

    print("\n[ЭТАП 2] Фиксация сессии...")
    clean_locks(PROFILE_DIR)

    # Этап 2: Запуск с CDP в фоне для быстрого экспорта cookie
    proc = subprocess.Popen([
        chrome_bin,
        "--remote-debugging-port=9222",
        "--remote-allow-origins=*",
        f"--user-data-dir={PROFILE_DIR}",
        "--headless=new"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    time.sleep(3)

    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            context = browser.contexts[0]
            context.storage_state(path=str(STORAGE_FILE))
            print(f"\n[+] УСПЕХ! Сессия успешно сохранена в: {STORAGE_FILE}")
            print("[+] Теперь генерации Google Flow готовы к работе в фоновом режиме.")
    except Exception as e:
        print(f"\n[-] Ошибка экспорта сессии: {e}")
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:
            pass

    print("\n" + "=" * 66)
    input("Готово! Нажмите Enter для закрытия этого окна...")

if __name__ == "__main__":
    main()
