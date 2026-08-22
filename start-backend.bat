@echo off
cd /d "C:\Users\pravi\OneDrive\Documents\Default Project\backend-api"
call venv\Scripts\activate.bat
python -m uvicorn app.main:app --host 127.0.0.1 --port 8080
