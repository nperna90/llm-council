/**
 * API client for the LLM Council backend.
 * 
 * IMPORTANT: Definisce l'URL del backend Python.
 * Assicurati che la porta corrisponda a quella usata da uvicorn (default: 8001)
 */

export const API_BASE = 'http://localhost:8001';


export const api = {
  /**
   * List all conversations.
   */
  async listConversations() {
    const response = await fetch(`${API_BASE}/api/conversations`);
    if (!response.ok) {
      throw new Error('Failed to list conversations');
    }
    return response.json();
  },

  /**
   * Create a new conversation.
   */
  async createConversation() {
    const response = await fetch(`${API_BASE}/api/conversations`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({}),
    });
    if (!response.ok) {
      throw new Error('Failed to create conversation');
    }
    return response.json();
  },

  /**
   * Get a specific conversation.
   */
  async getConversation(conversationId) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}`
    );
    if (!response.ok) {
      throw new Error('Failed to get conversation');
    }
    return response.json();
  },

  /**
   * Send a message in a conversation.
   */
  async sendMessage(conversationId, content, tutorMode = false, ecoMode = false) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}/message`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ content, tutor_mode: tutorMode, eco_mode: ecoMode }),
      }
    );
    if (!response.ok) {
      throw new Error('Failed to send message');
    }
    return response.json();
  },

  /**
   * Send a message and receive streaming updates.
   * @param {string} conversationId - The conversation ID
   * @param {string} content - The message content
   * @param {function} onEvent - Callback function for each event: (event) => void
   * @param {boolean} tutorMode - Enable tutor mode for simple explanations
   * @param {boolean} ecoMode - Enable eco mode to skip Raw Council models
   * @param {AbortSignal} abortSignal - Optional AbortSignal to cancel the request
   * @returns {Promise<void>}
   */
  async sendMessageStream(conversationId, content, onEvent, tutorMode = false, ecoMode = false, abortSignal = null) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}/message/stream`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ content, tutor_mode: tutorMode, eco_mode: ecoMode }),
        signal: abortSignal,
      }
    );

    if (!response.ok) {
      let errorMessage = 'Network response was not ok';
      try {
        const errorData = await response.json();
        errorMessage = errorData.detail || errorData.message || errorMessage;
      } catch (e) {
        const errorText = await response.text();
        if (errorText) errorMessage = errorText;
      }
      throw new Error(errorMessage);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        // SSE separa gli eventi con doppia newline
        const lines = buffer.split('\n\n');
        // Tieni l'ultimo pezzo incompleto nel buffer
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.slice(6);
            if (dataStr === '[DONE]') {
              return;
            }
            
            try {
              const event = JSON.parse(dataStr);
              onEvent(event); // Passa l'evento completo al componente React
            } catch (e) {
              console.error('Error parsing SSE JSON:', e, 'Raw data:', dataStr);
            }
          }
        }
      }
    } catch (error) {
      if (error.name === 'AbortError') {
        console.log('Stream interrotto dall\'utente');
        onEvent({ type: 'cancelled', message: 'Stream interrotto' });
        throw error;
      }
      throw error;
    } finally {
      reader.releaseLock();
    }
  },

  /**
   * Download a PDF report for a conversation.
   */
  async downloadReport(conversationId) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}/download_report`
    );
    
    if (!response.ok) {
      // Prova a leggere il messaggio di errore dal backend
      let errorMessage = 'Failed to download report';
      try {
        const errorData = await response.json();
        errorMessage = errorData.detail || errorData.message || errorMessage;
      } catch (e) {
        // Se non è JSON, usa il testo della risposta
        try {
          const errorText = await response.text();
          if (errorText) errorMessage = errorText;
        } catch (e2) {
          // Usa il messaggio di default
        }
      }
      throw new Error(errorMessage);
    }
    return response;
  },

  /**
   * Parse a document (PDF, CSV, etc.) and extract text.
   */
  async parseDocument(file) {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE}/api/parse-document`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error('Failed to parse document');
    }

    return response.json();
  },

  /**
   * Get current settings.
   */
  async getSettings() {
    try {
      const response = await fetch(`${API_BASE}/api/settings`);
      if (!response.ok) {
        throw new Error(`Failed to get settings: ${response.status} ${response.statusText}`);
      }
      return response.json();
    } catch (error) {
      console.error('Error fetching settings from:', `${API_BASE}/api/settings`, error);
      throw error;
    }
  },

  /**
   * Update settings.
   */
  async saveSettings(settings) {
    try {
      const response = await fetch(`${API_BASE}/api/settings`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(settings),
      });
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Failed to save settings: ${response.status} ${response.statusText} - ${errorText}`);
      }
      return response.json();
    } catch (error) {
      console.error('Error saving settings to:', `${API_BASE}/api/settings`, error);
      throw error;
    }
  },

  /**
   * Delete a single conversation.
   */
  async deleteConversation(conversationId) {
    const response = await fetch(`${API_BASE}/api/conversations/${conversationId}`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      throw new Error('Failed to delete conversation');
    }
    return response.json();
  },

  /**
   * Delete multiple conversations.
   */
  async deleteConversations(conversationIds) {
    const response = await fetch(`${API_BASE}/api/conversations`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ conversation_ids: conversationIds }),
    });
    if (!response.ok) {
      throw new Error('Failed to delete conversations');
    }
    return response.json();
  },
};
