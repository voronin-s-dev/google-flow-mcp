"""Google Flow Studio — Generative UI Widget Generator for Antigravity & Web Clients.

Generates self-contained, theme-adaptive HTML cards for inline embedding (<agent-embed>)
in chat and standalone preview artifacts, fully conforming to Antigravity Generative UI standards.
"""

from __future__ import annotations

import html
import os
from pathlib import Path
from typing import List, Optional


def generate_flow_card_html(
    media_paths: List[str],
    prompt: str,
    aspect_ratio: str = "1:1",
    media_type: str = "image",  # "image" or "video"
    batch_count: int = 1,
    status_label: str = "Черновик готов",
    model_name: str = "Imagen 3/4",
    tile_index: int = -1,
    is_autonomous: bool = False,
) -> str:
    """Generate self-contained HTML for an Antigravity Generative UI card.

    Uses official gstatic Tailwind CDN and native Antigravity CSS theme variables:
    --foreground, --muted-foreground, --card, --border, --primary, --accent.
    Maintains compact vertical budget (under 460px) for seamless inline embedding.
    """
    safe_prompt = html.escape(prompt)
    safe_status = html.escape(status_label)
    safe_aspect = html.escape(aspect_ratio)
    safe_model = html.escape(model_name)

    # Format media items into JavaScript array
    js_media_items = []
    for p in media_paths:
        abs_p = Path(p).resolve().as_posix()
        js_media_items.append(f"'file:///{abs_p}'")
    js_media_array = "[" + ", ".join(js_media_items) + "]"

    initial_media = f"file:///{Path(media_paths[0]).resolve().as_posix()}" if media_paths else ""

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>
  <style>
    /* Antigravity Design System fallback tokens */
    :root {{
      --foreground: #f1f5f9;
      --muted-foreground: #94a3b8;
      --card: rgba(30, 41, 59, 0.7);
      --border: rgba(148, 163, 184, 0.15);
      --primary: #38bdf8;
      --primary-foreground: #0f172a;
      --accent: #818cf8;
    }}
    .light {{
      --foreground: #0f172a;
      --muted-foreground: #64748b;
      --card: rgba(255, 255, 255, 0.85);
      --border: rgba(15, 23, 42, 0.1);
      --primary: #0284c7;
      --primary-foreground: #ffffff;
      --accent: #6366f1;
    }}
    .backdrop-blur {{
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
    }}
  </style>
