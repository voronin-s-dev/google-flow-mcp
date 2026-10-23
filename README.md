# 🎨 Google Flow MCP Server

An MCP (Model Context Protocol) server that empowers AI agents (Antigravity, Claude Desktop, Cursor, Cline, etc.) to generate **production-quality images and videos using Google Flow (Imagen 3/4 & Veo models)** completely in the background without per-token API costs by utilizing your existing **Google AI Pro** subscription.

---

## ✨ Features

* **Zero API Cost**: Uses your active Google AI Pro / Google Flow subscription quotas instead of metered cloud API calls.
* **100% Invisible Background Execution**: Runs via headless browser automation. No windows pop up, no icons on the taskbar, no focus stealing.
* **Veo & Imagen Models**: High-resolution image generation and cinematic video generation.
* **Direct Asset Delivery**: Automatically downloads rendered media files directly into your project's assets folder.
* **Secure Local Auth**: Your Google credentials and session cookies never leave your local machine.

---

## 🔒 Security & How Authentication Works

### How your account is authenticated:
1. When you run `python auth.py`, a standard browser window opens to `https://flow.google.com`.
2. You log into your own Google Account manually (including 2FA).
3. The script extracts only the required session cookies and stores them in a local file: `storage_state.json`.
4. **`storage_state.json` is strictly ignored by `.gitignore`** and will never be pushed to version control.
5. In subsequent operations, the MCP server runs silently in `headless` mode, passing the local session tokens directly to the internal rendering engine.

> [!NOTE]
> No passwords, API keys, or personal tokens are ever stored in code or uploaded to any remote server.

---

## 🚀 Quick Start

### 1. Prerequisites
* Python 3.10 or newer
* Google Chrome installed (or Chromium)
* Google Account with Google AI Pro or access to Google Flow (`flow.google.com`)

### 2. Installation

Clone this repository and install dependencies:

```bash
git clone https://github.com/voronin-s-dev/google-flow-mcp.git
cd google-flow-mcp

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux / macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
playwright install chromium
```

### 3. One-Time Login

Run the interactive authorization script:

```bash
python auth.py
```

* A Chrome window will open.
* Log into your Google account on `flow.google.com`.
* Once you see your Flow dashboard, switch back to the terminal and press `ENTER`.
* Your session is now saved locally to `storage_state.json`.

---

## ⚙️ Configuration in MCP Clients

Add the server to your MCP client configuration:

### Antigravity (`~/.gemini/config/mcp_config.json`):
```json
{
  "mcpServers": {
    "google-flow": {
      "command": "C:\\path\\to\\google-flow-mcp\\.venv\\Scripts\\python.exe",
      "args": ["C:\\path\\to\\google-flow-mcp\\server.py"]
    }
  }
}
```

### Claude Desktop (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "google-flow": {
      "command": "python",
      "args": ["/absolute/path/to/google-flow-mcp/server.py"]
    }
  }
}
```

---

## 🛠 Available Tools

| Tool | Parameters | Description |
|---|---|---|
| **`flow_generate_image`** | `prompt` (string, required)<br>`output_dir` (string, optional)<br>`timeout_seconds` (int, default: 90) | Generates images via Imagen 3/4 and saves `.png` files to the target folder. |
| **`flow_generate_video`** | `prompt` (string, required)<br>`output_dir` (string, optional)<br>`timeout_seconds` (int, default: 150) | Generates cinematic video clips via Veo and saves `.mp4` files. |
| **`flow_check_status`** | *none* | Checks whether the session is authenticated and ready to generate. |

---

## 📄 License

MIT License. Feel free to use, modify, and distribute.
