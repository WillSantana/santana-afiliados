import React, { useState, useEffect } from 'react';
import MetricCard from '../components/MetricCard';
import { api } from '../services/api';

export default function AnalyticsPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const res = await api.getAnalytics();
        setData(res);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return <p style={{ textAlign: 'center', padding: '4rem', color: 'var(--gray-500)' }}>Carregando métricas e indicadores...</p>;
  }

  const metrics = data?.metrics || {};
  const targets = data?.illustrative_targets || {};
  const categories = data?.category_distribution || [];

  return (
    <div style={{ paddingBottom: '3rem' }}>
      <div style={{ marginBottom: '1.5rem' }}>
        <h2 style={{ fontSize: '1.35rem', fontWeight: 800, color: 'var(--gray-900)' }}>
          Painel de Indicadores & Metas Comerciais
        </h2>
        <p style={{ fontSize: '0.85rem', color: 'var(--gray-500)' }}>
          Acompanhamento do funil de afiliados, conversões e distinção entre projeções e resultados reais (Seção 3.9).
        </p>
      </div>

      {/* Grid de KPIs Principais */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
        <MetricCard
          title="Produtos Encontrados"
          value={metrics.products_found ?? 0}
          subtitle={`${metrics.products_pending ?? 0} aguardando aprovação`}
          icon="📦"
        />
        <MetricCard
          title="Ofertas Aprovadas"
          value={metrics.products_approved ?? 0}
          subtitle={`${metrics.products_rejected ?? 0} rejeitadas`}
          icon="✓"
          highlight={true}
        />
        <MetricCard
          title="Links Oficiais"
          value={metrics.links_registered ?? 0}
          subtitle="Links de afiliados ativos"
          icon="🔗"
        />
        <MetricCard
          title="Ofertas Publicadas"
          value={metrics.offers_published ?? 0}
          subtitle="Enviadas para WhatsApp"
          icon="📢"
        />
        <MetricCard
          title="Cliques Rastreados"
          value={metrics.clicks ?? 0}
          subtitle="Total de acessos gerados"
          icon="👆"
        />
        <MetricCard
          title="Taxa de Conversão"
          value={`${metrics.conversion_rate ?? 0}%`}
          subtitle={`${metrics.sales ?? 0} vendas atribuídas`}
          icon="📈"
          highlight={true}
        />
        <MetricCard
          title="Comissão Confirmada"
          value={`R$ ${(metrics.approved_commission ?? 0).toFixed(2)}`}
          subtitle={`Estimada: R$ ${(metrics.estimated_commission ?? 0).toFixed(2)}`}
          icon="💰"
          highlight={true}
        />
      </div>

      {/* Seção de Comparativo com Metas Hipotéticas (Seção 3.9) */}
      <div style={{
        background: 'white',
        borderRadius: 'var(--radius-md)',
        padding: '1.5rem',
        border: '1px solid var(--gray-200)',
        boxShadow: 'var(--shadow-sm)',
        marginBottom: '1.5rem',
      }}>
        <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--gray-900)', marginBottom: '0.5rem' }}>
          Tabela de Planejamento de Metas (Seção 3.9)
        </h3>
        <p style={{ fontSize: '0.8rem', color: 'var(--gray-500)', marginBottom: '1.25rem' }}>
          * Valores de planejamento inicial. O sistema distingue rigidamente hipóteses de resultados financeiros efetivamente confirmados.
        </p>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
            <thead>
              <tr style={{ background: 'var(--gray-50)', textAlign: 'left', borderBottom: '1.5px solid var(--gray-200)' }}>
                <th style={{ padding: '0.75rem' }}>Indicador</th>
                <th style={{ padding: '0.75rem' }}>Meta Hipotética Inicial</th>
                <th style={{ padding: '0.75rem' }}>Status Atual Registrado</th>
              </tr>
            </thead>
            <tbody>
              <tr style={{ borderBottom: '1px solid var(--gray-100)' }}>
                <td style={{ padding: '0.75rem', fontWeight: 600 }}>Ofertas publicadas</td>
                <td style={{ padding: '0.75rem' }}>{targets.daily_offers} por dia</td>
                <td style={{ padding: '0.75rem' }}>{metrics.offers_published} ofertas</td>
              </tr>
              <tr style={{ borderBottom: '1px solid var(--gray-100)' }}>
                <td style={{ padding: '0.75rem', fontWeight: 600 }}>Cliques nos links</td>
                <td style={{ padding: '0.75rem' }}>{targets.daily_clicks} por dia</td>
                <td style={{ padding: '0.75rem' }}>{metrics.clicks} cliques</td>
              </tr>
              <tr style={{ borderBottom: '1px solid var(--gray-100)' }}>
                <td style={{ padding: '0.75rem', fontWeight: 600 }}>Taxa de conversão</td>
                <td style={{ padding: '0.75rem' }}>{targets.target_conversion}%</td>
                <td style={{ padding: '0.75rem' }}>{metrics.conversion_rate}%</td>
              </tr>
              <tr style={{ borderBottom: '1px solid var(--gray-100)' }}>
                <td style={{ padding: '0.75rem', fontWeight: 600 }}>Vendas estimadas</td>
                <td style={{ padding: '0.75rem' }}>{targets.daily_sales} por dia</td>
                <td style={{ padding: '0.75rem' }}>{metrics.sales} vendas</td>
              </tr>
              <tr style={{ borderBottom: '1px solid var(--gray-100)' }}>
                <td style={{ padding: '0.75rem', fontWeight: 600 }}>Comissão média</td>
                <td style={{ padding: '0.75rem' }}>R$ {targets.average_commission?.toFixed(2)}</td>
                <td style={{ padding: '0.75rem' }}>-</td>
              </tr>
              <tr style={{ background: '#f0fdf4' }}>
                <td style={{ padding: '0.75rem', fontWeight: 700, color: '#166534' }}>Projeção mensal inicial</td>
                <td style={{ padding: '0.75rem', fontWeight: 700, color: '#166534' }}>R$ {targets.monthly_projection?.toFixed(2)}</td>
                <td style={{ padding: '0.75rem', fontWeight: 700, color: '#166534' }}>
                  Metas futuras: R$ 300, R$ 500, R$ 1.000 e R$ 2.000
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Distribuição por Categoria */}
      <div style={{
        background: 'white',
        borderRadius: 'var(--radius-md)',
        padding: '1.5rem',
        border: '1px solid var(--gray-200)',
        boxShadow: 'var(--shadow-sm)',
      }}>
        <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--gray-900)', marginBottom: '0.75rem' }}>
          Distribuição do Catálogo por Categoria
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem' }}>
          {categories.map((c) => (
            <div key={c.category} style={{ padding: '1rem', background: 'var(--gray-50)', borderRadius: 'var(--radius-sm)' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--gray-500)', textTransform: 'uppercase' }}>
                {c.category}
              </span>
              <div style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--gray-800)' }}>
                {c.total} anúncios
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
