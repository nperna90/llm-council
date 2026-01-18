"""
Market Data Module for LLM Council

This module provides functions to fetch both price data and fundamental data
for stocks/ETFs using yfinance. Designed to support different agent personas:
- Boglehead: needs expense ratios, costs, simplicity metrics
- Quant: needs P/E, P/B, ratios, technical indicators
- Macro Strategist: needs sector data, market trends, economic indicators
"""

import yfinance as yf
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta


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
def get_llm_context_string(tickers: List[str]) -> str:
    """
    Funzione Helper che recupera tutto (Dati + News) e restituisce
    una SINGOLA STRINGA formattata pronta per il prompt dell'AI.
    """
    data_map = get_multiple_tickers(tickers)
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    report = f"--- REAL-TIME MARKET SNAPSHOT ({timestamp}) ---\n"
    report += "NOTA: Usa questi dati come unica fonte di verità. I prezzi sono aggiornati.\n\n"

    for ticker, data in data_map.items():
        if "error" in data:
            report += f"❌ {ticker}: Errore download ({data['error']})\n"
            continue

        info = data.get("info", {})
        fund = data.get("fundamentals", {})
        news = data.get("news", [])
        
        # Dati Essenziali
        price = data.get("current_price", "N/A")
        if isinstance(price, float): price = f"${price:.2f}"
        
        # Costruzione blocco dati
        report += f"📊 {ticker} ({info.get('shortName', ticker)})\n"
        report += f"   • Prezzo: {price} | P/E: {fund.get('pe_ratio', 'N/A')} | Beta: {fund.get('beta', 'N/A')}\n"
        
        # Aggiunta News (La parte nuova!)
        if news:
            report += "   • 📰 NEWS RECENTI:\n"
            # Prendiamo solo le prime 2 news per non intasare il prompt
            for n in news[:2]:
                title = n.get('title', 'Nessun titolo')
                publisher = n.get('publisher', 'Fonte sconosciuta')
                report += f"     - [{publisher}] {title}\n"
        else:
            report += "   • (Nessuna news recente rilevante)\n"
        
        report += "\n"

    report += "--- END OF SNAPSHOT ---"
    return report