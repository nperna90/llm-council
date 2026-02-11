import asyncio
import json
import logging
import re
from typing import List, Dict, Any, Optional, Tuple

from backend.config import AGENT_MODELS, RAW_COUNCIL_MODELS
from backend.prompts import (
    QUANT_PROMPT, RISK_PROMPT, MACRO_PROMPT, RAW_PROMPT, 
    RANKING_PROMPT, CHAIRMAN_PROMPT
)
from backend.openrouter import query_model
from backend.schemas import AgentOpinion, PeerReview, ChairmanSynthesis, SingleRanking

logger = logging.getLogger(__name__)

# --- UTILS ---
def build_conversation_context(history: list, max_turns: int = 3) -> str:
    """
    Extract last max_turns user+assistant pairs from conversation history
    for inclusion in stage 1 context. User content and assistant stage3 response
    are truncated to 500 chars.
    """
    if not history:
        return ""
    turns = []
    i = 0
    while i < len(history):
        msg = history[i]
        if msg.get("role") == "user":
            user_content = (msg.get("content") or "")[:500]
            assistant_content = ""
            j = i + 1
            if j < len(history) and history[j].get("role") == "assistant":
                stage3 = history[j].get("stage3") or {}
                assistant_content = (stage3.get("response") or "")[:500]
                i = j + 1
            else:
                i += 1
            turns.append((user_content, assistant_content))
        else:
            i += 1
    turns = turns[-max_turns:]
    if not turns:
        return ""
    lines = ["=== CONVERSATION CONTEXT ==="]
    for u, a in turns:
        lines.append(f"User: {u}")
        lines.append(f"Assistant: {a}")
        lines.append("")
    return "\n".join(lines).strip()


def clean_json(text: str) -> Optional[Dict]:
    """Pulisce la risposta LLM per estrarre JSON valido."""
    try:
        text = re.sub(r"```json\s*", "", text)
        text = re.sub(r"```\s*$", "", text)
        text = text.strip()
        return json.loads(text)
    except Exception as e:
        logger.warning(f"JSON parsing failed: {e}")
        return None

# --- STAGE 1: COLLECT OPINIONS ---
async def get_single_opinion(model: str, role: str, prompt: str, context: str) -> AgentOpinion:
    """Recupera l'opinione di un singolo agente."""
    try:
        msgs = [{"role": "system", "content": prompt}, {"role": "user", "content": context}]
        res = await query_model(model, msgs)
        
        if not res or 'content' not in res:
            raise ValueError("Empty response from model")
        
        data = clean_json(res['content'])
        if not data:
            raise ValueError("Invalid JSON")
        
        return AgentOpinion(
            agent_name=model,
            role=role,
            sentiment=data.get("sentiment", "NEUTRAL"),
            confidence=data.get("confidence", 0),
            key_arguments=data.get("key_arguments", []),
            risk_score=data.get("risk_score", 5)
        )
    except Exception as e:
        logger.error(f"Stage 1 Error ({role}): {e}")
        return AgentOpinion(
            agent_name=model,
            role=role,
            sentiment="NEUTRAL",
            confidence=0,
            key_arguments=[f"Errore: {str(e)}"],
            risk_score=5
        )

async def run_stage1(
    user_query: str,
    market_data: str,
    eco_mode: bool,
    conversation_context: str = "",
) -> List[AgentOpinion]:
    """Stage 1: Raccoglie opinioni da tutti gli agenti."""
    agents = [
        (AGENT_MODELS["quant"], "Quant", QUANT_PROMPT),
        (AGENT_MODELS["risk"], "Risk Manager", RISK_PROMPT),
        (AGENT_MODELS["macro"], "Macro Strategist", MACRO_PROMPT)
    ]
    if not eco_mode:
        for i, m in enumerate(RAW_COUNCIL_MODELS):
            agents.append((m, f"Analyst {i+1}", RAW_PROMPT))

    prefix = f"{conversation_context}\n\n" if conversation_context else ""
    context = f"{prefix}Query: {user_query}\n\nData: {market_data}"
    tasks = [get_single_opinion(m, r, p, context) for m, r, p in agents]
    return await asyncio.gather(*tasks)

