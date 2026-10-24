"""
Google Flow MCP — Prompt Expander & Cinematic Director
Модуль для автоматического расширения промптов, стилизации и применения настроек камеры/соотношения сторон.
"""

from typing import Optional, Dict

ASPECT_RATIOS = ["16:9", "9:16", "1:1", "4:3"]

ASPECT_FRAMING: Dict[str, str] = {
    "16:9": "widescreen 16:9 cinematic framing",
    "9:16": "vertical 9:16 mobile composition",
    "1:1": "centered 1:1 square framing",
    "4:3": "classic 4:3 ratio composition"
}

CAMERA_MOTIONS: Dict[str, str] = {
    "pan_left": "camera smoothly panning to the left, parallax depth",
    "pan_right": "camera smoothly panning to the right, parallax depth",
    "tilt_up": "camera tilting upwards, cinematic perspective",
    "tilt_down": "camera tilting downwards, revealing ground details",
    "zoom_in": "slow cinematic push in / slow zoom in towards subject",
    "zoom_out": "slow cinematic pull back / zoom out revealing the wider environment",
    "orbit": "smooth circular orbiting camera movement around the subject",
    "static": "steady locked-off tripod shot, no camera shake",
    "tracking": "smooth tracking camera following the subject action",
    "aerial": "aerial drone perspective, wide establishing view"
}

IMAGE_ENHANCEMENT_TAGS = [
    "masterpiece",
    "highly detailed",
    "8k resolution",
    "photorealistic texture",
    "cinematic lighting",
    "volumetric atmosphere",
    "sharp focus"
]

VIDEO_ENHANCEMENT_TAGS = [
    "photorealistic 4k video",
    "smooth motion",
    "cinematic color grading",
    "depth of field",
    "natural lighting"
]

def format_camera_prompt(camera_motion: Optional[str]) -> str:
    """Возвращает текстовый модификатор движения камеры."""
    if not camera_motion:
        return ""
    key = camera_motion.lower().strip().replace("-", "_").replace(" ", "_")
    return CAMERA_MOTIONS.get(key, f"cinematic {camera_motion} camera motion")

def expand_prompt(
    base_prompt: str,
    media_type: str = "image",
    camera_motion: Optional[str] = None,
    aspect_ratio: Optional[str] = None
) -> str:
    """
    Развертывает промпт пользователя, добавляя ключевые кинематографические модификаторы,
    освещение, ракурсы и композицию для моделей Imagen / Veo.
    """
    prompt = base_prompt.strip()

    # Добавление композиции соотношения сторон
    if aspect_ratio:
        norm_ratio = validate_aspect_ratio(aspect_ratio)
        if norm_ratio and norm_ratio in ASPECT_FRAMING:
            framing = ASPECT_FRAMING[norm_ratio]
            if framing.lower() not in prompt.lower():
                prompt = f"{prompt}, {framing}"

    # Добавление движения камеры (актуально для видео)
    cam_str = format_camera_prompt(camera_motion)
    if cam_str and cam_str.lower() not in prompt.lower():
        prompt = f"{prompt}, {cam_str}"

    # Добавление тегов качества и стиля
    tags = IMAGE_ENHANCEMENT_TAGS if media_type == "image" else VIDEO_ENHANCEMENT_TAGS
    
    # Добавляем только те теги, которых еще нет в тексте
    missing_tags = [t for t in tags if t.lower() not in prompt.lower()]
    if missing_tags:
        prompt = f"{prompt}, {', '.join(missing_tags[:3])}"

    return prompt

def validate_aspect_ratio(aspect_ratio: Optional[str]) -> Optional[str]:
    """Проверяет и строго нормализует соотношение сторон. Возвращает None, если некорректно."""
    if not aspect_ratio:
        return None
    cleaned = str(aspect_ratio).strip().lower()
    mapping = {
        "16:9": "16:9",
        "16/9": "16:9",
        "landscape": "16:9",
        "horizontal": "16:9",
        "9:16": "9:16",
        "9/16": "9:16",
        "portrait": "9:16",
        "vertical": "9:16",
        "1:1": "1:1",
        "square": "1:1",
        "4:3": "4:3",
        "4/3": "4:3"
    }
    return mapping.get(cleaned, None)
