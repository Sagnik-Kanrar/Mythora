import os
from pathlib import Path
from dotenv import load_dotenv

# Search for .env in current and parent directories
BASE_DIR = Path(__file__).resolve().parent.parent
env_paths = [
    BASE_DIR / ".env",
    BASE_DIR.parent / ".env",
    Path(".env")
]

for p in env_paths:
    if p.exists():
        load_dotenv(dotenv_path=p, override=True)
        break

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR = DATA_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Application Metadata
APP_NAME = os.getenv("APP_NAME", "Mythora")
APP_VERSION = os.getenv("APP_VERSION", "0.1.0")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# AI & Embedding Engine
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
CHROMA_PERSIST_DIRECTORY = os.getenv("CHROMA_PERSIST_DIRECTORY", str(DATA_DIR / "chroma"))

# Database Configuration
MONGODB_URI = os.getenv("MONGODB_URI", "")
DATABASE_NAME = os.getenv("DATABASE_NAME") or os.getenv("MONGODB_DB_NAME", "storyweave")
MONGODB_DB_NAME = DATABASE_NAME
FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH", "")

# Server Configuration
PORT = int(os.getenv("PORT", 8000))
HOST = os.getenv("HOST", "127.0.0.1")
