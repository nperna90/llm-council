#!/usr/bin/env python3
"""
Test completo di tutte le funzionalità dell'applicazione LLM Council.
Verifica backend, storage, memory, settings, file parsing, e API endpoints.
"""

import sys
import os
import json
import asyncio
from pathlib import Path

# Aggiungi il path del progetto
sys.path.insert(0, str(Path(__file__).parent))

from backend import storage
from backend import memory
from backend import settings
from backend import file_parser
from backend.config import DATA_DIR

# Colori per output
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

# Test 1: Storage System
def test_storage():
    print_test("Test Storage System")
    
    try:
        # Test 1.1: List conversations
        print_info("Test 1.1: Lista conversazioni")
        convs = storage.list_conversations()
        print_success(f"Trovate {len(convs)} conversazioni")
        if convs:
            print_info(f"  Esempio: {convs[0]['title']} ({convs[0]['message_count']} messaggi)")
        
        # Test 1.2: Create conversation
        print_info("Test 1.2: Creazione nuova conversazione")
        test_id = "test-conv-12345"
        conv = storage.create_conversation(test_id)
        assert conv['id'] == test_id
        print_success("Conversazione creata correttamente")
        
        # Test 1.3: Get conversation
        print_info("Test 1.3: Recupero conversazione")
        retrieved = storage.get_conversation(test_id)
        assert retrieved is not None
        assert retrieved['id'] == test_id
        print_success("Conversazione recuperata correttamente")
        
        # Test 1.4: Add messages
        print_info("Test 1.4: Aggiunta messaggi")
        storage.add_user_message(test_id, "Test message")
        conv_updated = storage.get_conversation(test_id)
        assert len(conv_updated['messages']) == 1
        assert conv_updated['messages'][0]['role'] == 'user'
        print_success("Messaggio utente aggiunto")
        
        # Test 1.5: Update title
        print_info("Test 1.5: Aggiornamento titolo")
        storage.update_conversation_title(test_id, "Test Conversation")
        conv_titled = storage.get_conversation(test_id)
        assert conv_titled['title'] == "Test Conversation"
        print_success("Titolo aggiornato correttamente")
        
        # Cleanup
        test_file = Path(DATA_DIR) / f"{test_id}.json"
        if test_file.exists():
            test_file.unlink()
            print_info("File di test rimosso")
        
        return True
    except Exception as e:
        print_error(f"Errore nel test storage: {e}")
        import traceback
        traceback.print_exc()
        return False

# Test 2: Memory System
def test_memory():
    print_test("Test Memory System")
    
    try:
        # Test 2.1: Initialize memory
        print_info("Test 2.1: Inizializzazione memoria")
        memory.init_memory()
        print_success("Memoria inizializzata")
        
        # Test 2.2: Add memory
        print_info("Test 2.2: Aggiunta ricordo")
        memory.add_memory(
            title="Test Memory",
            summary="Questa è una sintesi di test per verificare il sistema di memoria",
            tags=["TEST", "NVDA"]
        )
        print_success("Ricordo aggiunto")
        
        # Test 2.3: Get relevant context
        print_info("Test 2.3: Recupero contesto rilevante")
        context = memory.get_relevant_context(limit=3)
        assert len(context) > 0
        assert "Test Memory" in context
        print_success("Contesto recuperato correttamente")
        print_info(f"  Lunghezza contesto: {len(context)} caratteri")
        
        return True
    except Exception as e:
        print_error(f"Errore nel test memory: {e}")
        import traceback
        traceback.print_exc()
        return False

