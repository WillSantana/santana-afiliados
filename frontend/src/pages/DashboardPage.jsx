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
  mercadolivre: { bg: '#fefce8', fg: '#854d0e', bar: '#eab308', short: 'ML' },
  amazon: { bg: '#fff7ed', fg: '#c2410c', bar: '#ea580c', short: 'AMZ' },
  shopee: { bg: '#fff1f2', fg: '#be123c', bar: '#ee4d2d', short: 'SHP' },
  tiktok: { bg: '#f1f5f9', fg: '#0f172a', bar: '#334155', short: 'TTK' },
};

export default function DashboardPage({ onNavigateTab }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [syncingClicks, setSyncingClicks] = useState(false);

  const loadDashboard = useCallback(async () => {
    try {
      setError('');
      const res = await api.getDashboard();
      setData(res);
    } catch (err) {
      setError(err.message || 'Falha ao carregar métricas');
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

  const vipSentToday = funnelSummary.vip_sent_today ?? 0;
  const vipLimit = funnelSummary.vip_daily_limit ?? 12;
  const vipPct = Math.min(100, Math.round((vipSentToday / Math.max(1, vipLimit)) * 100));

  const isOnline = Boolean(botStatus.running && botStatus.chrome_connected);

  return (
    <div style={{ paddingBottom: '2.5rem' }}>
      {/* Cabeçalho limpo */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: '1.4rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', flexWrap: 'wrap' }}>
            <h1 style={{ fontSize: '1.45rem', fontWeight: 700, color: '#0f172a', margin: 0, letterSpacing: '-0.025em' }}>
              {getGreeting()}, Wilson
            </h1>
            <span className="dash-live-pill">
              <span style={{
                width: '7px',
                height: '7px',
                borderRadius: '999px',
                background: isOnline ? '#10b981' : '#ef4444',
              }} />
              {isOnline ? 'Monitor ativo' : 'Monitor offline'}
            </span>
          </div>
          <p style={{ fontSize: '0.82rem', color: '#64748b', margin: '0.25rem 0 0 0', textTransform: 'capitalize' }}>
            {formatTodayDate()}
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
          {funnelSummary.vitrine_url && (
            <a
              href={funnelSummary.vitrine_url}
              target="_blank"
              rel="noopener noreferrer"
              className="ripply-btn-outline"
            >
              <Icon name="external" size={14} color="#475569" />
              Vitrine Pública
            </a>
          )}
          <button
            type="button"
            className="ripply-btn-outline"
            onClick={handleSyncClicks}
            disabled={syncingClicks}
          >
            <Icon name="refresh" size={14} color="#475569" />
            {syncingClicks ? 'Sincronizando...' : 'Sincronizar Cliques'}
          </button>
          <button
            type="button"
            className="ripply-btn-dark"
            onClick={() => onNavigateTab && onNavigateTab('automation')}
          >
            <Icon name="plus" size={14} color="#ffffff" />
            Novo disparo
          </button>
        </div>
      </div>

      {error && (
        <div style={{ padding: '0.75rem 1rem', marginBottom: '1rem', background: '#fef2f2', color: '#b91c1c', borderRadius: '10px', border: '1px solid #fecaca', fontSize: '0.82rem' }}>
          Erro ao atualizar dados: {error}
        </div>
      )}

      {/* 5 KPIs Principais em cards individuais */}
      <div className="dash-kpi-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(175px, 1fr))' }}>
        <div className="dash-kpi-card">
          <div className="dash-kpi-label">Inscritos · Grupo VIP</div>
          <div className="dash-kpi-value" style={{ color: '#047857' }}>
            {funnelSummary.vip_members_count ?? '—'}
          </div>
          <div className="dash-kpi-sub">
            {funnelSummary.vip_members_count != null
              ? (funnelSummary.vip_members_joined_today > 0
                  ? `+${funnelSummary.vip_members_joined_today} entraram hoje`
                  : (funnelSummary.vip_group_name || 'Garimpo de Ofertas'))
              : 'Aguardando leitura do WhatsApp'}
          </div>
        </div>

        <div className="dash-kpi-card">
          <div className="dash-kpi-label">Cliques Oficiais</div>
          <div className="dash-kpi-value">{clicksSummary.total_clicks ?? 0}</div>
          <div className="dash-kpi-sub">Total sincronizado nas lojas</div>
        </div>

        <div
          className="dash-kpi-card is-clickable"
          onClick={() => onNavigateTab && onNavigateTab('publications')}
        >
          <div className="dash-kpi-label">Disparos Hoje</div>
          <div className="dash-kpi-value">{botStatus.today_sent ?? 0}</div>
          <div className="dash-kpi-sub" style={{ color: '#059669', fontWeight: 500 }}>
            Ver histórico de envios →
          </div>
        </div>

        <div className="dash-kpi-card">
          <div className="dash-kpi-label">Pedidos Oficiais</div>
          <div className="dash-kpi-value">{clicksSummary.total_orders ?? 0}</div>
          <div className="dash-kpi-sub">{metrics.affiliates_generated || 0} links afiliados gerados</div>
        </div>

        <div className="dash-kpi-card">
          <div className="dash-kpi-label">Cliques / Disparo</div>
          <div className="dash-kpi-value">{(clicksSummary.clicks_per_delivery ?? 0).toFixed(2)}</div>
          <div className="dash-kpi-sub">{metrics.pending_offers || 0} oferta(s) na fila agora</div>
        </div>
      </div>

      {/* Meio: Canais & Lojas + Cotas & Funil */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 380px), 1fr))', gap: '1rem', marginBottom: '1rem' }}>
        {/* Canais e Lojas */}
        <div className="ripply-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.65rem' }}>
            <h2 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 700, color: '#0f172a' }}>
              Canais e Lojas
            </h2>
            <button
              type="button"
              onClick={() => onNavigateTab && onNavigateTab('automation')}
              style={{ fontSize: '0.78rem', fontWeight: 600, color: '#64748b' }}
            >
              Gerenciar →
            </button>
          </div>

          <div>
            {/* WhatsApp Monitor */}
            <div className="dash-list-row">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <span style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '8px',
                  background: '#ecfdf5',
                  color: '#059669',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                }}>
                  <Icon name="whatsapp" size={16} color="#059669" />
                </span>
                <div>
                  <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#0f172a' }}>WhatsApp Web</div>
                  <div style={{ fontSize: '0.74rem', color: '#64748b' }}>
                    Chrome 9222 {botStatus.chrome_connected ? 'conectado' : 'desconectado'}
                  </div>
                </div>
              </div>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.74rem', fontWeight: 600, color: isOnline ? '#059669' : '#dc2626' }}>
                <span style={{ width: '6px', height: '6px', borderRadius: '999px', background: isOnline ? '#10b981' : '#ef4444' }} />
                {isOnline ? 'Online' : 'Offline'}
              </span>
            </div>

            {/* Lojas */}
            {storeMetrics.map((item) => {
              const st = STORE_STYLES[item.store] || STORE_STYLES.mercadolivre;
              const isActive = Boolean(item.enabled);
              return (
                <div key={item.store} className="dash-list-row" style={{ opacity: isActive ? 1 : 0.6 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <span style={{
                      width: '32px',
                      height: '32px',
                      borderRadius: '8px',
                      background: st.bg,
                      color: st.fg,
                      fontSize: '0.68rem',
                      fontWeight: 700,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                    }}>
                      {st.short}
                    </span>
                    <div>
                      <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#0f172a' }}>{item.label}</div>
                      <div style={{ fontSize: '0.74rem', color: '#64748b', fontVariantNumeric: 'tabular-nums' }}>
                        {item.clicks_month ?? 0} cliques · {item.deliveries_today} envios hoje
                      </div>
                    </div>
                  </div>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.74rem', fontWeight: 600, color: isActive ? '#059669' : '#94a3b8' }}>
                    <span style={{ width: '6px', height: '6px', borderRadius: '999px', background: isActive ? '#10b981' : '#cbd5e1' }} />
                    {isActive ? 'Ativo' : 'Pausado'}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Cotas e Funil Hoje */}
        <div className="ripply-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.95rem', gap: '0.5rem', flexWrap: 'wrap' }}>
            <h2 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 700, color: '#0f172a' }}>
              Cotas e Funil Hoje
            </h2>
            {windowStatus.enabled && (
              <span style={{
                fontSize: '0.72rem',
                fontWeight: 600,
                padding: '0.2rem 0.55rem',
                borderRadius: '999px',
                background: windowStatus.can_publish ? '#ecfdf5' : '#f8fafc',
                color: windowStatus.can_publish ? '#047857' : '#64748b',
                border: `1px solid ${windowStatus.can_publish ? '#d1fae5' : '#e2e8f0'}`,
              }}>
                {windowStatus.window_label
                  ? `Janela ${windowStatus.window_label} (${windowStatus.window_sent}/${windowStatus.window_limit})`
                  : `Próxima às ${windowStatus.next_window_label || '08:00'}`}
              </span>
            )}
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
            {/* Teto Diário Geral */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '0.35rem' }}>
                <span style={{ fontWeight: 600, color: '#334155' }}>Teto Diário de Ofertas</span>
                <span style={{ fontWeight: 700, color: '#0f172a', fontVariantNumeric: 'tabular-nums' }}>{offersToday}/{dailyLimit}</span>
              </div>
              <div className="ripply-progress-track">
                <div className="ripply-progress-fill" style={{ width: `${dailyPct}%`, background: '#0f172a' }} />
              </div>
            </div>

            {/* VIP Garimpo de Ofertas */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '0.35rem' }}>
                <span style={{ fontWeight: 600, color: '#334155' }}>
                  VIP {funnelSummary.vip_group_name || 'Garimpo de Ofertas'}
                </span>
                <span style={{ fontWeight: 700, color: '#047857', fontVariantNumeric: 'tabular-nums' }}>
                  {vipSentToday}/{vipLimit}
                </span>
              </div>
              <div className="ripply-progress-track">
                <div className="ripply-progress-fill" style={{ width: `${vipPct}%`, background: '#10b981' }} />
              </div>
            </div>

            {/* Barras das Lojas Ativas */}
            {storeMetrics.filter((item) => item.enabled).map((item) => {
              const st = STORE_STYLES[item.store] || STORE_STYLES.mercadolivre;
              const quota = item.daily_quota || 10;
              const used = item.offers_published_today ?? 0;
              const pct = Math.min(100, Math.round((used / Math.max(1, quota)) * 100));
              return (
                <div key={item.store}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '0.35rem' }}>
                    <span style={{ color: '#475569', fontWeight: 500 }}>
                      {item.label}{' '}
                      <span style={{ color: '#94a3b8', fontSize: '0.73rem' }}>({item.affiliates_generated} links)</span>
                    </span>
                    <span style={{ fontWeight: 700, color: '#0f172a', fontVariantNumeric: 'tabular-nums' }}>{used}/{quota}</span>
                  </div>
                  <div className="ripply-progress-track">
                    <div className="ripply-progress-fill" style={{ width: `${pct}%`, background: st.bar }} />
                  </div>
                </div>
              );
            })}

            {/* Mini-stats limpos (sem emojis) */}
            <div className="dash-mini-stats">
              <div className="dash-mini-stat">
                <span className="dash-mini-stat-label">Membros VIP</span>
                <span className="dash-mini-stat-value">
                  {funnelSummary.vip_members_count ?? '—'}
                  {funnelSummary.vip_members_joined_today > 0 && (
                    <span style={{ fontSize: '0.72rem', fontWeight: 600, color: '#059669', marginLeft: '0.3rem' }}>
                      +{funnelSummary.vip_members_joined_today} hoje
                    </span>
                  )}
                </span>
              </div>
              <div className="dash-mini-stat">
                <span className="dash-mini-stat-label">Ofertas Isca hoje</span>
                <span className="dash-mini-stat-value">{funnelSummary.bait_sent_today ?? 0}</span>
              </div>
              <div className="dash-mini-stat">
                <span className="dash-mini-stat-label">Entregas totais</span>
                <span className="dash-mini-stat-value" style={{ color: '#059669' }}>{metrics.deliveries_success || 0}</span>
              </div>
              <div className="dash-mini-stat">
                <span className="dash-mini-stat-label">Falhas acumuladas</span>
                <span className="dash-mini-stat-value" style={{ color: (metrics.deliveries_failed || 0) > 0 ? '#dc2626' : '#64748b' }}>
                  {metrics.deliveries_failed || 0}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Base: Top Ofertas · últimas 24h + Posts por Grupo */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 380px), 1fr))', gap: '1rem', marginBottom: '1rem' }}>
        {/* Top Ofertas 24h */}
        <div className="ripply-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.8rem' }}>
            <h2 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 700, color: '#0f172a' }}>
              Top ofertas · últimas 24h
            </h2>
            <button
              type="button"
              onClick={() => onNavigateTab && onNavigateTab('automation')}
              style={{ fontSize: '0.78rem', fontWeight: 600, color: '#64748b' }}
            >
              Ver todas →
            </button>
          </div>

          {!topOffers24h.length ? (
            <p style={{ color: '#64748b', fontSize: '0.82rem', margin: 0 }}>
              Nenhuma oferta publicada nas últimas 24 horas.
            </p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
              {topOffers24h.map((offer, idx) => {
                const st = STORE_STYLES[offer.store] || STORE_STYLES.mercadolivre;
                return (
                  <div key={offer.id} className="dash-offer-row">
                    <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#94a3b8', width: '16px', textAlign: 'center', fontVariantNumeric: 'tabular-nums' }}>
                      {idx + 1}
                    </span>
                    {offer.thumbnail ? (
                      <img
                        src={offer.thumbnail}
                        alt=""
                        style={{ width: '40px', height: '40px', borderRadius: '8px', objectFit: 'contain', background: '#ffffff', border: '1px solid #e2e8f0', padding: '2px', flexShrink: 0 }}
                      />
                    ) : (
                      <div style={{ width: '40px', height: '40px', borderRadius: '8px', background: '#f1f5f9', flexShrink: 0 }} />
                    )}
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: '0.82rem', fontWeight: 600, color: '#0f172a', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {offer.title}
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', marginTop: '0.18rem', fontSize: '0.73rem', color: '#64748b', fontVariantNumeric: 'tabular-nums' }}>
                        <span style={{ padding: '0.05rem 0.4rem', borderRadius: '4px', background: st.bg, color: st.fg, fontWeight: 600 }}>
                          {offer.store_label}
                        </span>
                        <span style={{ fontWeight: 700, color: '#0f172a' }}>{formatBRL(offer.price)}</span>
                        {offer.discount_pct > 0 && (
                          <span style={{ color: '#059669', fontWeight: 600 }}>-{offer.discount_pct}%</span>
                        )}
                      </div>
                    </div>
                    <span style={{ fontSize: '0.73rem', fontWeight: 600, color: '#475569', whiteSpace: 'nowrap', fontVariantNumeric: 'tabular-nums' }}>
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
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.8rem' }}>
            <div>
              <h2 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 700, color: '#0f172a' }}>
                Posts por Grupo
              </h2>
              <span style={{ fontSize: '0.74rem', color: '#64748b' }}>
                Distribuição hoje e acumulado
              </span>
            </div>
            <button
              type="button"
              onClick={() => onNavigateTab && onNavigateTab('publications')}
              style={{ fontSize: '0.78rem', fontWeight: 600, color: '#64748b' }}
            >
              Ver envios →
            </button>
          </div>

          {!postsByGroup.length ? (
            <p style={{ color: '#64748b', fontSize: '0.82rem', margin: 0 }}>Nenhum envio registrado por grupo ainda.</p>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table className="dash-table">
                <thead>
                  <tr style={{ textAlign: 'left' }}>
                    <th>Grupo</th>
                    <th style={{ textAlign: 'center' }}>Hoje</th>
                    <th style={{ width: '145px' }}>Total</th>
                    <th style={{ textAlign: 'center' }}>Falhas</th>
                  </tr>
                </thead>
                <tbody>
                  {postsByGroup.map((row) => {
                    const barWidth = Math.round(((row.total_success || 0) / maxGroupPosts) * 100);
                    return (
                      <tr key={row.group_name}>
                        <td style={{ fontWeight: 600, color: '#0f172a', maxWidth: '185px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {row.group_name}
                        </td>
                        <td style={{ textAlign: 'center', fontWeight: 600, color: row.today_success > 0 ? '#047857' : '#94a3b8' }}>
                          {row.today_success}
                        </td>
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <span style={{ fontWeight: 600, color: '#0f172a', minWidth: '24px' }}>{row.total_success}</span>
                            <div className="ripply-progress-track">
                              <div className="ripply-progress-fill" style={{ width: `${barWidth}%`, background: '#0f172a' }} />
                            </div>
                          </div>
                        </td>
                        <td style={{ textAlign: 'center', fontWeight: 600, color: row.total_failed > 0 ? '#dc2626' : '#cbd5e1' }}>
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
          <h2 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 700, color: '#0f172a' }}>
            Grupos Autorizados do WhatsApp
          </h2>
          <span style={{ fontSize: '0.74rem', color: '#64748b' }}>
            Clique para expandir origens e destinos
          </span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 260px), 1fr))', gap: '0.85rem' }}>
          <GroupDropdown
            label="Grupos de Origem (Monitorados)"
            groups={groups.sources || []}
            emptyText="Nenhum grupo de origem cadastrado"
            accent="blue"
          />
          <GroupDropdown
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
