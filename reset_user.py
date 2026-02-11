"""
Script per resettare/eliminare un utente dal database.
Utile se l'utente è stato creato con un hash non valido.
"""
from backend.database import SessionLocal, UserDB

def reset_user(username: str = None):
    """Elimina un utente specifico o tutti gli utenti se username è None"""
    db = SessionLocal()
    try:
        if username:
            user = db.query(UserDB).filter(UserDB.username == username).first()
            if user:
                db.delete(user)
                db.commit()
                print(f"[OK] Utente '{username}' eliminato con successo.")
            else:
                print(f"[WARN] Utente '{username}' non trovato nel database.")
        else:
            # Elimina tutti gli utenti
            count = db.query(UserDB).count()
            db.query(UserDB).delete()
            db.commit()
            print(f"[OK] {count} utente/i eliminato/i con successo.")
    except Exception as e:
        db.rollback()
        print(f"[ERRORE] Errore durante l'eliminazione: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    import sys
    username = sys.argv[1] if len(sys.argv) > 1 else None
    if username:
        print(f"Eliminazione utente: {username}")
    else:
        print("Eliminazione di tutti gli utenti...")
        response = input("Sei sicuro? (s/n): ")
        if response.lower() != 's':
            print("Operazione annullata.")
            exit(0)
    reset_user(username)
