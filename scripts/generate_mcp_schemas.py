"""
Автоматический генератор и синхронизатор JSON-схем MCP для Google Flow.
Синхронизирует схемы в локальную директорию репозитория (schemas/)
и в глобальную директорию Antigravity (~/.gemini/antigravity/mcp/google-flow/)
"""

import sys
import json
import asyncio
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import server

REPO_SCHEMAS_DIR = PROJECT_ROOT / "schemas"
GLOBAL_SCHEMAS_DIR = Path.home() / ".gemini" / "antigravity" / "mcp" / "google-flow"

def sync_schemas():
    target_dirs = [REPO_SCHEMAS_DIR]
    if GLOBAL_SCHEMAS_DIR.parent.exists() or Path.home().exists():
        target_dirs.append(GLOBAL_SCHEMAS_DIR)

    for target_dir in target_dirs:
        target_dir.mkdir(parents=True, exist_ok=True)

    tools = asyncio.run(server.app.list_tools())
    
    print(f"[*] Синхронизация {len(tools)} инструментов в целевые директории...")
    for tool in tools:
        schema_data = {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.input_schema
        }
        if tool.annotations:
            schema_data["annotations"] = tool.annotations.model_dump(by_alias=True, exclude_none=True)

        for target_dir in target_dirs:
            dest_file = target_dir / f"{tool.name}.json"
            with open(dest_file, "w", encoding="utf-8") as f:
                json.dump(schema_data, f, ensure_ascii=False, indent=2)
            print(f"[+] Обновлена схема: {dest_file}")

    print("[SUCCESS] Все схемы инструментов успешно обновлены!")

if __name__ == "__main__":
    sync_schemas()
