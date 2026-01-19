"""SQLite-based storage for conversations."""

from datetime import datetime
from typing import List, Dict, Any, Optional
from .database import SessionLocal, ConversationDB


def create_conversation(conversation_id: str) -> Dict[str, Any]:
    """
    Create a new conversation.

    Args:
        conversation_id: Unique identifier for the conversation

    Returns:
        New conversation dict
    """
    db = SessionLocal()
    try:
        # Verifica se esiste già
        existing = db.query(ConversationDB).filter(ConversationDB.id == conversation_id).first()
        if existing:
            return {
                "id": existing.id,
                "created_at": existing.created_at.isoformat(),
                "title": existing.title,
                "messages": existing.messages or []
            }

        new_conv = ConversationDB(
            id=conversation_id,
            title="New Conversation",
            messages=[]
        )
        db.add(new_conv)
        db.commit()

        return {
            "id": new_conv.id,
            "created_at": new_conv.created_at.isoformat(),
            "title": new_conv.title,
            "messages": new_conv.messages or []
        }
    except Exception as e:
        print(f"Errore creazione conversazione: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def get_conversation(conversation_id: str) -> Optional[Dict[str, Any]]:
    """
    Load a conversation from storage.

    Args:
        conversation_id: Unique identifier for the conversation

    Returns:
        Conversation dict or None if not found
    """
    db = SessionLocal()
    try:
        conv = db.query(ConversationDB).filter(ConversationDB.id == conversation_id).first()
        if conv:
            return {
                "id": conv.id,
                "title": conv.title,
                "messages": conv.messages or [],
                "created_at": conv.created_at.isoformat()
            }
        return None
    except Exception as e:
        print(f"Errore lettura conversazione: {e}")
        return None
    finally:
        db.close()


def save_conversation(conversation: Dict[str, Any]):
    """
    Save a conversation to storage.

    Args:
        conversation: Conversation dict to save
    """
    db = SessionLocal()
    try:
        conv = db.query(ConversationDB).filter(ConversationDB.id == conversation['id']).first()
        
        if conv:
            # Aggiorna esistente
            conv.messages = conversation.get('messages', [])
            if 'title' in conversation:
                conv.title = conversation['title']
        else:
            # Crea nuova
            new_conv = ConversationDB(
                id=conversation['id'],
                title=conversation.get('title', 'New Conversation'),
                messages=conversation.get('messages', [])
            )
            db.add(new_conv)
        
        db.commit()
    except Exception as e:
        print(f"Errore salvataggio conversazione: {e}")
        db.rollback()
    finally:
        db.close()


def list_conversations() -> List[Dict[str, Any]]:
    """
    List all conversations (metadata only).

    Returns:
        List of conversation metadata dicts
    """
    db = SessionLocal()
    try:
        convs = db.query(ConversationDB).order_by(ConversationDB.created_at.desc()).all()
        return [
            {
                "id": c.id,
                "title": c.title,
                "created_at": c.created_at.isoformat(),
                "message_count": len(c.messages) if c.messages else 0
            }
            for c in convs
        ]
    except Exception as e:
        print(f"Errore list conversazioni: {e}")
        return []
    finally:
        db.close()


def add_user_message(conversation_id: str, content: str):
    """
    Add a user message to a conversation.

    Args:
        conversation_id: Conversation identifier
        content: User message content
    """
    conversation = get_conversation(conversation_id)
    if conversation is None:
        raise ValueError(f"Conversation {conversation_id} not found")

    conversation["messages"].append({
        "role": "user",
        "content": content
    })

    save_conversation(conversation)


def add_assistant_message(
    conversation_id: str,
    stage1: List[Dict[str, Any]],
    stage2: List[Dict[str, Any]],
    stage3: Dict[str, Any]
):
    """
    Add an assistant message with all 3 stages to a conversation.

    Args:
        conversation_id: Conversation identifier
        stage1: List of individual model responses
        stage2: List of model rankings
        stage3: Final synthesized response
    """
    conversation = get_conversation(conversation_id)
    if conversation is None:
        raise ValueError(f"Conversation {conversation_id} not found")

    conversation["messages"].append({
        "role": "assistant",
        "stage1": stage1,
        "stage2": stage2,
        "stage3": stage3
    })

    save_conversation(conversation)


def update_conversation_title(conversation_id: str, title: str):
    """
    Update the title of a conversation.

    Args:
        conversation_id: Conversation identifier
        title: New title for the conversation
    """
    db = SessionLocal()
    try:
        conv = db.query(ConversationDB).filter(ConversationDB.id == conversation_id).first()
        if conv:
            conv.title = title
            db.commit()
        else:
            raise ValueError(f"Conversation {conversation_id} not found")
    except Exception as e:
        print(f"Errore aggiornamento titolo: {e}")
        db.rollback()
        raise
    finally:
        db.close()
