import React, { useEffect, useState } from 'react';

const StatusIndicator = ({ currentStreamedText, loadingState }) => {
  const [status, setStatus] = useState({ 
    text: "Inizializzazione connessione sicura...", 
    icon: "🔄", 
    color: "#9ca3af" 
  });

  useEffect(() => {
    // LOGICA DI RILEVAMENTO DELLO STATO
    // Se abbiamo uno stato di loading specifico, usiamo quello
    if (loadingState) {
      if (loadingState.stage1) {
        setStatus({ 
          text: "Il Consiglio si sta riunendo...", 
          icon: "👥", 
          color: "#9ca3af" 
        });
        return;
      }
      if (loadingState.stage2) {
        setStatus({ 
          text: "Valutazione delle risposte e ranking...", 
          icon: "📋", 
          color: "#6366f1" 
        });
        return;
      }
      if (loadingState.stage3) {
        // Se abbiamo già del testo, analizziamolo
        if (currentStreamedText && currentStreamedText.length > 10) {
          // Continua con l'analisi del testo
        } else {
          setStatus({ 
            text: "Il Chairman sta formulando la sintesi finale...", 
            icon: "⚖️", 
            color: "#d4af37" 
          });
          return;
        }
      }
    }

    // Se non abbiamo ancora testo, siamo nella fase di backend (download dati)
    if (!currentStreamedText || currentStreamedText.length < 10) {
      setStatus({ 
        text: "Scaricamento dati di mercato e news in tempo reale...", 
        icon: "📡", 
        color: "#3b82f6" 
      });
      return;
    }

    const text = currentStreamedText.toUpperCase();

    // Ordine inverso di priorità (l'ultimo trovato vince)
    if (text.includes("## BOGLEHEAD") || text.includes("BOGLEHEAD")) {
      setStatus({ 
        text: "Il Boglehead sta analizzando l'efficienza e i costi...", 
        icon: "🛡️", 
        color: "#10b981" 
      });
    } else if (text.includes("## QUANT") || text.includes("QUANT")) {
      setStatus({ 
        text: "Il Quant sta calcolando le valutazioni e i ratio...", 
        icon: "📊", 
        color: "#3b82f6" 
      });
    } else if (text.includes("## MACRO") || text.includes("MACRO") || text.includes("STRATEGIST")) {
      setStatus({ 
        text: "Il Macro Strategist sta valutando lo scenario globale...", 
        icon: "🌍", 
        color: "#8b5cf6" 
      });
    } else if (text.includes("## RISK") || text.includes("CRO")) {
      setStatus({ 
        text: "Il Risk Manager sta cercando falle nel piano...", 
        icon: "⚠️", 
        color: "#ef4444" 
      });
    } else if (text.includes("## CHAIRMAN") || text.includes("CHAIRMAN") || text.includes("DELIBERA") || text.includes("SINTESI FINALE") || text.includes("FINAL SYNTHESIS")) {
      setStatus({ 
        text: "Il Chairman sta formulando la sintesi finale...", 
        icon: "⚖️", 
        color: "#d4af37" 
      });
    } else {
      // Fase generica iniziale (Stage 1 prima che parli qualcuno)
      setStatus({ 
        text: "Il Consiglio si sta riunendo...", 
        icon: "👥", 
        color: "#9ca3af" 
      });
    }

  }, [currentStreamedText, loadingState]);

  return (
    <div 
      className="status-indicator"
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        padding: '12px 16px',
        background: 'rgba(17, 24, 39, 0.5)',
        borderRadius: '8px',
        border: '1px solid rgba(107, 114, 128, 0.3)',
        backdropFilter: 'blur(8px)',
        margin: '8px 0',
        animation: 'fade-in 0.3s ease-out'
      }}
    >
      <span 
        className="status-icon"
        style={{ 
          fontSize: '1.5rem',
          display: 'inline-block',
          animation: 'spin-slow 3s linear infinite'
        }}
      >
        {status.icon}
      </span>
      <span 
        style={{ 
          fontSize: '0.875rem',
          fontWeight: '500',
          letterSpacing: '0.025em',
          color: status.color
        }}
      >
        {status.text}
      </span>
    </div>
  );
};

export default StatusIndicator;
