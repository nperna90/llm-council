#!/bin/bash

# LLM Council - Start script

echo "==================================================="
echo "🏛️  AVVIO DEL LLM COUNCIL IN CORSO..."
echo "==================================================="
echo ""

# Verify security dependencies
echo "[0/4] Verifica dipendenze di sicurezza..."
if ! uv run python verify_env.py > /dev/null 2>&1; then
    echo "⚠️  Alcune dipendenze potrebbero mancare. Eseguendo verifica completa..."
    uv run python verify_env.py
    echo ""
    read -p "Premi INVIO per continuare o Ctrl+C per uscire..."
fi

# Start backend
echo "[1/4] Avvio Backend su porta 8001..."
uv run uvicorn backend.main:app --reload --port 8001 &
BACKEND_PID=$!

# Wait a bit for backend to start
sleep 5

# Start frontend
echo "[2/4] Avvio Frontend (React)..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

# Wait a bit for frontend to start
sleep 3

# Open browser (Linux/Mac)
echo "[3/4] Apertura Browser..."
if command -v xdg-open > /dev/null; then
    xdg-open http://localhost:5173 2>/dev/null &
elif command -v open > /dev/null; then
    open http://localhost:5173 2>/dev/null &
fi

# Security information
echo "[4/4] Informazioni di sicurezza..."
echo ""
echo "==================================================="
echo "✅ TUTTO AVVIATO!"
echo "==================================================="
echo ""
echo "🔐 SICUREZZA:"
echo "   - Il sistema richiede autenticazione"
echo "   - Al primo avvio, il primo login crea automaticamente"
echo "     l'utente admin con le credenziali che inserisci"
echo "   - Password dimenticata? Controlla la console del backend"
echo "     per il link di reset"
echo ""
echo "📍 URL:"
echo "   - Frontend: http://localhost:5173"
echo "   - Backend API: http://localhost:8001"
echo ""
echo "⚠️  Premi Ctrl+C per fermare entrambi i server"
echo "==================================================="

# Wait for Ctrl+C
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" SIGINT SIGTERM
wait
