---
name: remote-spectate
description: Inspect running web dev servers, take desktop or mobile visual snapshots via Playwright, and inspect UI changes locally. Triggered with /remote-spectate or when visual verification is requested.
---

# Remote Spectate Skill

Use this skill when the user asks to inspect, spectate, visually verify, or compare UI changes across design iterations (e.g. `/remote-spectate`, "spectate", "check the UI", "compare before and after", "capture using my email profile").

## Universal Architecture & Stack Discovery Protocol

Any web app may consist of:
- **Full-Stack Single Server**: Next.js, Nuxt, Remix, SvelteKit, Laravel, Rails, Django.
- **Decoupled Architecture**: Frontend (e.g. Vite, React, Vue on port 5173/3000) **and** Backend API (e.g. FastAPI, Express, Flask, Go, Spring on port 8000/3001/5000/8080).
- **Multi-Service / Monorepo**: `docker-compose.yml`, `Procfile`, `turborepo`, or parallel folders (`frontend/` + `backend/`, `web/` + `api/`, `client/` + `server/`).

Spectator must ensure the **entire application stack** is alive before taking visual captures, so data fetching, authentication, and state don't fail.

---

### Step 1: Check Cached Manifest OR Auto-Discover Stack

Execute discovery in this exact priority order:

#### ⚡ Fast Path: Project Cache (`.remoteSpectator.json`)
Check if `.remoteSpectator.json` exists in the project workspace root:
- **If Found**: Read `services` directly (ports, start commands, directories, and healthchecks). Skip all heuristic file scanning!
- **If Not Found or Invalid**: Proceed to the Universal Discovery Heuristic below.

#### 🔍 Discovery Heuristic (Cold Start / First Run):
1. **Container / Multi-Process Orchestration**:
   - Check `docker-compose.yml` / `compose.yaml` or `Procfile`.
   - If services are defined and not running, run `docker compose up -d` or the designated process manager.
2. **Frontend API Dependency & Proxy Cross-Reference**:
   - Inspect frontend configuration:
     - Vite: `vite.config.ts` / `vite.config.js` (`server.proxy` targeting ports like `http://localhost:8000` or `3001`).
     - Next.js: `next.config.js` (`rewrites`).
     - Environment files: `.env`, `.env.development`, `.env.local` looking for `VITE_API_URL`, `NEXT_PUBLIC_API_URL`, `REACT_APP_API_URL`, `BACKEND_URL`, etc.
   - If a backend URL/port is referenced (e.g. `localhost:8000`), **mark that backend port as a required prerequisite**.
3. **Decoupled / Multi-Folder Monorepo Discovery**:
   - Check for parallel service folders:
     - Backend candidates: `backend/`, `api/`, `server/`, `*-api/`, `service/`
     - Frontend candidates: `frontend/`, `web/`, `client/`, `ui/`, `*-ui/`
   - If both exist:
     - Identify Backend startup: `pyproject.toml`, `requirements.txt`, `manage.py`, `pom.xml`, or `package.json` inside backend dir.
     - Identify Frontend startup: `package.json` (`dev`, `start`) inside frontend dir.
4. **VS Code Tasks (`.vscode/tasks.json` if available)**:
   - Check for composite stack tasks (e.g. `dependsOn: ["Frontend", "Backend"]` or label containing `Stack` / `Dev Stack`).
   - If present, extract both backend and frontend commands and directories.
5. **Single Full-Stack Manifest**:
   - If single root `package.json` with Next.js/Nuxt or single `pyproject.toml`/`manage.py`, run standard root `npm run dev` or framework CLI.

---

### Step 2: Multi-Service Liveness Verification & Bootstrapping

1. **Check Liveness of All Required Ports**:
   - Ping the detected frontend URL/port and backend URL/port using `spectator_ping(url=...)` or PowerShell TCP check.
