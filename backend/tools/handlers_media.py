"""Media handlers — image generation, image editing, security camera."""
import os

import httpx


# ── Image Generation ────────────────────────────────────────────────────────

async def _generate_image(args: dict) -> dict:
    """Generate an image using Imagen 4.0 Ultra (Google's best image model)."""
    from google import genai
    import uuid as _uuid

    prompt = args.get("prompt", "")
    api_key = os.environ.get("GEMINI_API_KEY", "")

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_images(
            model="imagen-4.0-ultra-generate-001",
            prompt=prompt,
        )

        if response.generated_images:
            output_dir = os.path.expanduser("~/generated_imgs")
            os.makedirs(output_dir, exist_ok=True)
            filename = f"{_uuid.uuid4().hex[:12]}.png"
            output_path = os.path.join(output_dir, filename)

            img_bytes = response.generated_images[0].image.image_bytes
            with open(output_path, "wb") as f:
                f.write(img_bytes)

            return {
                "success": True,
                "file_path": output_path,
                "filename": filename,
                "prompt": prompt,
                "message": f"Image generated and saved to {output_path}",
            }

        return {"success": False, "error": "No image generated"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ── Image Editing ───────────────────────────────────────────────────────────

async def _edit_image(args: dict) -> dict:
    """Edit an existing image using Gemini API."""
    from google import genai
    from google.genai import types
    import base64 as b64
    import uuid as _uuid

    image_path = args.get("image_path", "")
    prompt = args.get("prompt", "")
    api_key = os.environ.get("GEMINI_API_KEY", "")

    if not os.path.exists(image_path):
        return {"success": False, "error": f"Image not found: {image_path}"}

    try:
        client = genai.Client(api_key=api_key)

        with open(image_path, "rb") as f:
            img_data = f.read()

        response = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=[
                types.Content(parts=[
                    types.Part.from_bytes(data=img_data, mime_type="image/png"),
                    types.Part.from_text(text=prompt),
                ])
            ],
        )

        if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'inline_data') and part.inline_data and part.inline_data.mime_type and part.inline_data.mime_type.startswith("image/"):
                    output_dir = os.path.expanduser("~/generated_imgs")
                    os.makedirs(output_dir, exist_ok=True)
                    filename = f"{_uuid.uuid4().hex[:12]}_edited.png"
                    output_path = os.path.join(output_dir, filename)

                    img_bytes = part.inline_data.data
                    if isinstance(img_bytes, str):
                        img_bytes = b64.b64decode(img_bytes)
                    with open(output_path, "wb") as f:
                        f.write(img_bytes)

                    return {"success": True, "file_path": output_path, "filename": filename, "prompt": prompt, "message": f"Image edited and saved to {output_path}"}

        return {"success": False, "error": "No image in response"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ── Security Camera ────────────────────────────────────────────────────────

async def _security_camera(args: dict) -> dict:
    """Capture a snapshot from the security camera and analyze it with Gemini vision."""
    import base64
    import uuid as _uuid

    camera = args.get("camera", "front_door")
    question = args.get("question", "")

    # Camera RTSP URLs
    cameras = {
        "front_door": {
            "url": "rtsp://admin:Camera1234@192.168.1.188:554/h264Preview_01_sub",
            "name": "Front Door",
        },
    }

    cam_info = cameras.get(camera, cameras["front_door"])
    cam_name = cam_info["name"]
    cam_url = cam_info["url"]

    # Capture frame via ffmpeg (more reliable than cv2 for RTSP)
    snapshot_dir = os.path.expanduser("~/generated_imgs")
    os.makedirs(snapshot_dir, exist_ok=True)
    filename = f"camera_{_uuid.uuid4().hex[:12]}.jpg"
    snapshot_path = os.path.join(snapshot_dir, filename)

    try:
        import subprocess as _sp
        result = _sp.run(
            [
                "ffmpeg", "-y",
                "-rtsp_transport", "tcp",
                "-i", cam_url,
                "-frames:v", "1",
                "-q:v", "2",
                snapshot_path,
            ],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0 or not os.path.exists(snapshot_path):
            return {"error": f"Could not capture from {cam_name} camera. It may be offline."}
    except Exception as e:
        return {"error": f"Camera capture failed: {str(e)}"}

    # Read and encode the image
    with open(snapshot_path, "rb") as f:
        img_bytes = f.read()
    frame_b64 = base64.b64encode(img_bytes).decode()

    # Analyze with Gemini vision
    analysis = ""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if api_key:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                vision_prompt = f"You are a home security assistant. Describe what you see in this image from the {cam_name} camera. Be specific about people, vehicles, animals, objects, and activities."
                if question:
                    vision_prompt += f" The user specifically asks: {question}"

                resp = await client.post(
                    "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
                    params={"key": api_key},
                    json={
                        "contents": [{
                            "parts": [
                                {"text": vision_prompt},
                                {"inline_data": {"mime_type": "image/jpeg", "data": frame_b64}},
                            ]
                        }]
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for candidate in data.get("candidates", []):
                        for part in candidate.get("content", {}).get("parts", []):
                            if "text" in part:
                                analysis = part["text"]
                                break
                        if analysis:
                            break
        except Exception as e:
            analysis = f"Camera captured but vision analysis failed: {str(e)}"

    if not analysis:
        analysis = "Snapshot captured but could not analyze the image (no vision API available)."

    return {
        "success": True,
        "filename": filename,
        "camera": cam_name,
        "analysis": analysis,
        "prompt": f"{cam_name} camera snapshot",
    }
