import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';
import { Icon } from '../components/Icons';
import GroupDropdown from '../components/GroupDropdown';

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
  const metrics = data?.metrics || {};
  const groups = data?.groups || {};
  const storeMetrics = data?.store_metrics || [];
  const postsByGroup = data?.posts_by_group || [];
  const maxGroupPosts = Math.max(1, ...postsByGroup.map((item) => item.total_success || 0));

  return (
    <div style={{ paddingBottom: '3rem' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--gray-900)', margin: 0 }}>
            Painel Geral do Santana Afiliados Bot
          </h2>
          <p style={{ fontSize: '0.85rem', color: 'var(--gray-500)', margin: '0.25rem 0 0 0' }}>
            Visão consolidada de captura, conversão de afiliados e redistribuição nos grupos de WhatsApp.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button
            type="button"
            onClick={loadDashboard}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              padding: '0.5rem 0.9rem',
              background: 'white',
              border: '1px solid var(--gray-300)',
              borderRadius: 'var(--radius-sm)',
              fontSize: '0.85rem',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            <Icon name="refresh" size={16} />
            Atualizar
          </button>
        </div>
      </div>

      {error && (
        <div style={{ padding: '0.8rem 1rem', marginBottom: '1rem', background: '#fef2f2', color: '#b91c1c', borderRadius: 'var(--radius-sm)', fontSize: '0.85rem' }}>
          Erro ao atualizar dados: {error}
        </div>
      )}

      {/* Status das Conexões e do Bot */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 240px), 1fr))', gap: '0.85rem', marginBottom: '1.25rem' }}>
        {/* Status do Monitor */}
        <div style={{ background: 'white', borderRadius: 'var(--radius-md)', padding: '1.25rem', border: '1px solid var(--gray-200)', display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{
            width: '44px',
            height: '44px',
            borderRadius: '50%',
            background: botStatus.running ? '#dcfce7' : '#fee2e2',
            color: botStatus.running ? '#16a34a' : '#dc2626',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontWeight: 800,
          }}>
            <Icon name="zap" size={22} color={botStatus.running ? '#16a34a' : '#dc2626'} />
          </div>
          <div>
            <div style={{ fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', color: 'var(--gray-500)' }}>Status do Monitor</div>
            <div style={{ fontSize: '1.1rem', fontWeight: 800, color: botStatus.running ? '#16a34a' : '#dc2626' }}>
              {botStatus.running ? 'Monitor Ativo (Rodando)' : 'Monitor Parado'}
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--gray-500)' }}>
              {botStatus.running ? 'Processando grupos em tempo real' : 'Execute o comando com --send'}
            </div>
          </div>
        </div>

        {/* Conexão com o Chrome */}
        <div style={{ background: 'white', borderRadius: 'var(--radius-md)', padding: '1.25rem', border: '1px solid var(--gray-200)', display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{
            width: '44px',
            height: '44px',
            borderRadius: '50%',
            background: botStatus.chrome_connected ? '#dcfce7' : '#fef3c7',
            color: botStatus.chrome_connected ? '#16a34a' : '#d97706',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <Icon name="external" size={22} color={botStatus.chrome_connected ? '#16a34a' : '#d97706'} />
          </div>
          <div>
            <div style={{ fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', color: 'var(--gray-500)' }}>Chrome Depuração (Porta 9222)</div>
            <div style={{ fontSize: '1.1rem', fontWeight: 800, color: botStatus.chrome_connected ? '#16a34a' : '#d97706' }}>
              {botStatus.chrome_connected ? 'Conectado (Porta 9222)' : 'Desconectado'}
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--gray-500)' }}>
              {botStatus.chrome_connected ? 'WhatsApp Web & Mercado Livre prontos' : 'Inicie iniciar_chrome_whatsapp.bat'}
            </div>
          </div>
        </div>

        {/* Limite Diário de Envios */}
        <div style={{ background: 'white', borderRadius: 'var(--radius-md)', padding: '1.25rem', border: '1px solid var(--gray-200)', display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{
            width: '44px',
            height: '44px',
            borderRadius: '50%',
            background: '#e0f2fe',
            color: '#0284c7',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <Icon name="trendingUp" size={22} color="#0284c7" />
          </div>
          <div>
            <div style={{ fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', color: 'var(--gray-500)' }}>Envios Realizados Hoje</div>
            <div style={{ fontSize: '1.1rem', fontWeight: 800, color: '#0369a1' }}>
              {botStatus.today_sent || 0} / {botStatus.daily_limit || 20} envios
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--gray-500)' }}>
              Limite configurado por segurança
            </div>
          </div>
        </div>
      </div>

      {/* Cards de Métricas Principais */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 155px), 1fr))', gap: '0.85rem', marginBottom: '1.25rem' }}>
        <div
          onClick={() => onNavigateTab && onNavigateTab('automation')}
          style={{ background: 'white', borderRadius: 'var(--radius-md)', padding: '1.25rem', border: '1px solid var(--gray-200)', cursor: 'pointer', transition: 'transform 0.15s' }}
        >
          <div style={{ fontSize: '0.78rem', color: 'var(--gray-500)', fontWeight: 600 }}>OFERTAS ENCONTRADAS</div>
          <div style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--gray-900)', marginTop: '0.25rem' }}>
            {metrics.total_offers || 0}
          </div>
          <div style={{ fontSize: '0.75rem', color: '#2563eb', marginTop: '0.25rem' }}>
            {metrics.pending_offers || 0} na fila de conversão
          </div>
        </div>

        <div
          onClick={() => onNavigateTab && onNavigateTab('affiliates')}
          style={{ background: 'white', borderRadius: 'var(--radius-md)', padding: '1.25rem', border: '1px solid var(--gray-200)', cursor: 'pointer' }}
        >
          <div style={{ fontSize: '0.78rem', color: 'var(--gray-500)', fontWeight: 600 }}>LINKS DE AFILIADOS</div>
          <div style={{ fontSize: '1.8rem', fontWeight: 800, color: '#16a34a', marginTop: '0.25rem' }}>
            {metrics.affiliates_generated || 0}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--gray-500)', marginTop: '0.25rem' }}>
            Links oficiais gerados no ML
          </div>
        </div>

        <div
          onClick={() => onNavigateTab && onNavigateTab('publications')}
          style={{ background: 'white', borderRadius: 'var(--radius-md)', padding: '1.25rem', border: '1px solid var(--gray-200)', cursor: 'pointer' }}
        >
          <div style={{ fontSize: '0.78rem', color: 'var(--gray-500)', fontWeight: 600 }}>PUBLICAÇÕES (SUCESSO)</div>
          <div style={{ fontSize: '1.8rem', fontWeight: 800, color: '#059669', marginTop: '0.25rem' }}>
            {metrics.deliveries_success || 0}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--gray-500)', marginTop: '0.25rem' }}>
            Disparos entregues aos grupos
          </div>
        </div>

        <div
          onClick={() => onNavigateTab && onNavigateTab('publications')}
          style={{ background: 'white', borderRadius: 'var(--radius-md)', padding: '1.25rem', border: '1px solid var(--gray-200)', cursor: 'pointer' }}
        >
          <div style={{ fontSize: '0.78rem', color: 'var(--gray-500)', fontWeight: 600 }}>FALHAS DE ENVIO</div>
          <div style={{ fontSize: '1.8rem', fontWeight: 800, color: (metrics.deliveries_failed || 0) > 0 ? '#dc2626' : 'var(--gray-500)', marginTop: '0.25rem' }}>
            {metrics.deliveries_failed || 0}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--gray-500)', marginTop: '0.25rem' }}>
            {metrics.deliveries_uncertain || 0} envios incertos
          </div>
        </div>
      </div>

      {/* Métricas por Loja (Mercado Livre / Amazon) */}
      {storeMetrics.length > 0 && (
        <div style={{ marginBottom: '1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.65rem', flexWrap: 'wrap', gap: '0.5rem' }}>
            <div>
              <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, color: 'var(--gray-900)' }}>
                Métricas por Loja
              </h3>
              <span style={{ fontSize: '0.78rem', color: 'var(--gray-500)' }}>
                Acompanhamento separado por marketplace (com cliques oficiais)
              </span>
            </div>
            <button
              type="button"
              onClick={handleSyncClicks}
              disabled={syncingClicks}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.35rem',
                padding: '0.4rem 0.75rem',
                background: 'white',
                border: '1px solid var(--gray-300)',
                borderRadius: 'var(--radius-sm)',
                fontSize: '0.78rem',
                fontWeight: 600,
                cursor: syncingClicks ? 'wait' : 'pointer',
              }}
            >
              <Icon name="refresh" size={14} />
              {syncingClicks ? 'Sincronizando cliques...' : 'Sincronizar Cliques'}
            </button>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 280px), 1fr))', gap: '0.85rem' }}>
            {storeMetrics.map((item) => {
              const isAmazon = item.store === 'amazon';
              const isShopee = item.store === 'shopee';
              const accentBg = isShopee ? '#fff1f2' : isAmazon ? '#fff7ed' : '#fefce8';
              const accentBorder = isShopee ? '#fecdd3' : isAmazon ? '#fed7aa' : '#fde047';
              const badgeBg = isShopee ? '#ee4d2d' : isAmazon ? '#ea580c' : '#eab308';
              const badgeColor = (isShopee || isAmazon) ? '#ffffff' : '#1e293b';
              const pillColor = isShopee ? '#be123c' : isAmazon ? '#c2410c' : '#854d0e';
              return (
                <div
                  key={item.store}
                  style={{
                    background: 'white',
                    borderRadius: 'var(--radius-md)',
                    padding: '1.1rem 1.25rem',
                    border: `1px solid ${accentBorder}`,
                    borderLeft: `4px solid ${badgeBg}`,
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.8rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <span style={{
                        padding: '0.2rem 0.55rem',
                        borderRadius: '999px',
                        fontSize: '0.72rem',
                        fontWeight: 800,
                        background: badgeBg,
                        color: badgeColor,
                      }}>
                        {item.label}
                      </span>
                      <span style={{ fontSize: '0.75rem', color: 'var(--gray-500)' }}>
                        {item.pending_offers} na fila
                      </span>
                    </div>
                    <span style={{
                      fontSize: '0.75rem',
                      fontWeight: 700,
                      padding: '0.15rem 0.5rem',
                      borderRadius: '999px',
                      background: accentBg,
                      color: pillColor,
                    }}>
                      {item.deliveries_today} envio(s) hoje{item.daily_quota ? ` • meta ${item.daily_quota}` : ''}
                    </span>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(95px, 1fr))', gap: '0.6rem' }}>
                    <div style={{ background: '#f8fafc', borderRadius: '8px', padding: '0.6rem 0.7rem' }}>
                      <div style={{ fontSize: '0.68rem', fontWeight: 600, color: 'var(--gray-500)', textTransform: 'uppercase' }}>Links Capturados</div>
                      <div style={{ fontSize: '1.3rem', fontWeight: 800, color: 'var(--gray-900)', marginTop: '0.15rem' }}>
                        {item.offers_found}
                      </div>
                    </div>
                    <div style={{ background: '#f8fafc', borderRadius: '8px', padding: '0.6rem 0.7rem' }}>
                      <div style={{ fontSize: '0.68rem', fontWeight: 600, color: 'var(--gray-500)', textTransform: 'uppercase' }}>Links Afiliados</div>
                      <div style={{ fontSize: '1.3rem', fontWeight: 800, color: '#16a34a', marginTop: '0.15rem' }}>
                        {item.affiliates_generated}
                      </div>
                    </div>
                    <div style={{ background: '#f8fafc', borderRadius: '8px', padding: '0.6rem 0.7rem' }}>
                      <div style={{ fontSize: '0.68rem', fontWeight: 600, color: 'var(--gray-500)', textTransform: 'uppercase' }}>Envios Totais</div>
                      <div style={{ fontSize: '1.3rem', fontWeight: 800, color: '#0284c7', marginTop: '0.15rem' }}>
                        {item.deliveries_total}
                      </div>
                    </div>
                    <div style={{ background: '#f8fafc', borderRadius: '8px', padding: '0.6rem 0.7rem' }}>
                      <div style={{ fontSize: '0.68rem', fontWeight: 600, color: 'var(--gray-500)', textTransform: 'uppercase' }}>Cliques Oficiais</div>
                      <div style={{ fontSize: '1.3rem', fontWeight: 800, color: '#7c3aed', marginTop: '0.15rem' }}>
                        {item.clicks_month ?? 0}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Grupos Monitorados e Destinos */}
      <div style={{ background: 'white', borderRadius: 'var(--radius-md)', padding: '1.25rem', border: '1px solid var(--gray-200)', marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.85rem', flexWrap: 'wrap', gap: '0.5rem' }}>
          <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 700 }}>Grupos Autorizados do WhatsApp</h3>
          <span style={{ fontSize: '0.78rem', color: 'var(--gray-500)' }}>
            Clique para expandir a lista de grupos
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
            emptyText="Modo automático — envia para todos os grupos do WhatsApp"
            accent="green"
          />
        </div>
      </div>

      {/* Posts por Grupo */}
      <div style={{ background: 'white', borderRadius: 'var(--radius-md)', padding: '1.25rem', border: '1px solid var(--gray-200)', marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.85rem', flexWrap: 'wrap', gap: '0.5rem' }}>
          <div>
            <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 700 }}>Posts por Grupo</h3>
            <p style={{ margin: '0.2rem 0 0 0', fontSize: '0.78rem', color: 'var(--gray-500)' }}>
              Total de ofertas enviadas com sucesso em cada grupo (hoje e acumulado).
            </p>
          </div>
          <span style={{ fontSize: '0.78rem', fontWeight: 600, color: '#059669', background: '#ecfdf5', padding: '0.25rem 0.6rem', borderRadius: '999px' }}>
            {postsByGroup.length} grupo(s)
          </span>
        </div>
        {!postsByGroup.length ? (
          <p style={{ color: 'var(--gray-500)', fontSize: '0.85rem', margin: 0 }}>Nenhum envio registrado por grupo ainda.</p>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem' }}>
              <thead>
                <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--gray-200)', color: 'var(--gray-500)' }}>
                  <th style={{ padding: '0.5rem 0.6rem' }}>Grupo</th>
                  <th style={{ padding: '0.5rem 0.6rem', textAlign: 'center', width: '90px' }}>Hoje</th>
                  <th style={{ padding: '0.5rem 0.6rem', width: '210px' }}>Total Enviados</th>
                  <th style={{ padding: '0.5rem 0.6rem', textAlign: 'center', width: '90px' }}>Falhas</th>
                  <th style={{ padding: '0.5rem 0.6rem', textAlign: 'right', width: '130px' }}>Último Envio</th>
                </tr>
              </thead>
              <tbody>
                {postsByGroup.map((row) => {
                  const barWidth = Math.round(((row.total_success || 0) / maxGroupPosts) * 100);
                  return (
                    <tr key={row.group_name} style={{ borderBottom: '1px solid var(--gray-100)' }}>
                      <td style={{ padding: '0.55rem 0.6rem', fontWeight: 600, color: 'var(--gray-900)' }}>
                        {row.group_name}
                      </td>
                      <td style={{ padding: '0.55rem 0.6rem', textAlign: 'center' }}>
                        <span style={{
                          display: 'inline-block',
                          minWidth: '28px',
                          padding: '0.15rem 0.45rem',
                          borderRadius: '999px',
                          fontSize: '0.75rem',
                          fontWeight: 700,
                          background: row.today_success > 0 ? '#e0f2fe' : '#f1f5f9',
                          color: row.today_success > 0 ? '#0369a1' : '#64748b',
                        }}>
                          {row.today_success}
                        </span>
                      </td>
                      <td style={{ padding: '0.55rem 0.6rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                          <span style={{ fontWeight: 800, color: '#059669', minWidth: '28px' }}>
                            {row.total_success}
                          </span>
                          <div style={{ flex: 1, height: '8px', background: '#f1f5f9', borderRadius: '999px', overflow: 'hidden' }}>
                            <div style={{
                              width: `${barWidth}%`,
                              height: '100%',
                              background: '#10b981',
                              borderRadius: '999px',
                            }} />
                          </div>
                        </div>
                      </td>
                      <td style={{ padding: '0.55rem 0.6rem', textAlign: 'center' }}>
                        <span style={{
                          fontWeight: 700,
                          color: row.total_failed > 0 ? '#dc2626' : '#94a3b8',
                        }}>
                          {row.total_failed}
                        </span>
                      </td>
                      <td style={{ padding: '0.55rem 0.6rem', textAlign: 'right', color: 'var(--gray-500)' }}>
                        {row.last_sent_at
                          ? new Date(row.last_sent_at).toLocaleString([], {
                            day: '2-digit',
                            month: '2-digit',
                            hour: '2-digit',
                            minute: '2-digit',
                          })
                          : '—'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Tabelas de Visão Rápida */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 340px), 1fr))', gap: '1.25rem' }}>
        {/* Últimos Envios por Grupo */}
        <div style={{ background: 'white', borderRadius: 'var(--radius-md)', padding: '1.25rem', border: '1px solid var(--gray-200)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.8rem' }}>
            <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 700 }}>Últimos Envios por Grupo</h3>
            <button
              type="button"
              onClick={() => onNavigateTab && onNavigateTab('publications')}
              style={{ background: 'none', border: 'none', color: '#2563eb', fontSize: '0.8rem', fontWeight: 600, cursor: 'pointer' }}
            >
              Ver todos →
            </button>
          </div>
          {!data?.recent_deliveries?.length ? (
            <p style={{ color: 'var(--gray-500)', fontSize: '0.85rem' }}>Nenhum envio registrado ainda.</p>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
                <thead>
                  <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--gray-200)', color: 'var(--gray-500)' }}>
                    <th style={{ padding: '0.4rem' }}>Produto</th>
                    <th style={{ padding: '0.4rem' }}>Destino</th>
                    <th style={{ padding: '0.4rem' }}>Status</th>
                    <th style={{ padding: '0.4rem' }}>Horário</th>
                  </tr>
                </thead>
                <tbody>
                  {data.recent_deliveries.slice(0, 5).map((del) => (
                    <tr key={del.id} style={{ borderBottom: '1px solid var(--gray-100)' }}>
                      <td style={{ padding: '0.5rem', fontWeight: 600, maxWidth: '160px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {del.product_title}
                      </td>
                      <td style={{ padding: '0.5rem' }}>{del.target_group_name}</td>
                      <td style={{ padding: '0.5rem' }}>
                        <span style={{
                          padding: '0.15rem 0.45rem',
                          borderRadius: '4px',
                          fontSize: '0.72rem',
                          fontWeight: 700,
                          background: del.status === 'success' ? '#dcfce7' : '#fee2e2',
                          color: del.status === 'success' ? '#166534' : '#b91c1c',
                        }}>
                          {del.status === 'success' ? 'Enviado' : 'Falha'}
                        </span>
                      </td>
                      <td style={{ padding: '0.5rem', color: 'var(--gray-500)' }}>
                        {new Date(del.sent_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Últimas Ofertas Capturadas */}
        <div style={{ background: 'white', borderRadius: 'var(--radius-md)', padding: '1.25rem', border: '1px solid var(--gray-200)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.8rem' }}>
            <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 700 }}>Últimas Ofertas Capturadas</h3>
            <button
              type="button"
              onClick={() => onNavigateTab && onNavigateTab('automation')}
              style={{ background: 'none', border: 'none', color: '#2563eb', fontSize: '0.8rem', fontWeight: 600, cursor: 'pointer' }}
            >
              Ver todas →
            </button>
          </div>
          {!data?.recent_offers?.length ? (
            <p style={{ color: 'var(--gray-500)', fontSize: '0.85rem' }}>Nenhuma oferta encontrada até o momento.</p>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
                <thead>
                  <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--gray-200)', color: 'var(--gray-500)' }}>
                    <th style={{ padding: '0.4rem' }}>Produto / Link</th>
                    <th style={{ padding: '0.4rem' }}>Origem</th>
                    <th style={{ padding: '0.4rem' }}>Status</th>
                    <th style={{ padding: '0.4rem' }}>Horário</th>
                  </tr>
                </thead>
                <tbody>
                  {data.recent_offers.slice(0, 5).map((off) => (
                    <tr key={off.id} style={{ borderBottom: '1px solid var(--gray-100)' }}>
                      <td style={{ padding: '0.5rem', maxWidth: '160px' }}>
                        <div style={{ fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {off.product_title || 'Link recebido'}
                        </div>
                        <a href={off.source_link} target="_blank" rel="noreferrer" style={{ fontSize: '0.72rem', color: '#2563eb' }}>
                          Abrir link
                        </a>
                      </td>
                      <td style={{ padding: '0.5rem' }}>{off.source_group}</td>
                      <td style={{ padding: '0.5rem', fontWeight: 600 }}>
                        <span style={{
                          padding: '0.15rem 0.45rem',
                          borderRadius: '4px',
                          fontSize: '0.72rem',
                          background: off.status === 'published' ? '#dcfce7' : off.status === 'pending' ? '#dbeafe' : '#f3f4f6',
                          color: off.status === 'published' ? '#166534' : off.status === 'pending' ? '#1d4ed8' : '#4b5563',
                        }}>
                          {off.status}
                        </span>
                      </td>
                      <td style={{ padding: '0.5rem', color: 'var(--gray-500)' }}>
                        {new Date(off.received_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
