import pandas as pd
from backend.market_data import get_market_data
from backend.analytics import get_performance_metrics, check_leverage_decay
from backend.backtester import run_quick_backtest

def test_financial_engine():
    print("AVVIO TEST FASE 1: MOTORE FINANZIARIO\n")

    # 1. DEFINIZIONE PORTAFOGLIO TEST
    # Usiamo un mix di un titolo solido (NVDA) e uno a leva (TQQQ) per testare tutto
    tickers = ['NVDA', 'TQQQ']
    print(f"1. Richiesta dati per: {tickers}...")

    # 2. TEST DOWNLOAD CENTRALIZZATO
    try:
        df = get_market_data(tickers, period="5y")
        if df.empty:
            print("ERRORE: Il DataFrame scaricato e vuoto.")
            return
        print(f"OK - Dati scaricati con successo. Shape: {df.shape}")
        print(f"   Colonne disponibili: {list(df.columns)}")
    except Exception as e:
        print(f"CRASH durante il download: {e}")
        import traceback
        traceback.print_exc()
        return

    # 3. TEST ANALYTICS (Calcoli su dati già scaricati)
    print("\n2. Test Analytics (SMA, RSI, Volatilità)...")
    for t in tickers:
        try:
            metrics = get_performance_metrics(t, df)
            if metrics:
                print(f"   OK - {t}: Prezzo {metrics['price']} | Volatilità {metrics['volatility']}% | SMA200 {metrics['sma_200']}")
                
                # Test Volatility Drag
                warning = check_leverage_decay(t, metrics['volatility'])
                if warning:
                    print(f"      WARNING RILEVATO CORRETTAMENTE per {t}")
            else:
                print(f"   ERRORE - {t}: Nessuna metrica calcolata.")
        except Exception as e:
            print(f"   ERRORE su {t}: {e}")
            import traceback
            traceback.print_exc()

    # 4. TEST BACKTESTER
    print("\n3. Test Backtester (Simulazione Storica)...")
    try:
        report = run_quick_backtest(tickers, df)
        print(report)
        if "BACKTEST STORICO" in report:
            print("\nOK - Report generato correttamente.")
        else:
            print("\nERRORE - Il report non contiene i dati attesi.")
    except Exception as e:
        print(f"CRASH Backtester: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_financial_engine()
