from .database import SessionLocal, MemoryDB
from datetime import datetime
from typing import List

def add_memory(title: str, summary: str, tags: List[str] = []):
    """Salva un ricordo nel Database SQLite."""
    db = SessionLocal()
    try:
        new_mem = MemoryDB(
            date=datetime.now().strftime("%Y-%m-%d"),
            title=title,
            summary=summary,
            tags=",".join(tags) if tags else ""
        )
        db.add(new_mem)
        db.commit()
        print(f"🧠 Memoria salvata su DB: {title}")
    except Exception as e:
        print(f"Errore salvataggio memoria: {e}")
        db.rollback()
    finally:
        db.close()

def get_relevant_context(limit=3) -> str:
    """Recupera gli ultimi ricordi dal DB."""
    db = SessionLocal()
    try:
        # Query SQL: Prendi gli ultimi N ordinati per ID decrescente
        memories = db.query(MemoryDB).order_by(MemoryDB.id.desc()).limit(limit).all()
        
        if not memories:
            return ""

        context_string = "\n[STORICO DECISIONI PASSATE (MEMORY LOG)]\n"
        for mem in memories:
            context_string += f"- Data: {mem.date} | Oggetto: {mem.title}\n"
            context_string += f"  Decisione: {mem.summary[:500]}...\n"
            context_string += "-" * 20 + "\n"
        context_string += "[FINE STORICO]\n"
        
        return context_string
    except Exception as e:
        print(f"Errore recupero memoria: {e}")
        return ""
    finally:
        db.close()
