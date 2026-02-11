import requests
import json
import time

BASE_URL = "http://localhost:8001"

print("[TEST] Creazione conversazione...")
try:
    conv = requests.post(f"{BASE_URL}/api/conversations").json()
    conv_id = conv['id']
    print(f"[OK] Conversazione creata: {conv_id}")
    
    print("[TEST] Invio query: analizza $NVDA")
    start = time.time()
    
    response = requests.post(
        f"{BASE_URL}/api/conversations/{conv_id}/message/stream",
        json={
            'content': 'analizza $NVDA',
            'tutor_mode': False,
            'eco_mode': True
        },
        stream=True,
        timeout=120
    )
    
    print("[OK] Stream iniziato")
    buffer = ''
    
    for chunk in response.iter_content(chunk_size=1024):
        buffer += chunk.decode('utf-8', errors='ignore')
        lines = buffer.split('\n\n')
        buffer = lines.pop() if lines else ''
        
        for line in lines:
            if line.startswith('data: '):
                data = line[6:]
                if data == '[DONE]':
                    print("\n[OK] Stream completato")
                    break
                try:
                    event = json.loads(data)
                    if event.get('type') == 'status':
                        print(f"[STATUS] {event.get('stage')}: {event.get('message')}")
                    elif event.get('type') == 'data':
                        stage = event.get('stage', '')
                        if stage == 'stage1_results':
                            print(f"[DATA] Stage 1: {len(event.get('content', []))} opinioni ricevute")
                        elif stage == 'stage2_results':
                            print(f"[DATA] Stage 2: {len(event.get('content', []))} review ricevute")
                    elif event.get('type') == 'result':
                        duration = time.time() - start
                        print(f"\n[RESULT] Tempo totale: {duration:.2f}s")
                        print("\n" + "="*60)
                        content = event.get('content', '')
                        # Gestisce encoding per Windows
                        try:
                            print(content.encode('utf-8', errors='replace').decode('utf-8', errors='replace'))
                        except:
                            print(content[:500].encode('ascii', errors='replace').decode('ascii', errors='replace'))
                        print("="*60)
                except Exception as e:
                    print(f"[ERROR] Parsing: {e}")
    
    print("\n[OK] Test completato")
    
except requests.exceptions.ConnectionError:
    print("[ERR] Impossibile connettersi al backend. Assicurati che sia in esecuzione su porta 8001")
except Exception as e:
    print(f"[ERR] Errore: {e}")
    import traceback
    traceback.print_exc()
