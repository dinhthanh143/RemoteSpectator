# Remote Spectator (Working Title) 👁️📱

> **DISCLAIMER:**  
> This document outlines raw architectural ideas, exploratory concepts, and working notes. Everything described here is strictly experimental and subject to change as prototyping progresses.

---

## 1. The Core Problem & Elevator Pitch

### The Blind Remote Vibe-Coder
Remote vibe coding from your phone (via Claude Code, Aider, Codex, or custom bridges over Telegram/Discord) works well for backend tasks, script writing, and refactoring. However, it is **completely blind for frontend and UI work**.

When an agent changes a component, modifies CSS, or introduces UI state logic, the developer on their phone has no visual feedback. You are left guessing whether:
- The layout broke or overflowed.
- The Tailwind utility classes aligned elements correctly.
- The modal or dropdown opened properly.
- The UI actually looks good on mobile vs. desktop viewports.

Terminal mirroring (PTY/tmux) only streams text and code diffs (`+` and `-` lines). It does **not** render browsers.

### The Solution: Remote Spectator
A lightweight, open-source local MCP tool / CLI daemon that serves as the **eyes** for your coding agent. It:
1. Verifies and connects to your local dev environment.
2. Captures visual state (single snapshots, Before/After visual diffs, and short interaction video/GIF clips) using headless Playwright.
3. Dispatches the resulting visual proof directly into your mobile chat (Telegram / Discord) without requiring any external cloud servers.

---

## 2. Key Architecture Principles

- **Zero Cloud Footprint (100% Client-Side & Open Source):**  
  The creator/maintainer hosts zero infrastructure. The user runs everything locally on their own workstation.
- **Direct-to-Chat Delivery:**  
  Uses free public bot APIs and webhooks (Telegram Bot API, Discord Webhooks) called directly from the user's machine.
- **Decoupled Engines:**  
  - **Capture Engine:** Headless Playwright (for web) / OS window capture adapters (for desktop apps).
  - **Dispatcher:** Modular notifications (Telegram album/video, Discord rich embeds).
  - **Agent Interface:** MCP tool commands (`capture_snapshot`, `record_interaction`, `compare_diff`) and CLI triggers.

---

## 3. Discussion & Brainstorming: The Proposed Auto-Start Flow

### User's Proposed Idea
> *"In Telegram/Discord or chat: just tell it to run remote spec => it automatically runs check => if nothing => searches through codebase, lets the AI know how to run the web => saves config to local => next time runs on its own (server startup, etc.) => opens on browser."*

### Honest Critique & Engineering Reality Check (No Sugar-Coating)

#### What Works Well:
1. **Zero-Config Detection (`package.json` heuristic):**  
   Checking `package.json` scripts (`npm run dev`, `pnpm dev`, `vite`, `next dev`) or Python virtual environments (`uvicorn`, `flask run`) is fast, deterministic, and reliable.
2. **Caching the Run Command (`.spectatorrc` or `.spectator.json`):**  
   Once discovered or configured, saving `{ "port": 5173, "dev_command": "pnpm dev", "default_path": "/" }` avoids re-scanning on subsequent runs.

#### Where the Traps & Failure Modes Lie:
1. **Dev Server Lifecycle & Port Collisions:**
   - If Remote Spectator spawns the dev server inside a background subprocess, who kills it when the session ends? Zombie Node processes holding port 3000/5173 on Windows are notoriously common.
   - **Better approach:** *Check first if a server is already alive.* Usually, the developer or the agent already has `npm run dev` running in a terminal. Spectator should first ping ports `[3000, 5173, 8080, 8000]`. Only if all are dead should it offer to launch the server.
2. **Waiting for Cold Builds & Compilation:**
   - Next.js and Vite take between 2s to 30s to compile on cold boot. If Playwright visits `localhost:3000` immediately, it hits `ECONNREFUSED` or captures a white loading screen.
   - Spectator must implement a **polling readiness probe** (retrying HTTP `GET /` with exponential backoff until `200 OK`) before triggering Playwright.
3. **Authentication & Gated Routes:**
   - What if the page being modified is `/dashboard/settings`, which requires login?
   - Playwright visiting `localhost:3000/dashboard/settings` will be redirected to `/login`, capturing a useless login screen instead of the modified component.
   - *Consideration:* Need support for storage state / cookies or testing URLs without full auth hurdles.

---

## 4. Proposed Flow: Step-by-Step

```
[Phone Chat: "Run Spectator" or Agent edits file]
                  │
                  ▼
         [1. Target Detection]
    Is localhost:<port> already alive?
         ├── YES ──► Use active port
         └── NO  ──► Inspect package.json / config
                     Prompt / Spawn dev server in background
                     Wait for HTTP 200 OK readiness
                  │
                  ▼
         [2. Capture Strategy]
    Agent/User selects mode:
         ├── Snapshot (Single Viewport PNG)
         ├── Diff (Before vs. After pixel diff / slider)
         └── Interaction Clip (Playwright click/hover -> 3s MP4/WebM)
                  │
                  ▼
         [3. Local Persistence]
    Saved into `.spectator/captures/`
                  │
                  ▼
         [4. Chat Dispatcher]
    Direct HTTPS POST via Telegram Bot API or Discord Webhook
    Notification with visual proof arrives on mobile
```

---

## 5. Scope Roadmap (Tentative)

- [ ] **Phase 1 (Core Web & Dispatcher):** Headless Playwright script + Telegram/Discord dispatchers + test snapshot on local dev port.
- [ ] **Phase 2 (MCP Integration):** Expose as an MCP tool so Claude Code, Antigravity, and Codex can autonomously trigger captures after code edits.
- [ ] **Phase 3 (Visual Diffing):** Capture baseline screenshot before edit, capture after edit, generate visual diff comparison card.
- [ ] **Phase 4 (Desktop/Native App Expansion):** OS window capture adapter for non-web projects (Electron, GUI tools, game windows).
