"""
Market Data Module for LLM Council

This module provides functions to fetch both price data and fundamental data
for stocks/ETFs using yfinance. Designed to support different agent personas:
- Boglehead: needs expense ratios, costs, simplicity metrics
- Quant: needs P/E, P/B, ratios, technical indicators
- Macro Strategist: needs sector data, market trends, economic indicators
"""

import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from .cache_manager import cached_data
from .search_tool import get_latest_news
from .analytics import get_performance_metrics, check_leverage_decay
from .fundamentals import get_fundamental_ratios
from .correlation import get_portfolio_correlation
from .backtester import run_quick_backtest


def get_market_data(ticker: str, period: str = "1y") -> Dict[str, Any]:
    """
    Fetch comprehensive market data for a ticker including:
    - Price history
    - Fundamental data (P/E, P/B, dividends, etc.)
    - Company info
    - News data (latest news articles)
    
    Args:
        ticker: Stock/ETF ticker symbol (e.g., "AAPL", "VOO")
        period: Time period for historical data ("1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max")
        
    Returns:
        Dictionary containing:
        - price_data: Historical price data (DataFrame)
        - fundamentals: Fundamental metrics (P/E, P/B, dividend yield, etc.)
        - info: Company/ETF information
        - current_price: Current/latest price
        - returns: Performance metrics
        - news: List of latest news articles
        - dividend_history: Historical dividend data
    """
    try:
        ticker_obj = yf.Ticker(ticker)
        
        # Get historical price data
        price_data = ticker_obj.history(period=period)
        
        # Get company/ETF info
        info = ticker_obj.info
        
        # Get news data
        try:
            news = ticker_obj.news
        except Exception:
            news = []
        
        # Extract fundamental data
        fundamentals = {
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "price_to_book": info.get("priceToBook"),
            "price_to_sales": info.get("priceToSalesTrailing12Months"),
            "dividend_yield": info.get("dividendYield"),
            "dividend_rate": info.get("dividendRate"),
            "payout_ratio": info.get("payoutRatio"),
            "earnings_growth": info.get("earningsQuarterlyGrowth"),
            "revenue_growth": info.get("revenueGrowth"),
            "profit_margin": info.get("profitMargins"),
            "operating_margin": info.get("operatingMargins"),
            "debt_to_equity": info.get("debtToEquity"),
            "current_ratio": info.get("currentRatio"),
            "roe": info.get("returnOnEquity"),
            "roa": info.get("returnOnAssets"),
            "beta": info.get("beta"),
            "market_cap": info.get("marketCap"),
            "enterprise_value": info.get("enterpriseValue"),
            "shares_outstanding": info.get("sharesOutstanding"),
            "float_shares": info.get("floatShares"),
        }
        
        # For ETFs, get expense ratio and other ETF-specific data
        if info.get("quoteType") == "ETF":
            # Try multiple fields for expense ratio (netExpenseRatio is most common)
            expense_ratio = (
                info.get("netExpenseRatio") or
                info.get("annualReportExpenseRatio") or 
                info.get("expenseRatio") or
                info.get("totalExpenseRatio")
            )
            # netExpenseRatio from yfinance is in "percentage base" format:
            # 0.03 means 0.03% (not 3%)
            # Store as-is for display (we'll format it correctly when printing)
            fundamentals["expense_ratio"] = expense_ratio
            fundamentals["total_assets"] = info.get("totalAssets")
            fundamentals["ytd_return"] = info.get("ytdReturn")
            fundamentals["beta_3y"] = info.get("beta3Year")
            fundamentals["holdings_turnover"] = info.get("holdingsTurnover")
        
        # Get current/latest price
        current_price = price_data["Close"].iloc[-1] if not price_data.empty else None
        
        # Calculate returns
        returns = {}
        if not price_data.empty:
            returns["current_price"] = float(current_price)
            returns["price_change_1d"] = float(price_data["Close"].iloc[-1] - price_data["Close"].iloc[-2]) if len(price_data) > 1 else None
            returns["price_change_pct_1d"] = float((price_data["Close"].iloc[-1] / price_data["Close"].iloc[-2] - 1) * 100) if len(price_data) > 1 else None
            returns["price_change_1mo"] = float(price_data["Close"].iloc[-1] - price_data["Close"].iloc[-20]) if len(price_data) > 20 else None
            returns["price_change_pct_1mo"] = float((price_data["Close"].iloc[-1] / price_data["Close"].iloc[-20] - 1) * 100) if len(price_data) > 20 else None
            returns["price_change_1y"] = float(price_data["Close"].iloc[-1] - price_data["Close"].iloc[0]) if len(price_data) > 0 else None
            returns["price_change_pct_1y"] = float((price_data["Close"].iloc[-1] / price_data["Close"].iloc[0] - 1) * 100) if len(price_data) > 0 else None
        
        # Get dividend history
        dividend_history = ticker_obj.dividends.tail(12)  # Last 12 months
        
        return {
            "ticker": ticker,
            "price_data": price_data,
            "fundamentals": fundamentals,
            "info": info,
            "current_price": current_price,
            "returns": returns,
            "dividend_history": dividend_history,
            "news": news,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "ticker": ticker,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


def get_multiple_tickers(tickers: List[str], period: str = "1y") -> Dict[str, Dict[str, Any]]:
    """
    Fetch market data for multiple tickers in parallel.
    
    Args:
        tickers: List of ticker symbols
        period: Time period for historical data
        
    Returns:
        Dictionary mapping ticker to its market data
    """
    results = {}
    for ticker in tickers:
        results[ticker] = get_market_data(ticker, period)
    return results


def get_portfolio_summary(tickers: List[str]) -> Dict[str, Any]:
    """
    Get a summary of portfolio data useful for different agent personas.
    
    Args:
        tickers: List of ticker symbols in portfolio
        
    Returns:
        Dictionary with:
        - boglehead_data: Expense ratios, costs, overlap analysis
        - quant_data: P/E ratios, valuations, technical metrics
        - macro_data: Sector exposure, market caps, beta
    """
    all_data = get_multiple_tickers(tickers)
    
    boglehead_data = {}
    quant_data = {}
    macro_data = {
        "sectors": {},
        "total_market_cap": 0,
        "avg_beta": 0,
        "etf_count": 0,
        "stock_count": 0
    }
    
    betas = []
    
    for ticker, data in all_data.items():
        if "error" in data:
            continue
            
        info = data.get("info", {})
        fundamentals = data.get("fundamentals", {})
        
        # Boglehead data (costs, simplicity)
        if info.get("quoteType") == "ETF":
            macro_data["etf_count"] += 1
            boglehead_data[ticker] = {
                "expense_ratio": fundamentals.get("expense_ratio"),
                "total_assets": fundamentals.get("total_assets"),
                "holdings_turnover": fundamentals.get("holdings_turnover"),
                "name": info.get("longName"),
            }
        else:
            macro_data["stock_count"] += 1
        
        # Quant data (ratios, valuations)
        quant_data[ticker] = {
            "pe_ratio": fundamentals.get("pe_ratio"),
            "forward_pe": fundamentals.get("forward_pe"),
            "price_to_book": fundamentals.get("price_to_book"),
            "dividend_yield": fundamentals.get("dividend_yield"),
            "roe": fundamentals.get("roe"),
            "profit_margin": fundamentals.get("profit_margin"),
            "beta": fundamentals.get("beta"),
            "current_price": data.get("current_price"),
            "returns_1y": data.get("returns", {}).get("price_change_pct_1y"),
        }
        
        # Macro data (sectors, market cap)
        sector = info.get("sector")
        if sector:
            if sector not in macro_data["sectors"]:
                macro_data["sectors"][sector] = {"tickers": [], "total_cap": 0}
            macro_data["sectors"][sector]["tickers"].append(ticker)
            market_cap = fundamentals.get("market_cap") or 0
            macro_data["sectors"][sector]["total_cap"] += market_cap
            macro_data["total_market_cap"] += market_cap
        
        if fundamentals.get("beta"):
            betas.append(fundamentals["beta"])
    
    macro_data["avg_beta"] = sum(betas) / len(betas) if betas else None
    
    return {
        "boglehead_data": boglehead_data,
        "quant_data": quant_data,
        "macro_data": macro_data,
        "timestamp": datetime.now().isoformat()
    }


if __name__ == "__main__":
    import json
    
    print("=" * 80)
    print("TESTING market_data.py - Portfolio Summary")
    print("=" * 80)
    
    # Test portfolio summary with specified tickers
    test_tickers = ['NVDA', 'VOO', 'MSFT']
    print(f"\nFetching data for tickers: {test_tickers}\n")
    
    portfolio = get_portfolio_summary(test_tickers)
    
    # Print Boglehead Data (ETF costs, expense ratios)
    print("\n" + "=" * 80)
    print("BOGLEHEAD DATA (Costs & Efficiency)")
    print("=" * 80)
    if portfolio['boglehead_data']:
        for ticker, data in portfolio['boglehead_data'].items():
            print(f"\n{ticker} ({data.get('name', 'N/A')}):")
            if data.get('expense_ratio') is not None:
                # Expense ratio from yfinance is in "percentage base" format:
                # 0.03 means 0.03% (already in the right format for display)
                print(f"  Expense Ratio: {data['expense_ratio']:.2f}%")
            if data.get('total_assets'):
                print(f"  Total Assets: ${data['total_assets']:,.0f}")
            if data.get('holdings_turnover') is not None:
                print(f"  Holdings Turnover: {data['holdings_turnover']:.2f}%")
    else:
        print("  (No ETF data found)")
    
    # Print Quant Data (Ratios, Valuations, Performance)
    print("\n" + "=" * 80)
    print("QUANT DATA (Ratios, Valuations, Performance)")
    print("=" * 80)
    for ticker, data in portfolio['quant_data'].items():
        print(f"\n{ticker}:")
        if data.get('current_price'):
            print(f"  Current Price: ${data['current_price']:.2f}")
        if data.get('pe_ratio'):
            print(f"  P/E Ratio: {data['pe_ratio']:.2f}")
        if data.get('forward_pe'):
            print(f"  Forward P/E: {data['forward_pe']:.2f}")
        if data.get('price_to_book'):
            print(f"  P/B Ratio: {data['price_to_book']:.2f}")
        if data.get('dividend_yield') is not None:
            # yfinance returns dividend yield as decimal (0.02 = 2%)
            # But sometimes it might be already as percentage, so check
            div_yield = data['dividend_yield']
            if div_yield > 1:
                # Already in percentage format, but check if reasonable (< 20%)
                if div_yield < 20:
                    print(f"  Dividend Yield: {div_yield:.2f}%")
                else:
                    # Likely data error, skip or show as N/A
                    print(f"  Dividend Yield: N/A (data error: {div_yield:.2f}%)")
            else:
                # In decimal format, convert to percentage
                # But check if reasonable (< 0.20 = 20%)
                if div_yield < 0.20:
                    print(f"  Dividend Yield: {div_yield*100:.2f}%")
                else:
                    # Likely data error (e.g., 0.79 = 79% is unrealistic)
                    print(f"  Dividend Yield: N/A (data error: {div_yield*100:.2f}%)")
        if data.get('roe'):
            print(f"  ROE: {data['roe']*100:.2f}%")
        if data.get('profit_margin'):
            print(f"  Profit Margin: {data['profit_margin']*100:.2f}%")
        if data.get('beta'):
            print(f"  Beta: {data['beta']:.2f}")
        if data.get('returns_1y') is not None:
            print(f"  1Y Return: {data['returns_1y']:.2f}%")
    
    # Print Macro Data (Sectors, Market Exposure)
    print("\n" + "=" * 80)
    print("MACRO DATA (Sectors, Market Exposure)")
    print("=" * 80)
    macro = portfolio['macro_data']
    print(f"\nPortfolio Composition:")
    print(f"  ETFs: {macro['etf_count']}")
    print(f"  Stocks: {macro['stock_count']}")
    if macro.get('avg_beta'):
        print(f"  Average Beta: {macro['avg_beta']:.2f}")
    if macro.get('total_market_cap'):
        print(f"  Total Market Cap: ${macro['total_market_cap']:,.0f}")
    
    if macro.get('sectors'):
        print(f"\nSector Exposure:")
        for sector, info in macro['sectors'].items():
            print(f"  {sector}:")
            print(f"    Tickers: {', '.join(info['tickers'])}")
            if info.get('total_cap'):
                print(f"    Total Cap: ${info['total_cap']:,.0f}")
    
    print("\n" + "=" * 80)
    print(f"Test completed at {portfolio['timestamp']}")
    print("=" * 80)
def calculate_rsi(prices: pd.Series, period: int = 14) -> Optional[float]:
    """
    Calcola l'RSI (Relative Strength Index) manualmente.
    
    Args:
        prices: Serie pandas con i prezzi di chiusura
        period: Periodo per il calcolo RSI (default 14)
        
    Returns:
        Valore RSI (0-100) o None se non calcolabile
    """
    if prices.empty or len(prices) < period + 1:
        return None
    
    try:
        # Calcola le variazioni di prezzo
        delta = prices.diff()
        
        # Separa guadagni e perdite
        gains = delta.where(delta > 0, 0)
        losses = -delta.where(delta < 0, 0)
        
        # Calcola la media mobile esponenziale (EMA) dei guadagni e perdite)
        avg_gain = gains.ewm(span=period, adjust=False).mean()
        avg_loss = losses.ewm(span=period, adjust=False).mean()
        
        # Calcola RS (Relative Strength)
        rs = avg_gain / avg_loss
        
        # Calcola RSI
        rsi = 100 - (100 / (1 + rs))
        
        # Restituisci l'ultimo valore
        return float(rsi.iloc[-1]) if not rsi.empty else None
    except Exception as e:
        print(f"Errore calcolo RSI: {e}")
        return None


@cached_data(ttl_seconds=300)
def get_llm_context_string(tickers: List[str]) -> str:
    """
    Funzione Helper che recupera tutto (Dati + News + Analisi Tecnica) e restituisce
    una SINGOLA STRINGA formattata pronta per il prompt dell'AI.
    Ora con CACHE: i dati durano 5 minuti.
    """
    if not tickers:
        return "Nessun ticker specificato."

    print(f"📥 Scarico dati per contesto: {tickers}")
    
    data_map = get_multiple_tickers(tickers)
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    report = f"--- REAL-TIME MARKET SNAPSHOT ({timestamp}) ---\n"
    report += "NOTA: Usa questi dati come unica fonte di verità. I prezzi sono aggiornati.\n\n"

    # Sezioni separate per organizzare meglio i dati
    section_quant = "--- DATI QUANTITATIVI, TECNICI E FONDAMENTALI (v2.0) ---\n"
    section_macro = "--- ULTIME NEWS DAL WEB (LIVE) ---\n"

    # --- 1. DATI PORTAFOGLIO (Correlazione + Backtest) ---
    print(f"⏳ Eseguo calcoli complessi per {tickers}...")
    
    correlation_report = get_portfolio_correlation(tickers)
    
    # NOVITÀ: Chiamata al Backtest
    # Passiamo 'SPY' come benchmark standard
    backtest_report = run_quick_backtest(tickers, benchmark='SPY', period='5y')
    
    # Costruiamo la sezione Quant
    if correlation_report or backtest_report:
        section_quant += f"{correlation_report}\n"
        section_quant += f"{backtest_report}\n\n"
        section_quant += "-"*40 + "\n"

    for ticker, data in data_map.items():
        if "error" in data:
            section_quant += f"❌ {ticker}: Errore download ({data['error']})\n"
            continue

        info = data.get("info", {})
        fund = data.get("fundamentals", {})
        news = data.get("news", [])
        price_data = data.get("price_data", pd.DataFrame())
        
        # Dati Essenziali
        price = data.get("current_price", "N/A")
        if isinstance(price, float): price = f"${price:.2f}"
        
        # ANALISI TECNICA: Calcolo RSI
        technical_msg = ""
        try:
            if not price_data.empty and 'Close' in price_data.columns:
                # Prendiamo almeno 6 mesi di storia per calcolare RSI
                hist = price_data.tail(180)  # ~6 mesi di dati giornalieri
                
                if len(hist) >= 15:  # Serve almeno 15 giorni per RSI(14)
                    rsi = calculate_rsi(hist['Close'], period=14)
                    
                    if rsi is not None:
                        rsi_status = "Neutrale"
                        if rsi > 70:
                            rsi_status = "IPERCOMPRATO (Rischio storno)"
                        elif rsi < 30:
                            rsi_status = "IPERVENDUTO (Possibile rimbalzo)"
                        
                        technical_msg = f" | RSI(14): {rsi:.1f} [{rsi_status}]"
        except Exception as e:
            print(f"Errore Tech Analysis su {ticker}: {e}")
            # Continua senza RSI se c'è un errore
        
        # --- ANALYTICS v2.0 ---
        perf = get_performance_metrics(ticker)
        perf_str = ""
        technical_levels = ""
        
        if perf:
            # Logica SMA per l'LLM
            sma_note = ""
            if perf['dist_sma_200'] is not None:
                trend = "Rialzista" if perf['dist_sma_200'] > 0 else "Ribassista"
                sma_note = f" | Trend 200gg: {trend} ({perf['dist_sma_200']}% vs SMA200)"
            else:
                sma_note = " | Dati storici insufficienti per trend lungo"

            risk_icon = "🟢"
            if perf['max_drawdown'] < -30: risk_icon = "🟠"
            if perf['max_drawdown'] < -50: risk_icon = "🔴"
            
            # Check Volatility Drag per asset a leva
            leverage_warning = check_leverage_decay(ticker, perf['volatility'])
            
            perf_str = (
                f"\n   └─ ⏳ HISTORY & TREND:\n"
                f"      • 1Y Perf: {perf['return_1y']}% | Drawdown: {perf['max_drawdown']}% {risk_icon}\n"
                f"      • Volatilità: {perf['volatility']}%\n"
                f"      • Livelli Chiave: SMA50 ${perf['sma_50']} | SMA200 ${perf['sma_200']}{sma_note}"
            )
            
            # Aggiungi warning Volatility Drag se presente
            if leverage_warning:
                perf_str += f"\n      {leverage_warning}"
        
        # --- NUOVO: WARREN BUFFETT MODE ---
        fundamentals_str = get_fundamental_ratios(ticker)
        
        # Costruzione blocco dati quantitativi
        section_quant += f"📊 {ticker} ({info.get('shortName', ticker)})\n"
        section_quant += f"   • Prezzo: {price} | P/E: {fund.get('pe_ratio', 'N/A')} | Beta: {fund.get('beta', 'N/A')}{technical_msg}{perf_str}{fundamentals_str}\n"
        
        # Aggiunta News da Yahoo Finance (esistenti)
        if news:
            section_quant += "   • 📰 NEWS RECENTI (Yahoo Finance):\n"
            # Prendiamo solo le prime 2 news per non intasare il prompt
            for n in news[:2]:
                title = n.get('title', 'Nessun titolo')
                publisher = n.get('publisher', 'Fonte sconosciuta')
                section_quant += f"     - [{publisher}] {title}\n"
        
        section_quant += "\n"
        
        # --- NUOVO: WEB SEARCH ---
        # Cerchiamo "Ticker Stock News" o "Ticker Financial News"
        try:
            news_text = get_latest_news(f"{ticker} stock news financial", max_results=2)
            section_macro += f"📰 NEWS SU {ticker}:\n{news_text}\n\n"
        except Exception as e:
            print(f"Errore ricerca web news per {ticker}: {e}")
            section_macro += f"📰 NEWS SU {ticker}: Errore nel recupero news web.\n\n"

    report += section_quant
    report += "\n"
    report += section_macro
    report += "\n--- END OF SNAPSHOT ---"
    return report