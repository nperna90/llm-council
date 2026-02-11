from .database import SessionLocal, SettingsDB
from typing import List, Dict
import json

DEFAULT_WATCHLIST = [
    # Tech & Growth
    "NVDA", "MSFT", "AAPL", "RGTI", "ACN", "ISRG", "QQQM",
    # Core & ETFs
    "VOO", "VT", "FXAIX", "VXUS", "SCHD",
    # Luxury & Consumer
    "LVMUY", "RACE", 
    # Financials, Health & Utilities
    "TD", "UNH", "IHE", "VPU",
    # Commodities & Industrials
    "SLV", "MLM",
    # Altro
    "IAU"
]

DEFAULT_SETTINGS = {
    "watchlist": DEFAULT_WATCHLIST,
    "risk_profile": "Balanced",  # Aggressive, Balanced, Conservative
    "council_mode": "Standard"  # Standard, Crisis, FOMO
}

def get_watchlist() -> List[str]:
    """Legge la watchlist dal DB."""
    db = SessionLocal()
    try:
        setting = db.query(SettingsDB).filter(SettingsDB.key == "watchlist").first()
        if setting:
            return setting.value if isinstance(setting.value, list) else DEFAULT_WATCHLIST
        return DEFAULT_WATCHLIST
    except Exception as e:
        print(f"Errore lettura watchlist: {e}")
        return DEFAULT_WATCHLIST
    finally:
        db.close()

def get_setting(key: str, default_value):
    """Legge un'impostazione specifica dal DB."""
    db = SessionLocal()
    try:
        setting = db.query(SettingsDB).filter(SettingsDB.key == key).first()
        if setting:
            return setting.value
        return default_value
    except Exception as e:
        print(f"Errore lettura setting {key}: {e}")
        return default_value
    finally:
        db.close()

def save_settings(new_settings: Dict):
    """Salva/Aggiorna impostazioni nel DB."""
    db = SessionLocal()
    try:
        # Gestiamo tutte le chiavi delle impostazioni
        for key, value in new_settings.items():
            # Cerchiamo se esiste già
            setting = db.query(SettingsDB).filter(SettingsDB.key == key).first()
            if not setting:
                setting = SettingsDB(key=key, value=value)
                db.add(setting)
            else:
                setting.value = value
            
        db.commit()
    except Exception as e:
        print(f"Errore salvataggio settings: {e}")
        db.rollback()
    finally:
        db.close()

def load_settings() -> Dict:
    """Carica tutte le impostazioni dal DB."""
    db = SessionLocal()
    try:
        settings = db.query(SettingsDB).all()
        result = DEFAULT_SETTINGS.copy()
        
        # Carica le impostazioni dal DB
        for setting in settings:
            result[setting.key] = setting.value
        
        return result
    except Exception as e:
        print(f"Errore caricamento settings: {e}")
        return DEFAULT_SETTINGS
    finally:
        db.close()