# --- STAGE 2: PEER REVIEW (RANKING) ---
async def get_single_review(model: str, role: str, anonymous_opinions: str) -> PeerReview:
    """Recupera il ranking di un singolo revisore."""
    try:
        msgs = [{"role": "system", "content": RANKING_PROMPT}, {"role": "user", "content": anonymous_opinions}]
        res = await query_model(model, msgs)
        
        if not res or 'content' not in res:
            raise ValueError("Empty response from model")
        
        data = clean_json(res['content'])
        if not data:
            raise ValueError("Invalid JSON")
        
        rankings = []
        for rank_data in data.get("rankings", []):
            rankings.append(SingleRanking(
                target_agent_id=rank_data.get("target_agent_id", ""),
                score=rank_data.get("score", 0),
                critique=rank_data.get("critique", "")
            ))
        
        return PeerReview(reviewer_name=role, rankings=rankings)
    except Exception as e:
        logger.error(f"Stage 2 Error ({role}): {e}")
        return PeerReview(reviewer_name=role, rankings=[])

async def run_stage2(opinions: List[AgentOpinion]) -> List[PeerReview]:
    """Stage 2: Peer review anonimo delle opinioni."""
    # 1. Crea input anonimo
    anon_map = {f"Response {chr(65+i)}": op for i, op in enumerate(opinions)}  # Response A, B, C...
    anon_text = "\n\n".join([
        f"--- {label} ---\nSentiment: {op.sentiment}\nConfidence: {op.confidence}%\nArgs: {', '.join(op.key_arguments)}\nRisk Score: {op.risk_score}/10"
        for label, op in anon_map.items()
    ])
    
    # 2. Tutti gli agenti (tranne chi ha fallito) votano
    reviewers = [(op.agent_name, op.role) for op in opinions if op.confidence > 0]
    
    if not reviewers:
        return []
    
    tasks = [get_single_review(m, r, anon_text) for m, r in reviewers]
    return await asyncio.gather(*tasks)

# --- STAGE 3: CHAIRMAN SYNTHESIS ---
async def run_stage3(
    user_query: str, 
    opinions: List[AgentOpinion], 
    reviews: List[PeerReview], 
    tutor_mode: bool
) -> Dict[str, Any]:
    """Stage 3: Il Chairman sintetizza tutto in un verdetto finale."""
    
    # Costruisci il report completo per il Chairman
    report = "--- OPINIONI DEGLI ESPERTI ---\n"
    for i, op in enumerate(opinions):
        label = f"Response {chr(65+i)}"
        report += f"ID: {label} ({op.role})\nSentiment: {op.sentiment}\nConfidence: {op.confidence}%\nRisk: {op.risk_score}/10\nArgs: {', '.join(op.key_arguments)}\n\n"
        
    report += "--- PEER REVIEWS (VOTI) ---\n"
    for rev in reviews:
        report += f"Revisore: {rev.reviewer_name} ha votato:\n"
        for rank in rev.rankings:
            report += f"  - {rank.target_agent_id}: Voto {rank.score}/10 ({rank.critique})\n"

    context = f"QUERY: {user_query}\n\n{report}\nTUTOR MODE: {tutor_mode}"
    
    try:
        msgs = [{"role": "system", "content": CHAIRMAN_PROMPT}, {"role": "user", "content": context}]
        res = await query_model(AGENT_MODELS["chairman"], msgs)
        
        if not res or 'content' not in res:
            raise ValueError("Empty response from Chairman")
        
        data = clean_json(res['content'])
        
        if not data:
            raise ValueError("Chairman JSON failed")
        
        # Formattazione Markdown per il Frontend
        md_output = f"""
# 🏛️ Verdetto: {data.get('final_verdict', 'HOLD')}

**Consenso:** {data.get('consensus_score', 0)}/100

## 📝 Sintesi
{data.get('executive_summary', 'Nessuna sintesi disponibile')}

## 🚀 Azioni
{chr(10).join(['- ' + s for s in data.get('actionable_steps', [])])}

## ⚠️ Rischi
{data.get('risk_warning', 'Nessun avviso di rischio specificato')}
"""
        if tutor_mode and data.get('tutor_explanation'):
            md_output += f"\n\n## 🎓 Tutor\n{data['tutor_explanation']}"
            
        return {
            "model": "Chairman",
            "response": md_output,
            "raw_data": data
        }
        
    except Exception as e:
        logger.error(f"Chairman Failed: {e}")
        return {
            "model": "Chairman",
            "response": "⚠️ Errore nella sintesi finale.",
            "raw_data": {}
        }

