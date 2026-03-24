"""MCP (Model Context Protocol) client — communicates with MCP servers via stdio JSON-RPC."""
import subprocess
import json
import os
import threading
import queue


class MCPClient:
    """Connects to an MCP server process and calls tools."""

    def __init__(self, command: str, args: list[str], env: dict[str, str] | None = None):
        self.command = command
        self.args = args
        self.env = {**os.environ, **(env or {})}
        self.process = None
        self.response_queue = queue.Queue()
        self._next_id = 1
        self._reader_thread = None

    def start(self):
        self.process = subprocess.Popen(
            [self.command] + self.args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=self.env,
        )
        self._reader_thread = threading.Thread(target=self._read_stdout, daemon=True)
        self._reader_thread.start()
        # Initialize
        self._send("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "claude-ui", "version": "1.0"},
        })
        self._recv(timeout=5)

    def stop(self):
        if self.process:
            self.process.kill()
            self.process = None

    def list_tools(self) -> list[dict]:
        self._send("tools/list", {})
        resp = self._recv(timeout=5)
        if resp and "result" in resp:
            return resp["result"].get("tools", [])
        return []

    def call_tool(self, name: str, arguments: dict, timeout: float = 60) -> dict:
        self._send("tools/call", {"name": name, "arguments": arguments})
        resp = self._recv(timeout=timeout)
        if resp and "result" in resp:
            return resp["result"]
        if resp and "error" in resp:
            return {"error": resp["error"].get("message", str(resp["error"]))}
        return {"error": "No response from MCP server"}

    def _send(self, method: str, params: dict):
        msg = json.dumps({"jsonrpc": "2.0", "id": self._next_id, "method": method, "params": params})
        self._next_id += 1
        self.process.stdin.write((msg + "\n").encode())
        self.process.stdin.flush()

    def _recv(self, timeout: float = 10) -> dict | None:
        try:
            return self.response_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def _read_stdout(self):
        """Read JSON-RPC responses line by line from stdout."""
        while self.process and self.process.poll() is None:
            try:
                line = self.process.stdout.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="replace").strip()
                if not text:
                    continue
                try:
                    obj = json.loads(text)
                    self.response_queue.put(obj)
                except json.JSONDecodeError:
                    # Might be partial — accumulate
                    pass
            except Exception:
                break


# ── Singleton MCP clients ───────────────────────────────────────────────────

_clients: dict[str, MCPClient] = {}


def get_mcp_client(name: str) -> MCPClient | None:
    """Get or start a named MCP client."""
    if name in _clients and _clients[name].process and _clients[name].process.poll() is None:
        return _clients[name]

    # Load config
    config_path = os.path.expanduser("~/.mcp.json")
    if not os.path.exists(config_path):
        return None
    with open(config_path) as f:
        config = json.load(f)

    server_config = config.get("mcpServers", {}).get(name)
    if not server_config:
        return None

    client = MCPClient(
        command=server_config["command"],
        args=server_config.get("args", []),
        env=server_config.get("env"),
    )
    try:
        client.start()
        _clients[name] = client
        return client
    except Exception as e:
        print(f"Failed to start MCP server '{name}': {e}")
        return None


def list_mcp_tools(name: str) -> list[dict]:
    client = get_mcp_client(name)
    if not client:
        return []
    return client.list_tools()


def call_mcp_tool(server_name: str, tool_name: str, arguments: dict, timeout: float = 60) -> dict:
    client = get_mcp_client(server_name)
    if not client:
        return {"error": f"MCP server '{server_name}' not available"}
    return client.call_tool(tool_name, arguments, timeout=timeout)
