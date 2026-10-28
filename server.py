import json
import sys
import io
from pathlib import Path
from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations
from engine import (
    generate_flow_media,
    generate_frames_to_video,
    extend_flow_video,
    upscale_flow_image,
    edit_flow_image,
    finalize_asset,
    regenerate_flow_tile,
    list_flow_projects,
    create_flow_project,
    is_cdp_available,
    STORAGE_FILE,
    PROFILE_DIR
)

app = MCPServer("google-flow")

@app.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False
    )
)
def flow_check_status() -> str:
    """
    Проверить доступность Google Flow и статус авторизации (CDP / Headless / Native Profile).
    """
    try:
        cdp_active = is_cdp_available()
        auth_exists = STORAGE_FILE.exists()
        profile_exists = PROFILE_DIR.exists()
        is_ready = cdp_active or auth_exists or profile_exists
        return json.dumps({
            "status": "ready" if is_ready else "needs_auth",
            "cdp_active": cdp_active,
            "profile_active": profile_exists,
            "headless_auth_saved": auth_exists,
            "message": (
                "Chrome с портом отладки активен." if cdp_active else
                "Готов к работе в фоновом режиме через профиль GoogleFlowAgentProfile." if profile_exists else
                "Готов к работе в скрытом Headless-режиме с сохраненными куками." if auth_exists else
                "Требуется однократный вход в Google-аккаунт через login.bat."
            )
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error": str(e)
        }, ensure_ascii=False, indent=2)

@app.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True
    )
)
def flow_generate_image(
    prompt: str,
    reference_image: str = "",
    aspect_ratio: str = "",
    batch_count: int = 1,
    model_name: str = "nano_banana_2.1",
    expand_prompt: bool = False,
    upscale_2k: bool = False,
    output_dir: str = "",
    timeout_seconds: int = 90
) -> str:
    """
    Сгенерировать высококачественное изображение через Google Flow в фоне.
    
    :param prompt: Детальный промпт на английском языке (стиль, освещение, композиция, детали).
    :param reference_image: Локальный путь к изображению-референсу для генерации (Image-to-Image / Style).
    :param aspect_ratio: Желаемое соотношение сторон: '16:9', '9:16', '1:1', '4:3', '3:4'.
    :param batch_count: Количество генерируемых вариантов за один вызов: 1, 2, 3 или 4 (по умолчанию 1).
    :param model_name: Модель: 'nano_banana_2.1', 'nano_banana_pro', 'nano_banana_2_lite'.
    :param expand_prompt: Если True, автоматически расширяет промпт стилистическими и световыми модификаторами.
    :param upscale_2k: Если True, сразу запрашивает и сохраняет 2K версию изображения.
    :param output_dir: Папка для сохранения сгенерированных файлов (по умолчанию: ./outputs).
    :param timeout_seconds: Максимальное время ожидания генерации (по умолчанию 90 секунд).
    """
    try:
        result = generate_flow_media(
            prompt=prompt,
            output_dir=output_dir if output_dir else None,
            media_type="image",
            reference_image=reference_image if reference_image else None,
            aspect_ratio=aspect_ratio if aspect_ratio else None,
            camera_motion=None,
            batch_count=batch_count,
            expand_prompt_flag=expand_prompt,
            upscale_2k=upscale_2k,
            model_name=model_name,
            timeout_sec=timeout_seconds
        )
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "prompt": prompt
        }, ensure_ascii=False, indent=2)

