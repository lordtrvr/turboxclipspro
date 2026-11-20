@echo off
cd /d "%~dp0"
if not exist .env (
    copy .env.example .env
    echo.
    echo Se creo .env desde .env.example. Editalo con tus datos (SMTP, SECRET_KEY, etc.)
    echo.
)
pip install -r backend\requirements.txt -q
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
pause