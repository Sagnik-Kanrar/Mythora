import uvicorn
import sys
import os

backend_dir = os.path.abspath(os.path.dirname(__file__))
parent_dir = os.path.abspath(os.path.join(backend_dir, ".."))

if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

if __name__ == "__main__":
    try:
        from backend.app.config import HOST, PORT
        app_target = "backend.app.main:app"
    except ImportError:
        from app.config import HOST, PORT
        app_target = "app.main:app"

    print(f"Starting StoryWeave AI Backend on http://{HOST}:{PORT} ...")
    uvicorn.run(app_target, host=HOST, port=PORT, reload=True)
