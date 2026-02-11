from pydantic import BaseModel, Field
from typing import List, Literal, Dict, Optional

# --- STAGE 1: OPINIONI ---
class AgentOpinion(BaseModel):
    agent_name: str
    role: str
    sentiment: Literal["BULLISH", "BEARISH", "NEUTRAL"]
    confidence: int = Field(..., ge=0, le=100)
    key_arguments: List[str]
    risk_score: int = Field(..., ge=0, le=10, description="0=Sicuro, 10=Pericoloso")

# --- STAGE 2: RANKING ---
class SingleRanking(BaseModel):
    target_agent_id: str = Field(..., description="ID dell'analisi valutata (es. 'Response A')")
    score: int = Field(..., ge=0, le=10, description="Voto alla qualità dell'analisi")
    critique: str = Field(..., description="Critica breve (max 1 frase)")

class PeerReview(BaseModel):
    reviewer_name: str
    rankings: List[SingleRanking]

# --- STAGE 3: VERDETTO ---
class ChairmanSynthesis(BaseModel):
    final_verdict: Literal["BUY", "HOLD", "SELL", "PANIC"]
    consensus_score: int = Field(..., description="Punteggio calcolato dai voti")
    executive_summary: str
    actionable_steps: List[str]
    risk_warning: str
    tutor_explanation: Optional[str] = None
