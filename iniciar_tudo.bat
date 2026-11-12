@echo off
chcp 65001 >nul
title Santana Afiliados Bot - Launcher
echo ===================================================================
echo  Santana Afiliados Bot - Iniciando Banco, Backend e Frontend
echo ===================================================================

set "BASEDIR=%~dp0"

REM 1. Verifica e inicia PostgreSQL sem remover postmaster.pid
echo [1/3] Verificando PostgreSQL 16...
"%BASEDIR%pgsql\pgsql\bin\pg_ctl.exe" status -D "%BASEDIR%pgsql\data"
if errorlevel 1 (
    echo PostgreSQL parado. Iniciando...
    "%BASEDIR%pgsql\pgsql\bin\pg_ctl.exe" -D "%BASEDIR%pgsql\data" -l "%BASEDIR%pgsql\server.log" start -w
    if errorlevel 1 (
        echo ERRO: Nao foi possivel iniciar o PostgreSQL.
        echo Verifique o log em: %BASEDIR%pgsql\server.log
        pause
        exit /b 1
    )
) else (
    echo PostgreSQL ja esta rodando.
)

REM 3. Abre Backend Django em janela dedicada
echo [2/3] Iniciando Backend Django (porta 8000)...
start "2. Backend Django - Santana Afiliados" cmd /k "title Backend Django && cd /d "%BASEDIR%backend" && .\venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000"

REM Aguarda Backend iniciar
timeout /t 2 /nobreak >nul

REM 4. Abre Frontend React Vite em janela dedicada
echo [3/3] Iniciando Frontend React (porta 5173)...
start "3. Frontend React - Santana Afiliados" cmd /k "title Frontend React && cd /d "%BASEDIR%frontend" && node node_modules\vite\bin\vite.js --host 0.0.0.0 --port 5173"

echo.
echo ===================================================================
echo  Tudo pronto e rodando!
echo.
echo  - Frontend React:  http://localhost:5173
echo  - API Backend:     http://localhost:8000/api/
echo  - Painel Admin:    http://localhost:8000/admin/
echo ===================================================================
pause
