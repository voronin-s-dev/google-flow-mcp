"""
Google Flow MCP CLI Client
Единый CLI-клиент для агентов и разработчиков, работающий поверх ядра Google Flow MCP.
"""

import sys
import io
import json
import argparse
from pathlib import Path

# UTF-8 stdout для Windows консоли
if hasattr(sys.stdout, "buffer") and sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    except Exception:
        pass

# Подключаем ядро MCP
PROJECT_CORE = Path(r"C:\Antigravity projects\Google flow mcp")
if str(PROJECT_CORE) not in sys.path:
    sys.path.insert(0, str(PROJECT_CORE))

try:
    import engine
    import expander
    import server
except ImportError as e:
    print(f"[ERROR] Не удалось загрузить ядро Google Flow MCP из {PROJECT_CORE}: {e}", file=sys.stderr)
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Google Flow V3 Studio Pipeline CLI Client")
    
    # Диагностика статуса
    parser.add_argument("--status", action="store_true", help="Проверить статус подключения (CDP / сохраненная сессия)")

    # Режимы работы
    parser.add_argument("--prompt", type=str, default="", help="Промпт для генерации")
    parser.add_argument("--out", type=str, default=None, help="Папка для сохранения выходных файлов")
    parser.add_argument("--reference", type=str, default=None, help="Путь к локальному изображению-референсу")
    parser.add_argument("--video", action="store_true", help="Генерировать видео (Veo) вместо изображения")
    
    # V3/V4 Studio Pipeline опции
    parser.add_argument("--aspect-ratio", type=str, default=None, choices=["16:9", "9:16", "1:1", "4:3", "3:4"], help="Соотношение сторон")
    parser.add_argument("--camera", type=str, default=None, help="Движение камеры (pan_left, pan_right, tilt_up, tilt_down, zoom_in, zoom_out, orbit, static)")
    parser.add_argument("--batch-count", type=int, default=1, choices=[1, 2, 3, 4], help="Количество генерируемых вариантов (1..4)")
    parser.add_argument("--mute", action="store_true", help="Отключить звук в генерируемом видео Veo")
    parser.add_argument("--expand", action="store_true", help="Автоматически развернуть промпт через стилистический Expander")
    parser.add_argument("--upscale-2k", action="store_true", help="Запросить 2K апскейл")
    parser.add_argument("--tile-index", type=int, default=None, help="Индекс плитки для операций апскейла или редактирования (-1 для последней)")
    parser.add_argument("--edit-tile", type=int, default=None, help="Индекс плитки для внесения правок / создания вариации (-1 для последней)")
    parser.add_argument("--regenerate-tile", type=int, default=None, help="Индекс плитки для повторной генерации (-1 для последней)")
    parser.add_argument("--list-projects", action="store_true", help="Вывести список проектов Google Flow")
    parser.add_argument("--create-project", type=str, default=None, help="Создать новый проект Google Flow с указанным именем")
    
    # Специфичные сценарии
    parser.add_argument("--end-frame", type=str, default=None, help="Конечный кадр для режима Frames-to-Video")
    parser.add_argument("--extend-video", type=int, default=None, help="Индекс видеоплитки для продления на 5-8 сек")
    parser.add_argument("--finalize-to", type=str, default=None, help="Целевой путь для финализации ассета в проект (напр: src/assets/hero.png)")
    parser.add_argument("--source-file", type=str, default=None, help="Исходный файл черновика при финализации")
    parser.add_argument("--card", action="store_true", help="Сгенерировать HTML-виджет Antigravity Generative UI")
    parser.add_argument("--auto", action="store_true", help="Автономный фоновый режим конвейера (Reels/Production)")
    
    parser.add_argument("--timeout", type=int, default=90, help="Таймаут ожидания в секундах")
    parser.add_argument("--json", action="store_true", help="Вывести результат в формате JSON")

    args = parser.parse_args()

    # Сценарий 0: Проверка статуса
    if args.status:
        status_json = server.flow_check_status()
        if args.json:
            print(status_json)
        else:
            data = json.loads(status_json)
            print(f"Статус Google Flow: {data.get('status')} | CDP: {data.get('cdp_active')} | Auth: {data.get('headless_auth_saved')}")
            print(f"Инфо: {data.get('message')}")
        return

    # Сценарий: Список проектов
    if args.list_projects:
        projects = engine.list_flow_projects()
        if args.json:
            print(json.dumps({"success": True, "count": len(projects), "projects": projects}, ensure_ascii=False, indent=2))
        else:
            print(f"[*] Найдено проектов: {len(projects)}")
            for p in projects:
                print(f"  - [{p['id']}] {p['title']} ({p['url']})")
        return

    # Сценарий: Создание проекта
    if args.create_project is not None:
        res = engine.create_flow_project(name=args.create_project)
        if args.json:
            print(json.dumps(res, ensure_ascii=False, indent=2))
        else:
            print(f"[SUCCESS] Создан проект: {res.get('project_id')} ({res.get('url')})")
        return

    # Сценарий: Повторная генерация плитки
    if args.regenerate_tile is not None:
        res = engine.regenerate_flow_tile(tile_index=args.regenerate_tile, output_dir=args.out, timeout_sec=args.timeout)
        if args.json:
            print(json.dumps(res, ensure_ascii=False, indent=2))
        else:
            print(f"[SUCCESS] Повторная генерация завершена: {res.get('files', [])}")
        return

    # Сценарий 1: Финализация ассета в проект
    if args.finalize_to:
        tile_idx = args.edit_tile if args.edit_tile is not None else (args.tile_index if args.tile_index is not None else -1)
        res = engine.finalize_asset(
            target_path=args.finalize_to,
            source_file=args.source_file,
            tile_index=tile_idx,
            upscale_2k=args.upscale_2k,
            timeout_sec=args.timeout
        )
        if args.json:
            print(json.dumps(res, ensure_ascii=False, indent=2))
        else:
            print(f"[SUCCESS] Ассет финализирован: {res['target_path']}")
            print(f"Ссылка для вставки в markdown: {res['markdown_link']}")
        return

    # Сценарий 2: Отдельный апскейл существующей плитки (без промпта)
    if args.upscale_2k and not args.prompt and (args.tile_index is not None or args.edit_tile is not None):
        target_idx = args.tile_index if args.tile_index is not None else args.edit_tile
        res = engine.upscale_flow_image(
            tile_index=target_idx,
            output_dir=args.out,
            timeout_sec=args.timeout
        )
        if args.json:
            print(json.dumps(res, ensure_ascii=False, indent=2))
        else:
            print(f"[SUCCESS] Изображение масштабировано до 2K: {res.get('files', [])}")
        return

    # Сценарий 3: Продление видео
    if args.extend_video is not None:
        res = engine.extend_flow_video(
            tile_index=args.extend_video,
            prompt=args.prompt,
            output_dir=args.out,
            timeout_sec=args.timeout if args.timeout != 90 else 180
        )
        if args.json:
            print(json.dumps(res, ensure_ascii=False, indent=2))
        else:
            print(f"[SUCCESS] Видео продлено: {res.get('files', [])}")
        return

    # Сценарий 4: Frames-to-Video
    if args.reference and args.end_frame:
        res = engine.generate_frames_to_video(
            start_frame=args.reference,
            end_frame=args.end_frame,
            prompt=args.prompt,
            aspect_ratio=args.aspect_ratio,
            output_dir=args.out,
            timeout_sec=args.timeout if args.timeout != 90 else 180
        )
        if args.json:
            print(json.dumps(res, ensure_ascii=False, indent=2))
        else:
            print(f"[SUCCESS] Frames-to-Video сгенерировано: {res.get('files', [])}")
        return

    # Сценарий 5: Стандартная генерация / Редактирование
    if not args.prompt:
        print("[ERROR] Не указан обязательный аргумент --prompt", file=sys.stderr)
        sys.exit(1)

    edit_idx = args.edit_tile if args.edit_tile is not None else args.tile_index
    res = engine.generate_flow_media(
        prompt=args.prompt,
        output_dir=args.out,
        media_type="video" if args.video else "image",
        reference_image=args.reference,
        aspect_ratio=args.aspect_ratio,
        camera_motion=args.camera,
        batch_count=args.batch_count,
        mute_audio=args.mute,
        expand_prompt_flag=args.expand,
        upscale_2k=args.upscale_2k,
        edit_tile_index=edit_idx,
        timeout_sec=args.timeout
    )

    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print(f"[SUCCESS] Генерация завершена. Файлов: {len(res.get('files', []))}")
        for f in res.get('files', []):
            print(f"  - {f}")
        if (args.card or not args.auto) and res.get('files'):
            try:
                import widget
                card_path = widget.save_flow_card(
                    media_paths=res['files'],
                    prompt=args.prompt,
                    output_dir=args.out,
                    aspect_ratio=args.aspect_ratio or "1:1",
                    media_type="video" if args.video else "image",
                    batch_count=args.batch_count,
                    status_label="⚡ Автономно" if args.auto else "Черновик готов",
                    is_autonomous=args.auto,
                    tile_index=edit_idx if edit_idx is not None else -1
                )
                print(f"[EMBED] <agent-embed src=\"file:///{Path(card_path).resolve().as_posix()}\"></agent-embed>")
            except Exception as e:
                pass

if __name__ == "__main__":
    main()
