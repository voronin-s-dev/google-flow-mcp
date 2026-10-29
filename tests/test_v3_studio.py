import pytest
import json
from pathlib import Path
import tempfile
import shutil

from expander import (
    validate_aspect_ratio,
    format_camera_prompt,
    expand_prompt,
    ASPECT_RATIOS,
    CAMERA_MOTIONS
)
from engine import finalize_asset
from server import app

def test_aspect_ratio_validation():
    assert validate_aspect_ratio("16:9") == "16:9"
    assert validate_aspect_ratio("landscape") == "16:9"
    assert validate_aspect_ratio("9:16") == "9:16"
    assert validate_aspect_ratio("portrait") == "9:16"
    assert validate_aspect_ratio("1:1") == "1:1"
    assert validate_aspect_ratio("square") == "1:1"
    assert validate_aspect_ratio("4:3") == "4:3"
    assert validate_aspect_ratio(None) is None
    assert validate_aspect_ratio("invalid_ratio") is None

def test_camera_motion_formatting():
    assert "panning to the left" in format_camera_prompt("pan_left")
    assert "push in" in format_camera_prompt("zoom_in")
    assert "circular orbiting" in format_camera_prompt("orbit")
    assert format_camera_prompt(None) == ""

def test_prompt_expander_image():
    base = "A cute cat on a roof"
    expanded = expand_prompt(base, media_type="image")
    assert base in expanded
    assert any(tag in expanded for tag in ["masterpiece", "8k resolution", "lighting", "detailed"])

def test_prompt_expander_video_with_camera():
    base = "Spaceship flying through an asteroid field"
    expanded = expand_prompt(base, media_type="video", camera_motion="pan_right")
    assert "panning to the right" in expanded
    assert any(tag in expanded for tag in ["smooth motion", "4k", "lighting", "cinematic"])

def test_finalize_asset_copy():
    # Создаем временный исходный файл (черновик)
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        source = tmp_path / "draft_image.png"
        source.write_bytes(b"FAKE_PNG_IMAGE_CONTENT_FOR_TESTING")

        target = tmp_path / "src" / "assets" / "hero.png"

        result = finalize_asset(
            target_path=str(target),
            source_file=str(source),
            upscale_2k=False
        )

        assert result["success"] is True
        assert Path(result["target_path"]).exists()
        assert Path(result["target_path"]).read_bytes() == b"FAKE_PNG_IMAGE_CONTENT_FOR_TESTING"
        assert result["file_size_bytes"] == len(b"FAKE_PNG_IMAGE_CONTENT_FOR_TESTING")
        assert "![hero.png]" in result["markdown_link"]

def test_finalize_asset_same_file():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        source = tmp_path / "already_in_place.png"
        source.write_bytes(b"EXISTING_ASSET_CONTENT")

        result = finalize_asset(
            target_path=str(source),
            source_file=str(source),
            upscale_2k=False
        )
        assert result["success"] is True
        assert Path(result["target_path"]).read_bytes() == b"EXISTING_ASSET_CONTENT"

@pytest.mark.asyncio
async def test_all_v3_tools_registered():
    tools = await app.list_tools()
    tool_names = [t.name for t in tools]
    v3_tools = [
        "flow_check_status",
        "flow_generate_image",
        "flow_generate_video",
        "flow_frames_to_video",
        "flow_extend_video",
        "flow_upscale_image",
        "flow_edit_image",
        "flow_finalize_asset"
    ]
    for expected in v3_tools:
        assert expected in tool_names, f"Tool {expected} must be registered in MCPServer"

def test_upscale_2k_preserves_aspect_ratio():
    from engine import upscale_image_fast_2k, HAS_PIL
    if not HAS_PIL:
        pytest.skip("PIL is not installed")
    from PIL import Image

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        # Создаем тестовое изображение 3:4 (300x400)
        src = tmp_path / "test_3_4.png"
        dest = tmp_path / "test_2k.png"
        img = Image.new("RGB", (300, 400), color=(255, 0, 0))
        img.save(src)

        ok = upscale_image_fast_2k(src, dest)
        assert ok is True
        assert dest.exists()

        with Image.open(dest) as up:
            assert max(up.width, up.height) >= 2048
            # Проверяем сохранение соотношения 3:4 (0.75)
            assert round(up.width / up.height, 2) == 0.75
