import React, { useState } from 'react';
import { Icon } from './Icons';

export default function RejectModal({ product, onClose, onConfirm }) {
  const [reason, setReason] = useState('');
  const [selectedQuickReason, setSelectedQuickReason] = useState('');

  if (!product) return null;

  const quickReasons = [
    'Preço acima do teto preferencial (R$ 200)',
    'Margem de desconto insuficiente',
    'Reputação ou histórico do vendedor duvidoso',
    'Produto fora do perfil do público',
    'Oferta duplicada no catálogo',
  ];

  const handleSelectQuick = (r) => {
    setSelectedQuickReason(r);
    setReason(r);
  };

  const handleConfirm = () => {
    onConfirm(product.id, reason.trim() || 'Rejeitado na triagem manual');
    onClose();
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content modern-card" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '480px' }}>
        <div className="modal-header">
          <div className="modal-title-wrap">
            <span className="modal-icon-badge danger">
              <Icon name="x" size={20} />
            </span>
            <div>
              <h3>Rejeitar Oferta</h3>
              <p className="modal-subtitle">Esta oferta será desativada e não irá para o canal.</p>
            </div>
          </div>
          <button className="modal-close-btn" onClick={onClose}>
            <Icon name="x" size={18} />
          </button>
        </div>

        <div className="modal-body">
          <div className="product-summary-box">
            <img src={product.thumbnail} alt="" className="product-summary-thumb" />
            <div className="product-summary-info">
              <div className="product-summary-title">{product.title}</div>
              <div className="product-summary-price">R$ {Number(product.price).toFixed(2)}</div>
            </div>
          </div>

          <label className="input-label" style={{ marginTop: '1rem' }}>
            Selecione uma justificativa rápida:
          </label>
          <div className="quick-tags-container">
            {quickReasons.map((r, i) => (
              <button
                key={i}
                type="button"
                className={`quick-tag ${selectedQuickReason === r ? 'active' : ''}`}
                onClick={() => handleSelectQuick(r)}
              >
                {r}
              </button>
            ))}
          </div>

          <label className="input-label" style={{ marginTop: '1rem' }}>
            Ou personalize a justificativa:
          </label>
          <textarea
            className="modern-input"
            rows="3"
            placeholder="Descreva o motivo da rejeição..."
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
        </div>

        <div className="modal-footer">
          <button type="button" className="btn-secondary" onClick={onClose}>
            Cancelar
          </button>
          <button type="button" className="btn-danger" onClick={handleConfirm}>
            <Icon name="x" size={16} />
            Confirmar Rejeição
          </button>
        </div>
      </div>
    </div>
  );
}
