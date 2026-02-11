import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import './Stage1.css';

export default function Stage1({ responses }) {
  const [activeTab, setActiveTab] = useState(0);

  if (!responses || responses.length === 0) {
    return null;
  }

  // Formatta la risposta per visualizzazione
  const formatResponse = (resp) => {
    // Se è nel nuovo formato (agent_name, role, sentiment, etc.)
    if (resp.agent_name || resp.role) {
      const sentimentEmoji = {
        'BULLISH': '🟢',
        'BEARISH': '🔴',
        'NEUTRAL': '🟡'
      };
      
      return `## ${resp.role || 'Analyst'}

**Sentiment:** ${sentimentEmoji[resp.sentiment] || ''} ${resp.sentiment || 'NEUTRAL'}
**Confidence:** ${resp.confidence || 0}%
**Risk Score:** ${resp.risk_score || 0}/10

### Key Arguments:
${resp.key_arguments?.map(arg => `- ${arg}`).join('\n') || 'Nessun argomento fornito'}
`;
    }
    
    // Formato legacy (model, response)
    return resp.response || '';
  };

  // Ottiene il nome da mostrare
  const getDisplayName = (resp) => {
    if (resp.role) {
      return resp.role;
    }
    if (resp.agent_name) {
      return resp.agent_name.split('/').pop() || resp.agent_name;
    }
    if (resp.model) {
      return resp.model.split('/').pop() || resp.model;
    }
    return 'Unknown';
  };

  return (
    <div className="stage stage1">
      <h3 className="stage-title">Stage 1: Individual Responses</h3>

      <div className="tabs">
        {responses.map((resp, index) => (
          <button
            key={index}
            className={`tab ${activeTab === index ? 'active' : ''}`}
            onClick={() => setActiveTab(index)}
          >
            {getDisplayName(resp)}
          </button>
        ))}
      </div>

      <div className="tab-content">
        <div className="model-name">{getDisplayName(responses[activeTab])}</div>
        <div className="response-text markdown-content">
          <ReactMarkdown>{formatResponse(responses[activeTab])}</ReactMarkdown>
        </div>
      </div>
    </div>
  );
}
