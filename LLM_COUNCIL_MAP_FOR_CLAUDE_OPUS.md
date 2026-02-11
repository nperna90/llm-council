# LLM Council — Detailed Map for Claude Opus 4.6

This document is a technical map of the **LLM Council** codebase, intended to be sent to Claude Opus 4.6 to support improvements to the tool. It covers architecture, data flow, key files, known issues, and extension points.

---

## 1. Project Purpose & High-Level Architecture

**What it is:** A local web app that implements a **3-stage deliberation system** for financial/investment questions. Instead of asking a single LLM, the user’s query is sent to multiple LLMs (via OpenRouter), which (1) give independent opinions, (2) anonymously rank each other’s answers, and (3) a “Chairman” LLM synthesizes a final verdict.

**Tech stack:**
- **Backend:** Python 3.10+, FastAPI, async httpx, OpenRouter API, SQLAlchemy (SQLite), yfinance, FPDF/HTML-to-PDF for reports.
- **Frontend:** React 18, Vite, react-markdown.
- **Storage:** SQLite (`council.db`) — conversations, settings; optional memories table.
- **Ports:** Backend `8001`, Frontend `5173`.

**Run:**
- Backend: `uv run python -m backend.main` (from project root).
- Frontend: `cd frontend && npm run dev`.

---

## 2. Backend — File-by-File Map

### 2.1 Entry & API — `backend/main.py`

- **Role:** FastAPI app, CORS (allow all origins), DB init via `init_db()`.
- **Endpoints:**
  - `GET /` — Health check.
  - **Conversations:** `GET/POST /api/conversations`, `GET/DELETE /api/conversations/{id}`, `DELETE /api/conversations` (body: `conversation_ids`).
  - **Chat:**  
    - `POST /api/conversations/{id}/message` — Sync (no stream). Saves user message, runs full council, saves assistant message, returns `{ stage1, stage2, stage3, metadata }`.  
    - `POST /api/conversations/{id}/message/stream` — **Streaming.** Saves user message, then runs `run_full_council_stream`, forwards SSE events; **at the end** it should save the assistant message with `add_assistant_message(conversation_id, stage1_results, stage2_results, stage3_result)`.
  - **Market:** `GET /api/market-history/{ticker}` — Price history for charts.
  - **Settings:** `GET/POST /api/settings` — watchlist, risk_profile, council_mode (from `backend/settings.py`).
  - **Report:** `GET /api/conversations/{id}/download_report` — PDF via `create_report.generate_pdf`.
- **Request body for message:** `SendMessageRequest`: `content`, `tutor_mode`, `eco_mode`.
- **Bug (streaming save):** In the stream handler, accumulation uses `chunk["stage"] == "stage1_results"` and `"stage2_results"`, but `council.run_full_council_stream` yields `"stage": "stage1"` and `"stage": "stage2"` in data events. So `stage1_results` and `stage2_results` stay empty; the final save either gets empty stage1/stage2 or the `if full_response_text and stage1_results` condition can prevent save. **Fix:** In `main.py` use `chunk["stage"] == "stage1"` and `"stage2"` when accumulating, and ensure the payload is the same structure as the sync endpoint (list of dicts for stage1/stage2).

### 2.2 Council Logic — `backend/council.py`

- **Role:** Orchestrates the 3 stages and optional streaming.
- **Imports:** config (models), prompts (all stage prompts), openrouter (`query_model`), schemas (`AgentOpinion`, `PeerReview`, etc.).

**Stage 1 — Collect opinions**
- `run_stage1(user_query, market_data, eco_mode)`:
  - Builds `agents`: always (QUANT_MODEL, Quant, QUANT_PROMPT), (RISK_MODEL, Risk Manager, RISK_PROMPT), (MACRO_MODEL, Macro Strategist, MACRO_PROMPT). If not eco_mode, appends RAW_COUNCIL_MODELS with role “Analyst i” and RAW_PROMPT.
  - Context string: `"Query: {user_query}\n\nData: {market_data}"`. Market data comes from `market_data.get_llm_context_string(tickers)` where tickers = `market_data.extract_tickers(user_query)`.
  - Runs `get_single_opinion` for each agent in parallel (`asyncio.gather`). Each call: system = role prompt, user = context; then `query_model` → parse JSON → `AgentOpinion(sentiment, confidence, key_arguments, risk_score)`.
  - Returns list of `AgentOpinion`. Converted to list of dicts for API (model, role, sentiment, confidence, key_arguments, risk_score).

