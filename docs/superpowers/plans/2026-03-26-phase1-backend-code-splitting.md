# Phase 1: Backend Code Splitting — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Split chat_routes.py (1,128 lines) and executor.py (1,206 lines) into focused modules with zero behavior change.

**Architecture:** Extract tool definitions, system prompt, CRUD endpoints, location logic, and utility functions into their own files. Split executor tool handlers by category. All imports updated, all existing behavior preserved.

**Tech Stack:** Python 3, FastAPI, SQLAlchemy async, Pydantic

---

### Task 1: Extract location module

**Files:**
- Create: `backend/location.py`
- Modify: `backend/routes/chat_routes.py` (remove lines 22-69)
- Modify: `backend/tools/executor.py` (change import at line 198)
- Modify: `backend/main.py` (change import at line 86)

- [ ] **Step 1:** Create `backend/location.py` with `_location_cache`, `_update_location_from_gps()`, `_get_user_location()` — copied verbatim from chat_routes.py lines 22-69.
- [ ] **Step 2:** Remove lines 22-69 from chat_routes.py. Add `from location import _get_user_location`.
- [ ] **Step 3:** In executor.py line 198, change `from routes.chat_routes import _location_cache` to `from location import _location_cache`.
- [ ] **Step 4:** In main.py line 86, change `from routes.chat_routes import _update_location_from_gps, _location_cache` to `from location import _update_location_from_gps, _location_cache`.
- [ ] **Step 5:** Verify: `bash stop.sh && bash start.sh`, check backend log shows "Uvicorn running".
- [ ] **Step 6:** Commit: `git commit -m "refactor: extract location module from chat_routes"`

---

### Task 2: Extract tool definitions

**Files:**
- Create: `backend/tools/definitions.py`
- Modify: `backend/routes/chat_routes.py` (remove TOOLS list, lines 70-536)

- [ ] **Step 1:** Create `backend/tools/definitions.py` containing the full `TOOLS = [...]` list (verbatim from chat_routes.py lines 73-536).
- [ ] **Step 2:** Remove TOOLS list from chat_routes.py. Add `from tools.definitions import TOOLS`.
- [ ] **Step 3:** Verify: restart, `curl -s http://localhost:3001/api/tools/status` returns tool list.
- [ ] **Step 4:** Commit: `git commit -m "refactor: extract tool definitions to tools/definitions.py"`

---

### Task 3: Extract system prompt and utility helpers

**Files:**
- Create: `backend/tools/system_prompt.py`
- Create: `backend/utils.py`
- Modify: `backend/routes/chat_routes.py`

- [ ] **Step 1:** Create `backend/tools/system_prompt.py` with: `SYSTEM_PROMPT_TEMPLATE`, `build_system_prompt()` function (consolidates the 28-line assembly block), `_get_persona_prompt()`, `_load_project_notes()`.
- [ ] **Step 2:** Create `backend/utils.py` with: `resize_image_for_vision()`, `read_file_content()` (drop leading underscore since now public).
- [ ] **Step 3:** In chat_routes.py: remove the extracted functions, add `from tools.system_prompt import build_system_prompt` and `from utils import resize_image_for_vision, read_file_content`. Replace the 28-line system prompt assembly block in `send_message()` with a single `build_system_prompt()` call. Replace `_resize_image_for_vision(` with `resize_image_for_vision(` and `_read_file_content(` with `read_file_content(`.
- [ ] **Step 4:** Verify: restart, send a message in the UI, confirm system prompt and attachments work.
- [ ] **Step 5:** Commit: `git commit -m "refactor: extract system prompt and utility functions"`

---

### Task 4: Extract CRUD endpoints

**Files:**
- Create: `backend/routes/chat_crud.py`
- Modify: `backend/routes/chat_routes.py`
- Modify: `backend/main.py`

- [ ] **Step 1:** Create `backend/routes/chat_crud.py` with its own `router = APIRouter(prefix="/api/chat")`. Move: `ConversationUpdate` model, `_convo_dict`, `_msg_dict`, `_get_convo`, and all CRUD endpoints (`list_conversations`, `get_conversation`, `update_conversation`, `delete_conversation`, `delete_messages_from`, `set_reaction`, `search_messages`, `export_conversation`).
- [ ] **Step 2:** In chat_routes.py: remove all moved code. Add `from routes.chat_crud import _get_convo, _convo_dict, _msg_dict` (used by send_message's save logic).
- [ ] **Step 3:** In main.py: add `from routes.chat_crud import router as chat_crud_router` and `app.include_router(chat_crud_router)`.
- [ ] **Step 4:** Verify: restart, test list/rename/star/delete/search in the UI.
- [ ] **Step 5:** Commit: `git commit -m "refactor: extract CRUD endpoints to chat_crud.py"`

---

### Task 5: Split executor.py into handler modules

**Files:**
- Create: `backend/tools/handlers_core.py` (_execute_code, _run_subprocess, _web_search, _fetch_url, _get_datetime, _get_weather + WEATHER_CODES, _calculator, _create_artifact)
- Create: `backend/tools/handlers_google.py` (_gmail_*, _calendar_*, _drive_*)
- Create: `backend/tools/handlers_notes.py` (_save_note, _read_note, _update_note, _list_notes, _save_note_to_drive, _get_or_create_folder, NOTES_DIR)
- Create: `backend/tools/handlers_media.py` (_generate_image, _edit_image, _security_camera)
- Create: `backend/tools/handlers_codebase.py` (_codebase_tree, _codebase_read, _codebase_search, ALLOWED_BASES, SKIP_DIRS, SKIP_EXTENSIONS, _is_safe_path)
- Create: `backend/tools/handlers_learning.py` (_tutor_*, _youtube_transcript)
- Modify: `backend/tools/executor.py`

- [ ] **Step 1:** Run `grep -n '^async def \|^def \|^[A-Z_].*=' backend/tools/executor.py` to map exact line ranges for each function.
- [ ] **Step 2:** Create all 6 handler files. Each gets its functions copied verbatim with their required imports and constants.
- [ ] **Step 3:** In `handlers_core.py`, fix the weather handler: change `from routes.chat_routes import _location_cache` to `from location import _location_cache`.
- [ ] **Step 4:** Replace executor.py body with imports from handler modules. Keep only `execute_tool()` dispatcher and `_call_mcp_tool()`.
- [ ] **Step 5:** Verify: restart, test "what time is it", "search the web for X", "what's the weather", check tools/status endpoint.
- [ ] **Step 6:** Commit: `git commit -m "refactor: split executor.py into category-based handler modules"`

---

### Task 6: Final verification and cleanup

- [ ] **Step 1:** Check line counts: `wc -l backend/routes/chat_routes.py backend/routes/chat_crud.py backend/tools/executor.py backend/tools/definitions.py backend/tools/system_prompt.py backend/tools/handlers_*.py backend/location.py backend/utils.py`. Expect chat_routes.py ~350 lines, executor.py ~80 lines.
- [ ] **Step 2:** Full integration test: create conversation, send message with tools, star, rename, search, delete, gallery, settings.
- [ ] **Step 3:** Push: `cd ~/claude-ui && git push`
