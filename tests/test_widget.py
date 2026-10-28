"""Unit tests for Generative UI widget generator."""

from pathlib import Path
from widget import generate_flow_card_html, save_flow_card


def test_generate_flow_card_html():
    html_out = generate_flow_card_html(
        media_paths=["outputs/test1.png", "outputs/test2.png"],
        prompt="A futuristic neon city street in Tokyo, 8k",
        aspect_ratio="9:16",
        media_type="image",
        batch_count=2,
        tile_index=3,
        is_autonomous=False,
    )
    assert "<!DOCTYPE html>" in html_out
    assert "tailwindcss.min.js" in html_out
    assert "9:16" in html_out
    assert "test1.png" in html_out
    assert "test2.png" in html_out
    assert "2K Upscale" in html_out


def test_save_flow_card(tmp_path):
    card_path = save_flow_card(
        media_paths=["test.png"],
        prompt="Test prompt",
        output_dir=str(tmp_path),
        aspect_ratio="16:9",
        filename="test_card.html",
    )
    assert Path(card_path).exists()
    content = Path(card_path).read_text(encoding="utf-8")
    assert "16:9" in content
