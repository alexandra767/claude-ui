"""Utility helpers for file reading and image processing."""

import base64
import os
from io import BytesIO


def resize_image_for_vision(filepath: str, max_size: int = 1024) -> str:
    """Resize image and convert to base64 for vision model. Keeps under ~1MB."""
    try:
        from PIL import Image
        img = Image.open(filepath)
        # Convert RGBA to RGB
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        # Resize if too large
        w, h = img.size
        if w > max_size or h > max_size:
            ratio = min(max_size / w, max_size / h)
            img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
        # Save to buffer as JPEG (smaller than PNG)
        buf = BytesIO()
        img.save(buf, format='JPEG', quality=85)
        return base64.b64encode(buf.getvalue()).decode('utf-8')
    except Exception:
        # Fallback: read raw file
        try:
            with open(filepath, 'rb') as f:
                data = f.read()
            if len(data) > 5 * 1024 * 1024:  # Skip files over 5MB
                return ""
            return base64.b64encode(data).decode('utf-8')
        except Exception:
            return ""


def read_file_content(filepath: str, filename: str) -> str:
    """Read file content, supporting PDF, text, code, and common formats."""
    if not filepath or not os.path.exists(filepath):
        return ""
    try:
        ext = os.path.splitext(filename.lower())[1]
        # PDF
        if ext == ".pdf":
            import fitz  # PyMuPDF
            doc = fitz.open(filepath)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            # Truncate very long PDFs
            if len(text) > 15000:
                text = text[:15000] + "\n\n...(truncated, showing first ~15000 characters)"
            return text
        # Binary files we can't read
        if ext in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".mp3", ".mp4", ".zip", ".tar", ".gz"):
            return f"[Binary file: {filename}, {os.path.getsize(filepath)} bytes]"
        # Everything else: try as text
        with open(filepath, "r", errors="replace") as f:
            text = f.read()
        if len(text) > 15000:
            text = text[:15000] + "\n\n...(truncated)"
        return text
    except Exception as e:
        return f"[Could not read file: {e}]"
