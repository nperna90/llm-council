# LLM Council - Start script for Windows PowerShell

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "AVVIO DEL LLM COUNCIL IN CORSO..." -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host ""

# Verify security dependencies
Write-Host "[0/4] Verifica dipendenze di sicurezza..." -ForegroundColor Yellow
& uv run python verify_env.py 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "ATTENZIONE: Alcune dipendenze potrebbero mancare. Eseguendo verifica completa..." -ForegroundColor Yellow
    & uv run python verify_env.py
    Write-Host ""
    Write-Host "Premi un tasto per continuare..." -ForegroundColor Yellow
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}

# Start backend
Write-Host "[1/4] Avvio Backend su porta 8001..." -ForegroundColor Yellow
try {
    $backendCmd = "cd '$PSScriptRoot'; uv run uvicorn backend.main:app --reload --port 8001"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd -WindowStyle Minimized
    Write-Host "   Backend avviato in finestra separata" -ForegroundColor Green
} catch {
    Write-Host "   ✗ Errore avvio backend: $_" -ForegroundColor Red
    exit 1
}

# Wait a bit for backend to start
Start-Sleep -Seconds 5

# Start frontend
Write-Host "[2/4] Avvio Frontend..." -ForegroundColor Yellow
try {
    $frontendPath = Join-Path $PSScriptRoot "frontend"
    $frontendCmd = "cd '$frontendPath'; npm run dev"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd -WindowStyle Minimized
    Write-Host "   Frontend avviato in finestra separata" -ForegroundColor Green
} catch {
    Write-Host "   Errore avvio frontend: $_" -ForegroundColor Red
    Write-Host "   Il backend e comunque in esecuzione." -ForegroundColor Yellow
}

# Wait a bit for frontend to start
Start-Sleep -Seconds 3

# Open browser
Write-Host "[3/4] Apertura Browser..." -ForegroundColor Yellow
Start-Process "http://localhost:5173"

# Security information
Write-Host "[4/4] Informazioni di sicurezza..." -ForegroundColor Yellow
Write-Host ""
Write-Host "===================================================" -ForegroundColor Green
Write-Host "TUTTO AVVIATO!" -ForegroundColor Green
Write-Host "===================================================" -ForegroundColor Green
Write-Host ""
Write-Host "SICUREZZA:" -ForegroundColor Cyan
Write-Host "   - Il sistema richiede autenticazione" -ForegroundColor White
Write-Host "   - Al primo avvio, il primo login crea automaticamente" -ForegroundColor White
Write-Host "     l utente admin con le credenziali che inserisci" -ForegroundColor White
Write-Host "   - Password dimenticata? Controlla la console del backend" -ForegroundColor White
Write-Host "     per il link di reset" -ForegroundColor White
Write-Host ""
Write-Host "URL:" -ForegroundColor Cyan
Write-Host "   - Frontend: http://localhost:5173" -ForegroundColor White
Write-Host "   - Backend API: http://localhost:8001" -ForegroundColor White
Write-Host ""
Write-Host "ATTENZIONE: Chiudi le finestre PowerShell per fermare il sistema." -ForegroundColor Yellow
Write-Host "===================================================" -ForegroundColor Green
