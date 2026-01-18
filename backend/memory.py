import json
import os
from datetime import datetime
from typing import List, Dict

# File dove salveremo la storia
MEMORY_FILE = "data/memory_log.json"

def init_memory():
    """Crea il file di memoria se non esiste."""
    if not os.path.exists("data"):
        os.makedirs("data")
    if not os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)

def add_memory(title: str, summary: str, tags: List[str] = []):
    """
    Aggiunge un nuovo ricordo al diario di bordo.
    Viene chiamato quando generi un Report PDF.
    """
    init_memory()
    
    new_entry = {
        "id": datetime.now().strftime("%Y%m%d%H%M%S"),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "title": title,
        "summary": summary, # La decisione finale del Council
        "tags": tags
    }
    
    # Leggi, aggiungi, salva
    try:
        with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
            memories = json.load(f)
    except:
        memories = []
        
    memories.append(new_entry)
    
    with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(memories, f, indent=2, ensure_ascii=False)
    
    print(f"🧠 Memoria salvata: {title}")

def get_relevant_context(limit=3) -> str:
    """
    Recupera gli ultimi 'limit' ricordi per iniettarli nel prompt del Council.
    """
    init_memory()
    try:
        with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
            memories = json.load(f)
    except:
        return ""

    if not memories:
        return ""

    # Prendiamo gli ultimi N ricordi
    recent_memories = memories[-limit:]
    
    context_string = "\n[STORICO DECISIONI PASSATE (MEMORY LOG)]\n"
    for mem in recent_memories:
        context_string += f"- Data: {mem['date']} | Oggetto: {mem['title']}\n"
        context_string += f"  Decisione: {mem['summary'][:500]}...\n" # Tagliamo se troppo lungo
        context_string += "-" * 20 + "\n"
    
    context_string += "[FINE STORICO]\n"
    return context_string
