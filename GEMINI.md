# Google Flow MCP — Инструкции и Контекст Проекта (GEMINI.md)

## 📌 Миссия проекта
Превратить веб-студию **Google Flow** (`flow.google.com`) в автономный программный инструмент (MCP-сервер и агентский скилл), позволяющий ИИ-агентам генерировать продакшн-медиа (фото, иллюстрации, баннеры, кинематографичные видео) прямо из чата **без платы за API-токены**, используя активную подписку Google AI Pro пользователя.

---

## 🏗 Архитектура и компоненты

### 1. Ядро проекта (`C:\Antigravity projects\Google flow mcp`)
- **`server.py`**: MCP-сервер (протокол stdio), объявляющий инструменты для агентских сред (Antigravity, Claude Desktop, Cursor).
- **`engine.py`**: Движок автоматизации на базе Playwright (поддерживает подключение через Chrome DevTools Protocol на порту 9222 или тихий автономный headless-режим с использованием локального файла сессии `storage_state.json`).
- **`auth.py`**: Скрипт интерактивного первого входа для сохранения сессионных куков.
- **`storage_state.json`**: Локальные авторизационные данные (строго в `.gitignore`).
- **Виртуальное окружение**: Управляется через `uv` (Python 3.14). Запуск команд через `.venv\Scripts\python.exe` или `uv run`.

### 2. Внешняя интеграция и скиллы
- **Схемы инструментов MCP**: `C:\Users\voron\.gemini\antigravity\mcp\google-flow\*.json`
- **Конфигурация MCP**: `C:\Users\voron\.gemini\config\mcp_config.json`
- **Глобальный агентский скилл**: `C:\Users\voron\.gemini\config\skills\google-flow-generator` (CLI-клиент `flow_client.py` и документация использования для агентов).

---

## 📋 Инженерные правила и стандарты разработки

### 1. Стандарты веб-автоматизации и Playwright
- **Селекторы (Locators):**
  - Строгий приоритет семантическим локаторам: `page.get_by_role()`, `page.get_by_text()`, устойчивым атрибутам `[aria-label]`, `[data-testid]`.
  - **Запрещены** хрупкие автогенерированные CSS-классы (например, `.sc-xyz`, сложные цепочки `div > div > div > button`).
- **Ожидания (Auto-waiting):**
  - **Запрещены** `time.sleep()`. Использовать `expect(locator).to_be_visible()`, `locator.wait_for(state="visible")`, `page.wait_for_load_state("networkidle")`.
  - Все таймауты должны иметь разумные дефолты (90с для изображений, 180с для видео) с возможностью переопределения через аргументы вызова.
- **Работа с файлами и скачиванием:**
  - Скачивание медиа обязательно оборачивать в `with page.expect_download() as download_info:`.
  - Загрузку референсов производить через `expect_file_chooser()` или прямой `set_input_files()` на скрытых `input[type="file"]`.
- **Изоляция и стабильность браузера:**
  - Профиль Chrome (`%LOCALAPPDATA%\GoogleFlowAgentProfile`) и `storage_state.json` защищены от одновременных конфликтующих сессий.
  - При запуске через `start_chrome.bat` обязательно проверять и сбрасывать `lockfile`, запускать с флагами `--remote-debugging-port=9222 --remote-allow-origins=*`.
- **Кодировка:**
  - В скриптах ввода/вывода принудительно задавать UTF-8: `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')`.

