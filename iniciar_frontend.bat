@echo off
chcp 65001 >nul
echo ==========================================
echo  Frontend React/Vite - Santana Afiliados
echo ==========================================
cd /d "%~dp0frontend"
echo Iniciando servidor Vite em http://localhost:5173
echo.
node node_modules\vite\bin\vite.js --host 0.0.0.0 --port 5173
pause
