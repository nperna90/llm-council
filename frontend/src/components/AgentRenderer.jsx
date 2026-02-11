import React from 'react';
import ReactMarkdown from 'react-markdown';

// Mappa delle identità
const AGENTS = {
  BOGLEHEAD: { 
    color: '#10b981', 
    colorClass: 'text-emerald-400',
    border: 'agent-boglehead', 
    icon: '🛡️',
    name: 'Boglehead'
  },
  QUANT: { 
    color: '#3b82f6', 
    colorClass: 'text-blue-400',
    border: 'agent-quant', 
    icon: '📊',
    name: 'Quant'
  },
  MACRO: { 
    color: '#8b5cf6', 
    colorClass: 'text-purple-400',
    border: 'agent-macro', 
    icon: '🌍',
    name: 'Macro Strategist'
  },
  RISK: { 
    color: '#ef4444', 
    colorClass: 'text-red-500',
    border: 'agent-risk', 
    icon: '⚠️',
    name: 'Risk Manager'
  },
  CHAIRMAN: { 
    color: '#d4af37', 
    colorClass: 'text-yellow-500',
    border: 'agent-chairman', 
    icon: '⚖️',
    name: 'Chairman'
  },
  DEFAULT: { 
    color: '#9ca3af', 
    colorClass: 'text-gray-300',
    border: '', 
    icon: '🤖',
    name: 'Council'
  }
};

const AgentRenderer = ({ content }) => {
  if (!content) return null;

  // 1. Dividiamo il messaggio in base ai titoli degli agenti (## NOME)
  // Questa regex cerca "## " seguito dal nome e cattura il contenuto fino al prossimo "##"
  const sections = content.split(/(?=## )/g);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      {sections.map((section, index) => {
        // Pulizia
        const text = section.trim();
        if (!text) return null;

        // Identifichiamo chi sta parlando
        let agentType = 'DEFAULT';
        let cleanText = text;
        const upperText = text.toUpperCase();

        if (upperText.includes('BOGLEHEAD') || upperText.includes('BOGLE')) {
          agentType = 'BOGLEHEAD';
        } else if (upperText.includes('QUANT') || upperText.includes('QUANTITATIVE')) {
          agentType = 'QUANT';
        } else if (upperText.includes('MACRO') || upperText.includes('STRATEGIST') || upperText.includes('GLOBAL')) {
          agentType = 'MACRO';
        } else if (upperText.includes('RISK') || upperText.includes('CRO')) {
          agentType = 'RISK';
        } else if (upperText.includes('CHAIRMAN') || upperText.includes('DELIBERA') || upperText.includes('SINTESI FINALE') || upperText.includes('FINAL SYNTHESIS')) {
          agentType = 'CHAIRMAN';
        }

        const style = AGENTS[agentType];

        // Se è un blocco Agente, lo renderizziamo con lo stile speciale
        if (agentType !== 'DEFAULT') {
          // Estraiamo il titolo (prima riga)
          const lines = text.split('\n');
          const titleLine = lines[0].replace(/#/g, '').trim();
          const bodyText = lines.slice(1).join('\n').trim();

          return (
            <div 
              key={index} 
              className={`agent-card ${style.border} animate-fade-in`}
              style={{ 
                marginBottom: '1rem',
                padding: '1rem',
                borderRadius: '0 8px 8px 0'
              }}
            >
              <div 
                style={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  gap: '0.5rem', 
                  marginBottom: '0.75rem',
                  fontWeight: '600',
                  color: style.color
                }}
              >
                <span style={{ fontSize: '1.25rem' }}>{style.icon}</span>
                <span>{titleLine || style.name}</span>
              </div>
              {bodyText && (
                <div 
                  className="agent-content"
                  style={{ 
                    paddingLeft: '2rem',
                    color: agentType === 'CHAIRMAN' ? '#000000' : '#111827',
                    fontSize: '0.875rem',
                    lineHeight: '1.75'
                  }}
                >
                  <ReactMarkdown>{bodyText}</ReactMarkdown>
                </div>
              )}
            </div>
          );
        }

        // Testo normale (es. introduzione o user)
        return (
          <div 
            key={index} 
            style={{ color: '#9ca3af', lineHeight: '1.75' }}
          >
            <ReactMarkdown>{text}</ReactMarkdown>
          </div>
        );
      })}
    </div>
  );
};

export default AgentRenderer;
