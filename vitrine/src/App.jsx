import React, { useEffect, useMemo, useState } from 'react';

function formatBRL(value) {
  if (value == null) return '';
  return Number(value).toLocaleString('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  });
}

function getOfferIdFromLocation() {
  const pathMatch = window.location.pathname.match(/^\/oferta\/([^/?#]+)/i);
  if (pathMatch) return decodeURIComponent(pathMatch[1]);
  const params = new URLSearchParams(window.location.search);
  return params.get('id') || '';
}

function updateMetaTags(offer) {
  if (!offer) return;
  const priceStr = formatBRL(offer.price);
  const title = offer.discount_pct > 0
    ? `${offer.discount_pct}% OFF — ${offer.title} por ${priceStr}`
    : `${offer.title} por ${priceStr}`;
  document.title = `${title} | Garimpo de Ofertas`;

  const setMeta = (prop, content) => {
    let tag = document.querySelector(`meta[property="${prop}"]`);
    if (!tag) {
      tag = document.createElement('meta');
      tag.setAttribute('property', prop);
      document.head.appendChild(tag);
    }
    tag.setAttribute('content', content || '');
  };
  setMeta('og:title', title);
  setMeta('og:description', `Oferta verificada em ${offer.store_label}. Confira antes que acabe!`);
  setMeta('og:image', offer.thumbnail || '');
}

const STORES = [
  { key: 'all', label: 'Todas' },
  { key: 'mercadolivre', label: 'Mercado Livre' },
  { key: 'amazon', label: 'Amazon' },
  { key: 'shopee', label: 'Shopee' },
  { key: 'tiktok', label: 'TikTok Shop' },
];

export default function App() {
  const [payload, setPayload] = useState({ offers: [], vip_group_name: 'GARIMPO DE OFERTAS', vip_invite_link: '' });
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');
  const [storeFilter, setStoreFilter] = useState('all');
  const [selectedId, setSelectedId] = useState(getOfferIdFromLocation);
  const [copied, setCopied] = useState(false);
  const [theme, setTheme] = useState(() => localStorage.getItem('vitrine_theme') || 'light');

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('vitrine_theme', theme);
  }, [theme]);

  useEffect(() => {
    const onPop = () => setSelectedId(getOfferIdFromLocation());
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  }, []);

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const res = await fetch('/ofertas.json', { cache: 'no-store' });
        if (!res.ok) throw new Error('Falha ao ler ofertas.json');
        const json = await res.json();
        if (active) setPayload(json);
      } catch {
        if (active) setPayload({ offers: [], vip_group_name: 'GARIMPO DE OFERTAS', vip_invite_link: '' });
      } finally {
        if (active) setLoading(false);
      }
    }
    load();
    return () => { active = false; };
  }, []);

  const selectedOffer = useMemo(() => {
    if (!selectedId) return null;
    return (payload.offers || []).find((item) => String(item.id) === String(selectedId)) || null;
  }, [payload.offers, selectedId]);

  useEffect(() => {
    if (selectedOffer) updateMetaTags(selectedOffer);
  }, [selectedOffer]);

  const visibleStores = useMemo(() => {
    const activeStores = new Set((payload.offers || []).map((offer) => offer.store).filter(Boolean));
    return STORES.filter((st) => {
      if (st.key === 'all' || st.key === 'mercadolivre' || st.key === 'amazon') return true;
      return activeStores.has(st.key);
    });
  }, [payload.offers]);

  const filteredOffers = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (payload.offers || []).filter((offer) => {
      if (storeFilter !== 'all' && offer.store !== storeFilter) return false;
      if (q && !(offer.title || '').toLowerCase().includes(q)) return false;
      return true;
    });
  }, [payload.offers, query, storeFilter]);

  const openOffer = (id) => {
    setSelectedId(id);
    setCopied(false);
    window.history.pushState({}, '', `/oferta/${encodeURIComponent(id)}`);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const goHome = () => {
    setSelectedId('');
    window.history.pushState({}, '', '/');
  };

  const handleCopyCoupon = async (coupon) => {
    try {
      await navigator.clipboard.writeText(coupon);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch {
      setCopied(false);
    }
  };

  return (
    <>
      {/* Banner fixo VIP GARIMPO DE OFERTAS */}
      <div className="vip-banner">
        <span>🔥 Receba bugs de preço e cupons relâmpago no grupo VIP {payload.vip_group_name || 'GARIMPO DE OFERTAS'}</span>
        {payload.vip_invite_link && (
          <a
            href={payload.vip_invite_link}
            target="_blank"
            rel="noopener noreferrer"
            className="vip-banner-btn"
          >
            Entrar no Grupo VIP →
          </a>
        )}
      </div>

      <div className="container">
        <header className="topbar">
          <button type="button" className="brand" onClick={goHome}>
            GARIMPO<span>DE OFERTAS</span>
          </button>
          <button
            type="button"
            className="theme-btn"
            onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}
          >
            {theme === 'light' ? '🌙 Escuro' : '☀️ Claro'}
          </button>
        </header>

        {loading ? (
          <p style={{ textAlign: 'center', color: 'var(--muted)', padding: '3rem 0' }}>
            Carregando ofertas verificadas...
          </p>
        ) : selectedOffer ? (
          <div>
            <button
              type="button"
              onClick={goHome}
              style={{ color: 'var(--muted)', fontSize: '0.85rem', fontWeight: 700, marginBottom: '0.5rem' }}
            >
              ← Voltar para todas as ofertas
            </button>

            <article className="detail-card">
              <div className="detail-img-box">
                {selectedOffer.discount_pct > 0 && (
                  <span className="discount-badge">-{selectedOffer.discount_pct}% OFF</span>
                )}
                <span className="store-badge">{selectedOffer.store_label}</span>
                {selectedOffer.thumbnail ? (
                  <img src={selectedOffer.thumbnail} alt={selectedOffer.title} />
                ) : (
                  <span style={{ color: '#94a3b8' }}>Sem imagem</span>
                )}
              </div>

              <div className="detail-body">
                <h1 style={{ fontSize: '1.2rem', fontWeight: 800, lineHeight: 1.3 }}>
                  {selectedOffer.title}
                </h1>

                <div>
                  {selectedOffer.original_price && selectedOffer.original_price > selectedOffer.price && (
                    <div className="price-old">De {formatBRL(selectedOffer.original_price)}</div>
                  )}
                  <div style={{ fontSize: '1.75rem', fontWeight: 900, color: 'var(--cta)' }}>
                    Por {formatBRL(selectedOffer.price)}
                  </div>
                </div>

                {selectedOffer.coupon && (
                  <div className="coupon-box">
                    <div>
                      <div style={{ fontSize: '0.72rem', color: 'var(--muted)', fontWeight: 700 }}>CUPOM DE DESCONTO</div>
                      <div style={{ fontSize: '1rem', fontWeight: 900, letterSpacing: '0.04em' }}>{selectedOffer.coupon}</div>
                    </div>
                    <button
                      type="button"
                      className="btn-copy"
                      onClick={() => handleCopyCoupon(selectedOffer.coupon)}
                    >
                      {copied ? '✓ Copiado!' : 'Copiar Cupom'}
                    </button>
                  </div>
                )}

                <a
                  href={selectedOffer.affiliate_url}
                  target="_blank"
                  rel="nofollow sponsored noopener noreferrer"
                  className="btn-cta-large"
                >
                  IR PARA A LOJA OFICIAL →
                </a>

                <p className="disclosure">
                  Como associado da Amazon e parceiro de outras lojas, posso receber comissões por compras qualificadas sem custo extra para você. Preços e disponibilidade sujeitos a alteração pela loja.
                </p>
              </div>
            </article>
          </div>
        ) : (
          <>
            <div className="controls">
              <input
                type="search"
                className="search-input"
                placeholder="Buscar produto em oferta..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
              <div className="store-pills">
                {visibleStores.map((st) => (
                  <button
                    key={st.key}
                    type="button"
                    className={`store-pill ${storeFilter === st.key ? 'active' : ''}`}
                    onClick={() => setStoreFilter(st.key)}
                  >
                    {st.label}
                  </button>
                ))}
              </div>
            </div>

            {!filteredOffers.length ? (
              <p style={{ textAlign: 'center', color: 'var(--muted)', padding: '2.5rem 0' }}>
                Nenhuma oferta encontrada para esse filtro nas últimas 48h.
              </p>
            ) : (
              <div className="grid">
                {filteredOffers.map((offer) => (
                  <article key={offer.id} className="offer-card">
                    <div className="card-img-wrap">
                      {offer.discount_pct > 0 && (
                        <span className="discount-badge">-{offer.discount_pct}% OFF</span>
                      )}
                      <span className="store-badge">{offer.store_label}</span>
                      {offer.thumbnail && <img src={offer.thumbnail} alt={offer.title} loading="lazy" />}
                    </div>
                    <div className="card-body">
                      <h2 className="card-title">{offer.title}</h2>
                      <div>
                        {offer.original_price && offer.original_price > offer.price && (
                          <div className="price-old">De {formatBRL(offer.original_price)}</div>
                        )}
                        <div className="price-now">{formatBRL(offer.price)}</div>
                      </div>
                      <button
                        type="button"
                        className="btn-offer"
                        onClick={() => openOffer(offer.id)}
                      >
                        Ver Oferta
                      </button>
                    </div>
                  </article>
                ))}
              </div>
            )}

            <p className="disclosure" style={{ marginTop: '2rem' }}>
              Como associado da Amazon e parceiro de outras lojas, posso receber comissões por compras qualificadas sem custo extra para você.
            </p>
          </>
        )}
      </div>
    </>
  );
}
