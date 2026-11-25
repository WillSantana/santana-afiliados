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
  setMeta('og:description', `Oferta verificada em ${offer.store_label}. Confira direto na loja oficial!`);
  setMeta('og:image', offer.thumbnail || '');
}

function ShieldCheckIcon({ size = 15 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      <path d="m9 12 2 2 4-4" />
    </svg>
  );
}

function LockIcon({ size = 14 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
    </svg>
  );
}

function SearchIcon({ size = 16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8" />
      <path d="m21 21-4.3-4.3" />
    </svg>
  );
}

function ExternalIcon({ size = 16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
      <polyline points="15 3 21 3 21 9" />
      <line x1="10" y1="14" x2="21" y2="3" />
    </svg>
  );
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
    document.title = 'Garimpo de Ofertas — Promoções Verificadas';
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

  const selectedSavings = selectedOffer && selectedOffer.original_price > selectedOffer.price
    ? selectedOffer.original_price - selectedOffer.price
    : 0;

  return (
    <>
      {/* Barra superior discreta para o Grupo VIP */}
      <div className="vip-banner">
        <span>Receba ofertas verificadas e cupons ativos no grupo VIP {payload.vip_group_name || 'GARIMPO DE OFERTAS'}</span>
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

      {/* Header institucional confiável */}
      <header className="site-header">
        <div className="header-inner">
          <button type="button" className="brand-btn" onClick={goHome}>
            <img src="/favicon.svg" alt="Garimpo de Ofertas" className="brand-logo" />
            <span className="brand-text">
              <span className="brand-name">GARIMPO <span>DE OFERTAS</span></span>
              <span className="brand-sub">Curadoria diária em lojas oficiais</span>
            </span>
          </button>

          <div className="header-actions">
            <span className="verified-pill">
              <ShieldCheckIcon size={14} />
              Links oficiais verificados
            </span>
            <button
              type="button"
              className="theme-btn"
              onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}
            >
              {theme === 'light' ? 'Modo escuro' : 'Modo claro'}
            </button>
          </div>
        </div>
      </header>

      <div className="container">
        {loading ? (
          <p style={{ textAlign: 'center', color: 'var(--muted)', padding: '3.5rem 0', fontSize: '0.9rem' }}>
            Carregando ofertas verificadas...
          </p>
        ) : selectedOffer ? (
          <div>
            <button type="button" className="back-btn" onClick={goHome}>
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
                <div className="detail-verified-row">
                  <span className="detail-verified-badge">
                    <ShieldCheckIcon size={14} />
                    Oferta verificada · {selectedOffer.store_label}
                  </span>
                </div>

                <h1 className="detail-title">{selectedOffer.title}</h1>

                <div className="detail-price-box">
                  {selectedOffer.original_price && selectedOffer.original_price > selectedOffer.price && (
                    <div className="price-old">De {formatBRL(selectedOffer.original_price)}</div>
                  )}
                  <div className="detail-price-now">{formatBRL(selectedOffer.price)}</div>
                  {selectedSavings > 0 && (
                    <div className="savings-tag" style={{ marginTop: '0.2rem' }}>
                      Você economiza {formatBRL(selectedSavings)} nesta oferta
                    </div>
                  )}
                </div>

                {selectedOffer.coupon && (
                  <div className="coupon-box">
                    <div>
                      <div style={{ fontSize: '0.7rem', color: 'var(--muted)', fontWeight: 700, letterSpacing: '0.04em' }}>
                        CUPOM DE DESCONTO
                      </div>
                      <div style={{ fontSize: '1rem', fontWeight: 800, letterSpacing: '0.04em' }}>
                        {selectedOffer.coupon}
                      </div>
                    </div>
                    <button
                      type="button"
                      className="btn-copy"
                      onClick={() => handleCopyCoupon(selectedOffer.coupon)}
                    >
                      {copied ? 'Copiado!' : 'Copiar Cupom'}
                    </button>
                  </div>
                )}

                <a
                  href={selectedOffer.affiliate_url}
                  target="_blank"
                  rel="nofollow sponsored noopener noreferrer"
                  className="btn-cta-large"
                >
                  <LockIcon size={16} />
                  IR PARA A LOJA OFICIAL ({selectedOffer.store_label})
                  <ExternalIcon size={16} />
                </a>

                <div className="security-note">
                  <ShieldCheckIcon size={16} />
                  <span>
                    Você será redirecionado com segurança para o site ou app oficial da loja <strong>{selectedOffer.store_label}</strong>. Nunca solicitamos dados pessoais, senha ou pagamento nesta página.
                  </span>
                </div>
              </div>
            </article>

            {payload.vip_invite_link && (
              <div className="vip-inline-card">
                <div>
                  <div style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--text)' }}>
                    Quer receber achados como este antes de esgotar?
                  </div>
                  <div style={{ fontSize: '0.78rem', color: 'var(--muted)', marginTop: '0.15rem' }}>
                    Entre gratuitamente no grupo VIP {payload.vip_group_name || 'GARIMPO DE OFERTAS'} (sem spam e sem chat travado).
                  </div>
                </div>
                <a
                  href={payload.vip_invite_link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn-offer"
                  style={{ width: 'auto', padding: '0.6rem 1.1rem', marginTop: 0 }}
                >
                  Entrar no Grupo VIP →
                </a>
              </div>
            )}

            <p className="disclosure">
              Transparência: como associado da Amazon e parceiro de outras lojas oficiais, posso receber comissões por compras qualificadas sem nenhum custo extra para você. Preços e disponibilidade são definidos pela loja oficial e podem sofrer alteração a qualquer momento.
            </p>
          </div>
        ) : (
          <>
            {/* Faixa de confiança limpa */}
            <div className="trust-strip">
              <div className="trust-item">
                <span className="trust-icon"><ShieldCheckIcon size={13} /></span>
                <span>Links 100% diretos para lojas oficiais</span>
              </div>
              <div className="trust-item">
                <span className="trust-icon"><LockIcon size={12} /></span>
                <span>Compra segura direto no site ou app da loja</span>
              </div>
              <div className="trust-item">
                <span className="trust-icon"><ShieldCheckIcon size={13} /></span>
                <span>Ofertas verificadas nas últimas 48 horas</span>
              </div>
            </div>

            {/* Busca + Filtros por Loja */}
            <div className="controls">
              <div className="search-wrap">
                <span className="search-icon"><SearchIcon size={16} /></span>
                <input
                  type="search"
                  className="search-input"
                  placeholder="Buscar produto em oferta..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                />
              </div>
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
              <p style={{ textAlign: 'center', color: 'var(--muted)', padding: '2.5rem 0', fontSize: '0.9rem' }}>
                Nenhuma oferta encontrada para esse filtro nas últimas 48h.
              </p>
            ) : (
              <div className="grid">
                {filteredOffers.map((offer) => {
                  const savings = offer.original_price && offer.original_price > offer.price
                    ? offer.original_price - offer.price
                    : 0;
                  return (
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
                        <div className="price-block">
                          {offer.original_price && offer.original_price > offer.price && (
                            <div className="price-old">De {formatBRL(offer.original_price)}</div>
                          )}
                          <div className="price-now">{formatBRL(offer.price)}</div>
                          {savings > 0 && (
                            <div className="savings-tag">Economize {formatBRL(savings)}</div>
                          )}
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
                  );
                })}
              </div>
            )}

            <p className="disclosure">
              Transparência: como associado da Amazon e parceiro de outras lojas oficiais, posso receber comissões por compras qualificadas sem nenhum custo extra para você. Todas as compras são finalizadas diretamente nos sites oficiais.
            </p>
          </>
        )}
      </div>
    </>
  );
}
