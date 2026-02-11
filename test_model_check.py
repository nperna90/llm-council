"""
Script per verificare se il modello GPT-5.2 esiste e risponde su OpenRouter
"""
import asyncio
import sys
import os
from dotenv import load_dotenv

sys.path.append(os.getcwd())
load_dotenv()

from backend.openrouter import query_model

async def test_gpt_model():
    """Test se GPT-5.2 risponde"""
    model_name = "openai/gpt-5.2"
    
    print(f"Test del modello: {model_name}")
    print("-" * 50)
    
    messages = [
        {"role": "user", "content": "Rispondi solo con 'OK' se mi senti."}
    ]
    
    try:
        response = await query_model(model_name, messages, timeout=30.0)
        
        if response is None:
            print(f"❌ ERRORE: Il modello {model_name} non ha risposto (None)")
            print("\nPossibili cause:")
            print("1. Il modello non esiste su OpenRouter")
            print("2. Errore di autenticazione (API key)")
            print("3. Timeout o errore di rete")
            print("4. Il modello è temporaneamente non disponibile")
        elif not response.get('content'):
            print(f"⚠️ WARN: Il modello ha risposto ma content è vuoto")
            print(f"Response: {response}")
        else:
            print(f"✅ SUCCESSO: Il modello ha risposto!")
            print(f"Risposta: {response.get('content')[:100]}...")
            
    except Exception as e:
        print(f"❌ ECCEZIONE: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_gpt_model())
