"""
Configuration settings for LLM Council.
All model IDs and simulation mode are environment-driven with sensible defaults.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# OpenRouter
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = os.getenv("OPENROUTER_API_URL", "https://openrouter.ai/api/v1/chat/completions")

# Data directory for conversation storage
DATA_DIR = os.getenv("DATA_DIR", "data/conversations")

# --- Base model IDs (env with defaults) ---
MODEL_GPT = os.getenv("MODEL_GPT", "openai/gpt-4o")
MODEL_CLAUDE = os.getenv("MODEL_CLAUDE", "anthropic/claude-sonnet-4")
MODEL_GEMINI = os.getenv("MODEL_GEMINI", "google/gemini-2.0-flash")
MODEL_GROK = os.getenv("MODEL_GROK", "x-ai/grok-3")

# --- Simulation mode (no real API calls when true) ---
SIMULATION_MODE = os.getenv("SIMULATION_MODE", "false").lower() == "true"

# --- Agent role → model mapping ---
AGENT_MODELS = {
    "quant": os.getenv("AGENT_QUANT_MODEL", MODEL_CLAUDE),
    "risk": os.getenv("AGENT_RISK_MODEL", MODEL_CLAUDE),
    "macro": os.getenv("AGENT_MACRO_MODEL", MODEL_GPT),
    "fundamental": os.getenv("AGENT_FUNDAMENTAL_MODEL", MODEL_GPT),
    "sentiment": os.getenv("AGENT_SENTIMENT_MODEL", MODEL_GROK),
    "contrarian": os.getenv("AGENT_CONTRARIAN_MODEL", MODEL_CLAUDE),
    "chairman": os.getenv("AGENT_CHAIRMAN_MODEL", MODEL_CLAUDE),
    "reviewer": os.getenv("AGENT_REVIEWER_MODEL", MODEL_GEMINI),
    "planner": os.getenv("AGENT_PLANNER_MODEL", MODEL_GEMINI),
}

# Raw council (generalist analysts) — list used for "Analyst 1", "Analyst 2", etc.
RAW_COUNCIL_MODELS = [
    AGENT_MODELS["fundamental"],
    AGENT_MODELS["sentiment"],
    AGENT_MODELS["contrarian"],
    AGENT_MODELS["reviewer"],
]

# Retrocompat
COUNCIL_MODELS = RAW_COUNCIL_MODELS

# --- Risk profiles (position size and risk score limits) ---
RISK_PROFILES = {
    "conservative": {"max_position_pct": 3, "max_risk_score": 4},
    "moderate": {"max_position_pct": 5, "max_risk_score": 6},
    "aggressive": {"max_position_pct": 10, "max_risk_score": 8},
}
