@echo off
chcp 65001 >nul
setlocal

set "CHROME=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
if not exist "%CHROME%" set "CHROME=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
if not exist "%CHROME%" (
    echo ERRO: Google Chrome nao encontrado.
    pause
    exit /b 1
)

curl.exe --fail --silent http://127.0.0.1:9222/json/version >nul 2>nul
if not errorlevel 1 (
    echo ERRO: A porta local 9222 ja esta em uso.
    echo Feche a instancia de depuracao existente e execute este arquivo novamente.
    pause
    exit /b 1
)

set "PROFILE=%LOCALAPPDATA%\SantanaAfiliadosBot\ChromeProfile"
if not exist "%PROFILE%" mkdir "%PROFILE%"

echo Iniciando Chrome com perfil exclusivo do monitor...
echo A porta de depuracao fica limitada a 127.0.0.1.
start "Chrome - Santana WhatsApp Monitor" "%CHROME%" ^
    --remote-debugging-address=127.0.0.1 ^
    --remote-debugging-port=9222 ^
    --user-data-dir="%PROFILE%" ^
    --profile-directory=Default ^
    https://web.whatsapp.com/

timeout /t 3 /nobreak >nul
curl.exe --fail --silent http://127.0.0.1:9222/json/version >nul 2>nul
if errorlevel 1 (
    echo ERRO: Chrome nao abriu a porta de depuracao.
    echo Confira o Chrome e tente novamente.
    pause
    exit /b 1
)

echo.
echo Chrome pronto. Faca login no WhatsApp Web e no gerador de afiliados.
echo Depois execute em outro terminal:
echo   cd /d "C:\projetos wilson\apivendas\backend"
echo   .\venv\Scripts\python.exe manage.py monitor_whatsapp_offers --send
echo.
echo Nao use este perfil para navegacao comum nem exponha a porta 9222 na rede.
pause
