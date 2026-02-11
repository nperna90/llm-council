# Script per creare un backup completo del progetto LLM Council
# Esegui questo script per creare un punto di ripristino del sistema

$sourcePath = "c:\Users\npern\LLM COUNCIL 2\llm-council"
$backupBasePath = "c:\Users\npern\LLM COUNCIL 2"

# Verifica che la cartella sorgente esista
if (-not (Test-Path $sourcePath)) {
    Write-Host "ERRORE: Cartella sorgente non trovata: $sourcePath" -ForegroundColor Red
    exit 1
}

# Crea timestamp per il nome del backup
$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$backupPath = Join-Path $backupBasePath "llm-council_backup_$timestamp"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  CREAZIONE BACKUP LLM COUNCIL" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Sorgente: $sourcePath" -ForegroundColor Yellow
Write-Host "Destinazione: $backupPath" -ForegroundColor Yellow
Write-Host ""
Write-Host "Creazione backup in corso..." -ForegroundColor Yellow

# Crea il backup
try {
    Copy-Item -Path $sourcePath -Destination $backupPath -Recurse -Force
    
    # Calcola la dimensione
    $sizeMB = [math]::Round((Get-ChildItem $backupPath -Recurse -ErrorAction SilentlyContinue | 
        Measure-Object -Property Length -Sum).Sum / 1MB, 2)
    
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  BACKUP COMPLETATO CON SUCCESSO!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Percorso backup: $backupPath" -ForegroundColor Cyan
    Write-Host "Dimensione: $sizeMB MB" -ForegroundColor Cyan
    Write-Host "Data/ora: $timestamp" -ForegroundColor Cyan
    Write-Host ""
    
    # Mostra tutti i backup disponibili
    Write-Host "Backup disponibili:" -ForegroundColor Yellow
    Get-ChildItem $backupBasePath -Directory | Where-Object {$_.Name -like "*backup*"} | 
        Select-Object Name, LastWriteTime, @{Name="Size(MB)";Expression={
            [math]::Round((Get-ChildItem $_.FullName -Recurse -ErrorAction SilentlyContinue | 
                Measure-Object -Property Length -Sum).Sum / 1MB, 2)
        }} | Format-Table -AutoSize
    
} catch {
    Write-Host ""
    Write-Host "ERRORE durante la creazione del backup:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
