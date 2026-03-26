# Claude UI Improvements — Design Spec

## Context

The Claude UI app (React + FastAPI + SQLite + Ollama) is a self-hosted AI chat platform running on a DGX Spark behind Tailscale. It works well but has grown organically — the two main backend files are 1,100+ lines each, there's no error recovery on SSE streams, the frontend swallows all errors silently, and the deployment uses bare `nohup` processes with a Vite dev server.

This spec covers 4 independent improvement areas, executed in order.

---

## Phase 1: Backend Code Splitting

**Goal:** Break `chat_routes.py` (1,128 lines) and `executor.py` (1,206 lines) into focused modules. Zero behavior change.

### New Files

| File | Contents | ~Lines |
|------|----------|--------|
| `tools/definitions.py` | `TOOLS` list (all 44 tool schemas) | 470 |
| `tools/system_prompt.py` | `SYSTEM_PROMPT_TEMPLATE`, `build_system_prompt()`, `_get_persona_prompt()`, `_load_project_notes()` | 60 |
| `tools/handlers_core.py` | `_execute_code`, `_run_subprocess`, `_web_search`, `_fetch_url`, `_get_datetime`, `_get_weather`, `_calculator`, `_create_artifact` | 150 |
| `tools/handlers_google.py` | `_gmail_*`, `_calendar_*`, `_drive_*` | 350 |
| `tools/handlers_notes.py` | `_save_note`, `_read_note`, `_update_note`, `_list_notes`, Drive sync helpers | 150 |
| `tools/handlers_media.py` | `_generate_image`, `_edit_image`, `_security_camera` | 150 |
| `tools/handlers_codebase.py` | `_codebase_tree`, `_codebase_read`, `_codebase_search`, safety checks | 200 |
| `tools/handlers_learning.py` | `_tutor_*`, `_youtube_transcript` | 60 |
| `routes/chat_crud.py` | Conversation/message CRUD, search, export endpoints | 200 |
| `location.py` | `_location_cache`, `_update_location_from_gps()`, `_get_user_location()` | 50 |
| `utils.py` | `_resize_image_for_vision()`, `_read_file_content()` | 60 |

### Modified Files

- **`chat_routes.py`** → ~350 lines: just `/send` streaming endpoint, `/models`, `SendMessageRequest`, `_parse_artifacts`, `_generate_title`
- **`executor.py`** → ~100 lines: `execute_tool()` dispatcher importing from handler modules
- **`main.py`** → register `chat_crud_router`, import location from `location.py`

### Key Details

