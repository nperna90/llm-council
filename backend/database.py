from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

# Configurazione SQLite Semplice
SQLALCHEMY_DATABASE_URL = "sqlite:///./council.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# --- MODELLI DATI (Solo ciò che serve) ---

class ConversationDB(Base):
    __tablename__ = "conversations"
    id = Column(String, primary_key=True, index=True)
    title = Column(String, default="New Conversation")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    # Salviamo i messaggi come JSON per flessibilità
    messages = Column(JSON, default=list)

class MemoryDB(Base):
    __tablename__ = "memories"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, default=datetime.datetime.utcnow)
    title = Column(String)
    summary = Column(Text)
    tags = Column(String) # Salvati come stringa separata da virgole

class SettingsDB(Base):
    __tablename__ = "settings"
    key = Column(String, primary_key=True, index=True)
    value = Column(JSON)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
