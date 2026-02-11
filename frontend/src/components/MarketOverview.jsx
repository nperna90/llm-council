import { useState, useEffect } from 'react';
import { api } from '../api';
import StockChart from './StockChart';
import './MarketOverview.css';

export default function MarketOverview({ isOpen, onClose }) {
  const [watchlist, setWatchlist] = useState([]);
  const [selectedTicker, setSelectedTicker] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen) {
      loadWatchlist();
    }
  }, [isOpen]);

  const loadWatchlist = async () => {
    setLoading(true);
    try {
      const settings = await api.getSettings();
      const tickers = settings.watchlist || [];
      setWatchlist(tickers);
      // SELEZIONA AUTOMATICAMENTE IL PRIMO TICKER
      if (tickers.length > 0) {
        setSelectedTicker(tickers[0]);
      }
    } catch (error) {
      console.error('Failed to load watchlist:', error);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="market-overview-overlay" onClick={onClose}>
      <div className="market-overview-modal" onClick={(e) => e.stopPropagation()}>
        <div className="market-overview-header">
          <h2>Market Overview</h2>
          <button className="market-overview-close" onClick={onClose}>×</button>
        </div>
        
        <div className="market-overview-content">
          {loading ? (
            <div style={{ padding: '20px', textAlign: 'center', color: '#9ca3af' }}>
              Caricamento watchlist...
            </div>
          ) : (
            <>
              <div className="market-overview-tickers">
                <h3 style={{ marginBottom: '12px', color: '#111827', fontSize: '14px', fontWeight: '600' }}>
                  Seleziona Ticker:
                </h3>
                <div className="ticker-chips">
                  {watchlist.map((ticker) => (
                    <button
                      key={ticker}
                      className={`ticker-chip ${selectedTicker === ticker ? 'active' : ''}`}
                      onClick={() => setSelectedTicker(ticker)}
                    >
                      {ticker}
                    </button>
                  ))}
                </div>
              </div>

              {selectedTicker && (
                <div className="market-overview-chart">
                  <StockChart ticker={selectedTicker} />
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
