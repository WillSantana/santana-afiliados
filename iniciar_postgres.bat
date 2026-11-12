@echo off
chcp 65001 >nul
setlocal

set "BASEDIR=%~dp0"
set "PGBIN=%BASEDIR%pgsql\pgsql\bin"
set "PGDATA=%BASEDIR%pgsql\data"
set "PGLOG=%BASEDIR%pgsql\server.log"

echo ==========================================
echo  Santana Afiliados Bot - Setup PostgreSQL
echo ==========================================

REM ----- 1. Inicia o PostgreSQL -----
echo.
echo [1/5] Iniciando servidor PostgreSQL na porta 5432...
"%PGBIN%\pg_ctl.exe" -D "%PGDATA%" -l "%PGLOG%" start -w
if %errorlevel% neq 0 (
    echo.
    echo AVISO: pg_ctl retornou erro. Verificando se o servidor ja esta rodando...
    "%PGBIN%\pg_ctl.exe" -D "%PGDATA%" status
    if %errorlevel% neq 0 (
        echo ERRO: Nao foi possivel iniciar o PostgreSQL.
        echo Verifique o log em: %PGLOG%
        pause
        exit /b 1
    )
)
echo PostgreSQL iniciado com sucesso!

REM ----- 2. Aguarda o servidor estar pronto -----
echo.
echo [2/5] Aguardando servidor aceitar conexoes...
timeout /t 2 /nobreak >nul
"%PGBIN%\pg_isready.exe" -h 127.0.0.1 -p 5432
if %errorlevel% neq 0 (
    timeout /t 3 /nobreak >nul
    "%PGBIN%\pg_isready.exe" -h 127.0.0.1 -p 5432
)

REM ----- 3. Cria usuario e banco (ignora se ja existir) -----
echo.
echo [3/5] Configurando usuario e banco de dados...
"%BASEDIR%backend\venv\Scripts\python.exe" "%BASEDIR%backend\setup_postgres.py"
if %errorlevel% neq 0 (
    echo ERRO ao configurar o banco. Confira o arquivo .env e o acesso do usuario postgres.
    pause
    exit /b 1
)

REM ----- 4. Roda migracoes Django (PostgreSQL) -----
echo.
echo [4/5] Rodando migracoes Django no PostgreSQL...
cd /d "%BASEDIR%backend"
.\venv\Scripts\python.exe manage.py migrate
if %errorlevel% neq 0 (
    echo ERRO nas migracoes! Verifique a conexao com o banco.
    pause
    exit /b 1
)

REM ----- 5. Cria admin e seed data -----
echo.
echo [5/5] Criando superusuario e dados de demonstracao...
.\venv\Scripts\python.exe create_admin.py

REM Verifica se ja tem dados
for /f "tokens=*" %%i in ('.\venv\Scripts\python.exe -c "import os, django; os.environ[\"DJANGO_SETTINGS_MODULE\"]=\"config.settings\"; django.setup(); from apps.catalog.models import ProductOffer; print(ProductOffer.objects.count())" 2^>nul') do set COUNT=%%i
if "%COUNT%"=="0" (
    echo Inserindo dados de demonstracao...
    .\venv\Scripts\python.exe seed_data.py
) else (
    echo Dados ja existem no banco ^(%COUNT% registros^), pulando seed.
)

echo.
echo ==========================================
echo  SETUP CONCLUIDO COM SUCESSO!
echo.
echo  Agora abra 2 terminais adicionais e rode:
echo    Terminal 2: iniciar_backend.bat
echo    Terminal 3: iniciar_frontend.bat
echo.
echo  URLs de acesso:
echo    Frontend:  http://localhost:5173
echo    API:       http://localhost:8000/api/
echo    Admin:     http://localhost:8000/admin/
echo    Use as credenciais do superusuario criado durante a configuracao.
echo ==========================================
pause
