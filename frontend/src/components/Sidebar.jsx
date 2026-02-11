import { useState, useEffect } from 'react';
import './Sidebar.css';
import { api } from '../api';

export default function Sidebar({
  conversations,
  currentConversationId,
  onSelectConversation,
  onNewConversation,
  onConversationDeleted,
}) {
  const [selectionMode, setSelectionMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [isDeleting, setIsDeleting] = useState(false);

  // Reset selection when exiting selection mode
  useEffect(() => {
    if (!selectionMode) {
      setSelectedIds(new Set());
    }
  }, [selectionMode]);

  const handleToggleSelection = (e, convId) => {
    e.stopPropagation();
    setSelectedIds((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(convId)) {
        newSet.delete(convId);
      } else {
        newSet.add(convId);
      }
      return newSet;
    });
  };

  const handleDeleteSingle = async (e, convId) => {
    e.stopPropagation();
    if (!window.confirm('Sei sicuro di voler eliminare questa conversazione?')) {
      return;
    }

    setIsDeleting(true);
    try {
      await api.deleteConversation(convId);
      if (onConversationDeleted) {
        onConversationDeleted();
      }
      // If deleted conversation was active, clear selection
      if (convId === currentConversationId) {
        onSelectConversation(null);
      }
    } catch (error) {
      console.error('Failed to delete conversation:', error);
      alert('Errore durante l\'eliminazione: ' + error.message);
    } finally {
      setIsDeleting(false);
    }
  };

  const handleDeleteSelected = async () => {
    if (selectedIds.size === 0) return;

    const count = selectedIds.size;
    if (!window.confirm(`Sei sicuro di voler eliminare ${count} conversazione/i?`)) {
      return;
    }

    setIsDeleting(true);
    try {
      await api.deleteConversations(Array.from(selectedIds));
      if (onConversationDeleted) {
        onConversationDeleted();
      }
      // If any deleted conversation was active, clear selection
      if (selectedIds.has(currentConversationId)) {
        onSelectConversation(null);
      }
      setSelectionMode(false);
      setSelectedIds(new Set());
    } catch (error) {
      console.error('Failed to delete conversations:', error);
      alert('Errore durante l\'eliminazione: ' + error.message);
    } finally {
      setIsDeleting(false);
    }
  };

  const handleSelectAll = () => {
    if (selectedIds.size === conversations.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(conversations.map((c) => c.id)));
    }
  };

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <h1>LLM Council</h1>
        <button className="new-conversation-btn" onClick={onNewConversation}>
          + New Conversation
        </button>
        {conversations.length > 0 && (
          <button
            className={`selection-mode-btn ${selectionMode ? 'active' : ''}`}
            onClick={() => setSelectionMode(!selectionMode)}
            style={{ marginTop: '8px', width: '100%' }}
          >
            {selectionMode ? '✕ Annulla' : '☑ Seleziona'}
          </button>
        )}
      </div>

      {selectionMode && selectedIds.size > 0 && (
        <div className="selection-actions">
          <button
            className="delete-selected-btn"
            onClick={handleDeleteSelected}
            disabled={isDeleting}
          >
            🗑️ Elimina selezionate ({selectedIds.size})
          </button>
          <button
            className="select-all-btn"
            onClick={handleSelectAll}
          >
            {selectedIds.size === conversations.length ? 'Deseleziona tutto' : 'Seleziona tutto'}
          </button>
        </div>
      )}

      <div className="conversation-list">
        {conversations.length === 0 ? (
          <div className="no-conversations">No conversations yet</div>
        ) : (
          conversations.map((conv) => (
            <div
              key={conv.id}
              className={`conversation-item ${
                conv.id === currentConversationId ? 'active' : ''
              } ${selectedIds.has(conv.id) ? 'selected' : ''}`}
              onClick={() => {
                if (!selectionMode) {
                  onSelectConversation(conv.id);
                }
              }}
            >
              {selectionMode && (
                <input
                  type="checkbox"
                  className="conversation-checkbox"
                  checked={selectedIds.has(conv.id)}
                  onChange={(e) => handleToggleSelection(e, conv.id)}
                  onClick={(e) => e.stopPropagation()}
                />
              )}
              <div className="conversation-content">
                <div className="conversation-title">
                  {conv.title || 'New Conversation'}
                </div>
                <div className="conversation-meta">
                  {conv.message_count} messages
                </div>
              </div>
              {!selectionMode && (
                <button
                  className="delete-btn"
                  onClick={(e) => handleDeleteSingle(e, conv.id)}
                  disabled={isDeleting}
                  title="Elimina conversazione"
                >
                  🗑️
                </button>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
