from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.api import router

app = FastAPI(
    title="PirateXPlay Anime API",
    description="Anime catalog, search, taxonomy, series, season and episode metadata.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "name": "PirateXPlay Anime API",
        "version": app.version,
        "docs": "/docs",
        "health": "/health",
    }

@app.get("/health")
async def health():
    return {"status": "ok", "service": "piratexplay-anime-api"}

app.include_router(router)
