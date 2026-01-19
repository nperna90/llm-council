"""FastAPI backend for LLM Council."""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from typing import List, Dict, Any
import uuid
import json
import asyncio
import os
import re

from . import storage
from . import market_data
from . import create_report_html as create_report
from . import memory
from . import file_parser
from . import settings
from . import cache_manager
from .council import run_full_council, generate_conversation_title, stage1_collect_responses, stage2_collect_rankings, stage3_synthesize_final, calculate_aggregate_rankings, THERAPIST_PROMPT
from .openrouter import query_model
from .config import CHAIRMAN_MODEL

app = FastAPI(title="LLM Council API")


def extract_tickers(text: str) -> list:
    """
    Estrae i ticker dal testo.
    MODIFICA v2.6: Modalità "Solo Dollaro".
    Accetta SOLO i ticker espliciti con il prefisso $ (es. $NVDA).
    Ignora qualsiasi altra parola maiuscola per massima efficienza e zero errori.
    """
    # 1. Cerca SOLO i pattern con il dollaro esplicito (es. $NVDA, $TSLA)
    explicit_tickers = re.findall(r'\$([A-Z]{1,5})', text.upper())
    
    # Rimuoviamo duplicati e restituiamo la lista pulita
    return list(set(explicit_tickers))

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CreateConversationRequest(BaseModel):
    """Request to create a new conversation."""
    pass


class SendMessageRequest(BaseModel):
    """Request to send a message in a conversation."""
    content: str
    tutor_mode: bool = False  # Nuovo parametro, default spento (Pro Mode)


class ConversationMetadata(BaseModel):
    """Conversation metadata for list view."""
    id: str
    created_at: str
    title: str
    message_count: int


class Conversation(BaseModel):
    """Full conversation with all messages."""
    id: str
    created_at: str
    title: str
    messages: List[Dict[str, Any]]


class SettingsUpdate(BaseModel):
    """Request to update settings."""
    watchlist: List[str]
    risk_profile: str = "Balanced"
    council_mode: str = "Standard"


# --- CONFIGURAZIONE PORTAFOGLIO ---
# Lista dei ticker da monitorare in tempo reale.
# Nota: Assicurati che i simboli siano quelli usati da Yahoo Finance.
ACTIVE_WATCHLIST = [
    # Tech & Growth
    "NVDA", "MSFT", "AAPL", "RGTI", "ACN", "ISRG", "QQQM",
    
    # Core & ETFs
    "VOO", "VT", "FXAIX", "VXUS", "SCHD",
    
    # Luxury & Consumer
    "LVMUY", "RACE", 
    
    # Financials, Health & Utilities
    "TD", "UNH", "IHE", "VPU",
    
    # Commodities & Industrials
    "SLV", "MLM",
    
    # Altro (Verifica questo ticker)
    "IAU" 
]


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "LLM Council API"}


@app.post("/api/parse-document")
async def parse_document_endpoint(file: UploadFile = File(...)):
    """
    Riceve un file, estrae il testo e lo restituisce al frontend.
    Non salviamo il file su disco per privacy, lo processiamo in memoria.
    """
    content = await file.read()
    extracted_text = file_parser.parse_document(content, file.filename)

    return {"filename": file.filename, "text": extracted_text}


@app.get("/api/market-history/{ticker}")
async def get_market_history(ticker: str):
    """
    Restituisce lo storico dei prezzi di un ticker per visualizzazione grafico.
    """
    import yfinance as yf
    try:
        # Scarica 1 anno di dati
        ticker_obj = yf.Ticker(ticker)
        hist = ticker_obj.history(period="1y")
        
        if hist.empty:
            return []
        
        # Formatta per Recharts (Array di oggetti)
        data = []
        for date, row in hist.iterrows():
            data.append({
                "date": date.strftime('%Y-%m-%d'),
                "price": float(row['Close']),
                "volume": int(row['Volume']) if 'Volume' in row else 0
            })
        
        # Ordina per data (più vecchio -> più recente)
        data.sort(key=lambda x: x['date'])
        
        return data
    except Exception as e:
        print(f"Errore recupero storico {ticker}: {e}")
        return []


@app.get("/api/settings")
async def get_settings():
    """Restituisce le impostazioni correnti."""
    return settings.load_settings()