2. **Boot Missing Services in Sequence**:
   - **Order Matters**: **Always boot the Backend API first**, wait 2–3s for its database connections/routes to initialize, then boot the Frontend.
   - Run startup commands using `run_command` with `IsDaemon: true` inside their respective `cwd`.
3. **Confirm Port Health Before Capturing**:
   - Verify both ports respond before taking the snapshot.

---

### Step 3: Auto-Generate `.remoteSpectator.json` Cache

Immediately after successfully resolving and verifying the active stack on a first run (or if `.remoteSpectator.json` was missing):
- Automatically create/write `.remoteSpectator.json` in the workspace root with the resolved stack structure:
  ```json
  {
    "version": "1.0",
    "generated_at": "<ISO_TIMESTAMP>",
    "services": {
      "backend": {
        "cwd": "<relative_or_absolute_dir>",
        "command": "<backend_start_command>",
        "port": 8000,
        "healthcheck": "http://localhost:8000/docs"
      },
      "frontend": {
        "cwd": "<relative_or_absolute_dir>",
        "command": "<frontend_start_command>",
        "port": 5173,
        "healthcheck": "http://localhost:5173"
      }
    },
    "defaults": {
      "url": "http://localhost:5173/",
      "viewport": "desktop"
    }
  }
  ```
- This ensures all future `/remote-spectate` invocations execute instantly with zero guesswork.

---

### Step 4: Capture Strategy: Snapshot vs. Multi-Variant Comparison

Detect browser and user profile requirements from user prompt:
- Browser: `"chrome" | "brave" | "chromium"`
- Profile: Email or profile identifier (e.g. `"neonlime123"`, `"neonlime123@gmail.com"`, `"Profile 35"`).

#### Mode A: Single Snapshot (`spectator_capture`)
- Call `spectator_capture`:
  ```python
  spectator_capture(
      url="http://localhost:<frontend_port>/<route>",
      viewport="desktop" | "mobile" | "tablet",
      browser="chrome" | "brave" | "chromium",
      profile="<email_or_profile_name>"  # auto-matches Google/Brave profiles safely!
  )
  ```
- Generate inline preview:
  ```bash
  python d:/BotTest/remoteSpectator/src/generate_preview.py "<captured_png_path>" "<target_url>" "<artifact_dir>/spectator_preview.html"
  ```
- Output inline with `<agent-embed src="file:///<artifact_dir>/spectator_preview.html"></agent-embed>`.

#### Mode B: Multi-Stage Iteration & Comparison (`spectator_compare`)
- Use when fixing bugs, refactoring UI, or iterating through multiple design variants:
  1. **Step 1 (Baseline)**: Take a baseline snapshot before edits:
     ```python
     spectator_compare(url="...", label="Baseline", session_id="<topic>", reset_session=True, browser="chrome", profile="<email>")
     ```
  2. **Subsequent steps**: Apply edit, wait for HMR reload, and record:
     ```python
     spectator_compare(url="...", label="<Variant Name>", session_id="<topic>", browser="chrome", profile="<email>")
     ```
- Generate interactive switcher widget:
  ```bash
  python d:/BotTest/remoteSpectator/src/generate_preview.py --session "<topic>" "<artifact_dir>/spectator_preview.html"
  ```
- Output inline with `<agent-embed>`.

---

### Step 5: Present & Asset Management

- **UI Dashboard Announcement (First-Time Only)**:
  - If this is the **first time** running `/remote-spectate` on this project (e.g. `.remoteSpectator.json` was just created during this turn), display the dashboard notice once:
    > 🔗 **Asset Manager UI:** [http://localhost:49152](http://localhost:49152) — *Browse captures, inspect file sizes, and delete assets directly from disk.*
  - On subsequent invocations for the project, **omit this notice** to keep output clean and concise.
- Provide clickable links to saved capture artifact(s).
- Inspect layout, alignment, responsiveness, visual contrast, and check that API-dependent widgets aren't rendering empty/broken states.