**Stage 2 — Peer review**
- `run_stage2(opinions)`:
  - Builds anonymous text: labels `Response A`, `Response B`, …; for each, text like `--- Response A ---\nSentiment: ...\nConfidence: ...\nArgs: ...\nRisk Score: ...`.
  - Reviewers = all agents that have `confidence > 0` (same model + role).
  - For each reviewer, `get_single_review(model, role, anonymous_opinions)`: system = RANKING_PROMPT, user = anonymous text; parse JSON → list of `SingleRanking(target_agent_id, score, critique)` → `PeerReview(reviewer_name=role, rankings)`.
  - Returns list of `PeerReview`, then converted to list of dicts for API (model, rankings with target_agent_id, score, critique).

**Stage 3 — Chairman**
- `run_stage3(user_query, opinions, reviews, tutor_mode)`:
  - Builds a report string: all opinions (with label + role + sentiment/confidence/risk/args), then all reviews (reviewer + votes per target).
  - Context = `"QUERY: ...\n\n{report}\nTUTOR MODE: {tutor_mode}"`. System = CHAIRMAN_PROMPT.
  - Calls `query_model(CHAIRMAN_MODEL, ...)`, parses JSON (final_verdict, consensus_score, executive_summary, actionable_steps, risk_warning, tutor_explanation).
  - Formats a markdown string for the frontend and returns `{ "model": "Chairman", "response": md_output, "raw_data": data }`.

**Full run**
- `run_full_council(...)`: gets tickers from query, gets market_data string, runs stage1 → stage2 → stage3, returns `(stage1_results, stage2_results, stage3_result, metadata)`.
- `run_full_council_stream(...)`: async generator. Yields:
  - `{ "type": "status", "stage": "market_data" | "stage1" | "stage2" | "stage3", "message": "..." }`
  - `{ "type": "data", "stage": "stage1", "content": [AgentOpinion dicts] }` (after stage1)
  - `{ "type": "data", "stage": "stage2", "content": [PeerReview dicts] }` (after stage2)
  - `{ "type": "result", "content": stage3_response_text }`

So the **stage names in data events are `"stage1"` and `"stage2"`**, not `stage1_results`/`stage2_results`. The backend that consumes this stream must use these keys.

### 2.3 Prompts — `backend/prompts.py`

- **JSON_INSTRUCTION:** Global instruction to respond only in JSON, no markdown.
- **Stage 1:** QUANT_PROMPT, RISK_PROMPT, MACRO_PROMPT, RAW_PROMPT. Each defines role and asks for JSON: sentiment (BULLISH/BEARISH/NEUTRAL), confidence 0–100, key_arguments list, risk_score 0–10.
- **Stage 2:** RANKING_PROMPT. Asks for JSON with `rankings`: array of `{ target_agent_id, score, critique }`.
- **Stage 3:** CHAIRMAN_PROMPT. Asks for JSON: final_verdict (BUY/HOLD/SELL/PANIC), consensus_score, executive_summary, actionable_steps, risk_warning, tutor_explanation (optional).

All prompts are f-strings that include `JSON_INSTRUCTION`.

### 2.4 Config — `backend/config.py`

- Loads `OPENROUTER_API_KEY` from `.env`.
- Model IDs: MODEL_GPT, MODEL_CLAUDE, MODEL_GEMINI, MODEL_GROK (OpenRouter identifiers).
- Role assignment: QUANT_MODEL, RISK_MODEL, MACRO_MODEL, CHAIRMAN_MODEL (each set to one of the above).
- RAW_COUNCIL_MODELS: list of 4 models for “pure” opinions when eco_mode is off. COUNCIL_MODELS = RAW_COUNCIL_MODELS for compatibility.

### 2.5 OpenRouter — `backend/openrouter.py`

- `query_model(model, messages, timeout=60)`: single LLM call.
  - If `SIMULATION_MODE` is True: no API call; returns mock JSON based on system prompt (Quant/Risk/Macro/Revisore/Chairman).
  - Else: POST to OpenRouter with `response_format: { type: "json_object" }`, temperature 0.1; returns `{ "content": response_text }`. On HTTP/other errors, returns content with error JSON or empty.