# Test 3: Settings System
def test_settings():
    print_test("Test Settings System")
    
    try:
        # Test 3.1: Load settings
        print_info("Test 3.1: Caricamento impostazioni")
        current_settings = settings.load_settings()
        assert 'watchlist' in current_settings
        assert 'risk_profile' in current_settings
        assert 'council_mode' in current_settings
        print_success("Impostazioni caricate")
        print_info(f"  Watchlist: {len(current_settings['watchlist'])} ticker")
        print_info(f"  Risk Profile: {current_settings['risk_profile']}")
        
        # Test 3.2: Get watchlist
        print_info("Test 3.2: Recupero watchlist")
        watchlist = settings.get_watchlist()
        assert isinstance(watchlist, list)
        assert len(watchlist) > 0
        print_success(f"Watchlist recuperata: {len(watchlist)} ticker")
        
        # Test 3.3: Save settings
        print_info("Test 3.3: Salvataggio impostazioni")
        original_watchlist = watchlist.copy()
        test_watchlist = ["NVDA", "AAPL", "MSFT"]
        settings.save_settings({"watchlist": test_watchlist})
        
        # Verifica
        new_watchlist = settings.get_watchlist()
        assert new_watchlist == test_watchlist
        print_success("Impostazioni salvate correttamente")
        
        # Ripristina
        settings.save_settings({"watchlist": original_watchlist})
        print_info("Impostazioni originali ripristinate")
        
        return True
    except Exception as e:
        print_error(f"Errore nel test settings: {e}")
        import traceback
        traceback.print_exc()
        return False

# Test 4: File Parser
def test_file_parser():
    print_test("Test File Parser")
    
    try:
        # Test 4.1: Parse text file
        print_info("Test 4.1: Parsing file di testo")
        test_text = "Questo è un file di test\nCon più righe\ne caratteri speciali: àèéìòù".encode('utf-8')
        result = file_parser.parse_document(test_text, "test.txt")
        assert "test" in result.lower()
        print_success("File di testo parsato correttamente")
        
        # Test 4.2: Parse CSV
        print_info("Test 4.2: Parsing file CSV")
        test_csv = b"Ticker,Price,Change\nNVDA,500.00,+5.2%\nAAPL,150.00,-1.5%"
        result = file_parser.parse_document(test_csv, "test.csv")
        assert "NVDA" in result or "ticker" in result.lower()
        print_success("File CSV parsato correttamente")
        
        # Test 4.3: Invalid file type
        print_info("Test 4.3: Gestione file non supportato")
        result = file_parser.parse_document(b"test", "test.xyz")
        assert "error" in result.lower() or "non supportato" in result.lower()
        print_success("File non supportato gestito correttamente")
        
        return True
    except Exception as e:
        print_error(f"Errore nel test file parser: {e}")
        import traceback
        traceback.print_exc()
        return False

# Test 5: Data Directory Structure
def test_data_structure():
    print_test("Test Struttura Directory Data")
    
    try:
        # Verifica esistenza directory
        print_info("Verifica directory data")
        assert Path(DATA_DIR).exists(), f"Directory {DATA_DIR} non esiste"
        print_success(f"Directory {DATA_DIR} esiste")
        
        # Verifica file JSON nella directory
        if Path(DATA_DIR).exists():
            json_files = list(Path(DATA_DIR).glob("*.json"))
            if json_files:
                print_success(f"Directory {DATA_DIR} contiene {len(json_files)} file JSON")
            else:
                print_info(f"Directory {DATA_DIR} esiste ma non contiene file JSON ancora")
        
        # Verifica file settings
        settings_file = Path(DATA_DIR) / "settings.json"
        if settings_file.exists():
            print_success("File settings.json esiste")
        else:
            print_warning("File settings.json non trovato (verrà creato al primo uso)")
        
        # Verifica file memory
        memory_file = Path(DATA_DIR) / "memory_log.json"
        if memory_file.exists():
            print_success("File memory_log.json esiste")
            with open(memory_file, 'r', encoding='utf-8') as f:
                memories = json.load(f)
            print_info(f"  Trovati {len(memories)} ricordi salvati")
        else:
            print_warning("File memory_log.json non trovato (verrà creato al primo uso)")
        
        return True
    except Exception as e:
        print_error(f"Errore nel test struttura: {e}")
        import traceback
        traceback.print_exc()
        return False

