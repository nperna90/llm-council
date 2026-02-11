import time
from functools import wraps

# Qui salviamo i dati: { "chiave_univoca": (dati, timestamp) }
_memory_cache = {}

# Durata standard della cache: 300 secondi (5 minuti)
DEFAULT_TTL = 300 

def cached_data(ttl_seconds=DEFAULT_TTL):
    """
    Decoratore che salva il risultato di una funzione.
    Se richiamata con gli stessi argomenti entro 'ttl_seconds',
    restituisce il valore salvato senza rieseguire la funzione.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Creiamo una "chiave" univoca basata sugli argomenti (es. la lista dei ticker)
            # Dobbiamo convertire le liste in tuple perché le liste non sono "hashabili" in Python
            key_parts = []
            for arg in args:
                if isinstance(arg, list):
                    key_parts.append(tuple(sorted(arg)))
                else:
                    key_parts.append(arg)
            
            cache_key = (func.__name__, tuple(key_parts))
            
            # 1. Controlliamo se abbiamo il dato in memoria
            if cache_key in _memory_cache:
                data, timestamp = _memory_cache[cache_key]
                age = time.time() - timestamp
                
                if age < ttl_seconds:
                    print(f"[CACHE HIT] Dati recuperati dalla memoria ({age:.1f}s old)")
                    return data
            
            # 2. Se non c'è o è scaduto, eseguiamo la funzione vera (Scarichiamo da Yahoo)
            print(f"[CACHE MISS] Scaricamento nuovi dati per {func.__name__}...")
            result = func(*args, **kwargs)
            
            # 3. Salviamo il risultato per la prossima volta
            _memory_cache[cache_key] = (result, time.time())
            
            return result
        return wrapper
    return decorator

def clear_cache():
    """Pulisce tutta la memoria (utile per un bottone 'Refresh')"""
    _memory_cache.clear()
    print("[CACHE CLEAR] Cache pulita manualmente.")
