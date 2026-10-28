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
    """Проверка регистрации всех 11 инструментов в MCP сервере."""
    tools = await app.list_tools()
    registered = [tool.name for tool in tools]
    expected_tools = [
        "flow_check_status",
        "flow_generate_image",
        "flow_generate_video",
        "flow_frames_to_video",
        "flow_extend_video",
        "flow_upscale_image",
        "flow_edit_image",
        "flow_finalize_asset",
        "flow_regenerate_tile",
        "flow_list_projects",
        "flow_create_project"
    ]
    for expected in expected_tools:
        assert expected in registered, f"Инструмент {expected} не зарегистрирован в MCPServer"

@pytest.mark.asyncio
async def test_mcp_tool_annotations():
    """Проверка наличия полных аннотаций безопасности (readOnlyHint, destructiveHint, etc.) для всех инструментов."""
    tools = await app.list_tools()
    assert len(tools) >= 11
    for tool in tools:
        assert tool.annotations is not None, f"Tool '{tool.name}' is missing annotations"
        ann = tool.annotations
        assert isinstance(ann.read_only_hint, bool), f"Tool '{tool.name}' read_only_hint must be boolean"
        assert isinstance(ann.destructive_hint, bool), f"Tool '{tool.name}' destructive_hint must be boolean"
        assert isinstance(ann.idempotent_hint, bool), f"Tool '{tool.name}' idempotent_hint must be boolean"
        assert isinstance(ann.open_world_hint, bool), f"Tool '{tool.name}' open_world_hint must be boolean"

def test_aspect_ratio_3_4_support():
    """Проверка поддержки портретного соотношения сторон 3:4."""
    from expander import validate_aspect_ratio, expand_prompt
    assert validate_aspect_ratio("3:4") == "3:4"
    assert validate_aspect_ratio("3/4") == "3:4"
    expanded = expand_prompt("portrait shot", aspect_ratio="3:4")
    assert "3:4" in expanded
