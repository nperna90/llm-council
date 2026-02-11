# backend/search_tool.py
from duckduckgo_search import DDGS
import logging

logger = logging.getLogger(__name__)

def get_latest_news(ticker: str, max_results: int = 5) -> str:
    """
    Cerca le ultime news finanziarie per un ticker usando DuckDuckGo.
    Restituisce una stringa formattata per l'LLM.
    """
    try:
        # Aggiungiamo "stock news" per filtrare risultati irrilevanti
        query = f"{ticker} stock news financial"
        
        results = DDGS().news(keywords=query, max_results=max_results)
        
        if not results:
            return "Nessuna news recente trovata."

        formatted_news = []
        for item in results:
            title = item.get('title', 'No Title')
            source = item.get('source', 'Unknown')
            date = item.get('date', '')
            # Puliamo il titolo da caratteri strani
            formatted_news.append(f"- [{date}] {source}: {title}")

        return "\n".join(formatted_news)

    except Exception as e:
        logger.error(f"News search failed for {ticker}: {e}")
        return "Errore nel recupero delle news (Servizio non disponibile)."
