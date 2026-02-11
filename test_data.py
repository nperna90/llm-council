# test_data.py
from backend.market_data import get_llm_context_string, extract_tickers
import sys

def test_market_feed():
    query = "Analizza $NVDA e $INTC"
    print(f"[QUERY] Query simulata: '{query}'")
    
    # 1. Estrazione Ticker
    tickers = extract_tickers(query)
    print(f"[TICKER] Ticker trovati: {tickers}")
    
    if not tickers:
        print("[ERR] Nessun ticker trovato. Controlla la funzione extract_tickers.")
        sys.exit(1)

    # 2. Scaricamento Dati
    print("[INFO] Scaricamento dati da Yahoo Finance...")
    try:
        context_string = get_llm_context_string(tickers)
        
        print("\n" + "="*50)
        print("[DATA] COSA VEDRA' L'AI (IL CONTESTO):")
        print("="*50)
        # Gestisce encoding per Windows
        try:
            preview = context_string[:1000].encode('utf-8', errors='replace').decode('utf-8', errors='replace')
            print(preview + "...\n[TRONCATO]")
        except:
            preview = context_string[:1000].encode('ascii', errors='replace').decode('ascii', errors='replace')
            print(preview + "...\n[TRONCATO]")
        print("="*50)
        print(f"[INFO] Lunghezza totale contesto: {len(context_string)} caratteri")
        
        # 3. Verifica Qualità Dati
        if "Error" in context_string or "Nessun dato" in context_string:
            print("[ERR] I dati sembrano vuoti o contengono errori.")
        else:
            print("[OK] I dati sembrano validi e formattati correttamente.")
            
    except Exception as e:
        print(f"[ERR] CRASH in market_data: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_market_feed()
