import React from 'react';
import StockChart from './StockChart';
import './RightPanel.css';

const RightPanel = ({ selectedTicker, onTickerSelect, watchlist }) => {
  return (
    <div className="right-panel">
      
      {/* Header Pannello */}
      <div className="right-panel-header">
        <h2>Market Data Terminal</h2>
        <div className="ticker-display">
          {selectedTicker || "SELECT ASSET"}
        </div>
      </div>

      {/* Area Grafico */}
      <div className="right-panel-chart">
        {selectedTicker ? (
          <StockChart ticker={selectedTicker} />
        ) : (
          <div className="empty-chart-placeholder">
            Seleziona un titolo
          </div>
        )}
      </div>

      {/* Watchlist Rapida */}
      <div className="right-panel-watchlist">
        <h3>Watchlist</h3>
        <div className="watchlist-buttons">
          {watchlist.map((t) => (
            <button
              key={t}
              onClick={() => onTickerSelect(t)}
              className={`watchlist-button ${selectedTicker === t ? 'active' : ''}`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* Qui potremo aggiungere News e Fondamentali in futuro */}
      <div className="right-panel-footer">
        <div className="status">
          System Status: <span className="status-online">ONLINE</span>
        </div>
      </div>
      
    </div>
  );
};

export default RightPanel;
