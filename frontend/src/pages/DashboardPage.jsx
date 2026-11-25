import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';
import { Icon } from '../components/Icons';
import GroupDropdown from '../components/GroupDropdown';

function getGreeting() {
  const hour = new Date().getHours();
  if (hour < 12) return 'Bom dia';
  if (hour < 18) return 'Boa tarde';
  return 'Boa noite';
}

function formatTodayDate() {
  return new Date().toLocaleDateString('pt-BR', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });
}

function formatBRL(value) {
  if (value == null) return '—';
  return Number(value).toLocaleString('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  });
}

const STORE_STYLES = {
  mercadolivre: { bg: '#fefce8', fg: '#854d0e', dot: '#eab308', short: 'ML' },
  amazon: { bg: '#fff7ed', fg: '#c2410c', dot: '#ea580c', short: 'AMZ' },
  shopee: { bg: '#fff1f2', fg: '#be123c', dot: '#ee4d2d', short: 'SHP' },
  tiktok: { bg: '#ecfeff', fg: '#0e7490', dot: '#0f172a', short: 'TTK' },
};

export default function DashboardPage({ onNavigateTab }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [syncingClicks, setSyncingClicks] = useState(false);

  const loadDashboard = useCallback(async () => {
    try {
      setError('');
      const res = await api.getDashboard();
      setData(res);
    } catch (err) {
      setError(err.message || 'Falha ao carregar métricas');
    } finally {
      setLoading(false);
    }
  }, []);

  const handleSyncClicks = async () => {
    setSyncingClicks(true);
    setError('');
    try {
      await api.syncAffiliateClicks();
      await loadDashboard();
    } catch (err) {
      setError(err.message || 'Falha ao sincronizar cliques oficiais');
    } finally {
      setSyncingClicks(false);
    }
  };

  useEffect(() => {
    loadDashboard();
    const timer = setInterval(loadDashboard, 8000);
    return () => clearInterval(timer);
  }, [loadDashboard]);

  const botStatus = data?.bot_status || {};
  const windowStatus = data?.window_status || {};
  const clicksSummary = data?.clicks_summary || {};
  const funnelSummary = data?.funnel_summary || {};
  const metrics = data?.metrics || {};
  const groups = data?.groups || {};
  const storeMetrics = data?.store_metrics || [];
  const topOffers24h = data?.top_offers_24h || [];
  const postsByGroup = data?.posts_by_group || [];
  const maxGroupPosts = Math.max(1, ...postsByGroup.map((item) => item.total_success || 0));

  const dailyLimit = botStatus.daily_limit || 100;
  const offersToday = botStatus.offers_published_today ?? 0;
  const dailyPct = Math.min(100, Math.round((offersToday / Math.max(1, dailyLimit)) * 100));

  return (
    <div style={{ paddingBottom: '2.5rem' }}>
      {/* Saudação + Ação Principal (estilo Ripply) */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.35rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 style={{ fontSize: '1.45rem', fontWeight: 700, color: '#111827', margin: 0, letterSpacing: '-0.02em' }}>
            {getGreeting()}, Wilson
          </h1>
          <p style={{ fontSize: '0.84rem', color: '#6b7280', margin: '0.2rem 0 0 0', textTransform: 'capitalize' }}>
            {formatTodayDate()}
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.55rem', flexWrap: 'wrap' }}>
          {funnelSummary.vitrine_url && (
            <a
              href={funnelSummary.vitrine_url}
              target="_blank"
              rel="noopener noreferrer"
              className="ripply-btn-outline"
              style={{ color: '#047857', borderColor: '#a7f3d0', background: '#ecfdf5' }}
            >
              <Icon name="external" size={14} color="#047857" />
              Vitrine Pública
            </a>
          )}
          <button
            type="button"
            className="ripply-btn-outline"
            onClick={handleSyncClicks}
            disabled={syncingClicks}
          >
            <Icon name="refresh" size={14} />
            {syncingClicks ? 'Sincronizando...' : 'Sincronizar Cliques'}
          </button>
          <button
            type="button"
            className="ripply-btn-outline"
            onClick={loadDashboard}
          >
            <Icon name="refresh" size={14} />
            Atualizar
          </button>
          <button
            type="button"
            className="ripply-btn-dark"
            onClick={() => onNavigateTab && onNavigateTab('automation')}
          >
            <Icon name="plus" size={15} color="#ffffff" />
            Novo disparo
          </button>
        </div>
      </div>

      {error && (
        <div style={{ padding: '0.75rem 1rem', marginBottom: '1rem', background: '#fef2f2', color: '#b91c1c', borderRadius: '10px', border: '1px solid #fecaca', fontSize: '0.84rem' }}>
          Erro ao atualizar dados: {error}
        </div>
      )}

      {/* Faixa de 4 KPIs Principais */}
      <div className="ripply-kpi-strip">
        <div className="ripply-kpi-cell">
          <div style={{ fontSize: '0.7rem', fontWeight: 700, letterSpacing: '0.05em', color: '#6b7280', textTransform: 'uppercase' }}>
            Cliques Oficiais
          </div>
          <div style={{ fontSize: '1.9rem', fontWeight: 800, color: '#111827', marginTop: '0.3rem', lineHeight: 1.1 }}>
            {clicksSummary.total_clicks ?? 0}
          </div>
          <div style={{ fontSize: '0.75rem', color: '#6b7280', marginTop: '0.35rem' }}>
            Soma ML, Amazon, Shopee e TikTok
          </div>
        </div>

        <div
          className="ripply-kpi-cell"
          onClick={() => onNavigateTab && onNavigateTab('publications')}
          style={{ cursor: 'pointer' }}
        >
          <div style={{ fontSize: '0.7rem', fontWeight: 700, letterSpacing: '0.05em', color: '#6b7280', textTransform: 'uppercase' }}>
            Disparos Hoje
          </div>
          <div style={{ fontSize: '1.9rem', fontWeight: 800, color: '#111827', marginTop: '0.3rem', lineHeight: 1.1 }}>
            {botStatus.today_sent ?? 0}
          </div>
          <div style={{ fontSize: '0.75rem', color: '#059669', marginTop: '0.35rem', fontWeight: 500 }}>
            Todos os grupos · ver detalhes
          </div>
        </div>

        <div className="ripply-kpi-cell">
          <div style={{ fontSize: '0.7rem', fontWeight: 700, letterSpacing: '0.05em', color: '#6b7280', textTransform: 'uppercase' }}>
            Pedidos Oficiais
          </div>
          <div style={{ fontSize: '1.9rem', fontWeight: 800, color: '#111827', marginTop: '0.3rem', lineHeight: 1.1 }}>
            {clicksSummary.total_orders ?? 0}
          </div>
          <div style={{ fontSize: '0.75rem', color: '#6b7280', marginTop: '0.35rem' }}>
            {metrics.affiliates_generated || 0} links afiliados gerados
          </div>
        </div>

        <div className="ripply-kpi-cell">
          <div style={{ fontSize: '0.7rem', fontWeight: 700, letterSpacing: '0.05em', color: '#6b7280', textTransform: 'uppercase' }}>
            Cliques / Disparo
          </div>
          <div style={{ fontSize: '1.9rem', fontWeight: 800, color: '#111827', marginTop: '0.3rem', lineHeight: 1.1 }}>
            {(clicksSummary.clicks_per_delivery ?? 0).toFixed(2)}
          </div>
          <div style={{ fontSize: '0.75rem', color: '#6b7280', marginTop: '0.35rem' }}>
            {metrics.pending_offers || 0} oferta(s) na fila agora
          </div>
        </div>
      </div>

      {/* Meio: Status dos Canais & Lojas + Cotas Hoje */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 380px), 1fr))', gap: '1.15rem', marginBottom: '1.15rem' }}>
        {/* Status dos Canais & Lojas */}
        <div className="ripply-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h2 style={{ margin: 0, fontSize: '0.96rem', fontWeight: 700, color: '#111827' }}>
              Status dos Canais e Lojas
            </h2>
            <button
              type="button"
              className="ripply-btn-outline"
              onClick={() => onNavigateTab && onNavigateTab('automation')}
              style={{ padding: '0.3rem 0.65rem', fontSize: '0.75rem' }}
            >
              Gerenciar
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.7rem' }}>
            {/* WhatsApp Monitor */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0.55rem 0.7rem', borderRadius: '10px', background: '#fafafa', border: '1px solid #f1f3f5' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.7rem' }}>
                <span style={{ width: '34px', height: '34px', borderRadius: '9px', background: '#dcfce7', color: '#15803d', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Icon name="whatsapp" size={18} color="#15803d" />
                </span>
                <div>
                  <div style={{ fontSize: '0.86rem', fontWeight: 600, color: '#111827' }}>WhatsApp Web (Monitor)</div>
                  <div style={{ fontSize: '0.74rem', color: '#6b7280' }}>
                    {botStatus.running ? '1 instância ativa' : 'Monitor parado'} · Chrome 9222 {botStatus.chrome_connected ? 'conectado' : 'offline'}
                  </div>
                </div>
              </div>
              <span style={{ width: '9px', height: '9px', borderRadius: '999px', background: botStatus.running && botStatus.chrome_connected ? '#16a34a' : '#dc2626' }} />
            </div>

            {/* Lojas */}
            {storeMetrics.map((item) => {
              const st = STORE_STYLES[item.store] || STORE_STYLES.mercadolivre;
              const isActive = Boolean(item.enabled);
              return (
                <div
                  key={item.store}
                  style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0.55rem 0.7rem', borderRadius: '10px', background: '#ffffff', border: '1px solid #f1f3f5' }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.7rem' }}>
                    <span style={{
                      width: '34px',
                      height: '34px',
                      borderRadius: '9px',
                      background: st.bg,
                      color: st.fg,
                      fontSize: '0.7rem',
                      fontWeight: 800,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}>
                      {st.short}
                    </span>
                    <div>
                      <div style={{ fontSize: '0.86rem', fontWeight: 600, color: '#111827' }}>
                        {item.label}
                      </div>
                      <div style={{ fontSize: '0.74rem', color: '#6b7280' }}>
                        {isActive ? 'Ativo' : 'Aguardando API / pausado'} · {item.clicks_month ?? 0} cliques · {item.deliveries_today} envios hoje
                      </div>
                    </div>
                  </div>
                  <span style={{
                    fontSize: '0.72rem',
                    fontWeight: 600,
                    padding: '0.2rem 0.55rem',
                    borderRadius: '999px',
                    background: isActive ? '#ecfdf5' : '#f3f4f6',
                    color: isActive ? '#047857' : '#6b7280',
                  }}>
                    {isActive ? 'Conectado' : 'Pausado'}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Cotas e Uso Hoje (barras de progresso estilo Ripply) */}
        <div className="ripply-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h2 style={{ margin: 0, fontSize: '0.96rem', fontWeight: 700, color: '#111827' }}>
              Cotas e Uso Hoje
            </h2>
            {windowStatus.enabled && (
              <span style={{
                fontSize: '0.72rem',
                fontWeight: 600,
                padding: '0.2rem 0.55rem',
                borderRadius: '999px',
                background: windowStatus.can_publish ? '#ecfdf5' : '#fffbeb',
                color: windowStatus.can_publish ? '#047857' : '#b45309',
              }}>
                {windowStatus.window_label
                  ? `Janela ${windowStatus.window_label} (${windowStatus.window_sent}/${windowStatus.window_limit})`
                  : `Próxima às ${windowStatus.next_window_label || '08:00'}`}
              </span>
            )}
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.95rem' }}>
            {/* Teto Diário Geral */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', marginBottom: '0.35rem' }}>
                <span style={{ fontWeight: 600, color: '#374151' }}>Teto Diário de Ofertas</span>
                <span style={{ fontWeight: 700, color: '#111827' }}>{offersToday}/{dailyLimit}</span>
              </div>
              <div className="ripply-progress-track">
                <div className="ripply-progress-fill" style={{ width: `${dailyPct}%`, background: '#111827' }} />
              </div>
            </div>

            {/* Barras por Loja */}
            {storeMetrics.map((item) => {
              const st = STORE_STYLES[item.store] || STORE_STYLES.mercadolivre;
              const quota = item.daily_quota || 10;
              const used = item.offers_published_today ?? 0;
              const pct = Math.min(100, Math.round((used / Math.max(1, quota)) * 100));
              return (
                <div key={item.store}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', marginBottom: '0.35rem' }}>
                    <span style={{ color: '#4b5563', fontWeight: 500 }}>
                      {item.label} <span style={{ color: '#9ca3af', fontSize: '0.74rem' }}>({item.affiliates_generated} links)</span>
                    </span>
                    <span style={{ fontWeight: 700, color: '#111827' }}>{used}/{quota}</span>
                  </div>
                  <div className="ripply-progress-track">
                    <div className="ripply-progress-fill" style={{ width: `${pct}%`, background: st.dot }} />
                  </div>
                </div>
              );
            })}

            {/* Funil VIP Garimpo de Ofertas & Taxa de entregas */}
            <div style={{ paddingTop: '0.65rem', borderTop: '1px solid #f1f3f5', display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.5rem', fontSize: '0.78rem', color: '#4b5563' }}>
              <span>
                🎯 Ofertas Isca hoje: <strong style={{ color: '#ea580c' }}>{funnelSummary.bait_sent_today ?? 0}</strong>
              </span>
              <span>
                ⭐ VIP {funnelSummary.vip_group_name || 'Garimpo'}: <strong style={{ color: '#047857' }}>{funnelSummary.vip_sent_today ?? 0}/{funnelSummary.vip_daily_limit ?? 12}</strong>
              </span>
            </div>
            <div style={{ paddingTop: '0.5rem', borderTop: '1px solid #f1f3f5', display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', color: '#6b7280' }}>
              <span>Entregas totais: <strong style={{ color: '#059669' }}>{metrics.deliveries_success || 0}</strong></span>
              <span>Falhas: <strong style={{ color: (metrics.deliveries_failed || 0) > 0 ? '#dc2626' : '#6b7280' }}>{metrics.deliveries_failed || 0}</strong></span>
              <span>Incertas: <strong>{metrics.deliveries_uncertain || 0}</strong></span>
            </div>
          </div>
        </div>
      </div>

      {/* Base: Top Ofertas · últimas 24h + Posts por Grupo */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 380px), 1fr))', gap: '1.15rem', marginBottom: '1.15rem' }}>
        {/* Top Ofertas 24h */}
        <div className="ripply-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.9rem' }}>
            <h2 style={{ margin: 0, fontSize: '0.96rem', fontWeight: 700, color: '#111827' }}>
              Top ofertas · últimas 24h
            </h2>
            <button
              type="button"
              onClick={() => onNavigateTab && onNavigateTab('automation')}
              style={{ fontSize: '0.78rem', fontWeight: 600, color: '#4b5563' }}
            >
              Ver todas →
            </button>
          </div>

          {!topOffers24h.length ? (
            <p style={{ color: '#6b7280', fontSize: '0.84rem', margin: 0 }}>
              Nenhuma oferta publicada nas últimas 24 horas.
            </p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
              {topOffers24h.map((offer, idx) => {
                const st = STORE_STYLES[offer.store] || STORE_STYLES.mercadolivre;
                return (
                  <div
                    key={offer.id}
                    style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.5rem 0.55rem', borderRadius: '10px', border: '1px solid #f1f3f5' }}
                  >
                    <span style={{ fontSize: '0.78rem', fontWeight: 700, color: '#9ca3af', width: '16px', textAlign: 'center' }}>
                      {idx + 1}
                    </span>
                    {offer.thumbnail ? (
                      <img
                        src={offer.thumbnail}
                        alt=""
                        style={{ width: '40px', height: '40px', borderRadius: '8px', objectFit: 'contain', background: '#f8fafc', border: '1px solid #f1f3f5', flexShrink: 0 }}
                      />
                    ) : (
                      <div style={{ width: '40px', height: '40px', borderRadius: '8px', background: '#f3f4f6', flexShrink: 0 }} />
                    )}
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: '0.82rem', fontWeight: 600, color: '#111827', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {offer.title}
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', marginTop: '0.2rem', fontSize: '0.73rem', color: '#6b7280' }}>
                        <span style={{ padding: '0.05rem 0.4rem', borderRadius: '4px', background: st.bg, color: st.fg, fontWeight: 700 }}>
                          {offer.store_label}
                        </span>
                        <span style={{ fontWeight: 700, color: '#111827' }}>{formatBRL(offer.price)}</span>
                        {offer.discount_pct > 0 && (
                          <span style={{ color: '#059669', fontWeight: 700 }}>{offer.discount_pct}% OFF</span>
                        )}
                      </div>
                    </div>
                    <span style={{
                      fontSize: '0.72rem',
                      fontWeight: 600,
                      padding: '0.2rem 0.5rem',
                      borderRadius: '999px',
                      background: '#f3f4f6',
                      color: '#374151',
                      whiteSpace: 'nowrap',
                    }}>
                      {offer.deliveries_count} grupos
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Posts por Grupo */}
        <div className="ripply-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.9rem' }}>
            <div>
              <h2 style={{ margin: 0, fontSize: '0.96rem', fontWeight: 700, color: '#111827' }}>
                Posts por Grupo
              </h2>
              <span style={{ fontSize: '0.74rem', color: '#6b7280' }}>
                Distribuição equilibrada (hoje e acumulado)
              </span>
            </div>
            <button
              type="button"
              onClick={() => onNavigateTab && onNavigateTab('publications')}
              style={{ fontSize: '0.78rem', fontWeight: 600, color: '#4b5563' }}
            >
              Ver envios →
            </button>
          </div>

          {!postsByGroup.length ? (
            <p style={{ color: '#6b7280', fontSize: '0.84rem', margin: 0 }}>Nenhum envio registrado por grupo ainda.</p>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
                <thead>
                  <tr style={{ textAlign: 'left', borderBottom: '1px solid #f1f3f5', color: '#6b7280' }}>
                    <th style={{ padding: '0.4rem 0.45rem' }}>Grupo</th>
                    <th style={{ padding: '0.4rem 0.45rem', textAlign: 'center' }}>Hoje</th>
                    <th style={{ padding: '0.4rem 0.45rem', width: '150px' }}>Total</th>
                    <th style={{ padding: '0.4rem 0.45rem', textAlign: 'center' }}>Falhas</th>
                  </tr>
                </thead>
                <tbody>
                  {postsByGroup.map((row) => {
                    const barWidth = Math.round(((row.total_success || 0) / maxGroupPosts) * 100);
                    return (
                      <tr key={row.group_name} style={{ borderBottom: '1px solid #f8fafc' }}>
                        <td style={{ padding: '0.48rem 0.45rem', fontWeight: 600, color: '#111827', maxWidth: '185px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {row.group_name}
                        </td>
                        <td style={{ padding: '0.48rem 0.45rem', textAlign: 'center' }}>
                          <span style={{
                            display: 'inline-block',
                            minWidth: '24px',
                            padding: '0.1rem 0.4rem',
                            borderRadius: '999px',
                            fontSize: '0.72rem',
                            fontWeight: 700,
                            background: row.today_success > 0 ? '#ecfdf5' : '#f3f4f6',
                            color: row.today_success > 0 ? '#047857' : '#6b7280',
                          }}>
                            {row.today_success}
                          </span>
                        </td>
                        <td style={{ padding: '0.48rem 0.45rem' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
                            <span style={{ fontWeight: 700, color: '#059669', minWidth: '24px' }}>{row.total_success}</span>
                            <div className="ripply-progress-track">
                              <div className="ripply-progress-fill" style={{ width: `${barWidth}%`, background: '#10b981' }} />
                            </div>
                          </div>
                        </td>
                        <td style={{ padding: '0.48rem 0.45rem', textAlign: 'center', fontWeight: 600, color: row.total_failed > 0 ? '#dc2626' : '#9ca3af' }}>
                          {row.total_failed}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Grupos Autorizados (Expansível) */}
      <div className="ripply-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem', flexWrap: 'wrap', gap: '0.5rem' }}>
          <h2 style={{ margin: 0, fontSize: '0.96rem', fontWeight: 700, color: '#111827' }}>
            Grupos Autorizados do WhatsApp
          </h2>
          <span style={{ fontSize: '0.75rem', color: '#6b7280' }}>
            Clique para expandir origens e destinos
          </span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 260px), 1fr))', gap: '0.85rem' }}>
          <GroupDropdown
            icon="📥"
            label="Grupos de Origem (Monitorados)"
            groups={groups.sources || []}
            emptyText="Nenhum grupo de origem cadastrado"
            accent="blue"
          />
          <GroupDropdown
            icon="📤"
            label="Grupos de Destino (Recebem Ofertas)"
            groups={groups.destinations || []}
            emptyText="Nenhum grupo de destino autorizado"
            accent="green"
          />
        </div>
      </div>
    </div>
  );
}
