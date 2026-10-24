import json
import pytest
from server import app, flow_check_status

def test_flow_check_status_json_format():
    """Проверка, что flow_check_status возвращает корректный JSON со статусом."""
    raw = flow_check_status()
    data = json.loads(raw)
    assert "status" in data
    assert data["status"] in ("ready", "needs_auth")
    assert "cdp_active" in data
    assert "headless_auth_saved" in data
    assert "message" in data

@pytest.mark.asyncio
async def test_mcp_registered_tools():
    """Проверка регистрации обязательных инструментов в MCP сервере."""
    tools = await app.list_tools()
    registered = [tool.name for tool in tools]
    expected_tools = [
        "flow_check_status",
        "flow_generate_image",
        "flow_generate_video",
        "flow_upscale_image",
        "flow_edit_image"
    ]
    for expected in expected_tools:
        assert expected in registered, f"Инструмент {expected} не зарегистрирован в MCPServer"