@app.post("/api/settings")
async def update_settings(data: SettingsUpdate):
    """Aggiorna le impostazioni."""
    settings.save_settings({
        "watchlist": data.watchlist,
        "risk_profile": data.risk_profile,
        "council_mode": data.council_mode
    })
    return {"status": "success", "settings": settings.load_settings()}


@app.post("/api/refresh-data")
async def refresh_market_data():
    """Forza la pulizia della cache per scaricare nuovi dati."""
    cache_manager.clear_cache()
    return {"status": "Cache cleared", "message": "I prossimi dati saranno scaricati freschi da Yahoo Finance."}


@app.get("/api/conversations", response_model=List[ConversationMetadata])
async def list_conversations():
    """List all conversations (metadata only)."""
    return storage.list_conversations()


@app.post("/api/conversations", response_model=Conversation)
async def create_conversation(request: CreateConversationRequest):
    """Create a new conversation."""
    conversation_id = str(uuid.uuid4())
    conversation = storage.create_conversation(conversation_id)
    return conversation


@app.get("/api/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(conversation_id: str):
    """Get a specific conversation with all its messages."""
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@app.post("/api/conversations/{conversation_id}/message")
async def send_message(conversation_id: str, request: SendMessageRequest):
    """
    Send a message and run the 3-stage council process.
    Returns the complete response with all stages.
    """
    # Check if conversation exists
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    # Get conversation history (all messages except the one we're about to add)
    conversation_history = conversation["messages"]

    # --- LOGICA PANIC MODE ---
    if request.content.strip() == "🚨 PANIC_MODE_TRIGGER 🚨":
        print("🚨 PANIC MODE ATTIVATO!")
        # Bypassiamo tutto il download dati. Serve psicologia, non numeri.
        storage.add_user_message(conversation_id, "Aiutami, sto perdendo soldi e voglio vendere tutto adesso!")
        
        # Chiamata diretta al Dr. Market
        therapist_messages = [
            {"role": "system", "content": THERAPIST_PROMPT},
            {"role": "user", "content": "Aiutami, sto perdendo soldi e voglio vendere tutto adesso!"}
        ]
        
        therapist_response = await query_model(CHAIRMAN_MODEL, therapist_messages)
        
        if therapist_response is None:
            therapist_response = {"content": "Errore: Impossibile generare risposta di supporto."}
        
        # Salviamo come risposta del council (formato compatibile)
        storage.add_assistant_message(
            conversation_id,
            [{"model": "Dr. Market", "response": therapist_response.get('content', '')}],
            [],
            {"model": "Dr. Market", "response": therapist_response.get('content', '')}
        )
        
        return {
            "stage1": [{"model": "Dr. Market", "response": therapist_response.get('content', '')}],
            "stage2": [],
            "stage3": {"model": "Dr. Market", "response": therapist_response.get('content', '')},
            "metadata": {}
        }

    # Add user message (salviamo il messaggio originale)
    storage.add_user_message(conversation_id, request.content)

    # If this is the first message, generate a title
    if is_first_message:
        title = await generate_conversation_title(request.content)
        storage.update_conversation_title(conversation_id, title)

    # --- INIZIO INTEGRAZIONE DATI DI MERCATO E MEMORIA ---
    try:
        print("🔄 Scaricamento dati di mercato in tempo reale...")
        # 1. Recupera la watchlist salvata (quelli fissi)
        active_tickers = settings.get_watchlist()
        
        # 2. --- RILEVAMENTO TICKER ESPLICITO ($) ---
        # Usa la funzione extract_tickers che accetta SOLO ticker con prefisso $
        detected_tickers = extract_tickers(request.content)
        
        # Unione finale: Watchlist + Ticker Espliciti
        full_ticker_list = list(set(active_tickers + detected_tickers))
        
        if detected_tickers:
            print(f"🎯 Ticker Espliciti Rilevati: {detected_tickers}")
        
        print(f"📋 Lista completa per LLM: {full_ticker_list}")
        # ----------------------------------------
        
        # 3. Scarica i dati e genera il contesto
        market_context = market_data.get_llm_context_string(full_ticker_list)
        
        # Recupera il contesto storico dalla memoria
        memory_context = memory.get_relevant_context(limit=3)
        
        # Creiamo il "Prompt Arricchito".
        # L'AI vedrà prima i dati freschi, poi la memoria storica, poi la tua domanda.
        augmented_content = f"""
[SYSTEM: REAL-TIME MARKET DATA SNAPSHOT]
Usa questi dati attuali come unica fonte di verità per prezzi e metriche.

{market_context}

{memory_context}

USER QUESTION:
{request.content}
"""
        
    except Exception as e:
        print(f"⚠️ Errore scaricamento dati (procedo senza): {e}")
        # Se fallisce il download, proviamo comunque ad aggiungere la memoria
        try:
            memory_context = memory.get_relevant_context(limit=3)
            augmented_content = f"""{memory_context}

USER QUESTION:
{request.content}
"""
        except:
            # Se anche la memoria fallisce, usiamo solo il messaggio dell'utente
            augmented_content = request.content
    # --- FINE INTEGRAZIONE ---

    # Run the 3-stage council process with conversation history
    # Usiamo augmented_content che include i dati di mercato e la memoria storica
    stage1_results, stage2_results, stage3_result, metadata = await run_full_council(
        augmented_content,
        conversation_history,
        tutor_mode=request.tutor_mode
    )

    # Add assistant message with all stages
    storage.add_assistant_message(
        conversation_id,
        stage1_results,
        stage2_results,
        stage3_result
    )

    # Return the complete response with metadata
    return {
        "stage1": stage1_results,
        "stage2": stage2_results,
        "stage3": stage3_result,
        "metadata": metadata
    }


@app.post("/api/conversations/{conversation_id}/message/stream")
async def send_message_stream(conversation_id: str, request: SendMessageRequest):
    """
    Send a message and stream the 3-stage council process.
    Returns Server-Sent Events as each stage completes.
    """
    # Check if conversation exists
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    # Get conversation history (all messages except the one we're about to add)
    conversation_history = conversation["messages"]

    # --- LOGICA PANIC MODE ---
    if request.content.strip() == "🚨 PANIC_MODE_TRIGGER 🚨":
        print("🚨 PANIC MODE ATTIVATO (Streaming)!")
        
        async def panic_event_generator():
            try:
                storage.add_user_message(conversation_id, "Aiutami, sto perdendo soldi e voglio vendere tutto adesso!")
                
                yield f"data: {json.dumps({'type': 'panic_mode_start'})}\n\n"
                
                # Chiamata diretta al Dr. Market
                therapist_messages = [
                    {"role": "system", "content": THERAPIST_PROMPT},
                    {"role": "user", "content": "Aiutami, sto perdendo soldi e voglio vendere tutto adesso!"}
                ]
                
                therapist_response = await query_model(CHAIRMAN_MODEL, therapist_messages)
                
                if therapist_response:
                    yield f"data: {json.dumps({'type': 'stage3_complete', 'data': {'model': 'Dr. Market', 'response': therapist_response.get('content', '')}})}\n\n"
                    
                    # Salva la risposta
                    storage.add_assistant_message(
                        conversation_id,
                        [{"model": "Dr. Market", "response": therapist_response.get('content', '')}],
                        [],
                        {"model": "Dr. Market", "response": therapist_response.get('content', '')}
                    )
                
                yield f"data: {json.dumps({'type': 'complete'})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        
        return StreamingResponse(
            panic_event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )

    # --- INIZIO INTEGRAZIONE DATI DI MERCATO E MEMORIA ---
    try:
        print("🔄 Scaricamento dati di mercato in tempo reale...")
        # 1. Recupera la watchlist salvata (quelli fissi)
        active_tickers = settings.get_watchlist()
        
        # 2. --- RILEVAMENTO TICKER ESPLICITO ($) ---
        # Usa la funzione extract_tickers che accetta SOLO ticker con prefisso $
        detected_tickers = extract_tickers(request.content)
        
        # Unione finale: Watchlist + Ticker Espliciti
        full_ticker_list = list(set(active_tickers + detected_tickers))
        
        if detected_tickers:
            print(f"🎯 Ticker Espliciti Rilevati: {detected_tickers}")
        
        print(f"📋 Lista completa per LLM: {full_ticker_list}")
        # ----------------------------------------
        
        # 3. Scarica i dati e genera il contesto
        market_context = market_data.get_llm_context_string(full_ticker_list)
        
        # Recupera il contesto storico dalla memoria
        memory_context = memory.get_relevant_context(limit=3)
        
        # Creiamo il "Prompt Arricchito".
        # L'AI vedrà prima i dati freschi, poi la memoria storica, poi la tua domanda.
        augmented_content = f"""
[SYSTEM: REAL-TIME MARKET DATA SNAPSHOT]
Usa questi dati attuali come unica fonte di verità per prezzi e metriche.

{market_context}

{memory_context}

USER QUESTION:
{request.content}
"""
        
    except Exception as e:
        print(f"⚠️ Errore scaricamento dati (procedo senza): {e}")
        # Se fallisce il download, proviamo comunque ad aggiungere la memoria
        try:
            memory_context = memory.get_relevant_context(limit=3)
            augmented_content = f"""{memory_context}

USER QUESTION:
{request.content}
"""
        except:
            # Se anche la memoria fallisce, usiamo solo il messaggio dell'utente
            augmented_content = request.content
    # --- FINE INTEGRAZIONE ---

    async def event_generator():
        try:
            # Add user message (salviamo il messaggio originale)
            storage.add_user_message(conversation_id, request.content)

            # Start title generation in parallel (don't await yet)
            title_task = None
            if is_first_message:
                title_task = asyncio.create_task(generate_conversation_title(request.content))

            # Stage 1: Collect responses
            yield f"data: {json.dumps({'type': 'stage1_start'})}\n\n"
            stage1_results = await stage1_collect_responses(augmented_content, conversation_history)
            yield f"data: {json.dumps({'type': 'stage1_complete', 'data': stage1_results})}\n\n"

            # Stage 2: Collect rankings
            yield f"data: {json.dumps({'type': 'stage2_start'})}\n\n"
            stage2_results, label_to_model = await stage2_collect_rankings(augmented_content, stage1_results)
            aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)
            yield f"data: {json.dumps({'type': 'stage2_complete', 'data': stage2_results, 'metadata': {'label_to_model': label_to_model, 'aggregate_rankings': aggregate_rankings}})}\n\n"

            # Stage 3: Synthesize final answer
            yield f"data: {json.dumps({'type': 'stage3_start'})}\n\n"
            stage3_result = await stage3_synthesize_final(augmented_content, stage1_results, stage2_results, conversation_history, tutor_mode=request.tutor_mode)
            yield f"data: {json.dumps({'type': 'stage3_complete', 'data': stage3_result})}\n\n"

            # Wait for title generation if it was started
            if title_task:
                title = await title_task
                storage.update_conversation_title(conversation_id, title)
                yield f"data: {json.dumps({'type': 'title_complete', 'data': {'title': title}})}\n\n"

            # Save complete assistant message
            storage.add_assistant_message(
                conversation_id,
                stage1_results,
                stage2_results,
                stage3_result
            )

            # Send completion event
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"

        except Exception as e:
            # Send error event
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.get("/api/conversations/{conversation_id}/download_report")
async def download_report(conversation_id: str):
    """
    Genera e scarica il PDF dell'intera conversazione.
    """
    # 1. Recupera la conversazione dal database (storage)
    conversation = storage.get_conversation(conversation_id)

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Verifica che ci siano messaggi
    if not conversation.get('messages') or len(conversation['messages']) == 0:
        raise HTTPException(
            status_code=400, 
            detail="Conversation has no messages. Cannot generate PDF for empty conversation."
        )
    
    # --- LOGICA DI FILTRO INTELLIGENTE ---
    full_text = ""
    
    # Intestazione introduttiva automatica
    full_text += "## Introduzione\n"
    full_text += "Il seguente documento riassume l'analisi strategica condotta dal Council AI in risposta ai quesiti dell'investitore.\n\n"

    has_stage3_content = False
    for msg in conversation['messages']:
        role = msg['role']
        content = msg.get('content', '')

        # 1. Se è l'UTENTE: Mostra sempre la domanda (è il titolo del capitolo)
        if role == 'user':
            # Puliamo eventuali dati di sistema iniettati nel prompt
            if "[SYSTEM:" in content:
                # Mostra solo la parte vera della domanda dell'utente, nascondendo i dati di mercato grezzi
                parts = content.split("USER QUESTION:")
                if len(parts) > 1:
                    clean_question = parts[1].strip()
                else:
                    clean_question = "Richiesta con dati di mercato allegati."
                full_text += f"## RICHIESTA INVESTITORE\n{clean_question}\n\n"
            else:
                full_text += f"## RICHIESTA INVESTITORE\n{content}\n\n"

        # 2. Se è l'ASSISTENTE: Prendiamo solo la risposta finale (Stage 3)
        elif role == 'assistant':
            stage3 = msg.get('stage3', {})
            if stage3:
                response = stage3.get('response', '')
                if response and len(response.strip()) > 0:
                    has_stage3_content = True
                    # Verifica se è una sintesi finale valida
                    is_final_synthesis = (
                        "synthesis" in response.lower() or 
                        "sintesi" in response.lower() or
                        "conclusione" in response.lower() or
                        "chairman" in response.lower() or
                        len(response) > 200  # Risposte significative sono lunghe
                    )
                    
                    if is_final_synthesis:
                        full_text += f"## DELIBERA DEL CONSIGLIO (Sintesi Finale)\n{response}\n\n"
                    else:
                        # Se non è chiaramente una sintesi, la includiamo comunque come analisi
                        full_text += f"## ANALISI DI DETTAGLIO\n{response}\n\n"
    # --- FINE FILTRO ---
    
    # Verifica che ci sia contenuto Stage 3
    if not has_stage3_content:
        raise HTTPException(
            status_code=400, 
            detail="Conversation has no completed Stage 3 responses. Please wait for the Council to complete its analysis before downloading the PDF."
        )

    # --- NUOVO BLOCCO: Salvataggio Memoria ---
    # Cerchiamo di estrarre solo la sintesi per salvarla nella memoria
    memory_summary = "Nessuna sintesi rilevata."
    if "## DELIBERA DEL CONSIGLIO" in full_text:
        # Prende tutto quello che c'è dopo questo titolo
        parts = full_text.split("## DELIBERA DEL CONSIGLIO")
        if len(parts) > 1:
            # Pulisce un po' il testo
            memory_summary = parts[1].replace("(Sintesi Finale)", "").strip()[:800]  # Max 800 caratteri

    # Salviamo nel cervello a lungo termine
    # Usiamo il titolo della chat come titolo del ricordo
    chat_title = conversation.get('title', 'Strategia senza titolo')
    
    # Estraiamo i tag dai ticker menzionati nel titolo o nel contenuto
    tags = []
    current_watchlist = settings.get_watchlist()
    for ticker in current_watchlist:
        if ticker in chat_title.upper() or ticker in full_text.upper():
            tags.append(ticker)
    
    # Salva nella memoria
    try:
        memory.add_memory(title=chat_title, summary=memory_summary, tags=tags)
    except Exception as e:
        print(f"⚠️ Errore salvataggio memoria (PDF generato comunque): {e}")
    # --- FINE NUOVO BLOCCO ---

    # 3. Genera il PDF
    title = conversation.get('title', 'Investment Analysis')
    
    # Verifica che ci sia contenuto da generare
    if not full_text or len(full_text.strip()) < 50:
        raise HTTPException(
            status_code=400, 
            detail="Conversation has no content to generate PDF. Make sure the conversation has messages with stage3 responses."
        )
    
    try:
        print(f"📄 Generazione PDF per conversazione {conversation_id[:8]}...")
        print(f"   Titolo: {title}")
        print(f"   Lunghezza contenuto: {len(full_text)} caratteri")
        
        pdf_path = create_report.generate_pdf(conversation_id, title, full_text)
        
        if not pdf_path:
            print("❌ PDF generation returned None")
            raise HTTPException(status_code=500, detail="PDF generation returned None. Check server logs for details.")
        
        print(f"✅ PDF generato: {pdf_path}")
        
        if not os.path.exists(pdf_path):
            print(f"❌ PDF file not found at: {pdf_path}")
            raise HTTPException(status_code=500, detail=f"PDF file not found at: {pdf_path}")
        
        print(f"📤 Invio PDF al client...")
        return FileResponse(
            pdf_path, 
            filename=os.path.basename(pdf_path), 
            media_type='application/pdf'
        )
    except HTTPException:
        # Rilancia le HTTPException così come sono
        raise
    except Exception as e:
        print(f"❌ Error generating PDF: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500, 
            detail=f"Error generating PDF: {str(e)}. Check server console for details."
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
