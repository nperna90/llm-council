from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import logging
import json

# Import interni puliti
from backend.database import init_db
from backend.storage import (
    create_conversation, get_conversation,
    list_conversations, delete_conversation, delete_conversations,
    add_user_message, add_assistant_message, update_conversation_title
)
from backend.council import run_full_council, run_full_council_stream
from backend.openrouter import query_model
from backend.config import MODEL_GEMINI
from backend.market_data import get_market_history
from backend.settings import save_settings, load_settings
from backend.create_report import generate_pdf

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Init App & DB
app = FastAPI(title="Financial Council AI - Local")
init_db()

# CORS (Aperto per localhost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- ENDPOINTS ---

@app.get("/")
def root():
    return {"status": "Council is Online", "security": "Disabled (Local Mode)"}

# 1. Gestione Conversazioni
@app.get("/api/conversations")
def api_list_conversations():
    return list_conversations()

@app.post("/api/conversations")
def api_create_conversation():
    import uuid
    conv_id = str(uuid.uuid4())
    return create_conversation(conv_id)

@app.get("/api/conversations/{conversation_id}")
def api_get_conversation(conversation_id: str):
    conv = get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv

@app.delete("/api/conversations/{conversation_id}")
def api_delete_conversation(conversation_id: str):
    success = delete_conversation(conversation_id)
    return {"success": success}

class DeleteConversationsRequest(BaseModel):
    conversation_ids: List[str]

@app.delete("/api/conversations")
def api_delete_conversations(request: DeleteConversationsRequest):
    success = delete_conversations(request.conversation_ids)
    return {"success": success}

# 2. Chat & Council Logic
async def generate_title(user_query: str) -> str:
    """
    Generate a short title for the conversation from the first user message.
    Uses a fast/cheap model with 10s timeout; falls back to first 50 chars on failure.
    """
    system = "Generate a concise 4-8 word title for this financial query. Return ONLY the title text, no quotes, no punctuation at the end."
    try:
        res = await query_model(MODEL_GEMINI, [
            {"role": "system", "content": system},
            {"role": "user", "content": user_query},
        ], timeout=10)
        if res and res.get("content"):
            title = (res["content"] or "").strip().strip('"\'')
            if title:
                return title[:80]
    except Exception as e:
        logger.warning("Title generation failed: %s", e)
    return (user_query or "")[:50]


class SendMessageRequest(BaseModel):
    content: str
    tutor_mode: bool = False
    eco_mode: bool = False

@app.post("/api/conversations/{conversation_id}/message")
async def api_send_message(
    conversation_id: str, 
    request: SendMessageRequest
):
    """Endpoint sincrono (non-streaming) per debug"""
    # 1. Salva messaggio utente
    add_user_message(conversation_id, request.content)

    # 2. Recupera contesto
    conv = get_conversation(conversation_id)
    history = conv['messages']

    # 2b. First message: generate conversation title
    if len(history) <= 1:
        title = await generate_title(request.content)
        update_conversation_title(conversation_id, title)
    
    # 3. Esegui il Council
    try:
        stage1, stage2, stage3, metadata = await run_full_council(
            user_query=request.content,
            conversation_history=history,
            tutor_mode=request.tutor_mode,
            eco_mode=request.eco_mode
        )
        
        # 4. Salva risposta
        add_assistant_message(conversation_id, stage1, stage2, stage3)
        return {
            "stage1": stage1,
            "stage2": stage2,
            "stage3": stage3,
            "metadata": metadata
        }
        
    except Exception as e:
        logger.error(f"Council Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/conversations/{conversation_id}/message/stream")
async def api_send_message_stream(
    conversation_id: str, 
    request: SendMessageRequest
):
    """Endpoint streaming per aggiornamenti in tempo reale"""
    # 1. Salva messaggio utente subito
    add_user_message(conversation_id, request.content)

    # 2. Recupera contesto
    conv = get_conversation(conversation_id)
    history = conv['messages']

    # 2b. First message: generate title before starting stream so it's available quickly
    if len(history) <= 1:
        title = await generate_title(request.content)
        update_conversation_title(conversation_id, title)

    async def event_generator():
        stage1_results: List = []
        stage2_results: List = []
        stage3_result: Optional[dict] = None

        try:
            async for chunk in run_full_council_stream(
                user_query=request.content,
                conversation_history=history,
                tutor_mode=request.tutor_mode,
                eco_mode=request.eco_mode
            ):
                # Accumulate for DB save: match stage1/stage2 (not stage1_results/stage2_results)
                if chunk.get("type") == "data":
                    if chunk.get("stage") == "stage1":
                        stage1_results = chunk.get("content", [])
                    elif chunk.get("stage") == "stage2":
                        stage2_results = chunk.get("content", [])
                elif chunk.get("type") == "result":
                    stage3_result = {"model": "Chairman", "response": chunk.get("content", "")}

                yield f"data: {json.dumps(chunk)}\n\n"

            # Always save after stream completes if we got a stage3 result
            if stage3_result is not None:
                add_assistant_message(conversation_id, stage1_results, stage2_results, stage3_result)

        except Exception as e:
            logger.exception("Stream error: %s", e)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# 3. Market Data & Settings
@app.get("/api/market-history/{ticker}")
def api_market_history(ticker: str):
    return get_market_history(ticker)

@app.get("/api/settings")
def api_get_settings():
    return load_settings()

class SettingsUpdate(BaseModel):
    watchlist: Optional[List[str]] = None
    risk_profile: Optional[str] = None
    council_mode: Optional[str] = None

@app.post("/api/settings")
def api_update_settings(settings: SettingsUpdate):
    current = load_settings()
    new_settings = current.copy()
    if settings.watchlist is not None: new_settings['watchlist'] = settings.watchlist
    if settings.risk_profile is not None: new_settings['risk_profile'] = settings.risk_profile
    if settings.council_mode is not None: new_settings['council_mode'] = settings.council_mode
    save_settings(new_settings)
    return new_settings

# 4. Tools
@app.get("/api/conversations/{conversation_id}/download_report")
def api_download_report(conversation_id: str):
    conv = get_conversation(conversation_id)
    if not conv: raise HTTPException(404)
    
    # Convert messages to text format for PDF
    full_text = ""
    for msg in conv.get('messages', []):
        if msg.get('role') == 'user':
            full_text += f"## USER QUESTION\n{msg.get('content', '')}\n\n"
        elif msg.get('role') == 'assistant':
            stage3 = msg.get('stage3', {})
            if isinstance(stage3, dict):
                response = stage3.get('response', '')
                if response:
                    full_text += f"## COUNCIL RESPONSE\n{response}\n\n"
    
    pdf_path = generate_pdf(conversation_id, conv.get('title', 'Report'), full_text)
    
    if not pdf_path or not os.path.exists(pdf_path):
        raise HTTPException(status_code=500, detail="PDF generation failed")
        
    return FileResponse(pdf_path, filename=os.path.basename(pdf_path), media_type="application/pdf")
