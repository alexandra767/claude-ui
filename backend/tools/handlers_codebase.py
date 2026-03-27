"""Codebase explorer handlers — tree, read, search."""
import os


# ── Codebase Explorer ───────────────────────────────────────────────────────

# Allowed base directories (security — prevent reading /etc/passwd etc)
ALLOWED_BASES = [
    os.path.expanduser("~/"),
]


def _is_safe_path(path: str) -> bool:
    """Check if path is under an allowed directory."""
    real = os.path.realpath(os.path.expanduser(path))
    return any(real.startswith(os.path.realpath(base)) for base in ALLOWED_BASES)

SKIP_DIRS = {
    'node_modules', '.git', '__pycache__', '.next', 'dist', 'build',
    '.venv', 'venv', '.cache', '.Trash', 'Pods', 'DerivedData',
    '.build', '.swiftpm', 'target', 'coverage', '.tox', 'egg-info',
}
SKIP_EXTENSIONS = {
    '.pyc', '.pyo', '.o', '.so', '.dylib', '.class', '.jar',
    '.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg', '.webp',
    '.mp3', '.mp4', '.mov', '.avi', '.wav',
    '.zip', '.tar', '.gz', '.bz2', '.7z',
    '.db', '.sqlite', '.lock', '.map',
    '.woff', '.woff2', '.ttf', '.eot',
    '.pickle', '.pkl',
}


async def _codebase_tree(args: dict) -> dict:
    """Get the file tree of a project directory."""
    path = os.path.expanduser(args.get("path", ""))
    max_depth = args.get("max_depth", 3)

    if not path or not os.path.isdir(path):
        return {"error": f"Directory not found: {path}"}
    if not _is_safe_path(path):
        return {"error": "Access denied"}

    tree = []
    file_count = 0
    dir_count = 0

    def walk(dirpath: str, prefix: str, depth: int):
        nonlocal file_count, dir_count
        if depth > max_depth:
            return
        try:
            entries = sorted(os.listdir(dirpath))
        except PermissionError:
            return

        dirs = []
        files = []
        for e in entries:
            if e.startswith('.') and e not in ('.env', '.gitignore'):
                continue
            full = os.path.join(dirpath, e)
            if os.path.isdir(full):
                if e not in SKIP_DIRS:
                    dirs.append(e)
            else:
                ext = os.path.splitext(e)[1].lower()
                if ext not in SKIP_EXTENSIONS:
                    files.append(e)

        for d in dirs:
            dir_count += 1
            tree.append(f"{prefix}{d}/")
            walk(os.path.join(dirpath, d), prefix + "  ", depth + 1)
        for f in files:
            file_count += 1
            size = os.path.getsize(os.path.join(dirpath, f))
            size_str = f"{size}" if size < 1024 else f"{size//1024}KB"
            tree.append(f"{prefix}{f} ({size_str})")

    tree.append(os.path.basename(path.rstrip('/')) + "/")
    walk(path, "  ", 0)

    return {
        "tree": "\n".join(tree),
        "files": file_count,
        "directories": dir_count,
        "path": path,
    }


async def _codebase_read(args: dict) -> dict:
    """Read a specific file from a project."""
    filepath = os.path.expanduser(args.get("path", ""))

    if not filepath or not os.path.isfile(filepath):
        return {"error": f"File not found: {filepath}"}
    if not _is_safe_path(filepath):
        return {"error": "Access denied"}

    ext = os.path.splitext(filepath)[1].lower()
    if ext in SKIP_EXTENSIONS:
        return {"error": f"Binary file, cannot read: {filepath}"}

    try:
        with open(filepath, "r", errors="replace") as f:
            content = f.read()
        if len(content) > 20000:
            content = content[:20000] + f"\n\n...(truncated, file is {len(content)} chars total)"
        lines = content.count('\n') + 1
        return {
            "path": filepath,
            "filename": os.path.basename(filepath),
            "content": content,
            "lines": lines,
            "size": os.path.getsize(filepath),
        }
    except Exception as e:
        return {"error": str(e)}


async def _codebase_search(args: dict) -> dict:
    """Search for text across all files in a project directory."""
    path = os.path.expanduser(args.get("path", ""))
    query = args.get("query", "")
    max_results = args.get("max_results", 20)

    if not path or not os.path.isdir(path):
        return {"error": f"Directory not found: {path}"}
    if not _is_safe_path(path):
        return {"error": "Access denied"}
    if not query:
        return {"error": "Search query required"}

    results = []
    query_lower = query.lower()

    for root, dirs, files in os.walk(path):
        # Skip ignored dirs
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith('.')]
        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            if ext in SKIP_EXTENSIONS:
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, "r", errors="replace") as f:
                    for i, line in enumerate(f, 1):
                        if query_lower in line.lower():
                            rel = os.path.relpath(fpath, path)
                            results.append({
                                "file": rel,
                                "line": i,
                                "text": line.strip()[:200],
                            })
                            if len(results) >= max_results:
                                return {"results": results, "count": len(results), "query": query, "truncated": True}
            except Exception:
                continue

    return {"results": results, "count": len(results), "query": query}