@app.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True
    )
)
def flow_generate_video(
    prompt: str,
    reference_image: str = "",
    aspect_ratio: str = "",
    camera_motion: str = "",
    mute_audio: bool = False,
    expand_prompt: bool = False,
    output_dir: str = "",
    timeout_seconds: int = 150
) -> str:
    """
    Сгенерировать кинематографичное видео через Google Flow (Veo) в фоне.
    
    :param prompt: Детальный кинематографичный промпт на английском языке (движение камеры, действие, свет).
    :param reference_image: Локальный путь к изображению для стартового кадра / референса видео.
    :param aspect_ratio: Желаемое соотношение сторон: '16:9', '9:16', '1:1', '4:3', '3:4'.
    :param camera_motion: Движение камеры: 'pan_left', 'pan_right', 'tilt_up', 'tilt_down', 'zoom_in', 'zoom_out', 'orbit', 'static'.
    :param mute_audio: Если True, отключает звук генерации Veo ('Вернуть видео без звука').
    :param expand_prompt: Если True, автоматически расширяет промпт кинематографическими модификаторами.
    :param output_dir: Папка для сохранения сгенерированных файлов (по умолчанию: ./outputs).
    :param timeout_seconds: Максимальное время ожидания генерации (по умолчанию 150 секунд).
    """
    try:
        result = generate_flow_media(
            prompt=prompt,
            output_dir=output_dir if output_dir else None,
            media_type="video",
            reference_image=reference_image if reference_image else None,
            aspect_ratio=aspect_ratio if aspect_ratio else None,
            camera_motion=camera_motion if camera_motion else None,
            mute_audio=mute_audio,
            expand_prompt_flag=expand_prompt,
            timeout_sec=timeout_seconds
        )
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "prompt": prompt
        }, ensure_ascii=False, indent=2)

@app.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True
    )
)
def flow_frames_to_video(
    start_frame: str,
    end_frame: str,
    prompt: str = "",
    aspect_ratio: str = "",
    output_dir: str = "",
    timeout_seconds: int = 180
) -> str:
    """
    Сгенерировать видео через Veo с плавной анимацией между стартовым и финальным кадрами (Frames-to-Video).
    
    :param start_frame: Путь к исходному изображению (первый кадр видео).
    :param end_frame: Путь к конечному изображению (финальный кадр видео).
    :param prompt: Опциональное описание перехода или динамики между кадрами.
    :param aspect_ratio: Соотношение сторон видео: '16:9', '9:16', '1:1', '4:3'.
    :param output_dir: Папка для сохранения видеофайла.
    :param timeout_seconds: Максимальное время ожидания генерации (по умолчанию 180 секунд).
    """
    try:
        result = generate_frames_to_video(
            start_frame=start_frame,
            end_frame=end_frame,
            prompt=prompt,
            aspect_ratio=aspect_ratio if aspect_ratio else None,
            output_dir=output_dir if output_dir else None,
            timeout_sec=timeout_seconds
        )
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "start_frame": start_frame,
            "end_frame": end_frame
        }, ensure_ascii=False, indent=2)

@app.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True
    )
)
def flow_extend_video(
    tile_index: int = -1,
    prompt: str = "",
    output_dir: str = "",
    timeout_seconds: int = 180
) -> str:
    """
    Продлить ранее сгенерированный видеоролик еще на 5-8 секунд (Veo Video Extend).
    
    :param tile_index: Индекс плитки с видео в проекте Google Flow (-1 для последнего).
    :param prompt: Описание продолжения действия / сюжета на английском языке.
    :param output_dir: Папка для сохранения продленного видео.
    :param timeout_seconds: Максимальное время ожидания генерации (по умолчанию 180 секунд).
    """
    try:
        result = extend_flow_video(
            tile_index=tile_index,
            prompt=prompt,
            output_dir=output_dir if output_dir else None,
            timeout_sec=timeout_seconds
        )
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "tile_index": tile_index
        }, ensure_ascii=False, indent=2)

@app.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True
    )
)
def flow_upscale_image(
    tile_index: int = -1,
    output_dir: str = "",
    timeout_seconds: int = 90
) -> str:
    """
    Получить 2K вариант уже сгенерированного изображения в проекте Google Flow.
    
    :param tile_index: Индекс плитки с изображением (-1 для последнего сгенерированного).
    :param output_dir: Папка для сохранения 2K файла (по умолчанию: ./outputs).
    :param timeout_seconds: Максимальное время ожидания апскейла (по умолчанию 90 секунд).
    """
    try:
        result = upscale_flow_image(
            tile_index=tile_index,
            output_dir=output_dir if output_dir else None,
            timeout_sec=timeout_seconds
        )
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "tile_index": tile_index
        }, ensure_ascii=False, indent=2)

