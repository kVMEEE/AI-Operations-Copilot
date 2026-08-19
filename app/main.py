import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from app.core.config import settings
from app.core.cpp_bridge import cpp_bridge
from app.routers import incidents, health, analyze

app = FastAPI(
    title=f"{settings.PROJECT_NAME} (100% C++ & Python)",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# CORS Middleware configuration
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Mount static files directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Include API Routers
app.include_router(incidents.router, prefix=f"{settings.API_V1_STR}/incidents", tags=["Incidents"])
app.include_router(health.router, tags=["Health"])
app.include_router(analyze.router, tags=["Analysis"])

@app.get("/")
def serve_dashboard():
    index_path = os.path.join(TEMPLATES_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": f"AI Operations Copilot API - Engine: {cpp_bridge.version}"}

@app.get("/api/v1/engine/info")
def engine_info():
    return {
        "engine": cpp_bridge.version,
        "is_native": cpp_bridge.is_native,
        "architecture": "100% C++17 Core Analytics & Python Async Orchestrator",
        "stack": ["C++17 (g++)", "Python 3.13", "FastAPI", "Uvicorn"]
    }
