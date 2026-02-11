# Script per riavviare il backend con le nuove configurazioni CORS

Write-Host "Arresto processi uvicorn esistenti..." -ForegroundColor Yellow

# Trova e termina i processi uvicorn
Get-Process | Where-Object {$_.ProcessName -eq "uvicorn" -or ($_.ProcessName -eq "python" -and $_.CommandLine -like "*uvicorn*")} | ForEach-Object {
    Write-Host "Terminando processo: $($_.Id) - $($_.ProcessName)" -ForegroundColor Yellow
    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
}

Start-Sleep -Seconds 2

Write-Host "Avvio backend con nuove configurazioni..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot'; uv run uvicorn backend.main:app --reload --port 8001" -WindowStyle Normal

Write-Host "Backend riavviato! Attendi 5 secondi per l'avvio..." -ForegroundColor Green
Start-Sleep -Seconds 5

Write-Host "Verifica connessione..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8001/" -Method GET
    Write-Host "✓ Backend risponde correttamente!" -ForegroundColor Green
} catch {
    Write-Host "✗ Backend non risponde ancora. Controlla la finestra PowerShell." -ForegroundColor Red
}
