import { useState, useEffect } from 'react';
import { api } from '../api';
import './SettingsModal.css';

export default function SettingsModal({ isOpen, onClose }) {
  const [watchlist, setWatchlist] = useState([]);
  const [newTicker, setNewTicker] = useState('');
  const [riskProfile, setRiskProfile] = useState('Balanced');
  const [councilMode, setCouncilMode] = useState('Standard');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (isOpen) {
      loadSettings();
    }
  }, [isOpen]);

  const loadSettings = async () => {
    setLoading(true);
    try {
      const settings = await api.getSettings();
      setWatchlist(settings.watchlist || []);
      setRiskProfile(settings.risk_profile || 'Balanced');
      setCouncilMode(settings.council_mode || 'Standard');
    } catch (error) {
      console.error('Failed to load settings:', error);
      alert('Impossibile caricare le impostazioni');
    } finally {
      setLoading(false);
    }
  };

  const handleAddTicker = (e) => {
    if (e) e.preventDefault();
    if (!newTicker.trim()) return;
    
    const ticker = newTicker.trim().toUpperCase();
    
    // Evita duplicati
    if (!watchlist.includes(ticker)) {
      setWatchlist([...watchlist, ticker]);
    }
    setNewTicker('');
  };

  const handleRemoveTicker = (ticker) => {
    setWatchlist(watchlist.filter(t => t !== ticker));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.saveSettings({
        watchlist,
        risk_profile: riskProfile,
        council_mode: councilMode
      });
      // Chiude la modale dopo il salvataggio
      onClose();
    } catch (error) {
      console.error('Failed to save settings:', error);
      alert('Errore durante il salvataggio');
    } finally {
      setSaving(false);
    }
  };


  if (!isOpen) return null;

  return (
    <div className="settings-modal-overlay" onClick={onClose}>
      <div className="settings-modal" onClick={(e) => e.stopPropagation()}>
        <div className="settings-modal-header">
          <h2>⚙️ Impostazioni Portafoglio</h2>
          <button className="settings-modal-close" onClick={onClose}>×</button>
        </div>

        <div className="settings-modal-content">
          {loading ? (
            <div className="settings-loading">Caricamento...</div>
          ) : (
            <>
              {/* Watchlist Section */}
              <div className="settings-section">
                <h3>Watchlist Ticker</h3>
                <p className="settings-description">
                  Aggiungi o rimuovi ticker dalla lista monitorata dal Council.
                </p>
                <p style={{ fontSize: '12px', color: '#6b7280', marginTop: '4px', marginBottom: '12px' }}>
                  Titoli monitorati ({watchlist.length})
                </p>
                
                <form onSubmit={handleAddTicker} className="ticker-input-group">
                  <input
                    type="text"
                    className="ticker-input"
                    placeholder="Es: TSLA, GOOGL, AMZN..."
                    value={newTicker}
                    onChange={(e) => setNewTicker(e.target.value.toUpperCase())}
                  />
                  <button 
                    type="submit"
                    className="ticker-add-button"
                    disabled={!newTicker.trim()}
                  >
                    Aggiungi
                  </button>
                </form>

                <div className="ticker-list">
                  {loading ? (
                    <div className="ticker-empty">Caricamento...</div>
                  ) : watchlist.length === 0 ? (
                    <div className="ticker-empty">Nessun titolo monitorato.</div>
                  ) : (
                    watchlist.map((ticker) => (
                      <div key={ticker} className="ticker-item">
                        <span className="ticker-symbol">{ticker}</span>
                        <button
                          className="ticker-remove-button"
                          onClick={() => handleRemoveTicker(ticker)}
                          title="Rimuovi ticker"
                        >
                          ×
                        </button>
                      </div>
                    ))
                  )}
                </div>
                <div style={{ fontSize: '12px', color: '#6b7280', marginTop: '8px' }}>
                  Nota: Il Council userà questi ticker per scaricare dati e news in tempo reale a ogni richiesta.
                </div>
              </div>

              {/* Risk Profile Section */}
              <div className="settings-section">
                <h3>Profilo di Rischio</h3>
                <p className="settings-description">
                  Imposta il livello di rischio per le raccomandazioni del Council.
                </p>
                <select
                  className="settings-select"
                  value={riskProfile}
                  onChange={(e) => setRiskProfile(e.target.value)}
                >
                  <option value="Conservative">Conservative - Bassa volatilità</option>
                  <option value="Balanced">Balanced - Bilanciato</option>
                  <option value="Aggressive">Aggressive - Alta crescita</option>
                </select>
              </div>

              {/* Council Mode Section */}
              <div className="settings-section">
                <h3>Modalità Council</h3>
                <p className="settings-description">
                  Scegli il contesto operativo del Council.
                </p>
                <select
                  className="settings-select"
                  value={councilMode}
                  onChange={(e) => setCouncilMode(e.target.value)}
                >
                  <option value="Standard">Standard - Analisi normale</option>
                  <option value="Crisis">Crisis - Gestione crisi</option>
                  <option value="FOMO">FOMO - Opportunità rapide</option>
                </select>
              </div>
            </>
          )}
        </div>

        <div className="settings-modal-footer">
          <button className="settings-cancel-button" onClick={onClose}>
            Annulla
          </button>
          <button
            className="settings-save-button"
            onClick={handleSave}
            disabled={saving || loading}
          >
            {saving ? 'Salvataggio...' : 'Salva Impostazioni'}
          </button>
        </div>
      </div>
    </div>
  );
}
