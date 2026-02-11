import React from 'react';

/**
 * Estrae i ticker dal testo e li rende cliccabili.
 * Pattern: 1-5 lettere maiuscole (es. NVDA, AAPL, TSLA, BRK.B)
 */
export function extractTickers(text) {
  if (!text) return [];
  
  // Pattern per ticker: 1-5 lettere maiuscole, opzionalmente seguito da . e lettere (es. BRK.B)
  const tickerPattern = /\b([A-Z]{1,5}(?:\.[A-Z]+)?)\b/g;
  const matches = [];
  let match;
  
  while ((match = tickerPattern.exec(text)) !== null) {
    // Filtra parole comuni che potrebbero essere scambiate per ticker
    const commonWords = ['THE', 'AND', 'FOR', 'YOU', 'ARE', 'WAS', 'WERE', 'THIS', 'THAT', 'WITH', 'FROM', 'HAVE', 'HAS', 'HAD', 'WILL', 'WOULD', 'COULD', 'SHOULD', 'MAY', 'MIGHT', 'CAN', 'MUST', 'ALL', 'EACH', 'EVERY', 'SOME', 'MORE', 'MOST', 'MANY', 'MUCH', 'LITTLE', 'FEW', 'OTHER', 'ANOTHER', 'SUCH', 'ONLY', 'JUST', 'ALSO', 'EVEN', 'STILL', 'YET', 'ALREADY', 'AGAIN', 'ONCE', 'TWICE', 'THREE', 'FOUR', 'FIVE', 'SIX', 'SEVEN', 'EIGHT', 'NINE', 'TEN', 'HUNDRED', 'THOUSAND', 'MILLION', 'BILLION', 'ABOUT', 'AFTER', 'BEFORE', 'DURING', 'UNTIL', 'WHILE', 'SINCE', 'BECAUSE', 'ALTHOUGH', 'THOUGH', 'DESPITE', 'HOWEVER', 'THEREFORE', 'THUS', 'HENCE', 'MOREOVER', 'FURTHERMORE', 'NEVERTHELESS', 'NONETHELESS', 'MEANWHILE', 'FINALLY', 'INDEED', 'CERTAINLY', 'PROBABLY', 'POSSIBLY', 'PERHAPS', 'MAYBE', 'ACTUALLY', 'REALLY', 'QUITE', 'VERY', 'TOO', 'SO', 'AS', 'THAN', 'THEN', 'THERE', 'THEIR', 'THEY', 'THEM', 'THESE', 'THOSE', 'WHICH', 'WHOSE', 'WHERE', 'WHEN', 'WHAT', 'WHO', 'WHOM', 'WHY', 'HOW', 'WHETHER', 'IF', 'UNLESS', 'UNTIL', 'WHILE', 'WHEREAS', 'WHEREVER', 'WHENEVER', 'WHATEVER', 'WHOEVER', 'WHICHEVER', 'HOWEVER', 'WHY', 'WHEN', 'WHERE', 'WHAT', 'WHO', 'WHOM', 'WHOSE', 'WHICH', 'THAT', 'THIS', 'THESE', 'THOSE', 'HERE', 'THERE', 'WHERE', 'WHEN', 'WHY', 'HOW', 'WHETHER', 'IF', 'UNLESS', 'UNTIL', 'WHILE', 'WHEREAS', 'WHEREVER', 'WHENEVER', 'WHATEVER', 'WHOEVER', 'WHICHEVER', 'HOWEVER'];
    
    const ticker = match[1];
    if (!commonWords.includes(ticker) && ticker.length >= 1 && ticker.length <= 5) {
      matches.push({
        ticker,
        index: match.index,
        length: match[0].length
      });
    }
  }
  
  return matches;
}

/**
 * Componente che rende il testo con i ticker cliccabili
 */
export function TickerText({ text, onTickerClick }) {
  if (!text) return null;
  
  const tickers = extractTickers(text);
  
  if (tickers.length === 0) {
    return <span>{text}</span>;
  }
  
  // Crea un array di parti (testo normale e ticker)
  const parts = [];
  let lastIndex = 0;
  
  tickers.forEach(({ ticker, index, length }) => {
    // Aggiungi il testo prima del ticker
    if (index > lastIndex) {
      parts.push({
        type: 'text',
        content: text.substring(lastIndex, index)
      });
    }
    
    // Aggiungi il ticker cliccabile
    parts.push({
      type: 'ticker',
      content: ticker,
      ticker: ticker
    });
    
    lastIndex = index + length;
  });
  
  // Aggiungi il testo rimanente
  if (lastIndex < text.length) {
    parts.push({
      type: 'text',
      content: text.substring(lastIndex)
    });
  }
  
  return (
    <span>
      {parts.map((part, i) => {
        if (part.type === 'ticker') {
          return (
            <button
              key={i}
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                onTickerClick(part.ticker);
              }}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#3b82f6',
                textDecoration: 'underline',
                cursor: 'pointer',
                padding: '0 2px',
                fontFamily: 'inherit',
                fontSize: 'inherit',
                fontWeight: 'bold'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.color = '#2563eb';
                e.currentTarget.style.backgroundColor = 'rgba(59, 130, 246, 0.1)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.color = '#3b82f6';
                e.currentTarget.style.backgroundColor = 'transparent';
              }}
            >
              {part.content}
            </button>
          );
        }
        return <span key={i}>{part.content}</span>;
      })}
    </span>
  );
}
