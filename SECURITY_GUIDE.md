# Guida alla Sicurezza - LLM Council

## 🔒 Analisi di Sicurezza

### ✅ Punti di Forza
- **Hashing Password**: bcrypt con pre-hashing SHA256 (robusto)
- **JWT**: Token con scadenza (buona pratica)
- **SQL Injection**: Protetto da SQLAlchemy ORM
- **CORS**: Limitato a localhost per sviluppo

### ⚠️ Vulnerabilità Identificate

#### 1. SECRET_KEY (RISOLTO ✅)
- **Prima**: Hardcoded nel codice
- **Dopo**: Usa variabile d'ambiente
- **Azione**: Aggiungi `SECRET_KEY` al file `.env`

#### 2. Protezione Brute Force (DA IMPLEMENTARE)
- **Rischio**: Attacchi a forza bruta sul login
- **Soluzione**: Rate limiting (max 5 tentativi per IP/utente ogni 15 minuti)

#### 3. Auto-creazione Admin (DA LIMITARE)
- **Rischio**: Chiunque può diventare admin se DB vuoto
- **Soluzione**: Disabilitare dopo primo setup o richiedere token di setup

#### 4. Token JWT Lunghi (DA RIDURRE)
- **Attuale**: 7 giorni
- **Raccomandato**: 1-2 giorni per produzione

## 🛠️ Setup Sicurezza

### 1. Genera SECRET_KEY Sicura

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copia l'output nel file `.env`:
```
SECRET_KEY=la_tua_chiave_generata_qui
```

### 2. Protezione Brute Force (Opzionale ma Consigliato)

Aggiungi rate limiting usando `slowapi`:

```bash
uv add slowapi
```

Poi aggiungi in `backend/main.py`:
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/api/token")
@limiter.limit("5/minute")  # Max 5 tentativi al minuto
async def login_for_access_token(...):
    ...
```

### 3. Riduci Durata Token (Produzione)

In `backend/auth.py`, cambia:
```python
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 giorno invece di 7
```

### 4. Disabilita Auto-creazione Admin (Dopo Setup)

Dopo aver creato il primo utente, rimuovi o commenta il codice di auto-creazione in `backend/main.py` (righe 171-183).

## 📊 Valutazione Sicurezza

| Aspetto | Sviluppo | Produzione |
|---------|----------|------------|
| Hashing Password | ✅ 9/10 | ✅ 9/10 |
| JWT | ⚠️ 6/10 | ⚠️ 4/10 |
| Brute Force | ❌ 2/10 | ❌ 1/10 |
| Secret Management | ✅ 8/10 | ✅ 8/10 |
| **TOTALE** | **6/10** | **3/10** |

## 🚀 Checklist Produzione

Prima di mettere in produzione:

- [ ] SECRET_KEY in variabile d'ambiente (non nel codice)
- [ ] Rate limiting su endpoint login
- [ ] Token JWT ridotti a 1-2 giorni
- [ ] Disabilitare auto-creazione admin
- [ ] HTTPS abilitato
- [ ] CORS configurato solo per domini autorizzati
- [ ] Logging tentativi di accesso
- [ ] Backup database regolari
- [ ] Monitoraggio errori e accessi sospetti

## 🔍 Monitoraggio

Aggiungi logging per:
- Tentativi di login falliti
- Accessi riusciti
- Tentativi di accesso a endpoint protetti
- Errori di autenticazione

## 📚 Risorse

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [JWT Best Practices](https://datatracker.ietf.org/doc/html/rfc8725)
