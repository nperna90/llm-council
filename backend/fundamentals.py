import yfinance as yf
from .cache_manager import cached_data

@cached_data(ttl_seconds=3600)
def get_fundamental_ratios(ticker: str) -> str:
    """
    Estrae dati fondamentali.
    Nota: Richiede una chiamata API per ticker. È il collo di bottiglia inevitabile.
    """
    try:
        stock = yf.Ticker(ticker)
        # fast_info è più veloce di info in alcune versioni, ma info è più completo.
        # Teniamo info per ora.
        info = stock.info
        
        if not info:
            return ""

        # --- 1. REDDITIVITÀ ---
        profit_margin = info.get('profitMargins', 0)
        if profit_margin is None: profit_margin = 0
        profit_margin *= 100
        
        roe = info.get('returnOnEquity', 0)
        if roe is None: roe = 0
        roe *= 100
        
        # --- 2. SALUTE FINANZIARIA ---
        debt_to_equity = info.get('debtToEquity', 0)
        if debt_to_equity is None: debt_to_equity = 0
        
        current_ratio = info.get('currentRatio', 0)
        
        # --- 3. VALUTAZIONE GROWTH ---
        peg_ratio = info.get('pegRatio')
        peg_str = "N/D (No Utili/Crescita)"
        peg_note = ""
        
        if peg_ratio is not None:
            peg_str = f"{peg_ratio:.2f}"
            if peg_ratio < 1.0: peg_note = "✅ SOTTOVALUTATO (Growth)"
            elif peg_ratio < 2.0: peg_note = "⚖️ FAIR VALUE"
            elif peg_ratio > 3.0: peg_note = "⚠️ SOPRAVVALUTATO"
        
        # --- 4. CASH FLOW ---
        free_cash_flow = info.get('freeCashflow', 0)
        fcf_str = "N/D"
        if free_cash_flow:
            if abs(free_cash_flow) > 1e9:
                fcf_str = f"${free_cash_flow/1e9:.2f}B"
            else:
                fcf_str = f"${free_cash_flow/1e6:.2f}M"

        health_note = "Solida" if debt_to_equity < 100 else "Indebitata"
        if debt_to_equity > 250: health_note = "🚨 RISCHIO DEBITO"

        return (
            f"\n   └─ 💎 FUNDAMENTALS (v2.0):\n"
            f"      • Growth Valuation: PEG {peg_str} {peg_note}\n"
            f"      • Redditività: Margine {profit_margin:.1f}% | ROE {roe:.1f}%\n"
            f"      • Salute: Debt/Equity {debt_to_equity:.1f}% [{health_note}] | Current Ratio {current_ratio:.2f}\n"
            f"      • Cash Flow: {fcf_str}"
        )

    except Exception as e:
        print(f"⚠️ Errore fundamentals {ticker}: {e}")
        return ""
