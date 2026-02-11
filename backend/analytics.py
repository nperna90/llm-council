import pandas as pd
import numpy as np

# Rimuoviamo yfinance e cache_manager da qui, non servono più
# La funzione ora è pura logica matematica (velocissima)

def get_performance_metrics(ticker: str, data: pd.DataFrame) -> dict:
    """
    Calcola metriche usando i dati GIA' SCARICATI.
    Zero chiamate API qui.
    """
    try:
        if ticker not in data.columns:
            return None
            
        # Estrai la serie storica del singolo ticker e pulisci i NaN (per IPO recenti)
        series = data[ticker].dropna()
        
        if series.empty:
            return None

        # --- 1. DATI BASE (Ultimo Anno) ---
        # Prendiamo gli ultimi 252 giorni di trading effettivi
        hist_1y = series.tail(252)
        
        if len(hist_1y) < 2: return None

        start_price = hist_1y.iloc[0]
        end_price = hist_1y.iloc[-1]
        total_return = ((end_price - start_price) / start_price) * 100
        
        # Max Drawdown 1Y
        rolling_max = hist_1y.cummax()
        drawdown = hist_1y / rolling_max - 1.0
        max_drawdown = drawdown.min() * 100
        
        # Volatilità
        daily_returns = hist_1y.pct_change().dropna()
        volatility = daily_returns.std() * np.sqrt(252) * 100
        
        # --- 2. MEDIE MOBILI (SMA) ---
        sma_50 = None
        sma_200 = None
        dist_sma_200 = None
        
        # Usiamo l'intera serie storica disponibile per le SMA
        if len(series) >= 50:
            sma_50 = round(series.rolling(window=50).mean().iloc[-1], 2)
            
        if len(series) >= 200:
            sma_200_val = series.rolling(window=200).mean().iloc[-1]
            sma_200 = round(sma_200_val, 2)
            dist_sma_200 = round(((end_price - sma_200_val) / sma_200_val) * 100, 2)
        
        return {
            "price": round(end_price, 2),
            "return_1y": round(total_return, 2),
            "max_drawdown": round(max_drawdown, 2),
            "volatility": round(volatility, 2),
            "sma_50": sma_50,
            "sma_200": sma_200,
            "dist_sma_200": dist_sma_200
        }

    except Exception as e:
        print(f"⚠️ Errore analytics {ticker}: {e}")
        return None


def check_leverage_decay(ticker: str, volatility: float) -> str:
    """
    Verifica se un asset a leva sta subendo un decadimento matematico critico.
    Regola empirica: Volatilità > 50% su asset a leva = Erosione capitale certa.
    """
    ticker = ticker.upper()
    # Lista parziale di ETF a leva noti o molto volatili
    leveraged_keywords = ["TQQQ", "SQQQ", "SOXL", "SOXS", "UPRO", "SPXU", "UDOW", "ARKK"] 
    
    # Se il ticker è nella lista O la volatilità è estrema (>60%)
    is_risky = any(k in ticker for k in leveraged_keywords) or volatility > 60
    
    if is_risky and volatility > 50:
        decay_msg = (
            f"⚠️ RISCHIO DECADIMENTO MATEMATICO (Volatility Drag):\n"
            f"      La volatilità annuale è {volatility:.2f}%.\n"
            f"      Con questi livelli, la composizione giornaliera dei rendimenti\n"
            f"      eroderà il capitale anche se il sottostante rimane laterale.\n"
            f"      Statisticamente inadatto al 'Buy & Hold'."
        )
        return decay_msg
    return ""
