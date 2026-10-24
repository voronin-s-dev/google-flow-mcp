import pytest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from verify_harness import check_mcp_contract

def test_mcp_tools_and_schemas_contract():
    """Детерминированная проверка соответствия инструментов server.py и JSON-схем MCP."""
    ok, errors = check_mcp_contract()
    assert ok, f"Нарушение контракта MCP схем:\n" + "\n".join(errors)
