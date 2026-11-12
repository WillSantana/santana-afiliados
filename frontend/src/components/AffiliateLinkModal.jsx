import React, { useState } from 'react';
import { Icon } from './Icons';
import { getMercadoLivreItemUrl } from '../utils/mercadoLivre';

export default function AffiliateLinkModal({ product, onClose, onSave }) {
  const [url, setUrl] = useState(product?.affiliate_url || '');
  const [submitting, setSubmitting] = useState(false);

  if (!product) return null;

  const safeMLUrl = getMercadoLivreItemUrl(product);

  const handlePaste = async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text) setUrl(text.trim());
    } catch {
      // Fallback if clipboard permission is denied
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!url.trim()) return;
    setSubmitting(true);
    await onSave(product.id, url.trim());
    setSubmitting(false);
    onClose();
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content modern-card" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '520px' }}>
        <div className="modal-header">
          <div className="modal-title-wrap">
            <span className="modal-icon-badge primary">
              <Icon name="link" size={20} />
            </span>
            <div>
              <h3>Link Oficial de Afiliado</h3>
              <p className="modal-subtitle">Gere o link no portal oficial do Mercado Livre Afiliados.</p>
            </div>
          </div>
          <button className="modal-close-btn" onClick={onClose}>
            <Icon name="x" size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            <div className="product-summary-box">
              <img src={product.thumbnail} alt="" className="product-summary-thumb" />
              <div className="product-summary-info">
                <div className="product-summary-title">{product.title}</div>
                <div className="product-summary-meta">
                  MLB ID: {product.item_id} • R$ {Number(product.price).toFixed(2)}
                  <span style={{ margin: '0 6px', opacity: 0.5 }}>•</span>
                  {safeMLUrl ? (
                    <a
                      href={safeMLUrl}
                      target="_blank"
                      rel="noreferrer"
                      style={{ color: '#3b82f6', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '3px', fontWeight: 500 }}
                      title="Abrir o anúncio original no Mercado Livre para gerar seu link de afiliado"
                    >
                      <Icon name="external" size={12} />
                      Ver no ML
                    </a>
                  ) : (
                    <span title="Este registro não tem um link de anúncio válido. Faça uma nova busca no Mercado Livre.">
                      Anúncio original indisponível
                    </span>
                  )}
                </div>
              </div>
            </div>

            <div style={{ marginTop: '1.25rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
                <label className="input-label" style={{ margin: 0 }}>
                  URL de Afiliado (Ex: https://mercadolivre.com/sec/...)
                </label>
                <button type="button" className="btn-text-action" onClick={handlePaste}>
                  <Icon name="copy" size={13} />
                  Colar do Clipboard
                </button>
              </div>
              <input
                type="url"
                required
                className="modern-input"
                placeholder="Cole o link rastreado aqui..."
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                autoFocus
              />
              <span className="input-help-text">
                ✓ Mantém a URL original e o rastreamento em conformidade estrita com o programa de afiliados.
              </span>
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" className="btn-secondary" onClick={onClose}>
              Cancelar
            </button>
            <button type="submit" className="btn-primary" disabled={submitting || !url.trim()}>
              <Icon name="check" size={16} />
              {submitting ? 'Salvando...' : 'Salvar Link'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