</head>
<body class="bg-transparent text-[var(--foreground)] antialiased p-2 m-0 select-none font-sans">
  <div class="bg-[var(--card)] backdrop-blur text-[var(--foreground)] border border-[var(--border)] rounded-2xl p-3.5 shadow-lg flex flex-col gap-2.5 max-w-xl mx-auto">
    
    <!-- Header -->
    <div class="flex items-center justify-between gap-2 border-b border-[var(--border)] pb-2.5">
      <div class="flex items-center gap-2">
        <div class="w-6 h-6 rounded-lg bg-gradient-to-tr from-sky-500 to-indigo-500 flex items-center justify-center text-white font-bold text-xs shadow-sm">
          F
        </div>
        <div>
          <div class="text-xs font-semibold tracking-wide flex items-center gap-1.5">
            Google Flow Studio
            <span class="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-sky-500/15 text-sky-400 border border-sky-500/20">
              {safe_model}
            </span>
          </div>
        </div>
      </div>
      <div class="flex items-center gap-1.5">
        <span class="text-[11px] font-medium px-2 py-0.5 rounded-md bg-[var(--border)] text-[var(--foreground)]">
          {safe_aspect}
        </span>
        <span class="text-[11px] font-medium px-2 py-0.5 rounded-md {'bg-purple-500/15 text-purple-400 border border-purple-500/20' if is_autonomous else 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20'}">
          {'⚡ Автономный пайплайн' if is_autonomous else safe_status}
        </span>
      </div>
    </div>

    <!-- Media Preview Container -->
    <div class="relative w-full rounded-xl overflow-hidden bg-black/20 border border-[var(--border)] flex items-center justify-center min-h-[190px] max-h-[220px]">
      {'<video id="main-video" controls class="max-h-[210px] max-w-full rounded-lg object-contain shadow-inner" src="' + initial_media + '"></video>' if media_type == "video" else '<img id="main-img" class="max-h-[210px] max-w-full rounded-lg object-contain transition-all duration-200" src="' + initial_media + '" alt="Flow Preview" />'}
      
      <!-- Multi-batch selector if batch > 1 -->
      <div id="batch-bar" class="absolute bottom-2 left-2 right-2 flex items-center justify-center gap-1.5 {'hidden' if len(media_paths) <= 1 else ''}">
        <div class="bg-black/60 backdrop-blur px-2 py-1 rounded-full border border-white/10 flex items-center gap-1">
          <!-- Thumbnail buttons generated dynamically -->
        </div>
      </div>
    </div>

    <!-- Prompt Bar -->
    <div class="bg-black/10 rounded-lg p-2 text-xs text-[var(--muted-foreground)] flex items-start justify-between gap-2 border border-[var(--border)]">
      <div class="line-clamp-2 leading-relaxed italic" title="{safe_prompt}">
        "{safe_prompt}"
      </div>
      <button onclick="copyToClipboard('{safe_prompt}', 'Промпт скопирован!')" 
              class="shrink-0 p-1 rounded hover:bg-white/10 text-[var(--foreground)] transition-colors" title="Скопировать промпт">
        📋
      </button>
    </div>

    <!-- Quick Action Buttons -->
    <div class="grid grid-cols-4 gap-1.5 pt-0.5">
      <button onclick="sendAction('Апскейли вариант ' + (currentIdx + 1) + ' до 2K и сохрани в проект')"
              class="flex items-center justify-center gap-1 py-1.5 px-2 rounded-lg bg-[var(--primary)] text-[var(--primary-foreground)] font-medium text-xs shadow hover:opacity-90 active:scale-95 transition-all">
        <span>💎</span> 2K Upscale
      </button>
      
      <button onclick="sendAction('Преврати этот кадр в 9:16 видео через Veo с кинематографичным движением')"
              class="flex items-center justify-center gap-1 py-1.5 px-2 rounded-lg bg-[var(--border)] hover:bg-white/10 text-[var(--foreground)] font-medium text-xs active:scale-95 transition-all">
        <span>🎬</span> В видео Veo
      </button>

      <button onclick="sendAction('Сгенерируй повторно плитку ' + {tile_index} + ' во Flow')"
              class="flex items-center justify-center gap-1 py-1.5 px-2 rounded-lg bg-[var(--border)] hover:bg-white/10 text-[var(--foreground)] font-medium text-xs active:scale-95 transition-all">
        <span>🔄</span> Повторить
      </button>

      <button onclick="sendAction('Сделай вариацию этого кадра: добавь больше контраста и неоновых отблесков')"
              class="flex items-center justify-center gap-1 py-1.5 px-2 rounded-lg bg-[var(--border)] hover:bg-white/10 text-[var(--foreground)] font-medium text-xs active:scale-95 transition-all">
        <span>✏️</span> Вариация
      </button>
    </div>

    <!-- Notification Toast -->
    <div id="toast" class="hidden text-center text-[11px] text-sky-400 font-medium py-0.5 transition-all">
      Готово
    </div>

  </div>

  <script>
    const mediaItems = {js_media_array};
    let currentIdx = 0;
    const isVideo = '{media_type}' === 'video';

    // Populate batch buttons if multiple
    const batchBar = document.getElementById('batch-bar');
    if (mediaItems.length > 1 && batchBar) {{
      const container = batchBar.firstElementChild;
      container.innerHTML = '';
      mediaItems.forEach((src, idx) => {{
        const btn = document.createElement('button');
        btn.className = `px-2 py-0.5 rounded text-[11px] font-bold transition-all ${{idx === 0 ? 'bg-sky-500 text-white shadow' : 'text-slate-300 hover:text-white'}}`;
        btn.innerText = `x${{idx + 1}}`;
        btn.onclick = () => selectMedia(idx);
        container.appendChild(btn);
      }});
    }}

    function selectMedia(idx) {{
      currentIdx = idx;
      if (isVideo) {{
        const vid = document.getElementById('main-video');
        if (vid) vid.src = mediaItems[idx];
      }} else {{
        const img = document.getElementById('main-img');
        if (img) img.src = mediaItems[idx];
      }}
      // Update buttons
      if (batchBar) {{
        const btns = batchBar.querySelectorAll('button');
        btns.forEach((b, i) => {{
          b.className = `px-2 py-0.5 rounded text-[11px] font-bold transition-all ${{i === idx ? 'bg-sky-500 text-white shadow' : 'text-slate-300 hover:text-white'}}`;
        }});
      }}
    }}

    function showToast(text) {{
      const toast = document.getElementById('toast');
      if (!toast) return;
      toast.innerText = text;
      toast.classList.remove('hidden');
      setTimeout(() => toast.classList.add('hidden'), 2500);
    }}

    function copyToClipboard(text, msg) {{
      if (navigator.clipboard) {{
        navigator.clipboard.writeText(text).then(() => showToast(msg || 'Скопировано в буфер!'));
      }} else {{
        showToast(msg || 'Скопировано!');
      }}
    }}

    function sendAction(commandText) {{
      copyToClipboard(commandText, 'Команда скопирована! Вставьте в чат: "' + commandText + '"');
    }}
  </script>
</body>
</html>
"""


def save_flow_card(
    media_paths: List[str],
    prompt: str,
    output_dir: Optional[str] = None,
    aspect_ratio: str = "1:1",
    media_type: str = "image",
    batch_count: int = 1,
    status_label: str = "Черновик готов",
    model_name: str = "Imagen 3/4",
    tile_index: int = -1,
    is_autonomous: bool = False,
    filename: Optional[str] = None,
) -> str:
    """Save the HTML card into output_dir and return its absolute path."""
    if output_dir is None:
        output_dir = Path.cwd() / "outputs"
    os.makedirs(output_dir, exist_ok=True)

    if not filename:
        import time
        filename = f"flow_card_{int(time.time())}.html"

    target_path = Path(output_dir) / filename
    html_content = generate_flow_card_html(
        media_paths=media_paths,
        prompt=prompt,
        aspect_ratio=aspect_ratio,
        media_type=media_type,
        batch_count=batch_count,
        status_label=status_label,
        model_name=model_name,
        tile_index=tile_index,
        is_autonomous=is_autonomous,
    )

    with open(target_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return str(target_path.resolve())
