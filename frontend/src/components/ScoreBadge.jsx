import React from 'react';
import { Icon } from './Icons';

export default function ScoreBadge({ score = 0, classification = 'pending' }) {
  let styleClass = 'score-low';
  let label = 'Regular';

  if (score >= 85) {
    styleClass = 'score-excellent';
    label = 'Excelente';
  } else if (score >= 70) {
    styleClass = 'score-good';
    label = 'Muito Bom';
  } else if (score >= 50) {
    styleClass = 'score-moderate';
    label = 'Moderado';
  }

  return (
    <div className={`score-badge ${styleClass}`} title={`Score de Oportunidade: ${score}/100 (${label})`}>
      <Icon name="zap" size={13} />
      <span className="score-num">{score}</span>
      <span className="score-label">{label}</span>
    </div>
  );
}
