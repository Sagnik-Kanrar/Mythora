@echo off
title StoryWeave AI - Investigative Studio Launcher
echo ===================================================================
echo     STORYWEAVE AI - INVESTIGATIVE STORYTELLING STUDIO
echo ===================================================================
echo.
cd /d "%~dp0"

echo [1/2] Starting FastAPI Backend on http://127.0.0.1:8000 ...
start "StoryWeave Backend" cmd /k "python backend/run.py"

echo [2/2] Starting Vite React Frontend on http://localhost:5173 ...
start "StoryWeave Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ===================================================================
echo  Studio services dispatched successfully:
echo  - Frontend Web UI: http://localhost:5173
echo  - Backend API:     http://127.0.0.1:8000
echo  - Swagger Docs:    http://127.0.0.1:8000/docs
echo ===================================================================
pause
