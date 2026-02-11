import asyncio
import sys
import os
from unittest.mock import MagicMock, patch

# Aggiungiamo la directory corrente al path
sys.path.append(os.getcwd())

# Importiamo la funzione che costruisce il prompt finale
from backend.council import stage3_synthesize_final

# Dati finti per il test
FAKE_USER_QUERY = "Analizza $NVDA"
FAKE_STAGE1_RESULTS = [{"model": "Quant", "response": "NVDA è solida."}]
FAKE_STAGE2_RESULTS = []
# Simuliamo la memoria "inquinata" che ha causato il problema
FAKE_MEMORY = """
[MEMORIA PASSATA]
L'utente possiede un portafoglio complesso con RGTI, VOO, SLV.
Abbiamo consigliato di vendere tutto.
"""

async def run_test():
    print("AVVIO TEST GRATUITO: VERIFICA FIX MEMORIA\n")

    # 1. MOCK DELL'API (Il trucco per non pagare)
    # Intercettiamo la funzione 'query_model' in backend.council
    with patch('backend.council.query_model') as mock_api:
        # Configuriamo il mock per restituire una risposta finta se chiamato
        mock_api.return_value = {"content": "Risposta simulata del Chairman."}
        
        # Intercettiamo anche la memoria per iniettare quella "sporca"
        with patch('backend.memory.get_relevant_context', return_value=FAKE_MEMORY):
            
            print("1. Esecuzione Stage 3 con Memoria 'Inquinata'...")
            
            # Eseguiamo la funzione reale del codice
            await stage3_synthesize_final(
                user_query=FAKE_USER_QUERY,
                stage1_results=FAKE_STAGE1_RESULTS,
                stage2_results=FAKE_STAGE2_RESULTS,
                tutor_mode=True # Testiamo anche se il Tutor si attiva
            )

            # 2. ANALISI DEL PROMPT GENERATO
            # Recuperiamo cosa è stato passato alla funzione mockata
            # args[0] è il modello, args[1] sono i messaggi
            call_args = mock_api.call_args
            if not call_args:
                print("[ERRORE] L'API non e stata chiamata.")
                return

            # Estraiamo il prompt di sistema inviato
            sent_messages = call_args[0][1] # Lista di messaggi
            final_prompt = sent_messages[0]['content']

            print("\n2. Ispezione del Prompt inviato al Chairman:")
            print("-" * 40)
            
            # 3. VERIFICHE DI SICUREZZA
            
            # Check A: La nuova regola è presente?
            if "GESTIONE MEMORIA STORICA" in final_prompt:
                print("[OK] PASSATO: La regola 'GESTIONE MEMORIA STORICA' e presente.")
            else:
                print("[ERRORE] FALLITO: La nuova regola non e nel prompt!")

            # Check B: L'istruzione di ignorare è presente?
            if "parla SOLO di NVDA" in final_prompt:
                print("[OK] PASSATO: L'istruzione 'parla SOLO di NVDA' e presente.")
            else:
                print("[ERRORE] FALLITO: Manca l'istruzione specifica di isolamento.")

            # Check C: La memoria vecchia è presente (deve esserci, ma gestita dalle regole sopra)
            if "RGTI" in final_prompt:
                print("[INFO] La memoria storica (RGTI) e nel contesto (Corretto, il prompt deve vederla per ignorarla).")

            print("-" * 40)
            print("\nESTRATTO DEL PROMPT (Le regole che l'AI leggera):")
            # Stampiamo solo la parte delle regole per conferma visiva
            start_index = final_prompt.find("REGOLE DI SINTESI")
            end_index = final_prompt.find("DOMANDA UTENTE")
            if start_index != -1 and end_index != -1:
                print(final_prompt[start_index:end_index])
            else:
                print("[WARN] Non e stato possibile estrarre la sezione delle regole.")

if __name__ == "__main__":
    asyncio.run(run_test())
