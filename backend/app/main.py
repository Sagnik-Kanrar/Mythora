from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from datetime import datetime, timezone
import os
from .routers import stories, chapters, characters, timeline, memory, plotholes, ai, storyboard
from .config import (
    PORT, HOST, UPLOADS_DIR, APP_NAME, APP_VERSION, ENVIRONMENT,
    GEMINI_API_KEY, GEMINI_MODEL, EMBEDDING_MODEL, MONGODB_URI, DATABASE_NAME
)
from .services.db_service import db_service
from .services.vector_service import vector_service

app = FastAPI(
    title=f"{APP_NAME} - Investigative Storytelling Studio API",
    version=APP_VERSION,
    description="Backend services for Phasmophobia-inspired storytelling, character dossiers, timeline evidence, and persistent vector memory."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/api/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

app.include_router(stories.router)
app.include_router(chapters.router)
app.include_router(characters.router)
app.include_router(timeline.router)
app.include_router(memory.router)
app.include_router(plotholes.router)
app.include_router(storyboard.router)
app.include_router(ai.router)

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": APP_NAME,
        "aesthetic": "Phasmophobia Investigator Journal & Clipboard",
        "version": APP_VERSION
    }

@app.get("/health")
@app.get("/api/health")
def healthcheck():
    return {
        "status": "healthy",
        "application": APP_NAME,
        "version": APP_VERSION,
        "environment": ENVIRONMENT,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/health/database")
@app.get("/api/health/database")
def database_healthcheck():
    # MongoDB Check
    mongo_status = "not_configured"
    mongo_msg = "MongoDB URI not provided. Using persistent local JSON store fallback."
    if db_service.use_mongo:
        try:
            db_service.client.admin.command('ping')
            mongo_status = "healthy"
            mongo_msg = f"Connected to MongoDB database '{DATABASE_NAME}'"
        except Exception as e:
            mongo_status = "unhealthy"
            mongo_msg = f"MongoDB ping failed: {str(e)}"
    
    # ChromaDB / Vector Store Check
    chroma_status = "healthy"
    chroma_mode = "ChromaDB Persistent" if vector_service.has_chroma else "Native Multi-Layer Vector Engine"
    
    return {
        "status": "healthy",
        "storage_mode": "MongoDB" if db_service.use_mongo else "Persistent Local Store (storyweave_store.json)",
        "databases": {
            "mongodb": {
                "status": mongo_status,
                "database_name": DATABASE_NAME,
                "message": mongo_msg
            },
            "vector_store": {
                "status": chroma_status,
                "engine": chroma_mode,
                "persist_directory": str(getattr(vector_service, 'chroma_dir', './data/chroma'))
            }
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/health/ai")
@app.get("/api/health/ai")
def ai_healthcheck():
    gemini_status = "configured" if GEMINI_API_KEY else "not_configured"
    gemini_msg = "Gemini API key is configured" if GEMINI_API_KEY else "GEMINI_API_KEY is not set"
    
    # Live connectivity test if configured
    if GEMINI_API_KEY:
        try:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=GEMINI_API_KEY, http_options=types.HttpOptions(timeout=10000))
            # Test ping
            resp = client.models.generate_content(
                model=GEMINI_MODEL,
                contents="Ping",
            )
            if resp and resp.text:
                gemini_status = "healthy"
                gemini_msg = f"Gemini API connection verified with model '{GEMINI_MODEL}'"
        except Exception as e:
            # Try REST fallback ping
            try:
                import httpx
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
                with httpx.Client(timeout=10.0) as http_client:
                    r = http_client.post(url, json={"contents": [{"parts": [{"text": "Ping"}]}]})
                    if r.status_code == 200:
                        gemini_status = "healthy"
                        gemini_msg = f"Gemini REST API verified with model '{GEMINI_MODEL}'"
                    else:
                        gemini_status = "degraded"
                        gemini_msg = f"Gemini API returned HTTP {r.status_code}"
            except Exception as e2:
                gemini_status = "unhealthy"
                gemini_msg = f"Gemini connectivity failed: {str(e2)}"
                
    return {
        "status": "healthy" if gemini_status == "healthy" else ("degraded" if gemini_status == "configured" else "unhealthy"),
        "services": {
            "gemini": {
                "status": gemini_status,
                "model": GEMINI_MODEL,
                "message": gemini_msg
            },
            "embedding": {
                "model": EMBEDDING_MODEL,
                "status": "available",
                "message": "Sentence transformer embedding engine"
            }
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=HOST, port=PORT, reload=True)
