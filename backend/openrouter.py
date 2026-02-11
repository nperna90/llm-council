# backend/openrouter.py
import os
import json
import asyncio
import logging
import httpx
from dotenv import load_dotenv

# --- CONFIGURAZIONE ---
from backend.config import SIMULATION_MODE

load_dotenv()
API_KEY = os.getenv("OPENROUTER_API_KEY")
API_URL = os.getenv("OPENROUTER_API_URL", "https://openrouter.ai/api/v1/chat/completions") 

logger = logging.getLogger(__name__)

# --- DATI FALSI PER LA SIMULAZIONE ---
MOCK_RESPONSES = {
    "Quant": {
        "sentiment": "BULLISH",
        "confidence": 85,
        "key_arguments": ["SMA 200 in trend ascendente", "RSI a 45 (Ipervenduto)", "Volatilità in contrazione"],
        "risk_score": 3
    },
    "Risk Manager": {
        "sentiment": "NEUTRAL",
        "confidence": 60,
        "key_arguments": ["Correlazione alta col settore Tech", "Drawdown storico del 15%", "Attenzione ai tassi Fed"],
        "risk_score": 6
    },
    "Macro": {
        "sentiment": "BEARISH",
        "confidence": 70,
        "key_arguments": ["Inflazione persistente", "Settore semiconduttori saturo", "Tensioni geopolitiche"],
        "risk_score": 7
    },
    "Ranking": {
        "rankings": [
            {"target_agent_id": "Response A", "score": 8, "critique": "Analisi tecnica solida."},
            {"target_agent_id": "Response B", "score": 5, "critique": "Troppo pessimista senza dati."}
        ]
    },
    "Chairman": {
        "final_verdict": "HOLD",
        "consensus_score": 55,
        "executive_summary": "Il consiglio è diviso. Il Quant vede opportunità tecniche, ma il Macro Strategist segnala venti contrari economici. Il Risk Manager suggerisce prudenza.",
        "actionable_steps": ["Non aprire nuove posizioni long ora", "Impostare Stop Loss al 5%", "Attendere i dati sull'inflazione"],
        "risk_warning": "Alta volatilità prevista per la prossima settimana.",
        "tutor_explanation": "Immagina di voler uscire in barca (comprare azioni). Il meteo locale è bello (Dati Tecnici), ma all'orizzonte c'è una tempesta (Macroeconomia). Il consiglio è: aspetta in porto."
    }
}

async def query_model(model: str, messages: list, timeout: int = 60) -> dict:
    """
    Se SIMULATION_MODE è True, restituisce dati finti.
    Altrimenti chiama OpenRouter.
    
    Returns:
        Dict con 'content' (stringa JSON) per compatibilità con council.py
    """
    
    # --- MODALITÀ SIMULAZIONE (GRATIS) ---
    if SIMULATION_MODE:
        logger.info(f"🧪 SIMULATION MODE: Mocking response for {model}")
        await asyncio.sleep(1.5) # Simula il tempo di "ragionamento"
        
        # Cerca di capire chi sta parlando guardando il System Prompt
        system_content = messages[0]['content'] if messages else ""
        
        # Log per debug (rimuovere in produzione)
        logger.debug(f"System content preview: {system_content[:100]}")
        
        if "Chairman" in system_content: # Per lo Stage 3 - controlla PRIMA degli altri
            content = json.dumps(MOCK_RESPONSES["Chairman"])
            logger.info("Using Chairman mock response")
        elif "Revisore" in system_content or "Ranking" in system_content: # Per lo Stage 2
            content = json.dumps(MOCK_RESPONSES["Ranking"])
            logger.info("Using Ranking mock response")
        elif "Quantitative" in system_content or "Quant" in system_content:
            content = json.dumps(MOCK_RESPONSES["Quant"])
            logger.info("Using Quant mock response")
        elif "Risk Manager" in system_content or "Risk" in system_content:
            content = json.dumps(MOCK_RESPONSES["Risk Manager"])
            logger.info("Using Risk Manager mock response")
        elif "Macro" in system_content:
            content = json.dumps(MOCK_RESPONSES["Macro"])
            logger.info("Using Macro mock response")
        else:
            # Fallback generico
            content = json.dumps(MOCK_RESPONSES["Quant"])
            logger.warning(f"Unknown prompt type, using Quant fallback. System content: {system_content[:200]}")
        
        return {'content': content}

    # --- MODALITÀ REALE (A PAGAMENTO) ---
    if not API_KEY:
        logger.error("OpenRouter API Key mancante!")
        return {'content': '{}'}

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:5173", 
        "X-Title": "Financial Council Local"
    }
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.1, # Bassa temperatura per JSON precisi
        "response_format": {"type": "json_object"} # Forza JSON se il modello lo supporta
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(API_URL, headers=headers, json=payload)
            response.raise_for_status()
            
            result = response.json()
            content = result['choices'][0]['message']['content']
            return {'content': content}

    except httpx.HTTPStatusError as e:
        logger.error(f"OpenRouter Error {e.response.status_code}: {e.response.text}")
        return {'content': json.dumps({"error": f"API Error: {e.response.status_code}"})}
    except Exception as e:
        logger.error(f"Request failed: {e}")
        # In caso di errore reale, ritorna un JSON vuoto o di errore per non crashare
        return {'content': json.dumps({"error": str(e)})}
