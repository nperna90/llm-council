import { useState, useEffect } from 'react';
import Confetti from 'react-confetti';
import Sidebar from './components/Sidebar';
import ChatInterface from './components/ChatInterface';
import RightPanel from './components/RightPanel';
import { api } from './api';
import './App.css';

function App() {
  const [conversations, setConversations] = useState([]);
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const [currentConversation, setCurrentConversation] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [watchlist, setWatchlist] = useState([]);
  const [activeTicker, setActiveTicker] = useState(null); // Il ticker mostrato a destra
  const [isPartyTime, setIsPartyTime] = useState(false);
  const [windowSize, setWindowSize] = useState({ width: window.innerWidth, height: window.innerHeight });
  const [abortController, setAbortController] = useState(null);

  // Carica la watchlist all'avvio
  const loadWatchlist = async () => {
    try {
      const s = await api.getSettings();
      if (s.watchlist) {
        setWatchlist(s.watchlist);
        if (s.watchlist.length > 0) setActiveTicker(s.watchlist[0]); // Seleziona il primo
      }
    } catch (e) { 
      console.error('Failed to load watchlist:', e); 
    }
  };

  // Load conversations on mount and periodically refresh
  useEffect(() => {
    loadConversations();
    loadWatchlist();
    
    // Refresh conversations list every 5 seconds to catch new ones
    const interval = setInterval(() => {
      loadConversations();
    }, 5000);
    
    return () => clearInterval(interval);
  }, []);

  // Load conversation details when selected
  useEffect(() => {
    if (!currentConversationId) return;
    loadConversation(currentConversationId);
  }, [currentConversationId]);

  // Aggiorna dimensioni finestra per i coriandoli
  useEffect(() => {
    const handleResize = () => setWindowSize({ width: window.innerWidth, height: window.innerHeight });
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Funzione che controlla se c'è un "Moonshot"
  const checkForMoonshot = (data) => {
    if (!data) return;
    
    // Cerca nel testo del backtest o nella risposta dell'assistant
    const backtestText = typeof data === 'string' ? data : JSON.stringify(data);
    
    // Pattern 1: "Rendimento Totale: +XX%"
    if (backtestText.includes("Rendimento Totale: +") && !backtestText.includes("BACKTEST FALLITO")) {
      const match = backtestText.match(/Rendimento Totale: \+([0-9]+)/);
      if (match && parseInt(match[1]) > 50) {
        triggerParty();
        return;
      }
    }
    
    // Pattern 2: "Totale vs SPY: +XX%" (dal backtest)
    if (backtestText.includes("Totale vs SPY: +") && !backtestText.includes("BACKTEST FALLITO")) {
      const match = backtestText.match(/Totale vs SPY: \+([0-9]+)/);
      if (match && parseInt(match[1]) > 50) {
        triggerParty();
        return;
      }
    }
    
    // Pattern 3: "1Y Perf: +XX%" (dalle analytics)
    if (backtestText.includes("1Y Perf: +")) {
      const match = backtestText.match(/1Y Perf: \+([0-9]+)/);
      if (match && parseInt(match[1]) > 50) {
        triggerParty();
        return;
      }
    }
  };

  const triggerParty = () => {
    setIsPartyTime(true);
    // Ferma i coriandoli dopo 8 secondi
    setTimeout(() => setIsPartyTime(false), 8000);
  };

  const loadConversations = async () => {
    try {
      const convs = await api.listConversations();
      console.log(`Loaded ${convs.length} conversations from backend`);
      setConversations(convs);
    } catch (error) {
      console.error('Failed to load conversations:', error);
      // Set empty array on error to avoid showing stale data
      setConversations([]);
    }
  };

  const loadConversation = async (id) => {
    try {
      const conv = await api.getConversation(id);
      setCurrentConversation(conv);
    } catch (error) {
      console.error('Failed to load conversation:', error);
    }
  };

  const handleNewConversation = async () => {
    try {
      const newConv = await api.createConversation();
      setConversations([
        { id: newConv.id, created_at: newConv.created_at, message_count: 0 },
        ...conversations,
      ]);
      setCurrentConversationId(newConv.id);
    } catch (error) {
      console.error('Failed to create conversation:', error);
    }
  };

  const handleSelectConversation = (id) => {
    setCurrentConversationId(id);
  };

  const handleSendMessage = async (content, tutorMode = false, ecoMode = false) => {
    console.log('🔄 handleSendMessage chiamato con:', { content, tutorMode, ecoMode, currentConversationId });
    
    // Se non c'è una conversazione attiva, creane una nuova automaticamente
    let conversationId = currentConversationId;
    if (!conversationId) {
      try {
        console.log('📝 Nessuna conversazione attiva, creazione automatica...');
        const newConv = await api.createConversation();
        console.log('✅ Conversazione creata:', newConv);
        conversationId = newConv.id;
        setConversations([
          { id: newConv.id, created_at: newConv.created_at, message_count: 0 },
          ...conversations,
        ]);
        setCurrentConversationId(newConv.id);
        // Carica la conversazione appena creata
        await loadConversation(newConv.id);
        console.log('✅ Conversazione caricata');
      } catch (error) {
        console.error('❌ Errore creazione conversazione:', error);
        alert('Impossibile creare una nuova conversazione. Riprova. Errore: ' + error.message);
        return;
      }
    }
    
    console.log('📤 Invio messaggio alla conversazione:', conversationId);

    setIsLoading(true);
    
    // Create AbortController for this request
    const controller = new AbortController();
    setAbortController(controller);
    
    try {
      // Assicurati che la conversazione sia caricata
      if (!currentConversation || currentConversation.id !== conversationId) {
        await loadConversation(conversationId);
      }
      
      // Optimistically add user message to UI
      const userMessage = { role: 'user', content };
      setCurrentConversation((prev) => {
        if (!prev || prev.id !== conversationId) {
          return {
            id: conversationId,
            title: 'New Conversation',
            messages: [userMessage],
            created_at: new Date().toISOString()
          };
        }
        return {
          ...prev,
          messages: [...(prev.messages || []), userMessage],
        };
      });

      // Create a partial assistant message that will be updated progressively
      const assistantMessage = {
        role: 'assistant',
        stage1: null,
        stage2: null,
        stage3: null,
        metadata: null,
        loading: {
          stage1: false,
          stage2: false,
          stage3: false,
        },
      };

      // Add the partial assistant message
      setCurrentConversation((prev) => {
        if (!prev || prev.id !== conversationId) {
          return {
            id: conversationId,
            title: 'New Conversation',
            messages: [{ role: 'user', content }, assistantMessage],
            created_at: new Date().toISOString()
          };
        }
        return {
          ...prev,
          messages: [...(prev.messages || []), assistantMessage],
        };
      });

      // Send message with streaming
      console.log('🚀 Invio stream alla conversazione:', conversationId);
      await api.sendMessageStream(conversationId, content, (event) => {
        console.log('📨 Evento ricevuto:', event);
        
        // Gestisce i nuovi eventi dal backend streaming
        if (event.type === 'status') {
          // Aggiornamenti di stato (market_data, stage1, stage2, stage3)
          const stage = event.stage;
          if (stage === 'stage1') {
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];
              if (lastMsg) lastMsg.loading.stage1 = true;
              return { ...prev, messages };
            });
          } else if (stage === 'stage2') {
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];
              if (lastMsg) {
                lastMsg.loading.stage1 = false;
                lastMsg.loading.stage2 = true;
              }
              return { ...prev, messages };
            });
          } else if (stage === 'stage3') {
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];
              if (lastMsg) {
                lastMsg.loading.stage2 = false;
                lastMsg.loading.stage3 = true;
              }
              return { ...prev, messages };
            });
          }
        } else if (event.type === 'data') {
          // 🟢 FIX: Salva i dati strutturati nel messaggio
          if (event.stage === 'stage1') {
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];
              if (lastMsg) {
                lastMsg.stage1 = event.content; // Salva le opinioni
                lastMsg.loading.stage1 = false;
              }
              return { ...prev, messages };
            });
          } else if (event.stage === 'stage2') {
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];
              if (lastMsg) {
                lastMsg.stage2 = event.content; // Salva i voti
                lastMsg.loading.stage2 = false;
              }
              return { ...prev, messages };
            });
          }
        } else if (event.type === 'result') {
          // Risultato finale (stage3)
          setCurrentConversation((prev) => {
            const messages = [...prev.messages];
            const lastMsg = messages[messages.length - 1];
            if (lastMsg) {
              lastMsg.stage3 = {
                model: 'Chairman',
                response: event.content
              };
              lastMsg.loading.stage3 = false;
            }
            return { ...prev, messages };
          });
          
          // Stream completo, reload conversations
          loadConversations();
          setIsLoading(false);
          setAbortController(null);
        } else if (event.type === 'cancelled') {
          console.log('🛑 Stream cancellato');
          setIsLoading(false);
          setAbortController(null);
          // Rimuovi il messaggio assistant parziale se presente
          setCurrentConversation((prev) => {
            if (!prev) return prev;
            const messages = [...prev.messages];
            const lastMsg = messages[messages.length - 1];
            if (lastMsg && lastMsg.role === 'assistant' && 
                (!lastMsg.stage1 || !lastMsg.stage2 || !lastMsg.stage3)) {
              return {
                ...prev,
                messages: messages.slice(0, -1),
              };
            }
            return prev;
          });
        } else if (event.type === 'error') {
          console.error('❌ Stream error:', event.message);
          alert('Errore durante lo streaming: ' + (event.message || 'Errore sconosciuto'));
          setIsLoading(false);
          setAbortController(null);
        }
      }, tutorMode, ecoMode, controller.signal);
    } catch (error) {
      if (error.name === 'AbortError') {
        console.log('🛑 Richiesta interrotta dall\'utente');
        // Non mostrare alert per interruzioni volontarie
      } else {
        console.error('❌ Errore invio messaggio:', error);
        alert('Errore durante l\'invio del messaggio: ' + error.message);
        // Remove optimistic messages on error
        setCurrentConversation((prev) => {
          if (!prev) return prev;
          return {
            ...prev,
            messages: prev.messages.slice(0, -2),
          };
        });
      }
      setIsLoading(false);
      setAbortController(null);
    }
  };

  const handleStopGeneration = () => {
    if (abortController) {
      abortController.abort();
      console.log('🛑 Interruzione richiesta dall\'utente');
    }
  };



  return (
    <div className="app">
      {/* EASTER EGG: I CORIANDOLI */}
      {isPartyTime && (
        <div style={{ position: 'fixed', top: 0, left: 0, zIndex: 9999, pointerEvents: 'none', width: '100%', height: '100%' }}>
          <Confetti 
            width={windowSize.width} 
            height={windowSize.height} 
            numberOfPieces={200} 
            gravity={0.3}
            recycle={false}
          />
          <div style={{
            position: 'absolute',
            top: '10%',
            left: '50%',
            transform: 'translateX(-50%)',
            background: '#fbbf24',
            color: '#000000',
            fontWeight: 'bold',
            padding: '16px 32px',
            borderRadius: '9999px',
            boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
            fontSize: '24px',
            border: '4px solid #000000',
            animation: 'bounce 1s infinite'
          }}>
            🚀 TO THE MOON! 🚀
          </div>
        </div>
      )}
      
      <Sidebar
        conversations={conversations}
        currentConversationId={currentConversationId}
        onSelectConversation={handleSelectConversation}
        onNewConversation={handleNewConversation}
        onConversationDeleted={loadConversations}
      />
      <div className="app-main-content">
        
        {/* COLONNA SINISTRA: CHAT (Flessibile, prende lo spazio rimanente) */}
        <div className="app-chat-column">
          <ChatInterface
            conversation={currentConversation}
            onSendMessage={handleSendMessage}
            isLoading={isLoading}
            onStopGeneration={handleStopGeneration}
            // Passiamo una funzione alla chat per cambiare il grafico
            onTickerClick={(ticker) => setActiveTicker(ticker)}
            // Passiamo la funzione per controllare i moonshot
            onNewMessage={checkForMoonshot}
          />
        </div>

        {/* COLONNA DESTRA: DATI (Fissa a 400px o 30% su schermi grandi) */}
        <div className="app-right-panel">
          <RightPanel 
            selectedTicker={activeTicker}
            watchlist={watchlist}
            onTickerSelect={setActiveTicker}
          />
        </div>

      </div>
    </div>
  );
}

export default App;
