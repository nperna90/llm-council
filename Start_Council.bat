@echo off
TITLE LLM Council Launcher

:: 1. Si posiziona nella cartella dove si trova questo file
cd /d "%~dp0"

echo ===================================================
echo 🏛️  AVVIO DEL LLM COUNCIL IN CORSO...
echo ===================================================
echo.

:: 1.5. Verifica dipendenze di sicurezza
echo [0/4] Verifica dipendenze di sicurezza...
uv run python verify_env.py >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ⚠️  Alcune dipendenze potrebbero mancare. Eseguendo verifica completa...
    uv run python verify_env.py
    echo.
    echo Premi un tasto per continuare o Ctrl+C per uscire...
    pause >nul
)

:: 2. Avvia il Backend (usa uv come nel tuo script)
echo [1/4] Avvio Backend su porta 8001...
start "Backend API" cmd /k "cd /d %~dp0 && uv run uvicorn backend.main:app --reload --port 8001"

:: Aspetta 5 secondi per dare tempo al backend di caricare
timeout /t 5 /nobreak >nul

:: 3. Avvia il Frontend
echo [2/4] Avvio Frontend (React)...
start "Frontend UI" cmd /k "cd /d %~dp0frontend && npm run dev"

:: Aspetta 3 secondi
timeout /t 3 /nobreak >nul

:: 4. Apre il Browser automaticamente
echo [3/4] Apertura Browser...
start http://localhost:5173

:: 5. Mostra informazioni di sicurezza
echo [4/4] Informazioni di sicurezza...
echo.
echo ===================================================
echo ✅ TUTTO AVVIATO!
echo ===================================================
echo.
echo 🔐 SICUREZZA:
echo    - Il sistema richiede autenticazione
echo    - Al primo avvio, il primo login crea automaticamente
echo      l'utente admin con le credenziali che inserisci
echo    - Password dimenticata? Controlla la console del backend
echo      per il link di reset
echo.
echo 📍 URL:
echo    - Frontend: http://localhost:5173
echo    - Backend API: http://localhost:8001
echo.
echo ⚠️  Chiudi le finestre nere per fermare il sistema.
echo ===================================================
timeout /t 5
