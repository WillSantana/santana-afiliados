import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';
import { Icon } from '../components/Icons';

export default function DashboardPage({ onNavigateTab }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

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

  useEffect(() => {
    loadDashboard();
    const timer = setInterval(loadDashboard, 8000);
    return () => clearInterval(timer);
  }, [loadDashboard]);

  const botStatus = data?.bot_status || {};
  const metrics = data?.metrics || {};
  const groups = data?.groups || {};

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
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
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
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
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

      {/* Grupos Monitorados e Destinos */}
      <div style={{ background: 'white', borderRadius: 'var(--radius-md)', padding: '1.25rem', border: '1px solid var(--gray-200)', marginBottom: '1.5rem' }}>
        <h3 style={{ margin: '0 0 0.8rem 0', fontSize: '1rem', fontWeight: 700 }}>Grupos Autorizados do WhatsApp</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.5rem' }}>
          <div>
            <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#1e40af', marginBottom: '0.4rem', textTransform: 'uppercase' }}>
              📥 Grupos de Origem (Monitorados)
            </div>
            {groups.sources?.length ? (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
                {groups.sources.map((s, idx) => (
                  <span key={idx} style={{ padding: '0.3rem 0.6rem', background: '#eff6ff', color: '#1e40af', borderRadius: '4px', fontSize: '0.8rem', fontWeight: 600 }}>
                    {s}
                  </span>
                ))}
              </div>
            ) : (
              <div style={{ color: 'var(--gray-400)', fontSize: '0.85rem' }}>Nenhum grupo de origem cadastrado</div>
            )}
          </div>

          <div>
            <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#15803d', marginBottom: '0.4rem', textTransform: 'uppercase' }}>
              📤 Grupos de Destino (Recebem as Ofertas)
            </div>
            {groups.destinations?.length ? (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
                {groups.destinations.map((d, idx) => (
                  <span key={idx} style={{ padding: '0.3rem 0.6rem', background: '#f0fdf4', color: '#15803d', borderRadius: '4px', fontSize: '0.8rem', fontWeight: 600 }}>
                    {d}
                  </span>
                ))}
              </div>
            ) : (
              <div style={{ color: '#15803d', fontSize: '0.85rem', fontStyle: 'italic' }}>
                🤖 Modo automático — envia para todos os grupos do WhatsApp (use <code>--send-all-groups</code>)
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Tabelas de Visão Rápida */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '1.5rem' }}>
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
