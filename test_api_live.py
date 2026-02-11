#!/usr/bin/env python3
"""
Test degli endpoint API del backend (richiede che il server sia in esecuzione).
Esegui questo test dopo aver avviato il backend con: uv run uvicorn backend.main:app --port 8001
"""

import sys
import requests
import json
from pathlib import Path

API_BASE = "http://localhost:8001"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_test(name):
    print(f"\n{Colors.BOLD}{Colors.BLUE}=== {name} ==={Colors.RESET}")

def print_success(msg):
    print(f"{Colors.GREEN}[OK] {msg}{Colors.RESET}")

def print_error(msg):
    print(f"{Colors.RED}[FAIL] {msg}{Colors.RESET}")

def print_warning(msg):
    print(f"{Colors.YELLOW}[WARN] {msg}{Colors.RESET}")

def print_info(msg):
    print(f"  {msg}")

def test_health_check():
    print_test("Test Health Check")
    try:
        response = requests.get(f"{API_BASE}/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_success(f"Backend risponde: {data.get('status', 'unknown')}")
            return True
        else:
            print_error(f"Status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_error("Impossibile connettersi al backend. Assicurati che sia in esecuzione su porta 8001")
        print_info("Avvia il backend con: uv run uvicorn backend.main:app --port 8001")
        return False
    except Exception as e:
        print_error(f"Errore: {e}")
        return False

def test_list_conversations():
    print_test("Test List Conversations")
    try:
        response = requests.get(f"{API_BASE}/api/conversations", timeout=5)
        if response.status_code == 200:
            conversations = response.json()
            print_success(f"Trovate {len(conversations)} conversazioni")
            if conversations:
                print_info(f"  Esempio: {conversations[0].get('title', 'N/A')} ({conversations[0].get('message_count', 0)} messaggi)")
            return True
        else:
            print_error(f"Status code: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Errore: {e}")
        return False

def test_create_conversation():
    print_test("Test Create Conversation")
    try:
        response = requests.post(f"{API_BASE}/api/conversations", json={}, timeout=5)
        if response.status_code == 200:
            conv = response.json()
            print_success(f"Conversazione creata: {conv.get('id', 'N/A')[:8]}")
            return conv.get('id')
        else:
            print_error(f"Status code: {response.status_code}")
            print_info(f"Response: {response.text}")
            return None
    except Exception as e:
        print_error(f"Errore: {e}")
        return None

def test_get_conversation(conversation_id):
    print_test("Test Get Conversation")
    if not conversation_id:
        print_warning("Skipped: nessuna conversazione disponibile")
        return False
    
    try:
        response = requests.get(f"{API_BASE}/api/conversations/{conversation_id}", timeout=5)
        if response.status_code == 200:
            conv = response.json()
            print_success(f"Conversazione recuperata: {conv.get('title', 'N/A')}")
            print_info(f"  Messaggi: {len(conv.get('messages', []))}")
            return True
        else:
            print_error(f"Status code: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Errore: {e}")
        return False

def test_get_settings():
    print_test("Test Get Settings")
    try:
        response = requests.get(f"{API_BASE}/api/settings", timeout=5)
        if response.status_code == 200:
            settings = response.json()
            print_success("Impostazioni recuperate")
            print_info(f"  Watchlist: {len(settings.get('watchlist', []))} ticker")
            print_info(f"  Risk Profile: {settings.get('risk_profile', 'N/A')}")
            return True
        else:
            print_error(f"Status code: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Errore: {e}")
        return False

def test_parse_document():
    print_test("Test Parse Document")
    try:
        # Crea un file di test in memoria
        test_content = b"Ticker,Price,Change\nNVDA,500.00,+5.2%\nAAPL,150.00,-1.5%"
        files = {'file': ('test.csv', test_content, 'text/csv')}
        
        response = requests.post(f"{API_BASE}/api/parse-document", files=files, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print_success(f"Documento parsato: {data.get('filename', 'N/A')}")
            print_info(f"  Lunghezza testo estratto: {len(data.get('text', ''))} caratteri")
            return True
        else:
            print_error(f"Status code: {response.status_code}")
            print_info(f"Response: {response.text}")
            return False
    except Exception as e:
        print_error(f"Errore: {e}")
        return False

def main():
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}")
    print("TEST API LIVE (Backend deve essere in esecuzione)")
    print(f"{'='*60}{Colors.RESET}\n")
    
    # Test 1: Health check
    if not test_health_check():
        print(f"\n{Colors.RED}{Colors.BOLD}[SKIP] Backend non disponibile. Avvia il server prima di eseguire questi test.{Colors.RESET}\n")
        return 1
    
    results = []
    
    # Test 2: List conversations
    results.append(("List Conversations", test_list_conversations()))
    
    # Test 3: Create conversation
    conv_id = test_create_conversation()
    results.append(("Create Conversation", conv_id is not None))
    
    # Test 4: Get conversation
    results.append(("Get Conversation", test_get_conversation(conv_id)))
    
    # Test 5: Get settings
    results.append(("Get Settings", test_get_settings()))
    
    # Test 6: Parse document
    results.append(("Parse Document", test_parse_document()))
    
    # Riepilogo
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}")
    print("RIEPILOGO TEST API")
    print(f"{'='*60}{Colors.RESET}\n")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        if result:
            print_success(f"{name}: PASSED")
        else:
            print_error(f"{name}: FAILED")
    
    print(f"\n{Colors.BOLD}Totale: {passed}/{total} test passati{Colors.RESET}")
    
    if passed == total:
        print(f"\n{Colors.GREEN}{Colors.BOLD}[SUCCESS] TUTTI I TEST API SONO PASSATI!{Colors.RESET}\n")
        return 0
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}[FAILED] ALCUNI TEST API SONO FALLITI{Colors.RESET}\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