- No streaming in this file; council uses only this single-call API.

### 2.6 Storage — `backend/storage.py`

- All operations use SQLite via `database.SessionLocal` and `ConversationDB`.
- `create_conversation(id)`, `get_conversation(id)`, `save_conversation(conv)`, `list_conversations()`, `add_user_message(id, content)`, `add_assistant_message(id, stage1, stage2, stage3)`, `update_conversation_title(id, title)`, `delete_conversation(id)`, `delete_conversations(ids)`.
- Conversation dict: `id`, `title`, `created_at`, `messages`. Each message: user `{ role, content }` or assistant `{ role, stage1, stage2, stage3 }`. stage1/stage2 are lists of dicts; stage3 is `{ model, response }` (and optionally raw_data in memory only if needed elsewhere).

### 2.7 Database — `backend/database.py`

- SQLAlchemy, `sqlite:///./council.db`.
- Tables: **ConversationDB** (id, title, created_at, messages JSON), **MemoryDB** (id, date, title, summary, tags), **SettingsDB** (key, value JSON). `init_db()` creates tables. SessionLocal sessionmaker.

### 2.8 Schemas — `backend/schemas.py`

- Pydantic: **AgentOpinion** (agent_name, role, sentiment, confidence, key_arguments, risk_score), **SingleRanking** (target_agent_id, score, critique), **PeerReview** (reviewer_name, rankings), **ChairmanSynthesis** (final_verdict, consensus_score, executive_summary, actionable_steps, risk_warning, tutor_explanation). Used in council for parsing and validation.

### 2.9 Market Data — `backend/market_data.py`

- **extract_tickers(text):** Only dollar-prefixed tickers, e.g. `$NVDA` → `["NVDA"]`. Regex `\$([A-Z]{1,5})`.
- **get_llm_context_string(tickers):** Main context for LLMs. Uses `get_market_data(tickers)` (batch price download, SPY added), then for each ticker: analytics (performance metrics, SMA200, volatility, max drawdown, leverage decay note), fundamentals (get_fundamental_ratios), news (get_latest_news), then correlation and backtest reports. Returns one big string.
- **get_market_history(ticker):** Returns list of `{ date, price, volume }` for charts (e.g. 1y).
- **get_market_data**, **get_market_data_single**, **get_multiple_tickers**, **get_portfolio_summary**, **calculate_rsi**, etc. Use `cache_manager.cached_data` (TTL 3600s for get_market_data). Depends on analytics, backtester, fundamentals, correlation, search_tool.

### 2.10 Other Backend Modules (short)

- **settings.py:** Load/save settings (watchlist, risk_profile, council_mode) to DB (SettingsDB).
- **file_parser.py:** Parse document (PDF, CSV, Excel, TXT) to text. Referenced from main only if you add a parse-document endpoint (e.g. POST /api/parse-document).
- **create_report.py:** FPDF-based PDF generation for conversation report (used by download_report).
- **create_report_html.py:** Alternative HTML-to-PDF report generation.
- **memory.py:** Add/get memories (MemoryDB); not wired into council flow in the provided code.
- **analytics.py:** get_performance_metrics, check_leverage_decay.
- **backtester.py:** run_quick_backtest (vs SPY).
- **correlation.py:** get_portfolio_correlation.
- **fundamentals.py:** get_fundamental_ratios.
- **cache_manager.py:** cached_data(ttl_seconds) decorator, clear_cache.
- **search_tool.py:** get_latest_news (used in get_llm_context_string).
- **convert_history.py:** Standalone script to convert conversation files to readable HTML/Markdown.

---

## 3. Frontend — File-by-File Map

### 3.1 Entry & Shell — `frontend/src/main.jsx`, `index.html`

- React root; App is the main component.

### 3.2 App — `frontend/src/App.jsx`