### 2. Синхронизация MCP-инструментов (Single Source of Truth)
Любое изменение или добавление инструмента в `server.py` **обязательно** сопровождается:
1. Автоматической генерацией / обновлением JSON-схем в `C:\Users\voron\.gemini\antigravity\mcp\google-flow\`.
2. Обновлением параметров в CLI-клиенте `google-flow-generator/scripts/flow_client.py`.
3. Обновлением описания в `google-flow-generator/SKILL.md`.
4. Внесением записи в хронологию и ADR файла `PROJECT_MEMORY.md`.

### 3. Тестирование и верификация перед сдачей кода
- Тесты запускаются через: `pytest tests/` (или `uv run pytest`).
- **Selector & Contract Harness (`scripts/verify_harness.py`)**:
  - Детерминированная проверка соответствия инструментов в `server.py` и JSON-схем в `mcp/google-flow/`.
  - Экспресс-проверка DOM-селекторов на живом Flow по CDP (порт 9222) **без расхода квот** генерации.
- Для проверки связи с Flow используется `flow_check_status()`.

---

## 🤖 Мультиагентный процесс разработки
Для сложных задач разработки и рефакторинга используются выделенные субагенты:
1. **`flow-dom-inspector`**: Подключается к живому браузеру на CDP 9222, исследует разметку Google Flow, находит стабильные семантические селекторы (aria-label, role, data-testid) без сжигания токенов генерации.
2. **`flow-quality-critic`**: Проводит жесткий аудит изменений кода по чек-листу: отсутствие `time.sleep()`, устойчивость селекторов, синхронизация 4-х файлов контракта (server.py $\leftrightarrow$ JSON schemas $\leftrightarrow$ flow_client.py $\leftrightarrow$ SKILL.md).

---

## 🛠 Реализованный функционал (V2)

1. **`flow_generate_image`**: Текстовая генерация (Imagen 3/4), `reference_image`, флаг `upscale_2k`.
2. **`flow_generate_video`**: Генерация видео через Veo, `reference_image` (стартовый кадр).
3. **`flow_upscale_image`**: Апскейл ранее сгенерированного изображения во Flow до 2K.
4. **`flow_edit_image`**: Внесение правок в существующие плитки («Edit / Use as input») или создание вариаций.
5. **`flow_check_status`**: Диагностика готовности (CDP или сохраненная сессия).

---

## 🚀 Следующий этап разработки (V3 Studio Pipeline)
Реализация **Студийного конвейера со стейджингом и интерактивным ревью**:
1. **Расширенные возможности Google Flow:**
   - Соотношения сторон (Aspect Ratio): `16:9`, `9:16`, `1:1`, `4:3`.
   - Режим **Frames to Video**: анимация между стартовым (`start_frame`) и финальным (`end_frame`) изображениями.
   - **Video Extend**: продление ролика еще на 5–8 секунд.
   - **Контроль камеры**: Pan, Tilt, Zoom, Orbit, Static.
   - **Expander**: автоматическое развертывание промпта через Gemini / LLM шаблоны.
2. **Интерактивный рабочий процесс агента:**
   - **Шаг 1 (Draft):** Агент создает черновики в стандартном разрешении и выводит превью прямо в чат через markdown `![preview](file:///path/to/asset.png)`.
   - **Шаг 2 (Review & Edit):** Ожидание отмашки или внесение правок (`flow_edit_image`).
   - **Шаг 3 (Finalize):** Инструмент `flow_finalize_asset(tile_index, target_path, upscale_2k=True)` атомарно апскейлит выбранный вариант и копирует его прямо в папку проекта пользователя (`src/assets/...`), автоматически вставляя ссылку в код.

---

## 🧩 Настроенные профильные скиллы проекта
- **`playwright-best-practices`**: Паттерны надежных селекторов, ожиданий, работы с сетевыми запросами и файловыми операциями.
- **`mcp-builder`**: Стандарты архитектуры MCP, типизация параметров, обработка ошибок JSON-RPC.
- **`python-testing-patterns`**: Паттерны pytest, асинхронные тесты, фикстуры и моки.
- **`prompt-engineering-patterns`**: Структура промптов для Expander и визуальных генераторов (Imagen / Veo).
- **`google-flow-generator`**: Глобальный фасадный скилл для взаимодействия агентов с сервером Flow.
- **`chrome-devtools` / `browser-testing-with-devtools`**: Живая инспекция DOM Flow на порту CDP 9222 при поиске селекторов.
