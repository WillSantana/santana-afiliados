import React, { useState, useMemo } from 'react';
import ProductCard from '../components/ProductCard';
import AffiliateLinkModal from '../components/AffiliateLinkModal';
import PublicationPreviewModal from '../components/PublicationPreviewModal';
import RejectModal from '../components/RejectModal';
import { useToast } from '../components/Toast';
import { Icon } from '../components/Icons';

export default function CatalogPage({
  products,
  loading,
  filters,
  setFilters,
  onApprove,
  onReject,
  onAssociateAffiliateLink,
  onReload,
}) {
  const { addToast } = useToast();
  const [selectedProductForAffiliate, setSelectedProductForAffiliate] = useState(null);
  const [selectedProductForPreview, setSelectedProductForPreview] = useState(null);
  const [selectedProductForReject, setSelectedProductForReject] = useState(null);
  const [searchTerm, setSearchTerm] = useState(filters.search || '');
  const [sortBy, setSortBy] = useState('score_desc');

  // Categorias
  const categories = [
    { id: '', label: 'Todas as Categorias' },
    { id: 'technology', label: 'Tecnologia' },
    { id: 'fashion', label: 'Moda' },
    { id: 'home', label: 'Casa' },
    { id: 'beauty', label: 'Beleza' },
  ];

  // Métricas do Topo
  const stats = useMemo(() => {
    const total = products.length;
    const pending = products.filter((p) => p.status === 'pending').length;
    const approved = products.filter((p) => p.status === 'approved').length;
    const published = products.filter((p) => p.status === 'published').length;

    let maxDiscount = 0;
    products.forEach((p) => {
      const disc = p.discount_percentage || 0;
      if (disc > maxDiscount) maxDiscount = disc;
    });

    return { total, pending, approved, published, maxDiscount };
  }, [products]);

  // Status Filter Tabs
  const statusTabs = [
    { id: '', label: 'Todas', count: stats.total },
    { id: 'pending', label: 'Pendentes', count: stats.pending, alert: stats.pending > 0 },
    { id: 'approved', label: 'Aprovadas', count: stats.approved },
    { id: 'published', label: 'Publicadas', count: stats.published },
    { id: 'rejected', label: 'Rejeitadas', count: products.filter((p) => p.status === 'rejected').length },
  ];

  // Tratamento de Busca
  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setFilters({ ...filters, search: searchTerm.trim() || undefined });
  };

  const handleClearSearch = () => {
    setSearchTerm('');
    setFilters({ ...filters, search: undefined });
  };

  // Aprovação com feedback moderno
  const handleApprove = async (id) => {
    try {
      await onApprove(id);
      addToast('Oferta aprovada com sucesso!', 'success');
    } catch (err) {
      addToast(`Erro ao aprovar: ${err.message}`, 'error');
    }
  };

  // Rejeição
  const handleRejectConfirm = async (id, reason) => {
    try {
      await onReject(id, reason);
      addToast('Oferta rejeitada e arquivada.', 'info');
    } catch (err) {
      addToast(`Erro ao rejeitar: ${err.message}`, 'error');
    }
  };

  // Salvar Link Afiliado
  const handleSaveAffiliate = async (id, url) => {
    try {
      await onAssociateAffiliateLink(id, url);
      addToast('Link oficial de afiliado vinculado!', 'success');
    } catch (err) {
      addToast(`Erro ao vincular link: ${err.message}`, 'error');
    }
  };

  // Ordenação dos produtos
  const sortedProducts = useMemo(() => {
    const list = [...products];
    if (sortBy === 'score_desc') {
      return list.sort((a, b) => (b.score || 0) - (a.score || 0));
    }
    if (sortBy === 'price_asc') {
      return list.sort((a, b) => Number(a.price) - Number(b.price));
    }
    if (sortBy === 'price_desc') {
      return list.sort((a, b) => Number(b.price) - Number(a.price));
    }
    if (sortBy === 'discount_desc') {
      return list.sort((a, b) => (b.discount_percentage || 0) - (a.discount_percentage || 0));
    }
    return list;
  }, [products, sortBy]);

  return (
    <div className="catalog-wrapper">
      {/* KPI Stats Bar */}
      <div className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-icon-wrap blue">
            <Icon name="catalog" size={22} />
          </div>
          <div className="kpi-info">
            <span className="kpi-label">Total Prospectado</span>
            <span className="kpi-value">{stats.total}</span>
          </div>
        </div>

        <div className="kpi-card highlight-amber">
          <div className="kpi-icon-wrap amber">
            <Icon name="clock" size={22} />
          </div>
          <div className="kpi-info">
            <span className="kpi-label">Revisão Pendente</span>
            <span className="kpi-value">{stats.pending}</span>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-icon-wrap emerald">
            <Icon name="check" size={22} />
          </div>
          <div className="kpi-info">
            <span className="kpi-label">Ofertas Aprovadas</span>
            <span className="kpi-value">{stats.approved}</span>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-icon-wrap purple">
            <Icon name="trendingUp" size={22} />
          </div>
          <div className="kpi-info">
            <span className="kpi-label">Maior Desconto</span>
            <span className="kpi-value">{stats.maxDiscount > 0 ? `${stats.maxDiscount}% OFF` : 'Até 30%'}</span>
          </div>
        </div>
      </div>

      {/* Modern Filter Toolbar */}
      <div className="modern-toolbar">
        {/* Status Filter Tabs */}
        <div className="status-tabs-container">
          {statusTabs.map((tab) => {
            const isActive = (filters.status || '') === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                className={`status-tab-btn ${isActive ? 'active' : ''}`}
                onClick={() => setFilters({ ...filters, status: tab.id })}
              >
                <span>{tab.label}</span>
                <span className={`status-counter ${isActive ? 'active' : ''} ${tab.alert ? 'alert' : ''}`}>
                  {tab.count}
                </span>
              </button>
            );
          })}
        </div>

        {/* Search & Select Row */}
        <div className="toolbar-controls-row">
          <form onSubmit={handleSearchSubmit} className="search-box-form">
            <span className="search-box-icon">
              <Icon name="search" size={16} />
            </span>
            <input
              type="text"
              className="search-box-input"
              placeholder="Buscar título ou MLB ID..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
            {searchTerm && (
              <button type="button" className="search-box-clear" onClick={handleClearSearch}>
                <Icon name="x" size={14} />
              </button>
            )}
          </form>

          <div className="dropdowns-group">
            {/* Category Dropdown */}
            <div className="select-wrapper">
              <select
                className="modern-select"
                value={filters.category || ''}
                onChange={(e) => setFilters({ ...filters, category: e.target.value })}
              >
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>{c.label}</option>
                ))}
              </select>
            </div>

            {/* Sort Dropdown */}
            <div className="select-wrapper">
              <select
                className="modern-select"
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
              >
                <option value="score_desc">⚡ Maior Score</option>
                <option value="discount_desc">🏷️ Maior Desconto</option>
                <option value="price_asc">💵 Menor Preço</option>
                <option value="price_desc">💎 Maior Preço</option>
              </select>
            </div>

            {/* Refresh Button */}
            <button
              type="button"
              className="btn-refresh"
              onClick={onReload}
              title="Atualizar catálogo"
            >
              <Icon name="refresh" size={16} className={loading ? 'spin' : ''} />
            </button>
          </div>
        </div>
      </div>

      {/* Catalog Grid Area */}
      {loading ? (
        <div className="catalog-loading-state">
          <div className="loading-spinner"></div>
          <p>Carregando ofertas do catálogo oficial...</p>
        </div>
      ) : sortedProducts.length === 0 ? (
        <div className="catalog-empty-state">
          <div className="empty-icon-circle">
            <Icon name="search" size={32} />
          </div>
          <h3>Nenhuma oferta encontrada</h3>
          <p>Tente ajustar os filtros de categoria e status ou faça uma nova busca no Mercado Livre.</p>
          <button
            type="button"
            className="btn-secondary"
            onClick={() => {
              setSearchTerm('');
              setFilters({});
            }}
          >
            Limpar Todos os Filtros
          </button>
        </div>
      ) : (
        <div className="catalog-cards-grid">
          {sortedProducts.map((product) => (
            <ProductCard
              key={product.id}
              product={product}
              onApprove={handleApprove}
              onOpenRejectModal={(p) => setSelectedProductForReject(p)}
              onOpenAffiliateModal={(p) => setSelectedProductForAffiliate(p)}
              onOpenPreviewModal={(p) => setSelectedProductForPreview(p)}
            />
          ))}
        </div>
      )}

      {/* Modals */}
      {selectedProductForAffiliate && (
        <AffiliateLinkModal
          product={selectedProductForAffiliate}
          onClose={() => setSelectedProductForAffiliate(null)}
          onSave={handleSaveAffiliate}
        />
      )}

      {selectedProductForPreview && (
        <PublicationPreviewModal
          product={selectedProductForPreview}
          onClose={() => setSelectedProductForPreview(null)}
          onPublished={onReload}
        />
      )}

      {selectedProductForReject && (
        <RejectModal
          product={selectedProductForReject}
          onClose={() => setSelectedProductForReject(null)}
          onConfirm={handleRejectConfirm}
        />
      )}
    </div>
  );
}
