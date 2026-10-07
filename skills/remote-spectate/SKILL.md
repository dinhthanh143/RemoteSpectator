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

### Step 1: Detect Full Stack Dependencies & Ports

Execute stack discovery in this exact priority order:

1. **Explicit Config (`.spectator.json` or `.spectatorrc` in workspace root)**:
   - If present, parse defined services (e.g., `services.backend`, `services.frontend`), their start commands, ports, and healthcheck URLs.
2. **Container / Multi-Process Orchestration**:
   - Check `docker-compose.yml` / `compose.yaml` or `Procfile`.
   - If services are defined and not running, run `docker compose up -d` or the designated process manager.
3. **Frontend API Dependency & Proxy Cross-Reference**:
   - Inspect frontend configuration:
     - Vite: `vite.config.ts` / `vite.config.js` (`server.proxy` targeting ports like `http://localhost:8000` or `3001`).
     - Next.js: `next.config.js` (`rewrites`).
     - Environment files: `.env`, `.env.development`, `.env.local` looking for `VITE_API_URL`, `NEXT_PUBLIC_API_URL`, `REACT_APP_API_URL`, `BACKEND_URL`, etc.
   - If a backend URL/port is referenced (e.g. `localhost:8000`), **mark that backend port as a required prerequisite**.
4. **Decoupled / Multi-Folder Monorepo Discovery**:
   - Check for parallel service folders:
     - Backend candidates: `backend/`, `api/`, `server/`, `*-api/`, `service/`
     - Frontend candidates: `frontend/`, `web/`, `client/`, `ui/`, `*-ui/`
   - If both exist:
     - Identify Backend startup: `pyproject.toml`, `requirements.txt`, `manage.py`, `pom.xml`, or `package.json` inside backend dir.
     - Identify Frontend startup: `package.json` (`dev`, `start`) inside frontend dir.
5. **VS Code Tasks (`.vscode/tasks.json` if available)**:
   - Check for composite stack tasks (e.g. `dependsOn: ["Frontend", "Backend"]` or label containing `Stack` / `Dev Stack`).
   - If present, extract both backend and frontend commands and directories.
6. **Single Full-Stack Manifest**:
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

### Step 3: Capture Strategy: Snapshot vs. Multi-Variant Comparison

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

### Step 4: Present & Asset Management

- Always include the **Asset Manager UI URL**:
  > 🔗 **Asset Manager UI:** [http://localhost:49152](http://localhost:49152) — *Browse captures, inspect file sizes, and delete assets directly from disk to prevent bloat.*
- Provide clickable links to saved capture artifact(s).
- Inspect layout, alignment, responsiveness, visual contrast, and check that API-dependent widgets aren't rendering empty/broken states.
