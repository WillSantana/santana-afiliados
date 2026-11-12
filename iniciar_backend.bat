@echo off
chcp 65001 >nul
echo ==========================================
echo  Backend Django - Santana Afiliados Bot
echo ==========================================
cd /d "%~dp0backend"
echo Iniciando servidor Django em http://localhost:8000
echo.
.\venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000
pause
