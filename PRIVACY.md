# Privacy Policy

**Last Updated:** October 2026  
**Project:** Google Flow MCP Server (`google-flow-mcp`)  
**Repository:** [https://github.com/voronin-s-dev/google-flow-mcp](https://github.com/voronin-s-dev/google-flow-mcp)

---

## 1. Overview

Google Flow MCP is an open-source, local-first Model Context Protocol (MCP) server. It enables AI coding assistants and agents to generate image and video media by orchestrating Google Flow directly on the user's local machine.

We respect your privacy. This policy explains how data is handled when you run this server.

---

## 2. Zero Data Collection & Zero Telemetry

* **No Analytics:** The server does not contain telemetry, tracking code, or analytics beacons.
* **No External Servers:** We operate no intermediary proxies, cloud backends, or collection endpoints.
* **No Logging to Third Parties:** Your prompts, generation requests, and rendered media never leave your workstation, except when transmitted directly to Google Flow as required for media creation.

---

## 3. Network Endpoints & Communication

All network communication from this project is strictly confined to:

1. **`https://flow.google.com`**: Official Google Flow web application endpoints for authenticating and creating media requests.
2. **`127.0.0.1:9222`**: Local Chrome DevTools Protocol (CDP) port, bound strictly to the local loopback interface for in-browser automation without external exposure.

No other domains or IP addresses are contacted.

---

## 4. Local Credential & Session Storage

* **Authentication Cookies:** Session cookies saved via `auth.py` are written to `storage_state.json` on your local filesystem.
* **Browser Profile:** Dedicated Chromium profile data is stored locally in your operating system's application data directory.
* **Git Protection:** Sensitive session files and credentials are hardcoded into `.gitignore` to prevent accidental commit or publication.
* **User Control:** You may revoke sessions or delete authentication state at any time by deleting `storage_state.json` and terminating Chrome.

---

## 5. Third-Party Services (Google)

Media generation is performed directly on Google Flow using your Google account and Google AI Pro subscription. Interaction with Google Flow is subject to Google's [Terms of Service](https://policies.google.com/terms) and [Privacy Policy](https://policies.google.com/privacy).

---

## 6. Open Source Verification

The entire codebase is open source under the MIT License. Anyone can audit the repository to verify that no unauthorized network calls, data exfiltration, or background telemetry exist.

For questions, security disclosures, or concerns, please open an issue on GitHub:  
[https://github.com/voronin-s-dev/google-flow-mcp/issues](https://github.com/voronin-s-dev/google-flow-mcp/issues)
