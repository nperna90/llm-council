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
    if (currentConversationId) {
      loadConversation(currentConversationId);
    }
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

  const handleSendMessage = async (content, tutorMode = false) => {
    if (!currentConversationId) return;

    setIsLoading(true);
    try {
      // Optimistically add user message to UI
      const userMessage = { role: 'user', content };
      setCurrentConversation((prev) => ({
        ...prev,
        messages: [...prev.messages, userMessage],
      }));

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
      setCurrentConversation((prev) => ({
        ...prev,
        messages: [...prev.messages, assistantMessage],
      }));

      // Send message with streaming
      await api.sendMessageStream(currentConversationId, content, (eventType, event) => {
        switch (eventType) {
          case 'stage1_start':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];
              lastMsg.loading.stage1 = true;
              return { ...prev, messages };
            });
            break;

          case 'stage1_complete':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];
              lastMsg.stage1 = event.data;
              lastMsg.loading.stage1 = false;
              return { ...prev, messages };
            });
            break;

          case 'stage2_start':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];
              lastMsg.loading.stage2 = true;
              return { ...prev, messages };
            });
            break;

          case 'stage2_complete':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];
              lastMsg.stage2 = event.data;
              lastMsg.metadata = event.metadata;
              lastMsg.loading.stage2 = false;
              return { ...prev, messages };
            });
            break;

          case 'stage3_start':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];
              lastMsg.loading.stage3 = true;
              return { ...prev, messages };
            });
            break;

          case 'stage3_complete':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];
              lastMsg.stage3 = event.data;
              lastMsg.loading.stage3 = false;
              return { ...prev, messages };
            });
            break;

          case 'title_complete':
            // Reload conversations to get updated title
            loadConversations();
            break;

          case 'complete':
            // Stream complete, reload conversations list
            loadConversations();
            setIsLoading(false);
            break;

          case 'error':
            console.error('Stream error:', event.message);
            setIsLoading(false);
            break;

          default:
            console.log('Unknown event type:', eventType);
        }
      }, tutorMode);
    } catch (error) {
      console.error('Failed to send message:', error);
      // Remove optimistic messages on error
      setCurrentConversation((prev) => ({
        ...prev,
        messages: prev.messages.slice(0, -2),
      }));
      setIsLoading(false);
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
      />
      <div className="app-main-content">
        
        {/* COLONNA SINISTRA: CHAT (Flessibile, prende lo spazio rimanente) */}
        <div className="app-chat-column">
          <ChatInterface
            conversation={currentConversation}
            onSendMessage={handleSendMessage}
            isLoading={isLoading}
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
