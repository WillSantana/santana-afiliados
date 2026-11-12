import React, { useState } from 'react';
import ScoreBadge from './ScoreBadge';
import { Icon } from './Icons';
import { getMercadoLivreItemUrl } from '../utils/mercadoLivre';

export default function ProductCard({
  product,
  onApprove,
  onOpenRejectModal,
  onOpenAffiliateModal,
  onOpenPreviewModal,
}) {
  const isApproved = product.status === 'approved';
  const isPending = product.status === 'pending';
  const isRejected = product.status === 'rejected';
  const isPublished = product.status === 'published';

  const categoryLabels = {
    technology: 'Tecnologia',
    fashion: 'Moda',
    home: 'Casa',
    beauty: 'Beleza',
  };
  const categoryName = categoryLabels[product.category] || product.category;

  const fallbackImages = {
    technology: 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=600&q=80',
    fashion: 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=600&q=80',
    home: 'https://images.unsplash.com/photo-1584622650111-993a426fbf0a?auto=format&fit=crop&w=600&q=80',
    beauty: 'https://images.unsplash.com/photo-1621607512214-68297480165e?auto=format&fit=crop&w=600&q=80',
  };

  const [imgSrc, setImgSrc] = useState(product.thumbnail || fallbackImages[product.category] || fallbackImages.technology);

  const handleImageError = () => {
    const fallback = fallbackImages[product.category] || fallbackImages.technology;
    if (imgSrc !== fallback) {
      setImgSrc(fallback);
    }
  };

  const hasDiscount = product.original_price && Number(product.original_price) > Number(product.price);
  const discountPercent = product.discount_percentage || (hasDiscount ? Math.round(((product.original_price - product.price) / product.original_price) * 100) : 0);

  const safeMLUrl = getMercadoLivreItemUrl(product);

  return (
    <div className={`modern-product-card status-${product.status}`}>
      {/* Top Banner & Media */}
      <div className="card-media-wrapper">
        <div className="card-floating-badges">
          <ScoreBadge score={product.score} classification={product.classification} />

          <div className="status-indicator-pill">
            {isPending && <span className="pill pill-pending"><span className="dot dot-amber"></span> Pendente</span>}
            {isApproved && <span className="pill pill-approved"><span className="dot dot-emerald"></span> Aprovado</span>}
            {isRejected && <span className="pill pill-rejected"><span className="dot dot-rose"></span> Rejeitado</span>}
            {isPublished && <span className="pill pill-published"><span className="dot dot-indigo"></span> Publicado</span>}
          </div>
        </div>

        <div className="image-container">
          <img
            src={imgSrc}
            alt={product.title}
            className="product-image"
            loading="lazy"
            referrerPolicy="no-referrer"
            onError={handleImageError}
          />
        </div>

        {hasDiscount && discountPercent > 0 && (
          <div className="discount-tag">
            <Icon name="tag" size={12} />
            <span>{discountPercent}% OFF</span>
          </div>
        )}
      </div>

      {/* Card Content */}
      <div className="card-body">
        {/* Meta / Category / Seller */}
        <div className="card-meta">
          <span className="category-pill">{categoryName}</span>
          <span className="seller-badge" title={`Reputação do vendedor: ${product.seller_reputation}`}>
            <span className={`status-dot ${product.seller_reputation === 'green' ? 'green' : 'gray'}`}></span>
            {product.seller_reputation === 'green' ? 'Vendedor MercadoLíder' : product.seller_reputation}
          </span>
        </div>

        {/* Product Title */}
        <h3 className="product-title" title={product.title}>
          {product.title}
        </h3>

        {/* Price Area */}
        <div className="price-container">
          {hasDiscount && (
            <div className="original-price">
              R$ {Number(product.original_price).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
            </div>
          )}
          <div className="current-price-row">
            <span className="currency">R$</span>
            <span className="price-amount">
              {Number(product.price).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
            </span>
          </div>
        </div>

        {/* Affiliate Link Status Indicator */}
        <div className={`affiliate-status-pill ${product.affiliate_url ? 'configured' : 'missing'}`}>
          <div className="affiliate-status-left">
            <Icon name={product.affiliate_url ? 'link' : 'info'} size={14} />
            <span>
              {product.affiliate_url ? 'Link Afiliado Vinculado' : 'Link Afiliado Pendente'}
            </span>
          </div>
          <button
            type="button"
            className="affiliate-edit-link"
            onClick={() => onOpenAffiliateModal(product)}
            title="Alterar link de afiliado oficial"
          >
            {product.affiliate_url ? 'Editar' : '+ Inserir'}
          </button>
        </div>

        {/* Rejection notice if any */}
        {isRejected && product.rejection_reason && (
          <div className="rejection-box">
            <strong>Motivo:</strong> {product.rejection_reason}
          </div>
        )}

        {/* Action Buttons */}
        <div className="card-actions">
          {isPending && (
            <div className="actions-dual">
              <button
                type="button"
                className="btn-action btn-approve"
                onClick={() => onApprove(product.id)}
              >
                <Icon name="check" size={16} />
                <span>Aprovar</span>
              </button>
              <button
                type="button"
                className="btn-action btn-reject"
                onClick={() => onOpenRejectModal(product)}
              >
                <Icon name="x" size={16} />
                <span>Rejeitar</span>
              </button>
            </div>
          )}

          <div className="actions-secondary">
            <button
              type="button"
              className="btn-whatsapp"
              onClick={() => onOpenPreviewModal(product)}
            >
              <Icon name="whatsapp" size={16} />
              <span>Post WhatsApp</span>
            </button>

            {safeMLUrl ? (
              <a
                href={safeMLUrl}
                target="_blank"
                rel="noreferrer"
                className="btn-link-ml"
                title="Abrir o anúncio original no Mercado Livre"
              >
                <Icon name="external" size={16} />
                <span className="btn-link-text">Ver no ML</span>
              </a>
            ) : (
              <span
                className="btn-link-ml"
                title="Este registro não tem um link de anúncio válido. Faça uma nova busca no Mercado Livre."
              >
                <Icon name="external" size={16} />
                <span className="btn-link-text">Anúncio indisponível</span>
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
