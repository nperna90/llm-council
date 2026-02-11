import requests
import json
import time
import sys

# Configurazione
BASE_URL = "http://localhost:8001"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"

def print_step(step, msg):
    print(f"\n{YELLOW}[STEP {step}] {msg}{RESET}")

def test_system():
    print(f"{GREEN}[TEST] AVVIO TEST FINANCIAL COUNCIL V2 (NO-AUTH){RESET}")
    
    # ---------------------------------------------------------
    # 1. HEALTH CHECK (Verifica che l'Auth sia rimossa)
    # ---------------------------------------------------------
    print_step(1, "Verifica Connessione e Sicurezza Disabilitata")
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code == 200:
            data = response.json()
            print(f"[OK] Server Online: {data}")
        else:
            print(f"{RED}[ERR] Errore Server: {response.status_code}{RESET}")
            sys.exit(1)
    except Exception as e:
        print(f"{RED}[ERR] Impossibile connettersi a localhost:8001. Il backend e' acceso?{RESET}")
        print(f"Errore: {e}")
        sys.exit(1)

    # ---------------------------------------------------------
    # 2. CREAZIONE CONVERSAZIONE (Test Database)
    # ---------------------------------------------------------
    print_step(2, "Creazione Nuova Conversazione nel DB")
    try:
        response = requests.post(f"{BASE_URL}/api/conversations")
        if response.status_code == 200:
            conv_data = response.json()
            conv_id = conv_data['id']
            print(f"[OK] Conversazione Creata. ID: {conv_id}")
        else:
            print(f"{RED}[ERR] Errore Creazione DB: {response.text}{RESET}")
            sys.exit(1)
    except Exception as e:
        print(f"{RED}[ERR] Errore richiesta: {e}{RESET}")
        sys.exit(1)

    # ---------------------------------------------------------
    # 3. TEST INTELLIGENZA (Il cuore del sistema)
    # ---------------------------------------------------------
    query = "Analizza NVDA e AMD. Quale è più rischiosa oggi?"
    print_step(3, f"Invio Query Complessa: '{query}'")
    print(f"{YELLOW}[INFO] Attendi... Il sistema sta eseguendo: Stage 1 (Analisi) -> Stage 2 (Ranking) -> Stage 3 (Sintesi){RESET}")
    
    start_time = time.time()
    
    payload = {
        "content": query,
        "tutor_mode": False,  # Metti True per testare la modalità tutor
        "eco_mode": True      # True = Solo 3 esperti (più veloce), False = Tutti i 7 modelli
    }

    try:
        # Nota: Usiamo l'endpoint sincrono per il test, non lo stream
        response = requests.post(
            f"{BASE_URL}/api/conversations/{conv_id}/message", 
            json=payload,
            timeout=120 # Timeout lungo perché l'AI deve ragionare
        )
        
        duration = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            
            # Il risultato è un dict con stage1, stage2, stage3, metadata
            # Estraiamo la risposta finale dal stage3
            if isinstance(result, dict):
                stage3 = result.get('stage3', {})
                if isinstance(stage3, dict):
                    final_response = stage3.get('response', str(result))
                else:
                    final_response = str(result)
            else:
                final_response = str(result)
            
            print(f"\n{GREEN}[OK] CICLO COMPLETATO IN {duration:.2f} SECONDI{RESET}")
            print(f"{GREEN}[INFO] Stage 1: {len(result.get('stage1', []))} opinioni raccolte{RESET}")
            print(f"{GREEN}[INFO] Stage 2: {len(result.get('stage2', []))} review completate{RESET}")
            print(f"{GREEN}[INFO] Stage 3: Sintesi finale generata{RESET}")
            print("-" * 60)
            try:
                # Prova a stampare con encoding UTF-8
                print(final_response.encode('utf-8', errors='replace').decode('utf-8', errors='replace'))
            except:
                # Fallback: stampa solo i primi caratteri ASCII-safe
                print(final_response[:500].encode('ascii', errors='replace').decode('ascii', errors='replace'))
            print("-" * 60)
            
            # Verifica base del contenuto
            if "Verdetto" in final_response or "Consenso" in final_response or "Sintesi" in final_response:
                print(f"{GREEN}[OK] Formato Output Corretto (Markdown rilevato){RESET}")
            else:
                print(f"{YELLOW}[WARN] Warning: L'output non sembra seguire il template standard.{RESET}")
                print(f"{YELLOW}   Output ricevuto: {final_response[:200]}...{RESET}")
                
        else:
            print(f"{RED}[ERR] Errore durante l'elaborazione AI: {response.status_code}{RESET}")
            print(f"{RED}   Risposta: {response.text}{RESET}")

    except requests.exceptions.ReadTimeout:
        print(f"{RED}[ERR] Timeout! Il backend e' troppo lento (o un modello si e' bloccato).{RESET}")
        print(f"{YELLOW}   Prova ad aumentare il timeout o usa eco_mode=True per velocizzare.{RESET}")
    except Exception as e:
        print(f"{RED}[ERR] Errore Generico: {e}{RESET}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_system()
