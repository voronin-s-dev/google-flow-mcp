import json
import sys
import io
from pathlib import Path
from mcp.server.mcpserver import MCPServer
from engine import generate_flow_media, is_cdp_available, STORAGE_FILE

# UTF-8 stdout для Windows консоли
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

app = MCPServer("google-flow")

@app.tool()
def flow_check_status() -> str:
    """
    Проверить доступность Google Flow и статус авторизации (CDP / Headless).
    """
    cdp_active = is_cdp_available()
    auth_exists = STORAGE_FILE.exists()
    return json.dumps({
        "status": "ready" if (cdp_active or auth_exists) else "needs_auth",
        "cdp_active": cdp_active,
        "headless_auth_saved": auth_exists,
        "message": (
            "Chrome с портом отладки активен." if cdp_active else
            "Готов к работе в скрытом Headless-режиме с сохраненными куками." if auth_exists else
            "Требуется однократный вход в Google-аккаунт."
        )
    }, ensure_ascii=False, indent=2)

@app.tool()
def flow_generate_image(prompt: str, output_dir: str = "", timeout_seconds: int = 90) -> str:
    """
    Сгенерировать высококачественное изображение через Google Flow (Imagen 3/4) в фоне.
    
    :param prompt: Детальный промпт на английском языке (стиль, освещение, композиция, детали).
    :param output_dir: Папка для сохранения сгенерированных файлов (по умолчанию: ./outputs).
    :param timeout_seconds: Максимальное время ожидания генерации (по умолчанию 90 секунд).
    """
    try:
        result = generate_flow_media(
            prompt=prompt,
            output_dir=output_dir if output_dir else None,
            media_type="image",
            timeout_sec=timeout_seconds
        )
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "prompt": prompt
        }, ensure_ascii=False, indent=2)

@app.tool()
def flow_generate_video(prompt: str, output_dir: str = "", timeout_seconds: int = 150) -> str:
    """
    Сгенерировать кинематографичное видео через Google Flow (Veo) в фоне.
    
    :param prompt: Детальный кинематографичный промпт на английском языке (движение камеры, действие, свет).
    :param output_dir: Папка для сохранения сгенерированных файлов (по умолчанию: ./outputs).
    :param timeout_seconds: Максимальное время ожидания генерации (по умолчанию 150 секунд).
    """
    try:
        result = generate_flow_media(
            prompt=prompt,
            output_dir=output_dir if output_dir else None,
            media_type="video",
            timeout_sec=timeout_seconds
        )
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "prompt": prompt
        }, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    app.run(transport="stdio")
