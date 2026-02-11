import React, { useEffect, useState } from 'react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { API_BASE } from '../api';

const StockChart = ({ ticker }) => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!ticker) return;

    setLoading(true);
    setError(null);
    console.log(`📉 Richiedo grafico per: ${ticker}`);

    fetch(`${API_BASE}/api/market-history/${ticker}`)
      .then(res => {
        if (!res.ok) throw new Error("Errore chiamata API");
        return res.json();
      })
      .then(fetchedData => {
        console.log("📈 Dati ricevuti:", fetchedData.length, "punti");
        if (fetchedData.length === 0) setError("Nessun dato storico trovato.");
        setData(fetchedData);
        setLoading(false);
      })
      .catch(err => {
        console.error("Errore fetch grafico:", err);
        setError("Impossibile caricare il grafico.");
        setLoading(false);
      });
  }, [ticker]);

  // Gestione Stati
  if (!ticker) {
    return (
      <div style={{ padding: '16px', color: '#6b7280', fontSize: '14px' }}>
        Seleziona un titolo per vedere il grafico.
      </div>
    );
  }
  if (loading) {
    return (
      <div style={{ padding: '16px', color: '#60a5fa', fontSize: '14px' }}>
        Caricamento dati di mercato...
      </div>
    );
  }
  if (error) {
    return (
      <div style={{ padding: '16px', color: '#ef4444', fontSize: '14px' }}>
        ⚠️ {error}
      </div>
    );
  }
  if (data.length === 0) {
    return (
      <div style={{ padding: '16px', color: '#6b7280', fontSize: '14px' }}>
        Nessun dato disponibile.
      </div>
    );
  }

  return (
    <div style={{
      width: '100%',
      backgroundColor: 'rgba(17, 24, 39, 0.5)',
      borderRadius: '8px',
      padding: '16px',
      border: '1px solid #374151',
      boxShadow: 'inset 0 2px 4px rgba(0, 0, 0, 0.1)'
    }}>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '16px'
      }}>
        <h3 style={{
          fontSize: '14px',
          fontWeight: 'bold',
          color: '#d1d5db'
        }}>
          ANDAMENTO {ticker} <span style={{ fontSize: '12px', fontWeight: 'normal', color: '#6b7280' }}>(1 Anno)</span>
        </h3>
        <span style={{
          fontSize: '12px',
          color: '#10b981',
          fontFamily: 'monospace'
        }}>
          Ultimo: ${data[data.length - 1]?.price?.toFixed(2)}
        </span>
      </div>

      {/* IMPORTANTE: L'altezza deve essere esplicita per Recharts */}
      <div style={{ height: '256px', width: '100%' }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data}>
            <defs>
              <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" vertical={false} />
            <XAxis 
              dataKey="date" 
              hide={true}
            />
            <YAxis 
              domain={['auto', 'auto']}
              orientation="right" 
              tick={{fill: '#9ca3af', fontSize: 10}}
              tickFormatter={(val) => `$${val.toFixed(0)}`}
              width={40}
            />
            <Tooltip 
              contentStyle={{
                backgroundColor: '#1f2937',
                borderColor: '#374151',
                borderRadius: '8px',
                color: '#fff'
              }}
              itemStyle={{color: '#60a5fa'}}
              labelStyle={{color: '#9ca3af', marginBottom: '0.5rem'}}
              formatter={(value) => [`$${value.toFixed(2)}`, 'Prezzo']}
            />
            <Area 
              type="monotone" 
              dataKey="price" 
              stroke="#3b82f6" 
              strokeWidth={2}
              fillOpacity={1} 
              fill="url(#colorPrice)" 
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default StockChart;
