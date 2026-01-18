import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { jsPDF } from 'jspdf';
import Stage1 from './Stage1';
import Stage2 from './Stage2';
import Stage3 from './Stage3';
import './ChatInterface.css';

export default function ChatInterface({
  conversation,
  onSendMessage,
  isLoading,
}) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [conversation]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim() && !isLoading) {
      onSendMessage(input);
      setInput('');
    }
  };

  const handleKeyDown = (e) => {
    // Submit on Enter (without Shift)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleExportPDF = () => {
    if (!conversation || conversation.messages.length === 0) {
      return;
    }

    const doc = new jsPDF();
    const pageWidth = doc.internal.pageSize.getWidth();
    const pageHeight = doc.internal.pageSize.getHeight();
    const margin = 20;
    const maxWidth = pageWidth - 2 * margin;
    let yPosition = margin;

    // Helper function to strip markdown and get plain text
    const stripMarkdown = (text) => {
      return text
        .replace(/#{1,6}\s+/g, '') // Remove headers
        .replace(/\*\*(.*?)\*\*/g, '$1') // Remove bold
        .replace(/\*(.*?)\*/g, '$1') // Remove italic
        .replace(/\[([^\]]+)\]\([^\)]+\)/g, '$1') // Remove links
        .replace(/`([^`]+)`/g, '$1') // Remove inline code
        .replace(/```[\s\S]*?```/g, '') // Remove code blocks
        .trim();
    };

    // Helper function to add text with word wrapping and page breaks
    const addText = (text, x, y, options = {}) => {
      const {
        maxWidth: textMaxWidth = maxWidth,
        fontSize = 10,
        fontStyle = 'normal',
        color = [0, 0, 0]
      } = options;

      if (!text || text.trim() === '') {
        return 0;
      }

      doc.setFontSize(fontSize);
      doc.setFont('helvetica', fontStyle);
      doc.setTextColor(...color);

      const lines = doc.splitTextToSize(text, textMaxWidth);
      const lineHeight = fontSize * 0.4;
      let currentY = y;

      // Process all lines, handling page breaks as needed
      for (let i = 0; i < lines.length; i++) {
        // Check if we need a new page before adding this line
        if (currentY + lineHeight > pageHeight - margin) {
          doc.addPage();
          currentY = margin;
        }

        // Add the line
        doc.text(lines[i], x, currentY);
        currentY += lineHeight;
      }

      // Update global yPosition to where we ended
      yPosition = currentY;

      // Return the total height used (approximation)
      return lines.length * lineHeight;
    };

    // Helper function to check and add a new page if needed
    const checkPageBreak = (requiredHeight) => {
      if (yPosition + requiredHeight > pageHeight - margin) {
        doc.addPage();
        yPosition = margin;
        return true;
      }
      return false;
    };

    // Title
    doc.setFontSize(18);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(51, 51, 51);
    const title = conversation.title || 'LLM Council Conversation';
    doc.text(title, margin, yPosition);
    yPosition += 10;

    // Date
    doc.setFontSize(10);
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(102, 102, 102);
    const date = new Date(conversation.created_at).toLocaleString();
    doc.text(`Created: ${date}`, margin, yPosition);
    yPosition += 15;

    // Add separator line
    doc.setDrawColor(200, 200, 200);
    doc.line(margin, yPosition, pageWidth - margin, yPosition);
    yPosition += 10;

    // Export all messages - iterate through entire conversation
    conversation.messages.forEach((msg, index) => {
      // Ensure we have space before starting a new message
      checkPageBreak(50);

      if (msg.role === 'user') {
        // User message
        yPosition += 5;
        addText(
          'YOU',
          margin,
          yPosition,
          { fontSize: 10, fontStyle: 'bold', color: [102, 102, 102] }
        );
        yPosition += 3;

        const userContent = stripMarkdown(msg.content || '');
        if (userContent) {
          addText(
            userContent,
            margin,
            yPosition,
            { fontSize: 11, color: [0, 0, 0] }
          );
        }
        yPosition += 8;
      } else if (msg.role === 'assistant') {
        // Assistant message
        yPosition += 5;
        addText(
          'LLM COUNCIL',
          margin,
          yPosition,
          { fontSize: 10, fontStyle: 'bold', color: [102, 102, 102] }
        );
        yPosition += 3;

        // Stage 3 (Final Answer) - most important
        if (msg.stage3 && msg.stage3.response) {
          addText(
            'Final Council Answer',
            margin,
            yPosition,
            { fontSize: 11, fontStyle: 'bold', color: [51, 51, 51] }
          );
          yPosition += 3;

          // Chairman info
          if (msg.stage3.model) {
            const chairmanInfo = `Chairman: ${msg.stage3.model.split('/').pop()}`;
            addText(
              chairmanInfo,
              margin,
              yPosition,
              { fontSize: 9, fontStyle: 'italic', color: [102, 102, 102] }
            );
            yPosition += 3;
          }

          const stage3Content = stripMarkdown(msg.stage3.response || '');
          if (stage3Content) {
            addText(
              stage3Content,
              margin,
              yPosition,
              { fontSize: 11, color: [0, 0, 0] }
            );
          }
          yPosition += 8;
        }
      }

      // Add separator between messages (but not after the last one)
      if (index < conversation.messages.length - 1) {
        checkPageBreak(15);
        yPosition += 5;
        doc.setDrawColor(230, 230, 230);
        doc.line(margin, yPosition, pageWidth - margin, yPosition);
        yPosition += 10;
      }
    });

    // Save PDF
    const filename = `${title.replace(/[^a-z0-9]/gi, '_').toLowerCase()}_${Date.now()}.pdf`;
    doc.save(filename);
  };

  if (!conversation) {
    return (
      <div className="chat-interface">
        <div className="empty-state">
          <h2>Welcome to LLM Council</h2>
          <p>Create a new conversation to get started</p>
        </div>
      </div>
    );
  }

  return (
    <div className="chat-interface">
      {conversation.messages.length > 0 && (
        <div className="chat-header">
          <h2 className="chat-title">{conversation.title || 'LLM Council Conversation'}</h2>
          <button
            className="export-pdf-button"
            onClick={handleExportPDF}
            title="Export conversation as PDF"
          >
            📄 Export PDF
          </button>
        </div>
      )}
      <div className="messages-container">
        {conversation.messages.length === 0 ? (
          <div className="empty-state">
            <h2>Start a conversation</h2>
            <p>Ask a question to consult the LLM Council</p>
          </div>
        ) : (
          conversation.messages.map((msg, index) => (
            <div key={index} className="message-group">
              {msg.role === 'user' ? (
                <div className="user-message">
                  <div className="message-label">You</div>
                  <div className="message-content">
                    <div className="markdown-content">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="assistant-message">
                  <div className="message-label">LLM Council</div>

                  {/* Stage 1 */}
                  {msg.loading?.stage1 && (
                    <div className="stage-loading">
                      <div className="spinner"></div>
                      <span>Running Stage 1: Collecting individual responses...</span>
                    </div>
                  )}
                  {msg.stage1 && <Stage1 responses={msg.stage1} />}

                  {/* Stage 2 */}
                  {msg.loading?.stage2 && (
                    <div className="stage-loading">
                      <div className="spinner"></div>
                      <span>Running Stage 2: Peer rankings...</span>
                    </div>
                  )}
                  {msg.stage2 && (
                    <Stage2
                      rankings={msg.stage2}
                      labelToModel={msg.metadata?.label_to_model}
                      aggregateRankings={msg.metadata?.aggregate_rankings}
                    />
                  )}

                  {/* Stage 3 */}
                  {msg.loading?.stage3 && (
                    <div className="stage-loading">
                      <div className="spinner"></div>
                      <span>Running Stage 3: Final synthesis...</span>
                    </div>
                  )}
                  {msg.stage3 && <Stage3 finalResponse={msg.stage3} />}
                </div>
              )}
            </div>
          ))
        )}

        {isLoading && (
          <div className="loading-indicator">
            <div className="spinner"></div>
            <span>Consulting the council...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <form className="input-form" onSubmit={handleSubmit}>
        <textarea
          className="message-input"
          placeholder="Ask your question... (Shift+Enter for new line, Enter to send)"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
          rows={3}
        />
        <button
          type="submit"
          className="send-button"
          disabled={!input.trim() || isLoading}
        >
          Send
        </button>
      </form>
    </div>
  );
}
