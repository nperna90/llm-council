from backend.search_tool import get_latest_news

ticker = "TSLA"
print(f"Cercando news per {ticker}...")
news = get_latest_news(ticker)
print("-" * 50)
print(news)
print("-" * 50)
