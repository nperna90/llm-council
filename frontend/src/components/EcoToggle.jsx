import React from 'react';
import './EcoToggle.css';

const LeafIcon = ({ className }) => (
  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.77 10-10 10Z"/>
    <path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"/>
  </svg>
);

const EcoToggle = ({ isEnabled, onToggle }) => {
  return (
    <div className="eco-toggle-container">
      <div className="eco-toggle-label">
        <LeafIcon 
          className={`eco-toggle-icon ${isEnabled ? 'enabled' : 'disabled'}`}
        />
        <span className={`eco-toggle-text ${isEnabled ? 'enabled' : 'disabled'}`}>
          Eco Mode
        </span>
      </div>
      
      <button 
        onClick={() => onToggle(!isEnabled)}
        className={`eco-toggle-switch ${isEnabled ? 'enabled' : 'disabled'}`}
        title="Risparmia token: usa solo gli Specialisti (Quant, Risk, Macro)"
      >
        <span
          className={`eco-toggle-slider ${isEnabled ? 'enabled' : 'disabled'}`}
        />
      </button>
    </div>
  );
};

export default EcoToggle;
