import React from 'react';
import './TutorToggle.css';

// Icona semplice SVG (puoi sostituirla con lucide-react se l'hai installata)
const GraduationCap = ({ className }) => (
  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="M22 10v6M2 10l10-5 10 5-10 5z"/>
    <path d="M6 12v5c3 3 9 3 12 0v-5"/>
  </svg>
);

const TutorToggle = ({ isEnabled, onToggle }) => {
  return (
    <div className="tutor-toggle-container">
      <div className="tutor-toggle-label">
        <GraduationCap 
          className={`tutor-toggle-icon ${isEnabled ? 'enabled' : 'disabled'}`}
        />
        <span className={`tutor-toggle-text ${isEnabled ? 'enabled' : 'disabled'}`}>
          Tutor Mode
        </span>
      </div>
      
      <button 
        onClick={() => onToggle(!isEnabled)}
        className={`tutor-toggle-switch ${isEnabled ? 'enabled' : 'disabled'}`}
        title="Attiva spiegazioni semplici per principianti"
      >
        <span
          className={`tutor-toggle-slider ${isEnabled ? 'enabled' : 'disabled'}`}
        />
      </button>
    </div>
  );
};

export default TutorToggle;
