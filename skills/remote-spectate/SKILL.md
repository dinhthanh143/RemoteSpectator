---
name: remote-spectate
description: Inspect running web dev servers, take desktop or mobile visual snapshots via Playwright, and inspect UI changes locally. Triggered with /remote-spectate or when visual verification is requested.
---

# Remote Spectate Skill

Use this skill when the user asks to inspect, spectate, visually verify, or compare UI changes across design iterations (e.g. `/remote-spectate`, "spectate", "check the UI", "compare before and after", "capture using my email profile").

## Execution Playbook (Detective & Camera Workflow)

### 1. Identify Workspace & Context
- Look at the active workspace and recent context (e.g. modified files, active project directory).
- **PRIORITY 1: Check `.vscode/tasks.json`**:
  - If `.vscode/tasks.json` exists in the workspace, inspect it immediately!
  - Look for tasks labeled with `Frontend`, `Dev`, `Serve`, `Start`, or composite stacks like `Dev Stack`.
  - Extract the exact startup command, arguments, target `cwd` (crucial for monorepos like `${workspaceFolder}/jikkei`), and port regex (e.g. Vite, Uvicorn, Next).
- **PRIORITY 2: Fallback to package manifests**:
  - If no `tasks.json`, check root or subfolder `package.json` scripts (`dev`, `start`).
  - Default framework ports: Vite (`5173`), Next.js (`3000`), Python/FastAPI (`8000`), Flask (`5000`).
- Determine target route if a specific page or component was edited (e.g. `/`, `/reader`, `/settings`).
- **Detect Browser & Profile Requirements**:
  - If the user mentions a specific browser or profile (e.g. "in brave", "using my neonlime123@gmail.com profile", "as neonlime12 google"), extract `browser="chrome"|"brave"` and `profile="<email_or_name>"`.

### 2. Verify Port Liveness
- Check if the dev server is responding on `http://localhost:<port>` (or `127.0.0.1:<port>`).
- You can test via PowerShell / curl or by calling `spectator_ping(url=...)` from `remote-spectator` MCP.
- **If the dev server is NOT running**:
  - If a task was found in `.vscode/tasks.json`:
    - Run the exact command and arguments within its specified `options.cwd` using `run_command` with `IsDaemon: true`.
  - If no `tasks.json`:
    - Run the package script (e.g. `npm run dev` in the frontend directory) as a background daemon.
  - Wait 2-5 seconds and verify the port returns HTTP 200 before proceeding.

### 3. Capture Strategy: Snapshot vs. Multi-Variant Comparison

#### Mode A: Single Snapshot (`spectator_capture`)
- Call `spectator_capture`:
  ```python
  spectator_capture(
      url="http://localhost:<port>/<route>",
      viewport="desktop" | "mobile",
      browser="chrome" | "brave" | "chromium",
      profile="<email_or_profile_name>"  # optional, auto-fuzzy-matches Google/Brave profiles!
  )
  ```
- Generate inline preview:
  ```bash
  python d:/BotTest/remoteSpectator/src/generate_preview.py "<captured_png_path>" "<target_url>" "<artifact_dir>/spectator_preview.html"
  ```
- Output inline with `<agent-embed src="file:///<artifact_dir>/spectator_preview.html"></agent-embed>`.

#### Mode B: Multi-Stage Iteration & Comparison (`spectator_compare`)
- Use when fixing bugs, refactoring UI, or iterating through multiple design variants (e.g., "try red, white, green"):
  1. **Step 1 (Baseline)**: Take a baseline snapshot before edits:
     ```python
     spectator_compare(url="...", label="Baseline", session_id="<topic>", reset_session=True, browser="chrome", profile="<email>")
     ```
  2. **Subsequent steps**: Apply edit and record:
     ```python
     spectator_compare(url="...", label="<Variant Name>", session_id="<topic>", browser="chrome", profile="<email>")
     ```
- Generate interactive switcher widget:
  ```bash
  python d:/BotTest/remoteSpectator/src/generate_preview.py --session "<topic>" "<artifact_dir>/spectator_preview.html"
  ```
- Output inline with `<agent-embed>`.

### 4. Present, Verify & Display UI Manager
- Always include the **Asset Manager UI URL**:
  > 🔗 **Asset Manager UI:** [http://localhost:49152](http://localhost:49152) — *Browse captures, inspect file sizes, and delete assets directly from disk to prevent bloat.*
- Provide the clickable link to the saved capture artifact(s).
- Inspect layout, alignment, responsiveness, and contrast to confirm the UI matches expectations.
