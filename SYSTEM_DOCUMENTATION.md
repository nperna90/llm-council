# Documentazione Completa del Sistema LLM Council

## 📋 Indice
1. [Backend - File Python](#backend---file-python)
2. [Frontend - File React/JavaScript](#frontend---file-reactjavascript)
3. [Script di Utilità](#script-di-utilità)
4. [File di Configurazione](#file-di-configurazione)

---

## 🔧 BACKEND - File Python

### **backend/main.py**
**Funzione principale:** FastAPI application server - Entry point del backend

**Funzioni principali:**
- `http_exception_handler()` - Gestisce errori HTTP con header CORS
- `general_exception_handler()` - Gestisce errori generici
- `extract_tickers(text)` - Estrae ticker con prefisso $ dal testo
- `root()` - Health check endpoint
- `parse_document_endpoint()` - Endpoint per parsing documenti (PDF, CSV, TXT)
- `get_market_history(ticker)` - Restituisce storico prezzi per grafici
- `get_settings()` - Restituisce impostazioni utente
- `update_settings()` - Aggiorna impostazioni (watchlist, risk profile, council mode)
- `refresh_market_data()` - Forza pulizia cache dati di mercato
- `list_conversations()` - Lista tutte le conversazioni (metadata)
- `create_conversation()` - Crea una nuova conversazione
- `get_conversation(conversation_id)` - Recupera conversazione completa
- `send_message()` - Invia messaggio e riceve risposta completa (non streaming)
- `send_message_stream()` - Invia messaggio con streaming Server-Sent Events
- `delete_conversation(conversation_id)` - Elimina una singola conversazione
- `delete_conversations()` - Elimina multiple conversazioni
- `download_report(conversation_id)` - Genera e scarica PDF della conversazione

**Modelli Pydantic:**
- `CreateConversationRequest` - Request per creare conversazione
- `SendMessageRequest` - Request per inviare messaggio (content, tutor_mode, eco_mode)
- `ConversationMetadata` - Metadata conversazione (id, title, created_at, message_count)
- `Conversation` - Conversazione completa con messaggi
- `SettingsUpdate` - Update impostazioni
- `DeleteConversationsRequest` - Request per eliminare multiple conversazioni

---

### **backend/council.py**
**Funzione principale:** Orchestrazione del processo a 3 stadi del Council

**Funzioni principali:**
- `format_conversation_history(messages)` - Formatta cronologia per chiamate LLM
- `stage1_collect_responses(user_query, conversation_history, eco_mode)` - **Stage 1:** Raccoglie opinioni da tutti i modelli (Raw Council + Specialisti)
  - Chiama Raw Models con prompt di identità anti-mimesi
  - Chiama Specialisti (Quant, Risk Manager, Macro Strategist)
  - Esegue chiamate in parallelo con asyncio.gather
- `stage2_collect_rankings(user_query, stage1_results)` - **Stage 2:** Ogni modello valuta e classifica le risposte anonime degli altri
  - Anonimizza risposte come "Response A, B, C..."
  - Crea mapping label_to_model per de-anonimizzazione
  - Restituisce classifiche e metadata
- `stage3_synthesize_final(user_query, stage1_results, stage2_results, conversation_history, tutor_mode)` - **Stage 3:** Chairman sintetizza risposta finale
  - Combina tutte le opinioni e classifiche
  - Genera sintesi esecutiva con verdetto (BUY/HOLD/SELL/PANIC)
  - Supporta Tutor Mode per spiegazioni semplificate
- `parse_ranking_from_text(ranking_text)` - Estrae classifiche dal testo delle risposte
- `calculate_aggregate_rankings(stage2_results, label_to_model)` - Calcola ranking aggregato
- `generate_conversation_title(user_query)` - Genera titolo automatico per conversazione
- `run_full_council(user_query, conversation_history, tutor_mode, eco_mode)` - Esegue il processo completo a 3 stadi

---

### **backend/prompts.py**
**Funzione principale:** Repository centralizzato di tutti i system prompts

**Prompt definiti:**
- `QUANT_PROMPT` - Prompt per Quantitative Analyst (analisi valutazioni, qualità, tecnica)
- `RISK_MANAGER_PROMPT` - Prompt per Chief Risk Officer (correlazioni, volatility drag, bolla detector)
- `MACRO_PROMPT` - Prompt per Macro Strategist (sentiment news, contesto settoriale, geopolitica)
- `RAW_MODEL_PROMPT_TEMPLATE` - Template per identità Raw Models (anti-mimesi)
- `CHAIRMAN_SYSTEM_PROMPT` - Prompt per Chairman (sintesi finale, gerarchia dati, gestione memoria)
- `THERAPIST_PROMPT` - Prompt per Dr. Market (modalità panico)
- `TUTOR_INSTRUCTIONS` - Istruzioni aggiuntive per Tutor Mode

**Caratteristiche:**
- Vincoli negativi espliciti per isolamento ruoli
- Regole anti-mimesi per Raw Models
- Gestione memoria storica

---

### **backend/openrouter.py**
**Funzione principale:** Client API per OpenRouter

**Funzioni principali:**
- `query_model(model, messages, timeout)` - Chiama un singolo modello via OpenRouter
  - Gestisce timeout, errori HTTP, risposte vuote
  - Logging dettagliato per debug
- `query_models_parallel(models, messages)` - Chiama multiple modelli in parallelo
  - Restituisce dict {model: response}

---

### **backend/config.py**
**Funzione principale:** Configurazione modelli e impostazioni

**Variabili principali:**
- `OPENROUTER_API_KEY` - API key da .env
- `OPENROUTER_API_URL` - Endpoint OpenRouter
- `MODEL_GPT`, `MODEL_CLAUDE`, `MODEL_GEMINI`, `MODEL_GROK` - Identificatori modelli
- `QUANT_MODEL` - Modello per Quantitative Analyst (Claude 4.5)
- `RISK_MODEL` - Modello per Risk Manager (GPT-5.2)
- `MACRO_MODEL` - Modello per Macro Strategist (Gemini 3)
- `CHAIRMAN_MODEL` - Modello per Chairman (Claude 4.5)
- `RAW_COUNCIL_MODELS` - Lista modelli per opinione pura (senza ruolo)
- `COUNCIL_MODELS` - Alias per RAW_COUNCIL_MODELS (retrocompatibilità)

---

### **backend/storage.py**
**Funzione principale:** Gestione persistenza conversazioni (SQLite)

**Funzioni principali:**
- `create_conversation(conversation_id)` - Crea nuova conversazione nel database
- `get_conversation(conversation_id)` - Recupera conversazione completa
- `save_conversation(conversation)` - Salva/aggiorna conversazione
- `list_conversations()` - Lista tutte le conversazioni (metadata)
- `add_user_message(conversation_id, content)` - Aggiunge messaggio utente
- `add_assistant_message(conversation_id, stage1, stage2, stage3)` - Aggiunge risposta assistant
- `update_conversation_title(conversation_id, title)` - Aggiorna titolo conversazione
- `delete_conversation(conversation_id)` - Elimina singola conversazione
- `delete_conversations(conversation_ids)` - Elimina multiple conversazioni

---

### **backend/database.py**
**Funzione principale:** Modelli SQLAlchemy e inizializzazione database

**Classi:**
- `ConversationDB` - Tabella conversations (id, title, created_at, messages JSON)
- `MemoryDB` - Tabella memories (id, date, title, summary, tags)
- `SettingsDB` - Tabella settings (key, value JSON)
- `UserDB` - Tabella users (username, hashed_password, recovery_token)

**Funzioni:**
- `init_db()` - Crea tutte le tabelle
- `get_db()` - Generator per sessioni database

---

### **backend/market_data.py**
**Funzione principale:** Download e analisi dati di mercato (Yahoo Finance)

**Funzioni principali:**
- `get_market_data(tickers, period)` - Scarica dati storici per multiple ticker
- `get_market_data_single(ticker, period)` - Scarica dati per singolo ticker
- `get_multiple_tickers(tickers, period)` - Scarica dati multipli con cache
- `get_portfolio_summary(tickers)` - Genera summary portafoglio
- `calculate_rsi(prices, period)` - Calcola RSI (Relative Strength Index)
- `get_llm_context_string(tickers)` - Genera stringa contesto per LLM con dati real-time

**Metriche calcolate:**
- Prezzo, Volume, P/E, PEG, Profit Margin, Debt/Equity, Free Cash Flow
- RSI, SMA200, Volatilità, Sharpe Ratio

---

### **backend/memory.py**
**Funzione principale:** Sistema di memoria a lungo termine per continuità conversazioni

**Funzioni principali:**
- `add_memory(title, summary, tags)` - Salva memoria nel database
- `get_relevant_context(limit)` - Recupera memorie rilevanti per contesto attuale

**Uso:** Le sintesi finali vengono salvate come memorie per riferimento futuro

---

### **backend/analytics.py**
**Funzione principale:** Analisi performance e metriche avanzate

**Funzioni principali:**
- `get_performance_metrics(ticker, data)` - Calcola metriche performance
- `check_leverage_decay(ticker, volatility)` - Verifica decay su ETF a leva

---

### **backend/backtester.py**
**Funzione principale:** Backtesting strategie di investimento

**Funzioni principali:**
- `run_quick_backtest(tickers, data, benchmark)` - Esegue backtest rapido vs benchmark (SPY)

---

### **backend/correlation.py**
**Funzione principale:** Analisi correlazioni portafoglio

**Funzioni principali:**
- `get_portfolio_correlation(tickers, data)` - Calcola matrice correlazione

---

### **backend/fundamentals.py**
**Funzione principale:** Analisi fondamentali aziendali

**Funzioni principali:**
- `get_fundamental_ratios(ticker)` - Recupera ratio fondamentali

---

### **backend/cache_manager.py**
**Funzione principale:** Gestione cache dati di mercato

**Funzioni principali:**
- `cached_data(ttl_seconds)` - Decorator per cache con TTL
- `clear_cache()` - Pulisce tutta la cache

---

### **backend/settings.py**
**Funzione principale:** Gestione impostazioni utente (watchlist, risk profile, council mode)

**Funzioni principali:**
- `get_watchlist()` - Recupera watchlist da database
- `get_setting(key, default_value)` - Recupera singola impostazione
- `save_settings(new_settings)` - Salva impostazioni
- `load_settings()` - Carica tutte le impostazioni

---

### **backend/file_parser.py**
**Funzione principale:** Parsing documenti (PDF, CSV, Excel, TXT)

**Funzioni principali:**
- `parse_document(file_content, filename)` - Router principale per parsing
- `_parse_pdf(content)` - Parsing PDF
- `_parse_spreadsheet(content, filename)` - Parsing CSV/Excel

---

### **backend/create_report.py**
**Funzione principale:** Generazione PDF report (versione FPDF)

**Funzioni principali:**
- `InvestmentMemoPDF` - Classe FPDF customizzata
- `clean_text_for_pdf(text)` - Pulisce testo per PDF
- `generate_pdf(conversation_id, title, content)` - Genera PDF completo

---

### **backend/create_report_html.py**
**Funzione principale:** Generazione PDF report (versione HTML-to-PDF)

**Funzioni principali:**
- `clean_text_for_pdf(text)` - Pulisce testo
- `identify_agent_type(text)` - Identifica tipo agente dal testo
- `generate_html_content(conversation_id, title, content)` - Genera HTML
- `generate_pdf(conversation_id, title, content)` - Genera PDF da HTML

---

### **backend/auth.py**
**Funzione principale:** Autenticazione utenti (JWT, password hashing)

**Funzioni principali:**
- `verify_password(plain_password, hashed_password)` - Verifica password
- `get_password_hash(password)` - Hash password
- `create_access_token(data, expires_delta)` - Crea JWT token
- `get_current_user(token, db)` - Verifica e recupera utente corrente

---

### **backend/search_tool.py**
**Funzione principale:** Ricerca news e informazioni

**Funzioni principali:**
- `get_latest_news(query, max_results)` - Recupera ultime news

---

### **backend/convert_history.py**
**Funzione principale:** Conversione conversazioni in formato leggibile (HTML/Markdown)

**Funzioni principali:**
- `create_html_header()` - Crea header HTML
- `extract_all_text(data)` - Estrae tutto il testo da conversazione
- `convert_file(filename)` - Converte file conversazione
- `main()` - Entry point script

---

## 🎨 FRONTEND - File React/JavaScript

### **frontend/src/App.jsx**
**Funzione principale:** Componente root dell'applicazione React

**Funzioni principali:**
- `App()` - Componente principale
  - Gestisce stato globale (conversazioni, conversazione corrente, loading)
  - Carica watchlist e conversazioni all'avvio
  - Gestisce invio messaggi con streaming
  - Gestisce eliminazione conversazioni
  - Gestisce interruzione generazione (Stop button)
  - Easter egg: confetti per "moonshot" (>50% rendimento)

**State:**
- `conversations` - Lista conversazioni
- `currentConversationId` - ID conversazione attiva
- `currentConversation` - Dati conversazione attiva
- `isLoading` - Stato caricamento
- `watchlist` - Lista ticker da monitorare
- `activeTicker` - Ticker selezionato per grafico
- `abortController` - Controller per interrompere richieste

---

### **frontend/src/api.js**
**Funzione principale:** Client API per comunicazione con backend

**Funzioni principali:**
- `listConversations()` - GET /api/conversations
- `createConversation()` - POST /api/conversations
- `getConversation(conversationId)` - GET /api/conversations/{id}
- `sendMessage(conversationId, content, tutorMode, ecoMode)` - POST /api/conversations/{id}/message
- `sendMessageStream(conversationId, content, onEvent, tutorMode, ecoMode, abortSignal)` - POST /api/conversations/{id}/message/stream
  - Gestisce Server-Sent Events
  - Supporta AbortSignal per interruzione
- `downloadReport(conversationId)` - GET /api/conversations/{id}/download_report
- `parseDocument(file)` - POST /api/parse-document
- `getSettings()` - GET /api/settings
- `saveSettings(settings)` - POST /api/settings
- `deleteConversation(conversationId)` - DELETE /api/conversations/{id}
- `deleteConversations(conversationIds)` - DELETE /api/conversations (multiple)

---

### **frontend/src/components/ChatInterface.jsx**
**Funzione principale:** Interfaccia chat principale

**Funzioni principali:**
- `ChatInterface()` - Componente chat
  - Gestisce input utente
  - Mostra messaggi conversazione
  - Gestisce upload file
  - Mostra Stage1, Stage2, Stage3
  - Pulsante Stop per interrompere generazione
  - Toggle Tutor Mode e Eco Mode

**Props:**
- `conversation` - Dati conversazione
- `onSendMessage` - Callback invio messaggio
- `isLoading` - Stato caricamento
- `onStopGeneration` - Callback interruzione
- `onTickerClick` - Callback click su ticker
- `onNewMessage` - Callback nuovo messaggio (per moonshot detection)

---

### **frontend/src/components/Sidebar.jsx**
**Funzione principale:** Sidebar con lista conversazioni

**Funzioni principali:**
- `Sidebar()` - Componente sidebar
  - Mostra lista conversazioni
  - Gestisce selezione conversazione
  - Pulsante "New Conversation"
  - **Modalità selezione multipla** con checkbox
  - **Icona cestino** per eliminazione singola
  - **Eliminazione multipla** con conferma

**Props:**
- `conversations` - Lista conversazioni
- `currentConversationId` - ID conversazione attiva
- `onSelectConversation` - Callback selezione
- `onNewConversation` - Callback nuova conversazione
- `onConversationDeleted` - Callback dopo eliminazione

---

### **frontend/src/components/Stage1.jsx**
**Funzione principale:** Visualizzazione Stage 1 - Risposte individuali

**Funzioni principali:**
- `Stage1({ responses })` - Mostra tutte le risposte dei modelli
  - Card per ogni modello
  - Rendering markdown
  - Highlighting ticker

---

### **frontend/src/components/Stage2.jsx**
**Funzione principale:** Visualizzazione Stage 2 - Classifiche peer review

**Funzioni principali:**
- `deAnonymizeText(text, labelToModel)` - De-anonimizza "Response A" -> nome modello
- `Stage2({ rankings, labelToModel, aggregateRankings })` - Mostra classifiche
  - Classifiche individuali per modello
  - Ranking aggregato finale

---

### **frontend/src/components/Stage3.jsx**
**Funzione principale:** Visualizzazione Stage 3 - Risposta finale Chairman

**Funzioni principali:**
- `Stage3({ finalResponse })` - Mostra sintesi finale
  - Label "Chairman"
  - Rendering markdown completo

---

### **frontend/src/components/RightPanel.jsx**
**Funzione principale:** Pannello destro con dati di mercato

**Funzioni principali:**
- `RightPanel({ selectedTicker, onTickerSelect, watchlist })` - Pannello dati
  - Header con ticker selezionato
  - Grafico stock (StockChart)
  - Watchlist rapida con bottoni
  - Status indicator

---

### **frontend/src/components/StockChart.jsx**
**Funzione principale:** Grafico prezzi stock (Recharts)

**Funzioni principali:**
- `StockChart({ ticker })` - Componente grafico
  - Fetch dati da /api/market-history/{ticker}
  - Visualizzazione line chart prezzo
  - Tooltip con dati

---

### **frontend/src/components/MarketOverview.jsx**
**Funzione principale:** Modal overview dati di mercato

**Funzioni principali:**
- `MarketOverview({ isOpen, onClose })` - Modal overview
  - Visualizza grafici multipli
  - Dati watchlist

---

### **frontend/src/components/SettingsModal.jsx**
**Funzione principale:** Modal impostazioni

**Funzioni principali:**
- `SettingsModal({ isOpen, onClose })` - Modal settings
  - Gestione watchlist (aggiungi/rimuovi ticker)
  - Selezione risk profile
  - Selezione council mode
  - Salvataggio impostazioni

---

### **frontend/src/components/Login.jsx**
**Funzione principale:** Componente login/autenticazione

**Funzioni principali:**
- `Login({ onLoginSuccess })` - Form login
  - Autenticazione utente
  - Creazione utente al primo accesso
  - Reset password

---

### **frontend/src/components/EcoToggle.jsx**
**Funzione principale:** Toggle Eco Mode

**Funzioni principali:**
- `EcoToggle({ isEnabled, onToggle })` - Toggle component
  - Attiva/disattiva Eco Mode (salta Raw Models)

---

### **frontend/src/components/TutorToggle.jsx**
**Funzione principale:** Toggle Tutor Mode

**Funzioni principali:**
- `TutorToggle({ isEnabled, onToggle })` - Toggle component
  - Attiva/disattiva Tutor Mode (spiegazioni semplificate)

---

### **frontend/src/components/StatusIndicator.jsx**
**Funzione principale:** Indicatore stato durante streaming

**Funzioni principali:**
- `StatusIndicator({ currentStreamedText, loadingState })` - Componente status
  - Mostra stato corrente (Stage 1/2/3)
  - Animazioni loading

---

### **frontend/src/components/AgentRenderer.jsx**
**Funzione principale:** Rendering intelligente contenuto agenti

**Funzioni principali:**
- `AgentRenderer({ content })` - Componente rendering
  - Identifica tipo agente (Quant, Risk Manager, Macro, Chairman)
  - Applica styling specifico
  - Rendering markdown con highlighting

---

### **frontend/src/components/TickerLink.jsx**
**Funzione principale:** Utility per ticker nel testo

**Funzioni principali:**
- `extractTickers(text)` - Estrae ticker dal testo
- `TickerText({ text, onTickerClick })` - Componente testo con ticker cliccabili

---

### **frontend/src/main.jsx**
**Funzione principale:** Entry point React

**Funzioni principali:**
- Inizializza React app
- Renderizza App component

---

## 🛠️ SCRIPT DI UTILITÀ

### **start.ps1** / **start.sh** / **Start_Council.bat**
**Funzione:** Script di avvio sistema completo
- Verifica dipendenze
- Avvia backend (uvicorn su porta 8001)
- Avvia frontend (npm run dev su porta 5173)
- Apre browser automaticamente

---

### **create_backup.ps1**
**Funzione:** Crea backup completo del progetto
- Copia intera cartella con timestamp
- Mostra dimensione backup
- Lista backup disponibili

---

### **verify_env.py**
**Funzione:** Verifica configurazione ambiente
- Controlla API key OpenRouter
- Verifica dipendenze Python

---

### **check_health.py**
**Funzione:** Health check sistema
- Verifica backend attivo
- Verifica frontend attivo

---

### **reset_user.py**
**Funzione:** Reset utente database
- Elimina utente esistente
- Permette ricreazione

---

### **test_*.py**
**Funzione:** Suite test vari
- `test_api_live.py` - Test API live
- `test_complete.py` - Test completo pipeline
- `test_cors_connection.py` - Test CORS
- `test_council_modes.py` - Test modalità council
- `test_full_pipeline.py` - Test pipeline completa
- `test_phase1.py` - Test Stage 1
- `test_phase2.py` - Test Stage 2
- `test_model_check.py` - Test verifica modelli
- `test_prompt_fix.py` - Test fix prompt memoria

---

## ⚙️ FILE DI CONFIGURAZIONE

### **pyproject.toml**
**Funzione:** Configurazione progetto Python (uv)
- Dipendenze Python
- Script entry points

---

### **frontend/package.json**
**Funzione:** Configurazione progetto Node.js
- Dipendenze npm
- Script (dev, build, etc.)

---

### **frontend/vite.config.js**
**Funzione:** Configurazione Vite (build tool)
- Configurazione dev server
- Proxy per API

---

### **frontend/eslint.config.js**
**Funzione:** Configurazione ESLint
- Regole linting JavaScript/React

---

### **.env**
**Funzione:** Variabili ambiente (non committato)
- `OPENROUTER_API_KEY` - API key OpenRouter

---

### **.gitignore**
**Funzione:** File da ignorare in git
- Database, cache, node_modules, etc.

---

## 📊 STRUTTURA DATI

### **Database SQLite (council.db)**
**Tabelle:**
- `conversations` - Conversazioni (id, title, created_at, messages JSON)
- `memories` - Memorie a lungo termine (id, date, title, summary, tags)
- `settings` - Impostazioni (key, value JSON)
- `users` - Utenti (username, hashed_password, recovery_token)

---

## 🔄 FLUSSO OPERATIVO

1. **Utente invia messaggio** → `ChatInterface.jsx`
2. **Frontend chiama API** → `api.js` → `sendMessageStream()`
3. **Backend riceve** → `main.py` → `send_message_stream()`
4. **Stage 1** → `council.py` → `stage1_collect_responses()`
   - Chiama Raw Models + Specialisti in parallelo
5. **Stage 2** → `council.py` → `stage2_collect_rankings()`
   - Ogni modello classifica risposte anonime
6. **Stage 3** → `council.py` → `stage3_synthesize_final()`
   - Chairman sintetizza risposta finale
7. **Salvataggio** → `storage.py` → `add_assistant_message()`
8. **Frontend aggiorna UI** → Eventi SSE aggiornano componenti

---

## 🎯 FUNZIONALITÀ CHIAVE

- ✅ **3-Stage Council Process** - Opinioni → Classifiche → Sintesi
- ✅ **Streaming Real-time** - Server-Sent Events per aggiornamenti progressivi
- ✅ **Role Isolation** - Vincoli negativi per evitare mimesi
- ✅ **Memory System** - Continuità tra conversazioni
- ✅ **Market Data Integration** - Dati real-time Yahoo Finance
- ✅ **PDF Report Generation** - Export conversazioni
- ✅ **Conversation Management** - Crea, elimina, lista conversazioni
- ✅ **Eco Mode** - Salta Raw Models per risparmiare token
- ✅ **Tutor Mode** - Spiegazioni semplificate
- ✅ **Stop Generation** - Interruzione generazione in corso
- ✅ **Multi-selection Delete** - Eliminazione multipla conversazioni

---

*Documentazione generata il 2026-01-21*