- **State:** conversations, currentConversationId, currentConversation, isLoading, watchlist, activeTicker, isPartyTime (easter egg), windowSize, abortController.
- **Effects:** Load conversations + watchlist on mount; refresh conversations every 5s; load conversation when currentConversationId changes; window resize for confetti.
- **Moonshot:** checkForMoonshot(data) looks for patterns like “Rendimento Totale: +XX%” or “1Y Perf: +XX%” > 50% and triggers confetti.
- **Handlers:** loadConversations, loadConversation, handleNewConversation, handleSelectConversation, handleSendMessage, handleStopGeneration.
- **handleSendMessage:** If no currentConversationId, creates conversation via API and sets it. Adds optimistic user message and a placeholder assistant message (stage1/stage2/stage3 null, loading flags). Calls `api.sendMessageStream(conversationId, content, onEvent, tutorMode, ecoMode, controller.signal)`. On event:
  - `type === 'status'`: updates loading flags (stage1/stage2/stage3) on the last message.
  - `type === 'data'`: if stage === 'stage1' or 'stage2', sets lastMsg.stage1 or stage2 to event.content and clears loading.
  - `type === 'result'`: sets lastMsg.stage3 to { model: 'Chairman', response: event.content }, clears loading, then loadConversations() and clears abortController.
  - `type === 'cancelled'` / `type === 'error'`: cleanup and optional removal of partial assistant message.
- Layout: Sidebar (left), app-chat-column (ChatInterface), app-right-panel (RightPanel with selectedTicker, watchlist). Confetti overlay when isPartyTime.

### 3.3 API Client — `frontend/src/api.js`

- **API_BASE = 'http://localhost:8001'.**
- listConversations, createConversation, getConversation, sendMessage (sync), sendMessageStream (SSE, parse `data: ...\n\n`, call onEvent(JSON), handle [DONE] and AbortError → onEvent({ type: 'cancelled' })), downloadReport, parseDocument, getSettings, saveSettings, deleteConversation, deleteConversations.

### 3.4 Chat — `frontend/src/components/ChatInterface.jsx`

- Props: conversation, onSendMessage, isLoading, onStopGeneration, onTickerClick, onNewMessage.
- Local state: input, isDownloading, isSettingsOpen, isMarketOverviewOpen, isTutorMode, ecoMode. Ref for scroll.
- When conversation or messages change, runs check on last assistant message with stage3 and calls onNewMessage(fullText) for moonshot.
- handleSubmit: validates input, calls onSendMessage(input, isTutorMode, ecoMode), clears input.
- Renders: messages list (user vs assistant; assistant shows Stage1/Stage2/Stage3 + StatusIndicator when loading), input form, TutorToggle, EcoToggle, Settings button, Market Overview button, Download Report, Stop button. Uses ReactMarkdown for message content; ticker linking can be wired via onTickerClick.

### 3.5 Stage Components

- **Stage1.jsx:** Receives `responses` (list of stage1 dicts). Renders each (e.g. cards/tabs) with role, sentiment, confidence, key_arguments, risk_score; markdown where needed.
- **Stage2.jsx:** Receives rankings and optional labelToModel. Shows each reviewer’s rankings (target_agent_id, score, critique). Can de-anonymize labels for display (Response A → model name) if labelToModel is passed; backend currently does not send labelToModel in stream, so frontend may derive it from stage1 order (Response A = first agent, etc.).
- **Stage3.jsx:** Receives finalResponse (Chairman markdown). Renders with distinct style (e.g. green-tinted).

### 3.6 Other Components

- **Sidebar.jsx:** List of conversations, currentConversationId, onSelectConversation, onNewConversation, onConversationDeleted (e.g. loadConversations). May support multi-delete and delete confirmation.
- **RightPanel.jsx:** selectedTicker, watchlist, onTickerSelect. Shows chart (StockChart) and watchlist buttons.
- **StockChart.jsx:** Fetches `/api/market-history/{ticker}` and displays line chart (e.g. Recharts).
- **SettingsModal.jsx:** Watchlist edit, risk_profile, council_mode; save via api.saveSettings.
- **MarketOverview.jsx:** Modal with broader market overview.
- **StatusIndicator.jsx:** Shows current stage (market_data, stage1, stage2, stage3) during loading.
- **EcoToggle.jsx / TutorToggle.jsx:** Booleans passed up to ChatInterface then to sendMessage.
- **AgentRenderer.jsx, TickerLink.jsx:** Used for rendering agent-specific content and clickable tickers.

---

## 4. End-to-End Data Flow

