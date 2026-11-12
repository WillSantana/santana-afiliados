import React from 'react';

export default function MetricCard({ title, value, subtitle, icon, highlight = false }) {
  return (
    <div className={`kpi-card ${highlight ? 'highlight-amber' : ''}`}>
      <div className={`kpi-icon-wrap ${highlight ? 'amber' : 'blue'}`}>
        <span style={{ fontSize: '1.25rem' }}>{icon}</span>
      </div>
      <div className="kpi-info">
        <span className="kpi-label">{title}</span>
        <span className="kpi-value">{value}</span>
        {subtitle && (
          <span style={{ fontSize: '0.75rem', color: 'var(--slate-500)', marginTop: '0.15rem' }}>
            {subtitle}
          </span>
        )}
      </div>
    </div>
  );
}
