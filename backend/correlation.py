import pandas as pd

# Rimuoviamo yfinance e cache_manager (i dati arrivano da fuori)

def get_portfolio_correlation(tickers: list, data: pd.DataFrame) -> str:
    """
    Calcola la matrice di correlazione usando i dati GIA' SCARICATI.
    """
    # Servono almeno 2 ticker presenti nei dati
    available_tickers = [t for t in tickers if t in data.columns]
    if len(available_tickers) < 2:
        return ""
        
    try:
        # Estrai solo i ticker richiesti
        subset = data[available_tickers].dropna()
        
        if subset.empty:
            return ""

        # 1. Calcolo Rendimenti Giornalieri
        returns = subset.pct_change().dropna()
        
        # 2. Matrice di Correlazione
        corr_matrix = returns.corr()
        
        # 3. Analisi
        report_lines = []
        high_corr_found = False
        
        cols = corr_matrix.columns
        for i in range(len(cols)):
            for j in range(i+1, len(cols)):
                ticker_a = cols[i]
                ticker_b = cols[j]
                corr_val = corr_matrix.iloc[i, j]
                
                if corr_val > 0.8:
                    report_lines.append(f"⚠️ {ticker_a} <-> {ticker_b}: {corr_val:.2f} (ESTREMA - È lo stesso trade!)")
                    high_corr_found = True
                elif corr_val > 0.6:
                    report_lines.append(f"🔸 {ticker_a} <-> {ticker_b}: {corr_val:.2f} (Alta - Diversificazione scarsa)")
                elif corr_val < -0.5:
                    report_lines.append(f"🛡️ {ticker_a} <-> {ticker_b}: {corr_val:.2f} (Inversa - Buon Hedge)")

        if not report_lines:
            return "\n   └─ 🔗 CORRELAZIONE: Nessuna anomalia rilevata (Portafoglio ben decorrelato)."
            
        header = "\n   └─ 🔗 ANALISI CORRELAZIONE (Rischio Sistemico):"
        if high_corr_found:
            header += " 🚨 CRITICO"
            
        return header + "\n      " + "\n      ".join(report_lines)

    except Exception as e:
        print(f"Errore calcolo correlazione: {e}")
        return ""
