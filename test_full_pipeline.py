import asyncio
import sys
import os

# Aggiungiamo la directory corrente al path per importare i moduli
sys.path.append(os.getcwd())

from backend.market_data import get_llm_context_string
from backend.prompts import RISK_MANAGER_PROMPT, CHAIRMAN_SYSTEM_PROMPT

def test_data_pipeline():
    print("AVVIO TEST INTEGRAZIONE: DATA PIPELINE & PROMPTS\n")

    # 1. TEST IMPORT PROMPT
    print("1. Verifica caricamento Prompt...")
    if "RISCHIO ROVINA" in RISK_MANAGER_PROMPT or "LEVERAGE TRAP" in RISK_MANAGER_PROMPT:
        if "GERARCHIA DEI DATI" in CHAIRMAN_SYSTEM_PROMPT or "REGOLE DI SINTESI" in CHAIRMAN_SYSTEM_PROMPT:
            print("OK - Prompt caricati correttamente dal nuovo file prompts.py")
        else:
            print("ERRORE - CHAIRMAN_SYSTEM_PROMPT non sembra corretto.")
            return
    else:
        print("ERRORE - RISK_MANAGER_PROMPT non sembra corretto.")
        return

    # 2. TEST GENERAZIONE CONTESTO (Il cuore del sistema)
    tickers = ['NVDA', 'AMD', 'INTC'] # Settore semi, alta correlazione attesa
    print(f"\n2. Generazione Contesto Dati per: {tickers}...")
    print("   (Questo testera: Download Batch, Analytics, Fundamentals, Correlation, Backtest)")
    
    try:
        # Questa è la funzione che abbiamo riscritto in market_data.py
        context = get_llm_context_string(tickers)
        
        if not context:
            print("ERRORE - Il contesto generato e vuoto.")
            return

        print("\nOK - CONTESTO GENERATO! Analisi del contenuto:")
        print("-" * 40)
        
        # 3. VERIFICA DEI BLOCCHI
        checks = {
            "Prezzi & Volatilita": "Vol:",
            "SMA200": "SMA200:",
            "Fondamentali (PEG)": "PEG",
            "Correlazione": "CORRELAZIONE",
            "Backtest": "BACKTEST STORICO"
        }
        
        all_passed = True
        for name, keyword in checks.items():
            if keyword in context:
                print(f"   OK - {name}: Presente")
            else:
                print(f"   ERRORE - {name}: MANCANTE")
                all_passed = False
        
        if all_passed:
            print("-" * 40)
            print("RISULTATO: LA PIPELINE DATI E INTEGRA.")
            print("   Il sistema scarica, calcola e formatta tutto in una sola passata.")
            
            # Stampa un'anteprima per controllo visivo
            print("\n--- ANTEPRIMA DATI (Primi 500 caratteri) ---")
            try:
                print(context[:500] + "...\n")
            except UnicodeEncodeError:
                # Gestione encoding per Windows
                safe_context = context.encode('ascii', 'ignore').decode('ascii')
                print(safe_context[:500] + "...\n")
        else:
            print("\nATTENZIONE - Mancano dei pezzi nel report dati.")

    except Exception as e:
        print(f"\nCRASH CRITICO: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_data_pipeline()
