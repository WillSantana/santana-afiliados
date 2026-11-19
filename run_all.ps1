# -------------------------------------------------
# run_all.ps1 - Inicia o ecossistema Santana Afiliados Bot
# -------------------------------------------------
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $projectRoot

$backendDir  = Join-Path $projectRoot 'backend'
$frontendDir = Join-Path $projectRoot 'frontend'
$pythonExe   = Join-Path $backendDir 'venv\Scripts\python.exe'
$pgCtl       = Join-Path $projectRoot 'pgsql\pgsql\bin\pg_ctl.exe'
$pgData      = Join-Path $projectRoot 'pgsql\data'
$pgLog       = Join-Path $projectRoot 'pgsql\server.log'

function Write-Info([string]$msg) {
    Write-Host "`n=== $msg ===`n" -ForegroundColor Cyan
}

# 1. PostgreSQL (so inicia se ainda estiver parado)
Write-Info "Verificando PostgreSQL"
& $pgCtl status -D $pgData | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "PostgreSQL parado. Iniciando..."
    & $pgCtl -D $pgData -l $pgLog start -w
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Falha ao iniciar o PostgreSQL. Verifique o log em $pgLog"
        exit 1
    }
} else {
    Write-Host "PostgreSQL ja esta rodando." -ForegroundColor Green
}

# 2. Migracoes Django
Write-Info "Verificando migracoes Django"
Set-Location $backendDir
& $pythonExe manage.py migrate
if ($LASTEXITCODE -ne 0) {
    Write-Error "Erro nas migracoes. Abortando."
    exit 1
}

# 3. Backend Django (porta 8000) em nova janela se nao estiver rodando
$backendUp = Test-NetConnection -ComputerName 127.0.0.1 -Port 8000 -InformationLevel Quiet -WarningAction SilentlyContinue
if (-not $backendUp) {
    Write-Info "Iniciando Backend Django (porta 8000)"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$backendDir'; & '$pythonExe' manage.py runserver 0.0.0.0:8000"
} else {
    Write-Host "Backend Django ja esta rodando na porta 8000." -ForegroundColor Green
}

# 4. Frontend React (porta 5173) em nova janela se nao estiver rodando
$frontendUp = Test-NetConnection -ComputerName 127.0.0.1 -Port 5173 -InformationLevel Quiet -WarningAction SilentlyContinue
if (-not $frontendUp) {
    Write-Info "Iniciando Frontend React (porta 5173)"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$frontendDir'; npm run dev"
} else {
    Write-Host "Frontend React ja esta rodando na porta 5173." -ForegroundColor Green
}

# 5. Chrome dedicado (porta 9222) se ainda nao estiver aberto
$chromeUp = Test-NetConnection -ComputerName 127.0.0.1 -Port 9222 -InformationLevel Quiet -WarningAction SilentlyContinue
if (-not $chromeUp) {
    Write-Info "Abrindo Chrome dedicado (porta 9222)"
    Start-Process cmd -ArgumentList "/c", "`"$projectRoot\iniciar_chrome_whatsapp.bat`""
} else {
    Write-Host "Chrome dedicado ja esta aberto na porta 9222." -ForegroundColor Green
}

Write-Info "Ambiente pronto!"
Write-Host "  Frontend : http://localhost:5173/"
Write-Host "  API      : http://localhost:8000/api/"
Write-Host "  Admin    : http://localhost:8000/admin/"
Write-Host ""
Write-Host "Depois de logar no WhatsApp Web e no Mercado Livre no Chrome dedicado, rode o monitor:" -ForegroundColor Yellow
Write-Host "  cd `"$backendDir`""
Write-Host "  .\venv\Scripts\python.exe manage.py monitor_whatsapp_offers --send"
