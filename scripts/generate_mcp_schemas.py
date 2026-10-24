"""
Автоматический генератор и синхронизатор JSON-схем MCP для Google Flow.
Читает актуальные инструменты из server.py и обновляет схемы в ~/.gemini/antigravity/mcp/google-flow/
"""

import sys
import json
import asyncio
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import server

SCHEMAS_DIR = Path("C:/Users/voron/.gemini/antigravity/mcp/google-flow")

def sync_schemas():
    SCHEMAS_DIR.mkdir(parents=True, exist_ok=True)
    tools = asyncio.run(server.app.list_tools())
    
    print(f"[*] Синхронизация {len(tools)} инструментов в {SCHEMAS_DIR}...")
    for tool in tools:
        schema_data = {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.input_schema
        }
        dest_file = SCHEMAS_DIR / f"{tool.name}.json"
        with open(dest_file, "w", encoding="utf-8") as f:
            json.dump(schema_data, f, ensure_ascii=False, indent=2)
        print(f"[+] Обновлена схема: {dest_file.name}")

    print("[SUCCESS] Все схемы инструментов успешно обновлены!")

if __name__ == "__main__":
    sync_schemas()
