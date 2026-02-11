import pandas as pd
import numpy as np

# Rimuoviamo yfinance e cache_manager
# La funzione riceve i dati pronti

def run_quick_backtest(tickers: list, data: pd.DataFrame, benchmark='SPY') -> str:
    """
    Esegue backtest usando i dati GIA' SCARICATI.
    """
    if not tickers or data.empty:
        return ""

    # Verifica quali ticker abbiamo davvero scaricato
    available_tickers = [t for t in tickers if t in data.columns]
    if not available_tickers:
        return "[WARNING] Dati insufficienti per il backtest."

    # Pesi (Equally Weighted)
    weights = [1.0 / len(available_tickers)] * len(available_tickers)
    
    try:
        # Prepara il subset di dati
        # Includi il benchmark se disponibile
        cols = available_tickers + [benchmark] if benchmark in data.columns else available_tickers
        subset = data[cols].dropna() # Taglia alla IPO più recente
        
        if subset.empty:
             return (
                f"\n   [WARNING] BACKTEST FALLITO: Dati storici insufficienti (IPO troppo recenti).\n"
                f"      ISTRUZIONE PER IL COUNCIL: NON usare backtest precedenti."
            )

        start_date = subset.index[0].strftime('%Y-%m-%d')
        end_date = subset.index[-1].strftime('%Y-%m-%d')
        
        # Calcoli (Vettoriali)
        daily_returns = subset.pct_change().dropna()
        
        # Portafoglio
        port_returns = (daily_returns[available_tickers] * weights).sum(axis=1)
        
        # Benchmark
        if benchmark in daily_returns:
            bench_returns = daily_returns[benchmark]
        else:
            bench_returns = pd.Series(0, index=daily_returns.index) # Fallback a 0 se manca SPY

        # Metriche
        cum_port = (1 + port_returns).prod() - 1
        cum_bench = (1 + bench_returns).prod() - 1
        
        vol_port = port_returns.std() * np.sqrt(252)
        vol_bench = bench_returns.std() * np.sqrt(252)
        
        cum_nav = (1 + port_returns).cumprod()
        max_dd = ((cum_nav - cum_nav.cummax()) / cum_nav.cummax()).min()
        
        rf = 0.04
        sharpe = ((port_returns.mean() - rf/252) * 252) / (port_returns.std() * np.sqrt(252))

        # Report
        win_icon = "[OK]" if cum_port > cum_bench else "[KO]"
        risk_icon = "[OK]" if vol_port < vol_bench else "[WARNING]"
        dd_icon = "[CRITICAL]" if max_dd < -0.30 else "[DOWN]"

        return (
            f"\n   [BACKTEST STORICO] (Reale: {start_date} -> {end_date}):\n"
            f"      • Totale vs SPY: {cum_port:.1%} vs {cum_bench:.1%} {win_icon}\n"
            f"      • Volatilità: {vol_port:.1%} (SPY: {vol_bench:.1%}) {risk_icon}\n"
            f"      • Max Drawdown: {max_dd:.1%} {dd_icon} (Il punto di massimo dolore)\n"
            f"      • Sharpe Ratio: {sharpe:.2f} (Efficienza Rischio/Rendimento)"
        )

    except Exception as e:
        return f"[ERROR] Errore calcolo Backtest: {e}"