@app.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True
    )
)
def flow_edit_image(
    prompt: str,
    tile_index: int = -1,
    reference_image: str = "",
    aspect_ratio: str = "",
    model_name: str = "nano_banana_2.1",
    upscale_2k: bool = False,
    output_dir: str = "",
    timeout_seconds: int = 90
) -> str:
    """
    Внести правки в ранее сгенерированное изображение или сгенерировать вариацию по референсу.
    
    :param prompt: Описание изменений или уточняющий промпт на английском языке.
    :param tile_index: Индекс плитки с исходным изображением (-1 для последнего сгенерированного).
    :param reference_image: Локальный путь к новому референсному изображению (если заменяет плитку).
    :param aspect_ratio: Новое соотношение сторон: '16:9', '9:16', '1:1', '4:3'.
    :param model_name: Модель: 'nano_banana_2.1', 'nano_banana_pro', 'nano_banana_2_lite'.
    :param upscale_2k: Если True, запрашивает результат в разрешении 2K.
    :param output_dir: Папка для сохранения файлов (по умолчанию: ./outputs).
    :param timeout_seconds: Максимальное время ожидания (по умолчанию 90 секунд).
    """
    try:
        result = edit_flow_image(
            prompt=prompt,
            tile_index=tile_index,
            reference_image=reference_image if reference_image else None,
            aspect_ratio=aspect_ratio if aspect_ratio else None,
            upscale_2k=upscale_2k,
            output_dir=output_dir if output_dir else None,
            model_name=model_name,
            timeout_sec=timeout_seconds
        )
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "prompt": prompt,
            "tile_index": tile_index
        }, ensure_ascii=False, indent=2)

@app.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True
    )
)
def flow_finalize_asset(
    target_path: str,
    source_file: str = "",
    tile_index: int = -1,
    upscale_2k: bool = True,
    timeout_seconds: int = 90
) -> str:
    """
    Финализировать черновик (Шаг 3 Studio Pipeline): атомарно апскейлит изображение до 2K и копирует в проект пользователя.
    
    :param target_path: Целевой путь для сохранения файла в проекте (например: 'src/assets/hero.png' или 'public/logo.png').
    :param source_file: Локальный путь к сгенерированному черновику.
    :param tile_index: Индекс плитки во Flow для апскейла (-1 для последней плитки).
    :param upscale_2k: Если True и ассет является изображением, выполняет 2K апскейл перед копированием.
    :param timeout_seconds: Максимальное время ожидания финализации (по умолчанию 90 секунд).
    """
    try:
        result = finalize_asset(
            target_path=target_path,
            source_file=source_file if source_file else None,
            tile_index=tile_index,
            upscale_2k=upscale_2k,
            timeout_sec=timeout_seconds
        )
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "target_path": target_path
        }, ensure_ascii=False, indent=2)

@app.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True
    )
)
def flow_regenerate_tile(
    tile_index: int = -1,
    output_dir: str = "",
    timeout_seconds: int = 90
) -> str:
    """
    Перезапустить генерацию выбранной плитки на холсте Google Flow ('Сгенерировать повторно').
    
    :param tile_index: Индекс плитки на холсте (-1 для последней созданной плитки).
    :param output_dir: Папка для сохранения повторно сгенерированного файла.
    :param timeout_seconds: Максимальное время ожидания генерации (по умолчанию 90 секунд).
    """
    try:
        result = regenerate_flow_tile(
            tile_index=tile_index,
            output_dir=output_dir if output_dir else None,
            timeout_sec=timeout_seconds
        )
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "tile_index": tile_index
        }, ensure_ascii=False, indent=2)

@app.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True
    )
)
def flow_list_projects() -> str:
    """
    Получить реестр всех проектов пользователя в Google Flow с их ID и постоянными ссылками.
    """
    try:
        projects = list_flow_projects()
        return json.dumps({
            "success": True,
            "count": len(projects),
            "projects": projects
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        }, ensure_ascii=False, indent=2)

@app.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True
    )
)
def flow_create_project(
    name: str = ""
) -> str:
    """
    Создать новый изолированный проект в Google Flow под конкретную задачу.
    
    :param name: Название нового проекта (опционально).
    """
    try:
        result = create_flow_project(name=name)
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "name": name
        }, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    if hasattr(sys.stdout, "buffer") and sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        except Exception:
            pass
    app.run(transport="stdio")