# Test 6: API Endpoints (simulazione)
def test_api_endpoints():
    print_test("Test API Endpoints (Verifica Import)")
    
    try:
        # Test 6.1: Import main
        print_info("Test 6.1: Import modulo main")
        from backend import main
        print_success("Modulo main importato correttamente")
        
        # Test 6.2: Verifica app FastAPI
        print_info("Test 6.2: Verifica app FastAPI")
        assert hasattr(main, 'app')
        assert main.app.title == "LLM Council API"
        print_success("App FastAPI configurata correttamente")
        
        # Test 6.3: Verifica endpoints
        print_info("Test 6.3: Verifica routes")
        routes = [route.path for route in main.app.routes]
        expected_routes = [
            "/",
            "/api/parse-document",
            "/api/settings",
            "/api/conversations",
            "/api/conversations/{conversation_id}",
        ]
        
        for route in expected_routes:
            if route in routes or any(route.replace("{", "").replace("}", "") in r for r in routes):
                print_success(f"Route {route} trovata")
            else:
                print_warning(f"Route {route} non trovata esattamente (potrebbe essere variante)")
        
        return True
    except Exception as e:
        print_error(f"Errore nel test API: {e}")
        import traceback
        traceback.print_exc()
        return False

# Test 7: Encoding e UTF-8
def test_encoding():
    print_test("Test Encoding UTF-8")
    
    try:
        # Test 7.1: Scrittura file con caratteri speciali
        print_info("Test 7.1: Scrittura file con caratteri speciali")
        test_file = Path(DATA_DIR) / "test_encoding.json"
        test_data = {
            "title": "Test con caratteri speciali: àèéìòù € £ ¥",
            "content": "Questo è un test per verificare l'encoding UTF-8"
        }
        
        with open(test_file, 'w', encoding='utf-8') as f:
            json.dump(test_data, f, indent=2, ensure_ascii=False)
        
        # Test 7.2: Lettura file con caratteri speciali
        print_info("Test 7.2: Lettura file con caratteri speciali")
        with open(test_file, 'r', encoding='utf-8') as f:
            loaded_data = json.load(f)
        
        assert loaded_data['title'] == test_data['title']
        print_success("Encoding UTF-8 funziona correttamente")
        
        # Cleanup
        if test_file.exists():
            test_file.unlink()
        
        return True
    except Exception as e:
        print_error(f"Errore nel test encoding: {e}")
        import traceback
        traceback.print_exc()
        return False

# Test 8: Report Generation
def test_report_generation():
    print_test("Test Report Generation")
    
    try:
        # Test 8.1: Import create_report
        print_info("Test 8.1: Import modulo create_report")
        from backend import create_report
        print_success("Modulo create_report importato")
        
        # Test 8.2: Verifica directory reports
        print_info("Test 8.2: Verifica directory reports")
        reports_dir = Path(__file__).parent / "reports"
        if reports_dir.exists():
            print_success(f"Directory reports esiste: {reports_dir}")
            pdf_files = list(reports_dir.glob("*.pdf"))
            print_info(f"  Trovati {len(pdf_files)} file PDF")
            if pdf_files:
                print_info(f"  Esempio: {pdf_files[0].name}")
        else:
            print_warning("Directory reports non trovata (verrà creata al primo uso)")
        
        return True
    except Exception as e:
        print_error(f"Errore nel test report: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}")
    print("TEST COMPLETO LLM COUNCIL APPLICATION")
    print(f"{'='*60}{Colors.RESET}\n")
    
    results = []
    
    # Esegui tutti i test
    results.append(("Storage System", test_storage()))
    results.append(("Memory System", test_memory()))
    results.append(("Settings System", test_settings()))
    results.append(("File Parser", test_file_parser()))
    results.append(("Data Structure", test_data_structure()))
    results.append(("API Endpoints", test_api_endpoints()))
    results.append(("Encoding UTF-8", test_encoding()))
    results.append(("Report Generation", test_report_generation()))
    
    # Riepilogo
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}")
    print("RIEPILOGO TEST")
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
        print(f"\n{Colors.GREEN}{Colors.BOLD}[SUCCESS] TUTTI I TEST SONO PASSATI!{Colors.RESET}\n")
        return 0
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}[FAILED] ALCUNI TEST SONO FALLITI{Colors.RESET}\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
