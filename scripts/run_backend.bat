@echo off
rem 启动后端服务（FastAPI + uvicorn）
cd /d "%~dp0..\backend"
set PYTHONIOENCODING=utf-8
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
pause