# --- MAIN RUNNER ---
async def run_full_council(
    user_query: str,
    conversation_history: Optional[List[Dict[str, Any]]] = None,
    tutor_mode: bool = False,
    eco_mode: bool = False
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any], Dict[str, Any]]:
    """
    Esegue il flusso completo: Stage 1 -> Stage 2 -> Stage 3.
    
    Returns:
        Tuple di (stage1_results, stage2_results, stage3_result, metadata)
    """
    # 0. Recupera Dati Mercato
    from backend.market_data import get_llm_context_string, extract_tickers
    tickers = extract_tickers(user_query)
    market_data = get_llm_context_string(tickers) if tickers else "Nessun ticker rilevato."

    # Conversation context for stage 1 only (stage 2/3 get current round only)
    conv_context = build_conversation_context(conversation_history or [])

    # Stage 1: Collect Opinions
    opinions = await run_stage1(user_query, market_data, eco_mode, conversation_context=conv_context)
    
    # Convert opinions to dict format for return
    stage1_results = [
        {
            "model": op.agent_name,
            "role": op.role,
            "sentiment": op.sentiment,
            "confidence": op.confidence,
            "key_arguments": op.key_arguments,
            "risk_score": op.risk_score
        }
        for op in opinions
    ]
    
    # Stage 2: Peer Review
    reviews = await run_stage2(opinions)
    
    # Convert reviews to dict format for return
    stage2_results = [
        {
            "model": rev.reviewer_name,
            "rankings": [
                {
                    "target_agent_id": rank.target_agent_id,
                    "score": rank.score,
                    "critique": rank.critique
                }
                for rank in rev.rankings
            ]
        }
        for rev in reviews
    ]
    
    # Stage 3: Chairman Synthesis
    stage3_result = await run_stage3(user_query, opinions, reviews, tutor_mode)
    
    # Metadata
    metadata = {
        "opinions_count": len(opinions),
        "reviews_count": len(reviews),
        "tickers_analyzed": tickers
    }
    
    return stage1_results, stage2_results, stage3_result, metadata


# --- STREAMING VERSION ---
async def run_full_council_stream(user_query: str, conversation_history: List, tutor_mode: bool, eco_mode: bool):
    """
    Generatore che invia aggiornamenti di stato e il risultato finale.
    """
    from backend.market_data import get_llm_context_string, extract_tickers
    
    # --- STEP 0: DATI ---
    yield {"type": "status", "stage": "market_data", "message": "🔍 Scaricamento dati di mercato..."}
    tickers = extract_tickers(user_query)
    market_data = get_llm_context_string(tickers) if tickers else "Nessun ticker rilevato."

    # Conversation context for stage 1 only (stage 2/3 get current round only)
    conv_context = build_conversation_context(conversation_history or [])

    # --- STEP 1: ANALISI ---
    yield {"type": "status", "stage": "stage1", "message": "🧠 Stage 1: Consultazione Esperti..."}
    opinions = await run_stage1(user_query, market_data, eco_mode, conversation_context=conv_context)
    
    # 🟢 FIX: Inviamo i dati dello Stage 1 al frontend
    yield {
        "type": "data", 
        "stage": "stage1", 
        "content": [op.model_dump() if hasattr(op, 'model_dump') else op.dict() for op in opinions]
    }

    # --- STEP 2: RANKING ---
    yield {"type": "status", "stage": "stage2", "message": "⚖️ Stage 2: Peer Review..."}
    reviews = await run_stage2(opinions)
    
    # 🟢 FIX: Inviamo i dati dello Stage 2 al frontend
    yield {
        "type": "data", 
        "stage": "stage2", 
        "content": [r.model_dump() if hasattr(r, 'model_dump') else r.dict() for r in reviews]
    }
    
    # --- STEP 3: SINTESI ---
    yield {"type": "status", "stage": "stage3", "message": "🏛️ Stage 3: Il Chairman sta decidendo..."}
    result = await run_stage3(user_query, opinions, reviews, tutor_mode)
    
    # --- FINAL RESULT ---
    yield {
        "type": "result", 
        "content": result["response"]
    }
