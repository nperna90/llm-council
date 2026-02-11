import sys
import io
from backend.market_data import get_llm_context_string

def test_integration():
    print("AVVIO TEST FASE 2: INTEGRAZIONE COMPLETA\n")
    
    tickers = ['NVDA', 'AMD', 'INTC'] # Settore semi, alta correlazione attesa
    print(f"Richiesta contesto per: {tickers}...")
    
    try:
        # Questa funzione ora orchestra tutto
        context = get_llm_context_string(tickers)
        
        print("\nOK - CONTESTO GENERATO CON SUCCESSO!")
        print("-" * 40)
        
        # Stampa il contesto gestendo l'encoding
        try:
            # Prova a stampare normalmente
            print(context)
        except UnicodeEncodeError:
            # Se fallisce, rimuovi caratteri problematici
            safe_context = context.encode('ascii', 'ignore').decode('ascii')
            print(safe_context)
        
        print("-" * 40)
        
        # Verifiche specifiche nel testo
        checks_passed = 0
        total_checks = 3
        
        if "ANALISI CORRELAZIONE" in context or "CORRELAZIONE" in context:
            print("OK - Correlazione presente")
            checks_passed += 1
        else:
            print("ERRORE - Correlazione MANCANTE")
            
        if "BACKTEST STORICO" in context or "BACKTEST" in context:
            print("OK - Backtest presente")
            checks_passed += 1
        else:
            print("ERRORE - Backtest MANCANTE")
            
        if "FUNDAMENTALS" in context:
            print("OK - Fondamentali presenti")
            checks_passed += 1
        else:
            print("ERRORE - Fondamentali MANCANTI")
        
        print(f"\nRISULTATO: {checks_passed}/{total_checks} verifiche superate")
        
        if checks_passed == total_checks:
            print("SUCCESSO - Tutte le componenti sono presenti!")
        else:
            print("ATTENZIONE - Alcune componenti mancano")
            
    except Exception as e:
        print(f"CRASH Integrazione: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_integration()
