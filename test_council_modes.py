import asyncio
import sys
import os
from unittest.mock import patch, MagicMock, AsyncMock

# Configura encoding UTF-8 per Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Aggiungiamo la directory corrente al path
sys.path.append(os.getcwd())

# Mock di tutte le dipendenze esterne prima dell'import
mock_modules = {
    'httpx': MagicMock(),
    'dotenv': MagicMock(),
    'sqlalchemy': MagicMock(),
    'yfinance': MagicMock(),
    'pandas': MagicMock(),
    'numpy': MagicMock(),
}

# Aggiungi i mock a sys.modules
for module_name, mock_module in mock_modules.items():
    sys.modules[module_name] = mock_module

# Mock anche i submoduli comuni
sys.modules['sqlalchemy.orm'] = MagicMock()
sys.modules['sqlalchemy.ext.declarative'] = MagicMock()

# Mock completo di httpx.AsyncClient
mock_httpx = sys.modules['httpx']
mock_response = MagicMock()
mock_response.json.return_value = {
    'choices': [{
        'message': {
            'content': 'Mock response',
            'reasoning_details': None
        }
    }]
}
mock_response.raise_for_status = MagicMock()
mock_async_client = AsyncMock()
mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
mock_async_client.__aexit__ = AsyncMock(return_value=None)
mock_async_client.post = AsyncMock(return_value=mock_response)
mock_httpx.AsyncClient = MagicMock(return_value=mock_async_client)

# Importiamo la funzione da testare
from backend.council import stage1_collect_responses

async def mock_query_model_impl(model, messages, **kwargs):
    """Simula una risposta singola dell'AI"""
    # Simula un piccolo delay per realismo
    await asyncio.sleep(0.01)
    return {"content": f"Risposta simulata da {model}"}

async def mock_query_models_parallel_impl(models, messages):
    """Simula risposte parallele"""
    # Simula un piccolo delay per realismo
    await asyncio.sleep(0.01)
    return {model: {"content": f"Risposta simulata da {model}"} for model in models}

async def run_tests():
    print("AVVIO TEST LOGICA: ECO MODE vs FULL MODE\n")

    # Patchiamo le funzioni API per non spendere soldi veri
    # Usiamo AsyncMock per le funzioni async
    mock_query_model = AsyncMock(side_effect=mock_query_model_impl)
    mock_query_parallel = AsyncMock(side_effect=mock_query_models_parallel_impl)
    
    with patch('backend.openrouter.query_model', new=mock_query_model), \
         patch('backend.openrouter.query_models_parallel', new=mock_query_parallel):

        # --- TEST 1: ECO MODE ATTIVA (Risparmio) ---
        print("TEST 1: Eco Mode = TRUE")
        results_eco = await stage1_collect_responses("Test Query", eco_mode=True)
        
        count_eco = len(results_eco)
        models_eco = [r['model'] for r in results_eco]
        
        print(f"   Risultati ricevuti: {count_eco}")
        print(f"   Modelli attivati: {models_eco}")
        
        if count_eco == 3 and "Quant" in models_eco and "Risk Manager" in models_eco:
            print("   [PASS] Solo gli specialisti sono stati chiamati.")
        else:
            print(f"   [FAIL] Attesi 3 modelli, ottenuti {count_eco}.")

        print("-" * 40)

        # --- TEST 2: FULL MODE (Pieno Consiglio) ---
        print("TEST 2: Eco Mode = FALSE (Default)")
        results_full = await stage1_collect_responses("Test Query", eco_mode=False)
        
        count_full = len(results_full)
        models_full = [r['model'] for r in results_full]
        
        print(f"   Risultati ricevuti: {count_full}")
        print(f"   Modelli attivati: {models_full}")
        
        # Ci aspettiamo 3 Specialisti + 4 Raw = 7
        if count_full >= 7:
            print("   [PASS] Il Pieno Consiglio e stato convocato.")
        else:
            print(f"   [FAIL] Attesi 7+ modelli, ottenuti {count_full}.")

if __name__ == "__main__":
    asyncio.run(run_tests())
