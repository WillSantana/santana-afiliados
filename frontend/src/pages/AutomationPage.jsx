import React, { useState, useEffect } from 'react';
import { api } from '../services/api';

export default function AutomationPage() {
  const [config, setConfig] = useState(null);
  const [runs, setRuns] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);

  const loadData = async () => {
    try {
      const [cfgData, runsData, alertsData] = await Promise.all([
        api.getAutomationConfig(),
        api.getSearchRuns(),
        api.getPriceAlerts(),
      ]);
      setConfig(cfgData);
      setRuns(runsData.results || runsData);
      setAlerts(alertsData.results || alertsData);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleToggleSearches = async () => {
    if (!config) return;
    try {
      const updated = await api.updateAutomationConfig({
        searches_enabled: !config.searches_enabled,
      });
      setConfig(updated);
    } catch (err) {
      alert(`Erro: ${err.message}`);
    }
  };

  const handleToggleMonitoring = async () => {
    if (!config) return;
    try {
      const updated = await api.updateAutomationConfig({
        price_monitoring_enabled: !config.price_monitoring_enabled,
      });
      setConfig(updated);
    } catch (err) {
      alert(`Erro: ${err.message}`);
    }
  };

  const handleTriggerSearch = async () => {
    setActionLoading(true);
    try {
      const res = await api.triggerSearchCycle(0);
      alert('Ciclo de pesquisa concluído com sucesso!');
      await loadData();
    } catch (err) {
      alert(`Falha no ciclo de busca: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleTriggerMonitor = async () => {
    setActionLoading(true);
    try {
      const res = await api.triggerPriceMonitoring(40);
      alert(`Ciclo de monitoramento concluído! Verificados: ${res.checked_count}, Novos alertas: ${res.alerts_count}`);
      await loadData();
    } catch (err) {
      alert(`Falha no monitoramento: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleAcknowledgeAlert = async (id) => {
    try {
      await api.acknowledgeAlert(id);
      await loadData();
    } catch (err) {
      alert(`Erro ao reconhecer alerta: ${err.message}`);
    }
  };

  if (loading) {
    return <p style={{ textAlign: 'center', padding: '4rem', color: 'var(--gray-500)' }}>Carregando dados do motor de automação...</p>;
  }

  return (
    <div style={{ paddingBottom: '3rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h2 style={{ fontSize: '1.35rem', fontWeight: 800, color: 'var(--gray-900)' }}>
            Motor de Automação & Monitoramento (V1.2)
          </h2>
          <p style={{ fontSize: '0.85rem', color: 'var(--gray-500)' }}>
            Coordenação dos 6 ciclos diários de pesquisa, monitoramento de preços a cada 2h e alertas de oportunidade.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button
            onClick={loadData}
            style={{
              padding: '0.5rem 0.9rem',
              background: 'white',
              border: '1px solid var(--gray-300)',
              borderRadius: 'var(--radius-sm)',
              fontSize: '0.85rem',
              fontWeight: 600,
            }}
          >
            🔄 Atualizar
          </button>
        </div>
      </div>

      {/* Painel de Controles e Disparadores */}
      <div style={{
        background: 'white',
        borderRadius: 'var(--radius-md)',
        padding: '1.5rem',
        border: '1px solid var(--gray-200)',
        boxShadow: 'var(--shadow-sm)',
        marginBottom: '1.5rem',
      }}>
        <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--gray-900)', marginBottom: '1rem' }}>
          Configurações e Controles em Tempo Real
        </h3>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1.25rem', marginBottom: '1.25rem' }}>
          {/* Card Pesquisas */}
          <div style={{ padding: '1rem', background: 'var(--gray-50)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--gray-200)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
              <span style={{ fontSize: '0.85rem', fontWeight: 700 }}>Pesquisas Programadas</span>
              <span style={{ fontSize: '0.75rem', fontWeight: 700, color: config?.searches_enabled ? 'var(--success)' : 'var(--danger)' }}>
                {config?.searches_enabled ? '● ATIVAS (6x/dia)' : '○ PAUSADAS'}
              </span>
            </div>
            <p style={{ fontSize: '0.78rem', color: 'var(--gray-600)', marginBottom: '0.75rem' }}>
              Horários: 08h, 10h, 12h, 14h, 16h e 18h com rotação de termos nas 4 categorias.
            </p>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button
                onClick={handleToggleSearches}
                style={{
                  padding: '0.4rem 0.75rem',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '0.78rem',
                  fontWeight: 600,
                  backgroundColor: config?.searches_enabled ? '#fee2e2' : '#dcfce7',
                  color: config?.searches_enabled ? '#b91c1c' : '#15803d',
                }}
              >
                {config?.searches_enabled ? 'Pausar Ciclos' : 'Ativar Ciclos'}
              </button>
              <button
                disabled={actionLoading}
                onClick={handleTriggerSearch}
                style={{
                  padding: '0.4rem 0.75rem',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '0.78rem',
                  fontWeight: 600,
                  backgroundColor: 'var(--primary)',
                  color: 'white',
                }}
              >
                ▶ Executar Ciclo Agora
              </button>
            </div>
          </div>

          {/* Card Monitoramento */}
          <div style={{ padding: '1rem', background: 'var(--gray-50)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--gray-200)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
              <span style={{ fontSize: '0.85rem', fontWeight: 700 }}>Monitor de Preços</span>
              <span style={{ fontSize: '0.75rem', fontWeight: 700, color: config?.price_monitoring_enabled ? 'var(--success)' : 'var(--danger)' }}>
                {config?.price_monitoring_enabled ? '● ATIVO (a cada 2h)' : '○ PAUSADO'}
              </span>
            </div>
            <p style={{ fontSize: '0.78rem', color: 'var(--gray-600)', marginBottom: '0.75rem' }}>
              Janela: 08:30 às 20:30. Dispara alerta para reduções de preço ≥ {config?.price_drop_threshold}%.
            </p>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button
                onClick={handleToggleMonitoring}
                style={{
                  padding: '0.4rem 0.75rem',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '0.78rem',
                  fontWeight: 600,
                  backgroundColor: config?.price_monitoring_enabled ? '#fee2e2' : '#dcfce7',
                  color: config?.price_monitoring_enabled ? '#b91c1c' : '#15803d',
                }}
              >
                {config?.price_monitoring_enabled ? 'Pausar Monitor' : 'Ativar Monitor'}
              </button>
              <button
                disabled={actionLoading}
                onClick={handleTriggerMonitor}
                style={{
                  padding: '0.4rem 0.75rem',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '0.78rem',
                  fontWeight: 600,
                  backgroundColor: 'var(--primary)',
                  color: 'white',
                }}
              >
                ▶ Monitorar Agora
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Alertas de Variação de Preço (Seção 10) */}
      <div style={{
        background: 'white',
        borderRadius: 'var(--radius-md)',
        padding: '1.5rem',
        border: '1px solid var(--gray-200)',
        boxShadow: 'var(--shadow-sm)',
        marginBottom: '1.5rem',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--gray-900)' }}>
            🚨 Alertas de Queda de Preço Detectados (≥ {config?.price_drop_threshold}%)
          </h3>
          <span style={{ fontSize: '0.8rem', color: 'var(--gray-500)' }}>
            Exige nova aprovação antes de qualquer nova publicação
          </span>
        </div>

        {alerts.length === 0 ? (
          <p style={{ color: 'var(--gray-500)', fontSize: '0.875rem' }}>Nenhum alerta de preço pendente.</p>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '1rem' }}>
            {alerts.map((alert) => (
              <div
                key={alert.id}
                style={{
                  padding: '1rem',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid #fed7aa',
                  background: alert.is_acknowledged ? '#f9fafb' : '#fff7ed',
                  display: 'flex',
                  flexDirection: 'column',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
                  <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#c2410c' }}>
                    QUEDA DE -{alert.discount_percentage}%
                  </span>
                  <span style={{ fontSize: '0.7rem', color: 'var(--gray-500)' }}>
                    {new Date(alert.created_at).toLocaleDateString()}
                  </span>
                </div>

                <div style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--gray-900)', marginBottom: '0.5rem' }}>
                  {alert.product_title}
                </div>

                <div style={{ fontSize: '0.85rem', marginBottom: '0.75rem' }}>
                  De <span style={{ textDecoration: 'line-through', color: 'var(--gray-500)' }}>R$ {Number(alert.old_price).toFixed(2)}</span> para{' '}
                  <strong style={{ color: 'var(--success)' }}>R$ {Number(alert.new_price).toFixed(2)}</strong>
                </div>

                <div style={{ marginTop: 'auto', display: 'flex', justifyContent: 'flex-end' }}>
                  {!alert.is_acknowledged ? (
                    <button
                      onClick={() => handleAcknowledgeAlert(alert.id)}
                      style={{
                        padding: '0.35rem 0.75rem',
                        borderRadius: 'var(--radius-sm)',
                        background: '#ea580c',
                        color: 'white',
                        fontSize: '0.75rem',
                        fontWeight: 600,
                      }}
                    >
                      ✓ Marcar como Revisado
                    </button>
                  ) : (
                    <span style={{ fontSize: '0.75rem', color: 'var(--gray-500)', fontWeight: 600 }}>✓ Revisado</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Histórico de Ciclos de Pesquisa (SearchRun - Seção 9.2) */}
      <div style={{
        background: 'white',
        borderRadius: 'var(--radius-md)',
        padding: '1.5rem',
        border: '1px solid var(--gray-200)',
        boxShadow: 'var(--shadow-sm)',
      }}>
        <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--gray-900)', marginBottom: '0.5rem' }}>
          Histórico e Auditoria de Pesquisas (SearchRun)
        </h3>
        <p style={{ fontSize: '0.8rem', color: 'var(--gray-500)', marginBottom: '1rem' }}>
          Registro imutável de cada ciclo de pesquisa programado ou manual com contadores de produtos e duração.
        </p>

        {runs.length === 0 ? (
          <p style={{ color: 'var(--gray-500)', fontSize: '0.875rem' }}>Nenhum ciclo registrado ainda.</p>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
              <thead>
                <tr style={{ background: 'var(--gray-50)', textAlign: 'left', borderBottom: '1.5px solid var(--gray-200)' }}>
                  <th style={{ padding: '0.65rem' }}>Categoria</th>
                  <th style={{ padding: '0.65rem' }}>Termo Pesquisado</th>
                  <th style={{ padding: '0.65rem' }}>Data/Hora</th>
                  <th style={{ padding: '0.65rem' }}>Encontrados</th>
                  <th style={{ padding: '0.65rem' }}>Criados</th>
                  <th style={{ padding: '0.65rem' }}>Atualizados</th>
                  <th style={{ padding: '0.65rem' }}>Duração</th>
                  <th style={{ padding: '0.65rem' }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((r) => (
                  <tr key={r.id} style={{ borderBottom: '1px solid var(--gray-100)' }}>
                    <td style={{ padding: '0.65rem', fontWeight: 600 }}>{r.category}</td>
                    <td style={{ padding: '0.65rem' }}>{r.search_term}</td>
                    <td style={{ padding: '0.65rem' }}>{new Date(r.started_at).toLocaleString()}</td>
                    <td style={{ padding: '0.65rem' }}>{r.products_found}</td>
                    <td style={{ padding: '0.65rem', color: 'var(--success)', fontWeight: 600 }}>+{r.products_created}</td>
                    <td style={{ padding: '0.65rem' }}>{r.products_updated}</td>
                    <td style={{ padding: '0.65rem' }}>{r.duration_seconds}s</td>
                    <td style={{ padding: '0.65rem' }}>
                      <span style={{
                        padding: '0.15rem 0.45rem',
                        borderRadius: '4px',
                        fontSize: '0.72rem',
                        fontWeight: 700,
                        background: r.status === 'completed' ? '#dcfce7' : '#fee2e2',
                        color: r.status === 'completed' ? '#166534' : '#991b1b',
                      }}>
                        {r.status.toUpperCase()}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