1. User types message (with optional `$TICKER`), optionally toggles Tutor/Eco, sends.
2. Frontend: if no conversation, POST /api/conversations; then POST /api/conversations/{id}/message/stream with { content, tutor_mode, eco_mode }.
3. Backend: add_user_message(id, content); get_conversation; run_full_council_stream(content, history, tutor_mode, eco_mode).
4. Council stream: extract_tickers(query) → get_llm_context_string(tickers) → stage1 (parallel agent calls) → yield stage1 data → stage2 (parallel review calls) → yield stage2 data → stage3 (Chairman) → yield result.
5. Backend stream handler: forwards every chunk as SSE; **should** accumulate stage1/stage2 from data chunks with stage "stage1"/"stage2" and at end call add_assistant_message(id, stage1_results, stage2_results, stage3_result). Currently broken as noted.
6. Frontend: onEvent updates currentConversation messages (loading flags, then stage1, stage2, stage3); on result, reloads conversation list.
7. User sees Stage1 tabs, Stage2 rankings, Stage3 verdict. Can download PDF report, change settings, open new conversation, delete conversations.

---

## 5. Known Issues & Improvement Hooks

- **Streaming save bug:** In main.py, use `chunk["stage"] == "stage1"` and `"stage2"` when accumulating content for add_assistant_message so that after streaming, the conversation is saved with full stage1/stage2 data.
- **Label-to-model in stream:** Frontend could derive labelToModel from stage1 order (Response A = first agent in stage1, etc.) so Stage2 can show “Response A (Quant)” style labels.
- **Conversation history:** run_full_council and run_full_council_stream accept conversation_history but do not currently inject it into the prompts; only the last user query and current market context are used. Adding a short summary or last N turns would improve continuity.
- **Memory:** memory.py and MemoryDB exist but are not used in the council flow. Could be used to inject past verdicts or summaries.
- **Title:** Conversation title is not auto-generated from first message in the current flow; update_conversation_title exists in storage but is not called from main.
- **Parse document:** file_parser exists; if you add POST /api/parse-document, frontend already has api.parseDocument(file).
- **Error handling:** OpenRouter errors return JSON with error string; council treats missing/invalid JSON as fallback AgentOpinion or PeerReview with empty/error message. Frontend could show per-agent errors in Stage1/Stage2.
- **Simulation mode:** openrouter.SIMULATION_MODE allows testing without API cost; toggled in code, not via env/settings.

---

## 6. File Tree (Key Files)

```
backend/
  main.py          # FastAPI, all API routes, streaming bug here
  council.py       # Stage 1/2/3 + stream generator
  prompts.py      # All prompts
  config.py       # Models and roles
  openrouter.py   # query_model, simulation
  storage.py      # Conversation CRUD (SQLite)
  database.py     # SQLAlchemy models, init_db
  schemas.py      # Pydantic AgentOpinion, PeerReview, etc.
  market_data.py  # extract_tickers, get_llm_context_string, get_market_history
  settings.py     # Watchlist, risk_profile, council_mode
  create_report.py
  file_parser.py
  memory.py
  analytics.py, backtester.py, correlation.py, fundamentals.py
  cache_manager.py, search_tool.py
frontend/src/
  App.jsx
  api.js
  components/
    ChatInterface.jsx
    Stage1.jsx, Stage2.jsx, Stage3.jsx
    Sidebar.jsx, RightPanel.jsx, StockChart.jsx
    SettingsModal.jsx, MarketOverview.jsx
    StatusIndicator.jsx, AgentRenderer.jsx, TickerLink.jsx
    EcoToggle.jsx, TutorToggle.jsx
```

---

## 7. Summary for Claude Opus 4.6

- **Purpose:** Multi-LLM financial council (3 stages: opinions → anonymous ranking → Chairman verdict), with market data and optional tutor/eco modes.
- **Backend:** FastAPI on 8001, SQLite, OpenRouter; council in council.py, prompts in prompts.py; streaming in run_full_council_stream; **fix streaming save in main.py by matching stage keys "stage1"/"stage2".**
- **Frontend:** React + Vite, SSE for streaming; App.jsx owns conversation state and stream handling; ChatInterface renders messages and Stage1/2/3.
- **Data:** Tickers only via `$TICKER` in query; context from market_data.get_llm_context_string (prices, fundamentals, news, correlation, backtest).
- **Improvement areas:** Conversation history in prompts, memory integration, auto-title, per-agent error display, simulation mode via config, and any UX/flow improvements you want to drive from this map.

Use this map to reason about changes, fix the streaming persistence bug, and extend the tool (e.g. new stages, new data sources, or different ranking logic) in a consistent way.
