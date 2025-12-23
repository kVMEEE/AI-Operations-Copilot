from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.routers import incidents

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(incidents.router, prefix=f"{settings.API_V1_STR}/incidents", tags=["incidents"])

@app.get("/")
def root():
    return {"message": "Welcome to AI Operations Copilot API"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
