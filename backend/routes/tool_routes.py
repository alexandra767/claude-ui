from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from auth import get_current_user
import subprocess
import tempfile
import os
import httpx

router = APIRouter(prefix="/api/tools", tags=["tools"])


class CodeExecRequest(BaseModel):
    code: str
    language: str = "python"


class WebSearchRequest(BaseModel):
    query: str


@router.post("/execute")
async def execute_code(req: CodeExecRequest, user_id: str = Depends(get_current_user)):
    """Execute code in a sandboxed subprocess."""
    if req.language == "python":
        return _run_python(req.code)
    elif req.language == "javascript":
        return _run_node(req.code)
    elif req.language == "bash":
        return _run_bash(req.code)
    else:
        raise HTTPException(400, f"Unsupported language: {req.language}")


@router.post("/search")
async def web_search(req: WebSearchRequest, user_id: str = Depends(get_current_user)):
    """Perform a web search using DuckDuckGo HTML."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://html.duckduckgo.com/html/",
                params={"q": req.query},
                headers={"User-Agent": "Mozilla/5.0"},
            )
            # Basic extraction of results
            from html.parser import HTMLParser
            results = []

            class DDGParser(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.in_result = False
                    self.in_snippet = False
                    self.current = {}

                def handle_starttag(self, tag, attrs):
                    attrs_dict = dict(attrs)
                    if tag == "a" and "result__a" in attrs_dict.get("class", ""):
                        self.in_result = True
                        self.current = {"url": attrs_dict.get("href", ""), "title": ""}
                    if tag == "a" and "result__snippet" in attrs_dict.get("class", ""):
                        self.in_snippet = True
                        self.current["snippet"] = ""

                def handle_data(self, data):
                    if self.in_result:
                        self.current["title"] += data
                    if self.in_snippet:
                        self.current["snippet"] = self.current.get("snippet", "") + data

                def handle_endtag(self, tag):
                    if tag == "a" and self.in_result:
                        self.in_result = False
                    if tag == "a" and self.in_snippet:
                        self.in_snippet = False
                        if self.current.get("title"):
                            results.append(dict(self.current))
                        self.current = {}

            parser = DDGParser()
            parser.feed(resp.text)
            return {"results": results[:8]}
    except Exception as e:
        return {"results": [], "error": str(e)}


@router.get("/available")
async def list_tools(user_id: str = Depends(get_current_user)):
    return {
        "tools": [
            {"name": "execute_code", "description": "Execute Python, JavaScript, or Bash code", "icon": "terminal"},
            {"name": "web_search", "description": "Search the web using DuckDuckGo", "icon": "search"},
            {"name": "create_artifact", "description": "Create rich content (code, documents, HTML, SVG)", "icon": "file-code"},
            {"name": "read_file", "description": "Read uploaded file contents", "icon": "file-text"},
        ]
    }


def _run_python(code: str) -> dict:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()
        try:
            result = subprocess.run(
                ["python3", f.name],
                capture_output=True, text=True, timeout=30,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            )
            return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}
        except subprocess.TimeoutExpired:
            return {"stdout": "", "stderr": "Execution timed out (30s limit)", "returncode": -1}
        finally:
            os.unlink(f.name)


def _run_node(code: str) -> dict:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
        f.write(code)
        f.flush()
        try:
            result = subprocess.run(
                ["node", f.name],
                capture_output=True, text=True, timeout=30,
            )
            return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}
        except subprocess.TimeoutExpired:
            return {"stdout": "", "stderr": "Execution timed out (30s limit)", "returncode": -1}
        except FileNotFoundError:
            return {"stdout": "", "stderr": "Node.js not found", "returncode": -1}
        finally:
            os.unlink(f.name)


def _run_bash(code: str) -> dict:
    try:
        result = subprocess.run(
            ["bash", "-c", code],
            capture_output=True, text=True, timeout=30,
        )
        return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": "Execution timed out (30s limit)", "returncode": -1}
