import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from database import init_db

from routes.auth_routes import router as auth_router
from routes.chat_routes import router as chat_router
from routes.project_routes import router as project_router
from routes.tool_routes import router as tool_router
from routes.file_routes import router as file_router
from routes.share_routes import router as share_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Import models so tables are created
    import models  # noqa
    from routes.share_routes import SharedItem  # noqa
    await init_db()
    yield


app = FastAPI(title="Claude UI Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins — local app, safe behind Tailscale
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(project_router)
app.include_router(tool_router)
app.include_router(file_router)
app.include_router(share_router)

# Serve uploaded files
uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

# Serve generated images
generated_imgs_dir = os.path.expanduser("~/generated_imgs")
os.makedirs(generated_imgs_dir, exist_ok=True)
app.mount("/generated", StaticFiles(directory=generated_imgs_dir), name="generated")


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/personas")
async def list_personas():
    """List available AI personas."""
    import json as _json
    personas_path = os.path.join(os.path.dirname(__file__), "tools", "personas.json")
    with open(personas_path) as f:
        return _json.load(f)


@app.get("/api/gallery")
async def list_gallery():
    """List all generated images."""
    images = []
    for f in sorted(os.listdir(generated_imgs_dir), reverse=True):
        if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
            images.append({"name": f, "url": f"/generated/{f}"})
    return {"images": images}


@app.post("/api/location/update")
async def update_location(data: dict):
    """Receive GPS coordinates from the browser and reverse geocode."""
    from routes.chat_routes import _update_location_from_gps, _location_cache
    lat = data.get("lat")
    lon = data.get("lon")
    if lat is not None and lon is not None:
        await _update_location_from_gps(lat, lon)
        return {"status": "ok", "location": _location_cache.get("location", "")}
    return {"status": "error", "message": "Missing lat/lon"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=3001)
