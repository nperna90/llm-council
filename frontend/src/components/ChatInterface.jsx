import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import Stage1 from './Stage1';
import Stage2 from './Stage2';
import Stage3 from './Stage3';
import StatusIndicator from './StatusIndicator';
import SettingsModal from './SettingsModal';
import MarketOverview from './MarketOverview';
import TutorToggle from './TutorToggle';
import EcoToggle from './EcoToggle';
import { api } from '../api';
import './ChatInterface.css';

export default function ChatInterface({
  conversation,
  onSendMessage,
  isLoading,
  onStopGeneration,
  onTickerClick,
  onNewMessage,
}) {
  const [input, setInput] = useState('');
  const [isDownloading, setIsDownloading] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isMarketOverviewOpen, setIsMarketOverviewOpen] = useState(false);
  const [isTutorMode, setIsTutorMode] = useState(false); // Default false (Pro Mode)
  const [ecoMode, setEcoMode] = useState(false); // Default false (Full Mode)
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [conversation]);

  // Monitora i messaggi dell'assistant per rilevare moonshot
  useEffect(() => {
    if (!conversation || !conversation.messages || !onNewMessage) return;
    
    // Trova l'ultimo messaggio dell'assistant con stage3 completo
    const lastAssistantMsg = conversation.messages
      .slice()
      .reverse()
      .find(msg => msg.role === 'assistant' && msg.stage3);
    
    if (lastAssistantMsg && lastAssistantMsg.stage3) {
      // Estrai il testo della risposta
      const responseText = lastAssistantMsg.stage3.response || '';
      
      // Cerca anche nei dati di stage1 e stage2 per il backtest
      let fullText = responseText;
      if (lastAssistantMsg.stage1) {
        fullText += ' ' + JSON.stringify(lastAssistantMsg.stage1);
      }
      if (lastAssistantMsg.stage2) {
        fullText += ' ' + JSON.stringify(lastAssistantMsg.stage2);
      }
      
      // Passa il testo alla funzione di controllo
      onNewMessage(fullText);
    }
  }, [conversation, onNewMessage]);

  const handleSubmit = (e) => {
    e.preventDefault();
    console.log('📝 handleSubmit chiamato:', { 
      input: input.trim(), 
      inputLength: input.trim().length,
      isLoading, 
      hasOnSendMessage: !!onSendMessage,
      tutorMode: isTutorMode,
      ecoMode: ecoMode
    });
    
    if (!input.trim()) {
      console.warn('⚠️ Input vuoto, messaggio non inviato');
      return;
    }
    
    if (isLoading) {
      console.warn('⚠️ Già in caricamento, messaggio non inviato');
      return;
    }
    
    if (!onSendMessage) {
      console.error('❌ onSendMessage non disponibile!');
      alert('Errore: funzione di invio non disponibile. Ricarica la pagina.');
      return;
    }
    
    console.log('✅ Invio messaggio...');
    try {
      onSendMessage(input.trim(), isTutorMode, ecoMode);
      setInput('');
      console.log('✅ Messaggio inviato, input pulito');
    } catch (error) {
      console.error('❌ Errore durante invio:', error);
      alert('Errore durante l\'invio: ' + error.message);
    }
  };

  const handleKeyDown = (e) => {
    // Submit on Enter (without Shift)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  // Funzione per gestire l'upload di file
  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    try {
      const data = await api.parseDocument(file);

      // Inseriamo il testo estratto nel box di input dell'utente
      const currentText = input;
      const newText = `Analizza questo documento allegato (${data.filename}):\n\n${data.text}\n\n${currentText}`;
      setInput(newText);

    } catch (error) {
      console.error("Errore upload:", error);
      alert("Impossibile leggere il file.");
    } finally {
      // Pulisci l'input file così puoi ricaricare lo stesso file se vuoi
      event.target.value = null;
    }
  };

  // Funzione per scaricare il report
  const handleExportPDF = async () => {
    if (!conversation || !conversation.id || conversation.messages.length === 0) {
      return;
    }

    setIsDownloading(true);
    try {
      // 1. Chiamata all'API
      const response = await api.downloadReport(conversation.id);

      if (!response.ok) {
        throw new Error('Errore durante la generazione del report');
      }

      // 2. Converti la risposta in un "Blob" (file binario)
      const blob = await response.blob();

      // 3. Crea un URL temporaneo per il file
      const url = window.URL.createObjectURL(blob);
      
      // 4. Crea un link invisibile nel DOM
      const link = document.createElement('a');
      link.href = url;
      // Nome del file che verrà scaricato
      link.setAttribute('download', `Investment_Memo_${conversation.id.slice(0, 8)}.pdf`);
      
      // 5. Simula il click e pulisci
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
      window.URL.revokeObjectURL(url); // Libera memoria

    } catch (error) {
      console.error("Download fallito:", error);
      console.error("Stack trace:", error.stack);
      const errorMessage = error.message || "Errore sconosciuto";
      alert(`Impossibile scaricare il report:\n\n${errorMessage}\n\nControlla la console del browser (F12) e la console del backend per maggiori dettagli.`);
    } finally {
      setIsDownloading(false);
    }
  };

  if (!conversation) {
    return (
      <div className="chat-interface">
        <div className="empty-state">
          <h2>Welcome to LLM Council</h2>
          <p>Inizia a scrivere un messaggio per creare automaticamente una nuova conversazione</p>
        </div>
        {/* Mostra il form di input anche senza conversazione */}
        <form className="input-form" onSubmit={handleSubmit}>
          <textarea
            className="message-input"
            placeholder="Scrivi qui il tuo messaggio per iniziare..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            rows={3}
            style={{ flex: 1 }}
          />
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <EcoToggle isEnabled={ecoMode} onToggle={setEcoMode} disabled={isLoading} />
            <TutorToggle isEnabled={isTutorMode} onToggle={setIsTutorMode} disabled={isLoading} />
          </div>
          {isLoading && onStopGeneration ? (
            <button
              type="button"
              className="stop-button"
              onClick={onStopGeneration}
              style={{
                padding: '10px 20px',
                background: '#dc3545',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                fontWeight: '500',
                fontSize: '14px',
                transition: 'background 0.2s',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = '#c82333';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = '#dc3545';
              }}
            >
              ⏹ Stop
            </button>
          ) : (
            <button
              type="submit"
              className="send-button"
              disabled={!input.trim() || isLoading}
            >
              Send
            </button>
          )}
        </form>
      </div>
    );
  }

  return (
    <div className="chat-interface">
      {conversation.messages.length > 0 && (
        <div className="chat-header">
          <h2 className="chat-title">{conversation.title || 'LLM Council Conversation'}</h2>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            {/* IL PANIC BUTTON */}
            <button
              onClick={() => onSendMessage("🚨 PANIC_MODE_TRIGGER 🚨", false)}
              className="panic-button"
              title="Clicca SOLO se sei nel panico per i mercati"
              style={{
                background: '#dc2626',
                color: 'white',
                fontWeight: 'bold',
                padding: '8px 16px',
                borderRadius: '9999px',
                border: '2px solid #ef4444',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '14px',
                transition: 'all 0.2s',
                boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
                animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = '#b91c1c';
                e.currentTarget.style.transform = 'scale(1.05)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = '#dc2626';
                e.currentTarget.style.transform = 'scale(1)';
              }}
            >
              <span style={{ fontSize: '18px' }}>😱</span>
              <span>Panic Button</span>
            </button>
            <button
              className="market-overview-button"
              onClick={() => setIsMarketOverviewOpen(true)}
              title="Market Overview - Visualizza Grafici"
              style={{
                padding: '8px 12px',
                background: '#f3f4f6',
                border: '1px solid #d1d5db',
                borderRadius: '6px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '14px',
                color: '#374151',
                transition: 'all 0.2s'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = '#e5e7eb';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = '#f3f4f6';
              }}
            >
              <svg 
                xmlns="http://www.w3.org/2000/svg" 
                width="18" 
                height="18" 
                viewBox="0 0 24 24" 
                fill="none" 
                stroke="currentColor" 
                strokeWidth="2" 
                strokeLinecap="round" 
                strokeLinejoin="round"
                style={{ display: 'inline-block' }}
              >
                <path d="M3 3v18h18"/>
                <path d="M7 12h10M7 8h10M7 16h10"/>
                <path d="M3 21l9-9 4 4 5-5"/>
              </svg>
              <span>Market</span>
            </button>
            <button
              className="settings-button"
              onClick={() => setIsSettingsOpen(true)}
              title="Configura Watchlist"
              style={{
                padding: '8px 12px',
                background: '#f3f4f6',
                border: '1px solid #d1d5db',
                borderRadius: '6px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '14px',
                color: '#374151',
                transition: 'all 0.2s'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = '#e5e7eb';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = '#f3f4f6';
              }}
            >
              <svg 
                xmlns="http://www.w3.org/2000/svg" 
                width="18" 
                height="18" 
                viewBox="0 0 24 24" 
                fill="none" 
                stroke="currentColor" 
                strokeWidth="2" 
                strokeLinecap="round" 
                strokeLinejoin="round"
                style={{ display: 'inline-block' }}
              >
                <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.1a2 2 0 0 1-1-1.74v-.47a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/>
                <circle cx="12" cy="12" r="3"/>
              </svg>
              <span>Settings</span>
            </button>
            <button
              className="export-pdf-button"
              onClick={handleExportPDF}
              disabled={isDownloading}
              title="Scarica Investment Memo in PDF"
            >
              {isDownloading ? (
                <>
                  <span className="spinner-small"></span>
                  <span>Generando...</span>
                </>
              ) : (
                <>
                  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ display: 'inline-block', marginRight: '8px' }}>
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                    <polyline points="7 10 12 15 17 10"></polyline>
                    <line x1="12" y1="15" x2="12" y2="3"></line>
                  </svg>
                  <span>Export PDF</span>
                </>
              )}
            </button>
          </div>
        </div>
      )}
      
      {/* Settings Modal */}
      <SettingsModal 
        isOpen={isSettingsOpen} 
        onClose={() => setIsSettingsOpen(false)} 
      />
      
      {/* Market Overview Modal */}
      <MarketOverview 
        isOpen={isMarketOverviewOpen} 
        onClose={() => setIsMarketOverviewOpen(false)} 
      />
      <div className="messages-container">
        {conversation.messages.length === 0 ? (
          <div className="empty-state">
            <h2>Start a conversation</h2>
            <p>Ask a question to consult the LLM Council</p>
          </div>
        ) : (
          conversation.messages.map((msg, index) => (
            <div key={index} className="message-group">
              {msg.role === 'user' ? (
                <div className="user-message">
                  <div className="message-label">You</div>
                  <div className="message-content">
                    <div className="markdown-content">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="assistant-message">
                  <div className="message-label">LLM Council</div>

                  {/* Stage 1 */}
                  {msg.loading?.stage1 && (
                    <div className="stage-loading">
                      <div className="spinner"></div>
                      <span>Running Stage 1: Collecting individual responses...</span>
                    </div>
                  )}
                  {msg.stage1 && <Stage1 responses={msg.stage1} />}

                  {/* Stage 2 */}
                  {msg.loading?.stage2 && (
                    <div className="stage-loading">
                      <div className="spinner"></div>
                      <span>Running Stage 2: Peer rankings...</span>
                    </div>
                  )}
                  {msg.stage2 && (
                    <Stage2
                      rankings={msg.stage2}
                      labelToModel={msg.metadata?.label_to_model}
                      aggregateRankings={msg.metadata?.aggregate_rankings}
                    />
                  )}

                  {/* Stage 3 */}
                  {msg.loading?.stage3 && (
                    <div className="stage-loading">
                      <div className="spinner"></div>
                      <span>Running Stage 3: Final synthesis...</span>
                    </div>
                  )}
                  {msg.stage3 && <Stage3 finalResponse={msg.stage3} />}
                </div>
              )}
            </div>
          ))
        )}

        {/* Status Indicator - mostra lo stato intelligente durante il caricamento */}
        {isLoading && (() => {
          // Trova l'ultimo messaggio dell'assistente per ottenere lo stato corrente
          const lastAssistantMsg = conversation.messages
            ? conversation.messages
                .slice()
                .reverse()
                .find(msg => msg.role === 'assistant')
            : null;
          
          const currentText = lastAssistantMsg?.stage3?.response || '';
          const loadingState = lastAssistantMsg?.loading || null;
          
          return (
            <div style={{ padding: '0 24px', marginBottom: '16px' }}>
              <StatusIndicator 
                currentStreamedText={currentText}
                loadingState={loadingState}
              />
            </div>
          );
        })()}

        <div ref={messagesEndRef} />
      </div>

      <form className="input-form" onSubmit={handleSubmit}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', width: '100%' }}>
          {/* Bottone Upload Nascosto + Icona Graffetta */}
          <label
            className="file-upload-label"
            style={{
              cursor: 'pointer',
              padding: '8px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: '8px',
              transition: 'background-color 0.2s',
              color: '#666',
            }}
            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#f0f0f0'}
            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
            title="Carica documento (PDF, CSV, TXT)"
          >
            <input
              type="file"
              style={{ display: 'none' }}
              accept=".pdf,.csv,.txt,.md,.xls,.xlsx"
              onChange={handleFileUpload}
            />
            {/* Icona Graffetta (Paperclip) */}
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
            </svg>
          </label>

          <textarea
            className="message-input"
            placeholder="Ask your question... (Shift+Enter for new line, Enter to send)"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            rows={3}
            style={{ flex: 1 }}
          />
          
          {/* TOGGLES */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <EcoToggle isEnabled={ecoMode} onToggle={setEcoMode} />
            <TutorToggle isEnabled={isTutorMode} onToggle={setIsTutorMode} />
          </div>
          
          {isLoading && onStopGeneration ? (
            <button
              type="button"
              className="stop-button"
              onClick={onStopGeneration}
              style={{
                padding: '10px 20px',
                background: '#dc3545',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                fontWeight: '500',
                fontSize: '14px',
                transition: 'background 0.2s',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = '#c82333';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = '#dc3545';
              }}
            >
              ⏹ Stop
            </button>
          ) : (
            <button
              type="submit"
              className="send-button"
              disabled={!input.trim() || isLoading}
            >
              Send
            </button>
          )}
        </div>
      </form>
    </div>
  );
}
