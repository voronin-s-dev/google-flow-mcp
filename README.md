# Google Flow MCP Server

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Playwright](https://img.shields.io/badge/playwright-v1.40+-green.svg)](https://playwright.dev/)
[![M8ven Score](https://m8ven.ai/badge/mcp/voronin-s-dev/google-flow-mcp)](https://m8ven.ai/mcp/voronin-s-dev/google-flow-mcp?s=readme)

An MCP (Model Context Protocol) server that empowers AI agents (Antigravity, Claude Desktop, Cursor) to generate production-quality visual media using **Google Flow** (powered by Imagen and Veo models) completely in the background, with **zero per-token API costs** by leveraging your Google AI Pro subscription.

---

## 🌟 Key Features

* **Zero API Cost**: Uses your active Google AI Pro / Google Flow subscription quotas instead of metered cloud API calls.
* **100% Invisible Background Execution**: Runs via headless browser automation or attaches seamlessly to Chrome via CDP (port 9222). No focus stealing.
* **V3 Studio Staging Pipeline**: 3-step interactive draft review and finalization workflow (`flow_finalize_asset`) with automatic 2K upscaling.
* **Veo & Imagen Models**: High-resolution image generation and cinematic video generation.
* **Aspect Ratio Selection**: Support for `16:9`, `9:16`, `1:1`, `4:3`, and `3:4` (portrait/poster).
* **Batch Variation Multiplier**: Request up to 4 concurrent variations per prompt (`batch_count=1..4`).
* **Veo Audio Control**: Toggle native audio generation or mute soundtracks for custom audio scoring.
* **Cinematic Camera Director**: Controls camera motion (`pan_left`, `pan_right`, `tilt_up`, `tilt_down`, `zoom_in`, `zoom_out`, `orbit`, `static`).
* **Prompt Expander**: Automatic enrichment of prompts with professional lighting, optics, and atmospheric descriptors.
* **Frames-to-Video Animation**: Interpolate between starting (`start_frame`) and final (`end_frame`) images.
* **Video Extension**: Extend generated videos by another 5–8 seconds.
* **2K Upscaling**: Request 2K versions directly or upscale previously generated images.
* **Project Management**: List and create isolated projects directly from MCP tools.
* **Image-to-Image / Reference Input**: Attach local reference images to guide generation or seed video clips.
* **Direct Asset Delivery**: Automatically downloads rendered media files directly into your project's assets folder and provides Markdown embed links.

---

## 🎬 3-Step Studio Staging Workflow

```mermaid
flowchart LR
    Step1["1. Draft
    flow_generate_image/video
    (quick preview)"] --> Step2["2. Review & Edit
    Chat preview embed
    flow_edit_image"]
    Step2 --> Step3["3. Finalize
    flow_finalize_asset
    (2K upscale & code export)"]
```

---

## 🚀 Quick Start

### 1. Installation

```bash
git clone https://github.com/voronin-s-dev/google-flow-mcp.git
cd google-flow-mcp
uv venv
uv pip install -r requirements.txt
playwright install chromium
```

### 2. First-Time Authentication

Run the interactive login script once to save your session cookies:

```bash
uv run python auth.py
```

A browser window will open. Sign in to your Google Account with Google AI Pro access, navigate to [flow.google.com](https://flow.google.com), and the session state will automatically be saved to `storage_state.json`.

---

## 🛠 Available Tools

| Tool | Parameters | Description |
|---|---|---|
| **`flow_generate_image`** | `prompt` (string, required)<br>`reference_image` (string, optional)<br>`aspect_ratio` (string, optional: `16:9`, `9:16`, `1:1`, `4:3`, `3:4`)<br>`batch_count` (int, default: 1, 1..4)<br>`expand_prompt` (bool, default: False)<br>`upscale_2k` (bool, default: False)<br>`output_dir` (string, optional)<br>`timeout_seconds` (int, default: 90) | Generates images via Imagen 3/4. Supports reference input, aspect ratio (including 3:4), batch multipliers (x1–x4), prompt expansion, and 2K upscaling. |
| **`flow_generate_video`** | `prompt` (string, required)<br>`reference_image` (string, optional)<br>`aspect_ratio` (string, optional)<br>`camera_motion` (string, optional: `pan_left`, `orbit`, etc.)<br>`mute_audio` (bool, default: False)<br>`expand_prompt` (bool, default: False)<br>`output_dir` (string, optional)<br>`timeout_seconds` (int, default: 150) | Generates cinematic video clips via Veo with camera controls and optional audio muting. |
| **`flow_frames_to_video`** | `start_frame` (string, required)<br>`end_frame` (string, required)<br>`prompt` (string, optional)<br>`aspect_ratio` (string, optional)<br>`output_dir` (string, optional)<br>`timeout_seconds` (int, default: 180) | Generates a video interpolating between starting and ending frames. |
| **`flow_extend_video`** | `tile_index` (int, default: -1)<br>`prompt` (string, optional)<br>`output_dir` (string, optional)<br>`timeout_seconds` (int, default: 180) | Extends an existing video tile by an additional 5–8 seconds. |
| **`flow_finalize_asset`** | `target_path` (string, required)<br>`source_file` (string, optional)<br>`tile_index` (int, default: -1)<br>`upscale_2k` (bool, default: True)<br>`timeout_seconds` (int, default: 90) | Atomically upscales the chosen asset to 2K and saves it directly into the user's project folder. |
| **`flow_upscale_image`** | `tile_index` (int, default: -1)<br>`output_dir` (string, optional)<br>`timeout_seconds` (int, default: 90) | Upscales a previously generated image in the project to 2K resolution. |
| **`flow_edit_image`** | `prompt` (string, required)<br>`tile_index` (int, default: -1)<br>`reference_image` (string, optional)<br>`aspect_ratio` (string, optional)<br>`upscale_2k` (bool, default: False)<br>`output_dir` (string, optional)<br>`timeout_seconds` (int, default: 90) | Applies modifications or creates variations of an existing image. |
| **`flow_regenerate_tile`** | `tile_index` (int, default: -1)<br>`output_dir` (string, optional)<br>`timeout_seconds` (int, default: 90) | Triggers re-generation of a tile with the same prompt and parameters. |
| **`flow_list_projects`** | *none* | Lists existing Google Flow projects with their IDs and direct links. |
| **`flow_create_project`** | `name` (string, optional) | Creates a new isolated project in Google Flow. |
| **`flow_check_status`** | *none* | Checks whether the session is authenticated and ready to generate. |

---

## 🔒 Security, Privacy & Architecture

* **Local-First & Off-Cloud Execution**: The MCP server runs exclusively on your local workstation. It requires no intermediary cloud proxy or external telemetry service.
* **Controlled Network Endpoints**: All network communications are strictly bounded to:
  1. `https://flow.google.com` (Google's official web studio endpoint).
  2. `127.0.0.1:9222` (Local Chrome DevTools Protocol port, bound only to the local loopback interface).
* **Safe Credential Isolation**: Google session cookies (`storage_state.json`) and temporary Chrome profile data are stored locally and explicitly protected via `.gitignore` to prevent leakage.
* **MCP Tool Annotations**: Every exposed tool declares strict safety hints (`readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`) following MCP specifications, enabling client hosts to reason about side effects before execution.
* **Privacy Policy**: See detailed privacy terms in [PRIVACY.md](PRIVACY.md).

---

## 🧪 Testing & Verification

Run the test suite and contract harness:

```bash
# Run unit & contract tests
uv run pytest

# Run contract and live CDP selector verification
uv run python scripts/verify_harness.py
```

---

## 📄 License

MIT License. Feel free to use, modify, and distribute.
