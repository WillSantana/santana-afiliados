import React, { useState } from 'react';
import { api } from '../services/api';
import { Icon } from './Icons';

export default function SearchModal({ onClose, onSearchCompleted }) {
  const [category, setCategory] = useState('technology');
  const [query, setQuery] = useState('');
  const [limit, setLimit] = useState(20);
  const [loading, setLoading] = useState(false);
  const [resultMessage, setResultMessage] = useState(null);

  const categories = [
    { id: 'technology', label: 'Tecnologia & Games', icon: 'zap' },
    { id: 'fashion', label: 'Moda Masculina', icon: 'tag' },
    { id: 'home', label: 'Casa & Utilidades', icon: 'catalog' },
    { id: 'beauty', label: 'Beleza & Cuidados', icon: 'star' },
  ];

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setResultMessage(null);
    try {
      const res = await api.runSearch({
        category,
        query: query.trim() || undefined,
        limit: Number(limit),
      });
      setResultMessage({
        type: 'success',
        text: res.message || 'Busca concluída e catálogo atualizado!',
      });
      setTimeout(() => {
        if (onSearchCompleted) onSearchCompleted();
        onClose();
      }, 1200);
    } catch (err) {
      setResultMessage({
        type: 'error',
        text: `Erro na busca: ${err.message}`,
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content modern-card" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '560px' }}>
        <div className="modal-header">
          <div className="modal-title-wrap">
            <span className="modal-icon-badge primary">
              <Icon name="search" size={20} />
            </span>
            <div>
              <h3>Buscar no Mercado Livre</h3>
              <p className="modal-subtitle">Busca anúncios reais. Requer token OAuth do Mercado Livre configurado no backend.</p>
            </div>
          </div>
          <button className="modal-close-btn" onClick={onClose}>
            <Icon name="x" size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {/* Category Cards */}
            <label className="input-label">Selecione o Nicho / Categoria</label>
            <div className="category-selection-grid">
              {categories.map((c) => (
                <div
                  key={c.id}
                  className={`category-select-card ${category === c.id ? 'active' : ''}`}
                  onClick={() => setCategory(c.id)}
                >
                  <Icon name={c.icon} size={18} />
                  <span>{c.label}</span>
                </div>
              ))}
            </div>

            {/* Query */}
            <div style={{ marginTop: '1.25rem' }}>
              <label className="input-label">Termo de Pesquisa (Opcional)</label>
              <div className="search-input-wrapper">
                <span className="search-icon-affix">
                  <Icon name="search" size={16} />
                </span>
                <input
                  type="text"
                  className="modern-input has-affix"
                  placeholder="Ex: controle sem fio, fone bluetooth, tenis..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                />
              </div>
            </div>

            {/* Limit Slider */}
            <div style={{ marginTop: '1.25rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
                <label className="input-label" style={{ margin: 0 }}>Quantidade de Ofertas</label>
                <span className="badge-value-highlight">{limit} anúncios</span>
              </div>
              <input
                type="range"
                min="5"
                max="50"
                step="5"
                value={limit}
                onChange={(e) => setLimit(e.target.value)}
                style={{ width: '100%', accentColor: 'var(--primary)' }}
              />
            </div>

            {resultMessage && (
              <div className={`status-banner-box ${resultMessage.type}`} style={{ marginTop: '1.25rem' }}>
                <Icon name={resultMessage.type === 'success' ? 'check' : 'x'} size={18} />
                <span>{resultMessage.text}</span>
              </div>
            )}
          </div>

          <div className="modal-footer">
            <button type="button" className="btn-secondary" onClick={onClose} disabled={loading}>
              Cancelar
            </button>
            <button type="submit" className="btn-primary" disabled={loading}>
              <Icon name={loading ? 'refresh' : 'search'} size={16} className={loading ? 'spin' : ''} />
              {loading ? 'Consultando Mercado Livre...' : 'Executar Busca'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