- Location logic (`_location_cache`) moves to `location.py` to break circular import between `chat_routes.py` and `executor.py`
- `_convo_dict`, `_msg_dict`, `_get_convo` move to `chat_crud.py` (also imported by `chat_routes.py` for the `/send` endpoint's final save)
- `ConversationUpdate` Pydantic model moves to `chat_crud.py`
- `build_system_prompt()` consolidates the 28-line prompt assembly block from the `/send` endpoint into a single function call

### Verification

Start the server, send a message with tool calls, verify CRUD operations (rename, delete, star, search, export).

---

## Phase 2: Frontend Error Handling

**Goal:** Make errors visible to the user instead of swallowing them silently.

### New Files

| File | Purpose |
|------|---------|
| `stores/toastStore.ts` | Zustand store: `{ toasts[], addToast(msg, type), removeToast(id) }` |
| `components/Toast.tsx` | Fixed bottom-right container, auto-dismiss after 5s, error/warning/info icons (lucide-react) |
| `components/ErrorBoundary.tsx` | React class component, catches render errors, "Something went wrong" + Reload button |
| `components/ConnectionStatus.tsx` | Pings `/api/health` every 30s, shows green/yellow/red dot. States: connected → reconnecting (1 failure) → disconnected (3 failures) |

### Modified Files

- **`App.tsx`** — Wrap `<Routes>` with `<ErrorBoundary>`, add `<Toast />` at root
- **`Chat.tsx`** — Replace empty catches with `toastStore.addToast()` calls. Keep the SSE line-parser catch empty (correct behavior for partial chunks). Add `<ConnectionStatus />` in top bar.
- **`ChatInput.tsx`** — Toast on file upload and paste failures
- **`MessageBubble.tsx`** — Toast on reaction save failure (warning level)

### Catches Left Silent

- `chatStore.ts` location update — not critical, add `console.warn` only
- SSE JSON parse inner catch — correct behavior, partial SSE chunks aren't errors

---

## Phase 3: SSE Streaming Resilience

**Goal:** Don't lose partial responses when connections drop.

### Backend Changes (`chat_routes.py`)

1. **Periodic partial save** — After the first token, insert a preliminary assistant message. Update its content after each tool round completes. The final save becomes an update, not an insert.

2. **Reduced Ollama timeout** — Change `httpx.AsyncClient(timeout=300.0)` to `httpx.Timeout(connect=10, read=60, write=10, pool=10)`. If Ollama dies, the stream errors in 60s instead of hanging for 5 minutes.

3. **Heartbeats between tool rounds** — Yield `: heartbeat\n\n` (SSE comment, ignored by `data:` parser) during tool execution to keep the connection alive.

### Frontend Changes (`Chat.tsx`)

4. **Preserve partial content on disconnect** — In the catch block, read `streamingContent` from Zustand. If non-empty, save it as the assistant message with a "[Connection lost]" suffix.

5. **Stream timeout detection** — Wrap `reader.read()` in `Promise.race` with a 60-second timeout. If no data (including heartbeats) for 60s, treat as connection loss.

6. **Manual retry button** — Error messages include a "Retry" button (calls `handleRegenerate`). No automatic retry — too dangerous with tools that send emails or create events.

---

## Phase 4: Deployment Hardening

**Goal:** Docker Compose, production build, auto-restart, proper logging.

### New Files

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Two services: backend (Python) + frontend (nginx) |
| `backend/Dockerfile` | Python 3.11 slim + ffmpeg + pip deps |
| `backend/requirements.txt` | Pinned Python dependencies (generated from pip freeze) |
| `backend/.dockerignore` | Exclude `claude_ui.db`, `.env`, token JSONs, `__pycache__` |
| `frontend/Dockerfile` | Multi-stage: Node 20 build → nginx:alpine serve |
| `frontend/.dockerignore` | Exclude `node_modules`, `dist` |
| `frontend/nginx.conf` | Serve static build, proxy `/api` + `/uploads` + `/generated` to backend. `proxy_buffering off` for SSE. |

### Key Design Decisions

- **Host network mode** — Backend needs localhost access to Ollama (port 11434) and LAN access to security camera (192.168.1.188). Host networking avoids complex bridge config. Safe behind Tailscale.
- **Bind-mount database** — `claude_ui.db` mounted from host, not baked into image. Survives rebuilds.
- **Bind-mount OAuth tokens** — Google API tokens in `backend/tools/*.json` mounted, not copied.
- **Ollama stays on host** — Not containerized (needs GPU). `start.sh` checks it's running before `docker compose up`.
- **Production frontend** — `npm run build` → static files served by nginx. No more Vite dev server.

### Updated Scripts

- **`start.sh`** → Check Ollama, then `docker compose up -d --build`
- **`stop.sh`** → `docker compose down`

### Docker Features

- `restart: unless-stopped` — Auto-restart on crash or reboot
- Health checks on both services
- JSON-file logging with `max-size: 10m, max-file: 3` — automatic rotation
- Layer caching for fast rebuilds

### Risk: TypeScript build errors

Running `npm run build` may surface TypeScript errors currently masked by dev mode. Run the build manually first on the host to identify issues before Dockerizing.

---

## Execution Order

1. **Phase 1** first — pure refactoring, makes subsequent work cleaner
2. **Phase 2** next — low risk, immediate UX improvement
3. **Phase 3** — builds on the split backend (Phase 1) and error UI (Phase 2)
4. **Phase 4** last — riskiest (changes how app runs), do after everything else is stable
