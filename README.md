# StoryWeave AI — Investigative Storytelling Studio & Universe Intelligence

> An immersive, tactical AI authoring and narrative world-building platform inspired by investigative journals and evidence boards, reinterpreted for fiction writers across **Mystery, Horror, Fantasy, Sci-Fi, Adventure, and Drama**.

---

## 🏛️ Project Architecture & Unified Integration

This repository unifies and integrates the complete backend and frontend services into a clean, cohesive full-stack architecture:

```
final-project/
│
├── run_studio.bat             # ⚡ One-click launcher for both Backend & Frontend
├── package.json               # Root scripts
├── README.md                  # Comprehensive documentation
│
├── backend/                   # 🐍 FastAPI AI Intelligence Services
│   ├── run.py                 # Uvicorn backend launcher (http://127.0.0.1:8000)
│   ├── requirements.txt       # Python dependencies
│   ├── .env.example           # Environment variables template
│   ├── app/
│   │   ├── config.py          # Port, Host, Gemini API, Uploads directory
│   │   ├── main.py            # FastAPI entry point, CORS, static uploads
│   │   ├── models/            # Pydantic domain models (Story, Chapter, Page, Character, etc.)
│   │   ├── routers/           # 8 REST API Routers (70 endpoints)
│   │   │   ├── stories.py     # Story lifecycle + Cover image upload
│   │   │   ├── chapters.py    # Chapters CRUD, Page pagination & auto-extraction
│   │   │   ├── characters.py  # 745-line Entity Resolution, POI classification & Dossiers
│   │   │   ├── timeline.py    # Timeline event extraction & tracking
│   │   │   ├── memory.py      # Universe Memory grounded RAG synthesis & retrieval
│   │   │   ├── plotholes.py   # Plot hole contradiction audits & document parsing
│   │   │   ├── storyboard.py  # Investigation corkboard & yarn thread connections
│   │   │   └── ai.py          # Context-grounded Co-writer assistance
│   │   └── services/
│   │       ├── ai_service.py      # Gemini intelligence, outline synthesis & analysis
│   │       ├── db_service.py      # Reentrant thread-safe RLock persistence
│   │       ├── vector_service.py  # ChromaDB & semantic vector codex engine
│   │       └── document_parser.py # Docx, PDF, TXT manuscript parsing
│   ├── data/
│   │   ├── storyweave_store.json  # Consolidated universe database (12 stories, 17 characters)
│   │   └── uploads/               # Uploaded cover images and evidence assets
│   └── tests/                 # Automated test suite (25 verified tests)
│       ├── test_character_intelligence.py
│       ├── test_universe_and_consolidation.py
│       └── test_full_system_verification.py
│
├── frontend/                  # ⚛️ React 19 + TypeScript + Vite UI
│   ├── index.html             # HTML entry with antique aesthetic
│   ├── vite.config.ts         # Proxy config: forwards /api to http://127.0.0.1:8000
│   ├── package.json           # Frontend dependencies
│   ├── public/                # Video backgrounds, textures, and cursor assets
│   └── src/
│       ├── components/        # InvestigationBoard, CustomCursor, BookHero, RichTextToolbar, etc.
│       ├── context/           # StoryContext (active story persistence) & CursorContext
│       ├── pages/             # HomeDesk, CharacterArchive, WritingStudio, UniverseMemory, etc.
│       ├── services/          # api.ts (Unified REST client) & audioService.ts (synthesized typewriter soundscape)
│       └── types/             # Full TypeScript interfaces
│
├── StoryAI/                   # 📁 Synchronized module folder
└── writer-helper/             # 📁 Synchronized module folder
```

---

## ✨ Integrated Capabilities & Features

1. **The Writer's Desk (`HomeDesk.tsx`)**
   - Dark wooden detective workspace, open case files, Polaroid evidence, brass fittings, and live universe telemetry.
2. **Character Archive & Dossiers (`CharacterArchive.tsx`)**
   - **Person of Interest (POI) Classification**: Classify suspects (`Innocent`, `Person of Interest`, `Unclassified`).
   - **AI Entity Resolution**: Identifies aliases and titles (e.g. `Mr. Calder` $\to$ `Julian Calder`) without accidental merges.
   - **Sync from Manuscript**: Scan chapters to automatically extract new characters and register dossiers.
   - **Evidence Board**: Visual corkboard with connected yarn threads and pushpins.
3. **Writing Studio (`WritingStudio.tsx`)**
   - **Multi-page Virtual Document**: Realistic page turning, 3D flip animation, and per-page autosave.
   - **Rich Text Toolbar**: Formatting controls on tactile brass/wood toolbar.
   - **Manuscript Character Sync**: In-editor button to scan chapters and update character dossiers live.
   - **Grounded AI Co-writer**: Context-aware suggestions powered by Gemini with injected vector memories.
4. **Universe Memory & RAG Retrieval (`UniverseMemory.tsx`)**
   - Semantic retrieval across character lore, locations, relationships, and manuscript chunks.
   - **Interactive RAG Chat**: Ask questions about fictional canon with citation sources and confidence scoring.
   - **Reindex Engine**: One-click reindexing of narrative chunks.
5. **Plot Hole Detector (`PlotHoleDetector.tsx`)**
   - Cross-chapter contradiction analysis across characters, timelines, and world rules.
   - Support for document uploads (Word `.docx`, PDF `.pdf`, text `.txt`).
6. **Custom Antique Fountain Pen Cursor System**
   - Golden fountain pen and pointing hand cursor states with smooth motion trails and click ink ripples.
7. **Cover Image Upload & Persistence**
   - Custom story cover image uploads served from `/api/uploads/` with instant context reflection.

---

## 🚀 Getting Started & Local Launch

### Quick Launch (Recommended for Windows)

Double-click `run_studio.bat` in the root folder, or execute:

```powershell
.\run_studio.bat
```

This starts:
- **Backend API**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive Swagger Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Frontend Studio UI**: [http://localhost:5173](http://localhost:5173)

---

### Manual Launch

#### 1. Backend:
```powershell
# Navigate to backend directory
cd backend

# Install dependencies if not already installed
pip install -r requirements.txt

# Start FastAPI server
python run.py
```

#### 2. Frontend:
```powershell
# Open a new terminal in the frontend directory
cd frontend

# Install npm dependencies (first time only)
npm install

# Start Vite development server
npm run dev
```

Navigate to `http://localhost:5173` in your browser.

---

## 🧪 Verification & Automated Tests

All 25 automated backend tests have been verified:
- `test_character_intelligence.py`: 15 passed (canonical matching, alias resolution, status history, relationship directionality).
- `test_universe_and_consolidation.py`: 4 passed (chunking, dense indexing, lossless consolidation).
- `test_full_system_verification.py`: 6 passed (idempotent reindexing, cross-universe isolation, anti-hallucination).

To run the verification suite:
```powershell
python -c "import sys, types; sys.modules['pytest'] = types.ModuleType('pytest'); sys.path.insert(0, 'backend'); import tests.test_character_intelligence as a, tests.test_universe_and_consolidation as b, tests.test_full_system_verification as c; [getattr(m, f)() for m in (a, b, c) for f in dir(m) if f.startswith('test_')]; print('All tests passed!')"
```
