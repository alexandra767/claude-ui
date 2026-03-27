from dotenv import load_dotenv as _ld
_ld("/home/alexandratitus767/claude-ui/backend/.env")
"""Central tool executor — routes tool calls to the right handler."""

from tools.handlers_core import (
    _execute_code, _web_search, _fetch_url, _get_datetime,
    _get_weather, _calculator, _create_artifact,
)
from tools.handlers_google import (
    _gmail_search, _gmail_read, _gmail_send,
    _calendar_list, _calendar_create,
    _drive_list_files, _drive_search, _drive_read_doc, _drive_create_doc,
)
from tools.handlers_notes import (
    _save_note, _read_note, _update_note, _list_notes,
)
from tools.handlers_media import (
    _generate_image, _edit_image, _security_camera,
)
from tools.handlers_codebase import (
    _codebase_tree, _codebase_read, _codebase_search,
)
from tools.handlers_learning import (
    _tutor_topics, _tutor_challenge, _tutor_validate,
    _tutor_validate_dynamic, _tutor_progress, _youtube_transcript,
)


async def execute_tool(name: str, arguments: dict) -> dict:
    """Execute a tool by name and return the result."""
    # Check if it's an MCP tool (prefixed with mcp__)
    if name.startswith("mcp__"):
        return _call_mcp_tool(name, arguments)

    handlers = {
        "execute_code": _execute_code,
        "web_search": _web_search,
        "fetch_url": _fetch_url,
        "get_datetime": _get_datetime,
        "get_weather": _get_weather,
        "calculator": _calculator,
        "create_artifact": _create_artifact,
        "generate_image": _generate_image,
        "edit_image": _edit_image,
        "gmail_search": _gmail_search,
        "gmail_read": _gmail_read,
        "gmail_send": _gmail_send,
        "calendar_list": _calendar_list,
        "calendar_create": _calendar_create,
        "drive_search": _drive_search,
        "drive_read_doc": _drive_read_doc,
        "drive_create_doc": _drive_create_doc,
        "save_note": _save_note,
        "update_note": _update_note,
        "read_note": _read_note,
        "list_notes": _list_notes,
        "youtube_transcript": _youtube_transcript,
        "tutor_topics": _tutor_topics,
        "tutor_challenge": _tutor_challenge,
        "tutor_validate": _tutor_validate,
        "tutor_validate_dynamic": _tutor_validate_dynamic,
        "tutor_progress": _tutor_progress,
        "codebase_tree": _codebase_tree,
        "codebase_read": _codebase_read,
        "codebase_search": _codebase_search,
        "drive_list_files": _drive_list_files,
        "security_camera": _security_camera,
    }
    handler = handlers.get(name)
    if not handler:
        return {"error": f"Unknown tool: {name}"}
    try:
        return await handler(arguments)
    except Exception as e:
        return {"error": f"{name} failed: {str(e)}"}


# ── MCP Tool Routing ────────────────────────────────────────────────────────

def _call_mcp_tool(name: str, arguments: dict) -> dict:
    """Route mcp__<server>__<tool> calls to the MCP client."""
    from tools.mcp_client import call_mcp_tool
    parts = name.split("__", 2)  # mcp__server__tool
    if len(parts) != 3:
        return {"error": f"Invalid MCP tool name: {name}"}
    _, server, tool = parts
    result = call_mcp_tool(server.replace("_", "-"), tool, arguments, timeout=120)
    # Extract text content from MCP response
    if isinstance(result, dict) and "content" in result:
        contents = result["content"]
        if isinstance(contents, list):
            texts = [c.get("text", "") for c in contents if c.get("type") == "text"]
            return {"result": "\n".join(texts) if texts else str(contents)}
    return result
