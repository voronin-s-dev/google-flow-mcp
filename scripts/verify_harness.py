"""
Google Flow MCP — Selector & Contract Verification Harness
Проверяет целостность контрактов MCP, JSON-схем и доступность DOM-селекторов Google Flow через CDP без сжигания квот.
"""

import sys
import io
import json
import argparse
import urllib.request
from pathlib import Path
from typing import Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MCP_SCHEMAS_DIR = Path("C:/Users/voron/.gemini/antigravity/mcp/google-flow")
CDP_URL = "http://127.0.0.1:9222"

def check_mcp_contract() -> Tuple[bool, List[str]]:
    """
    Проверяет, что каждый инструмент в server.py имеет соответствующую и актуальную JSON-схему.
    """
    errors = []
    sys.path.insert(0, str(PROJECT_ROOT))
    import asyncio
    import server

    tools = asyncio.run(server.app.list_tools())
    server_tool_names = {t.name: t for t in tools}

    if not MCP_SCHEMAS_DIR.exists():
        errors.append(f"Директория схем MCP не найдена: {MCP_SCHEMAS_DIR}")
        return False, errors

    schema_files = list(MCP_SCHEMAS_DIR.glob("*.json"))
    schema_tool_names = {f.stem: f for f in schema_files}

    # 1. Проверка наличия схем для всех инструментов
    for tool_name, tool_obj in server_tool_names.items():
        if tool_name not in schema_tool_names:
            errors.append(f"[MCP Contract Error] Для инструмента '{tool_name}' отсутствует схема: {MCP_SCHEMAS_DIR / f'{tool_name}.json'}")
        else:
            # Сверяем обязательные аргументы
            schema_path = schema_tool_names[tool_name]
            try:
                with open(schema_path, "r", encoding="utf-8") as f:
                    schema_data = json.load(f)
                
                # Проверка наличия свойств
                schema_props = set(schema_data.get("parameters", {}).get("properties", {}).keys())
                tool_props = set(tool_obj.input_schema.get("properties", {}).keys())
                
                missing_in_schema = tool_props - schema_props
                if missing_in_schema:
                    errors.append(f"[MCP Schema Mismatch] Инструмент '{tool_name}' содержит аргументы {missing_in_schema}, отсутствующие в JSON-схеме.")
            except Exception as e:
                errors.append(f"[MCP Schema Read Error] Ошибка чтения {schema_path}: {e}")

    # 2. Проверка устаревших схем, которых больше нет в коде
    for schema_name in schema_tool_names:
        if schema_name not in server_tool_names:
            errors.append(f"[MCP Contract Warning] Найден файл схемы '{schema_name}.json', но инструмент не зарегистрирован в server.py.")

    return len(errors) == 0, errors

def is_cdp_online() -> bool:
    try:
        with urllib.request.urlopen(f"{CDP_URL}/json/version", timeout=1.5) as resp:
            return resp.status == 200
    except Exception:
        return False

def check_dom_selectors() -> Tuple[bool, List[str]]:
    """
    Подключается к запущенному Chrome по CDP и проверяет видимость основных селекторов Google Flow.
    НЕ выполняет генерацию и не расходует квоты пользователя.
    """
    from playwright.sync_api import sync_playwright

    logs = []
    success = True

    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(CDP_URL)
            context = browser.contexts[0]
            
            # Поиск страницы Flow
            flow_page = None
            for page in context.pages:
                if "flow.google.com" in page.url or "labs.google" in page.url:
                    flow_page = page
                    break

            if not flow_page:
                logs.append("[-] В открытом Chrome нет активной вкладки flow.google.com.")
                return False, logs

            logs.append(f"[+] Найдена страница Flow: {flow_page.url}")

            # Проверяемые ключевые элементы
            checks = [
                ("Поле ввода промпта", [
                    "textarea",
                    "[contenteditable='true']",
                    "[placeholder*='prompt' i]",
                    "[placeholder*='опишите' i]",
                    "[aria-label*='prompt' i]"
                ]),
                ("Кнопка запуска генерации", [
                    "button[aria-label*='generate' i]",
                    "button[aria-label*='создать' i]",
                    "button[aria-label*='create' i]",
                    "button:has-text('Generate')",
                    "button:has-text('Создать')"
                ]),
                ("Селектор референсного файла", [
                    "input[type='file']",
                    "button[aria-label*='image' i]",
                    "button[aria-label*='референс' i]",
                    "button[aria-label*='attach' i]"
                ]),
                ("Область плиток / результатов", [
                    "flow-tile",
                    "[class*='tile']",
                    "[data-testid*='tile']"
                ])
            ]

            for name, selectors in checks:
                found = False
                for sel in selectors:
                    loc = flow_page.locator(sel).first
                    try:
                        if loc.is_visible(timeout=800):
                            logs.append(f"[PASS] {name}: найден селектор '{sel}'")
                            found = True
                            break
                    except Exception:
                        pass
                
                if not found:
                    logs.append(f"[WARN] {name}: ни один селектор из списка не обнаружен на текущем экране.")
                    # Это не критическая ошибка, если мы на главной странице, а не в проекте
                    if "/project/" in flow_page.url:
                        success = False

        except Exception as e:
            logs.append(f"[ERROR] Ошибка подключения к CDP: {e}")
            return False, logs

    return success, logs

def main():
    parser = argparse.ArgumentParser(description="Google Flow MCP Smoke & Contract Harness")
    parser.add_argument("--skip-cdp", action="store_true", help="Пропустить проверку DOM через CDP")
    args = parser.parse_args()

    print("=" * 60)
    print(" Google Flow MCP — Verification Harness")
    print("=" * 60)

    # 1. Проверка контрактов MCP
    print("\n[*] Шаг 1: Проверка контрактов MCP и JSON-схем...")
    contract_ok, contract_errors = check_mcp_contract()
    if contract_ok:
        print("[PASS] Все инструменты server.py синхронизированы с JSON-схемами.")
    else:
        print("[FAIL] Обнаружены нарушения контракта:")
        for err in contract_errors:
            print(f"  - {err}")

    # 2. Проверка CDP и DOM селекторов
    cdp_ok = True
    if not args.skip_cdp:
        print("\n[*] Шаг 2: Проверка селекторов в живом интерфейсе Google Flow...")
        if is_cdp_online():
            print(f"[+] CDP порт 9222 активен ({CDP_URL}). Запуск быстрой инспекции...")
            dom_ok, dom_logs = check_dom_selectors()
            for log in dom_logs:
                print(f"  {log}")
            cdp_ok = dom_ok
        else:
            print("[INFO] Chrome на порту 9222 не запущен. Для живой проверки DOM запустите: start_chrome.bat")

    print("\n" + "=" * 60)
    if contract_ok and cdp_ok:
        print(" ИТОГ: Верификация успешно пройдена! Система стабильна.")
        print("=" * 60)
        sys.exit(0)
    else:
        print(" ИТОГ: Обнаружены замечания при верификации.")
        print("=" * 60)
        sys.exit(1)

if __name__ == "__main__":
    if hasattr(sys.stdout, "buffer") and sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        except Exception:
            pass
    main()
