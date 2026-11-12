import React, { useState, useEffect } from 'react';
import { api } from '../services/api';

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState([]);
  const [loading, setLoading] = useState(false);

  const fetchCampaigns = async () => {
    setLoading(true);
    try {
      const data = await api.getCampaigns();
      setCampaigns(data.results || data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCampaigns();
  }, []);

  return (
    <div style={{ paddingBottom: '3rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h2 style={{ fontSize: '1.35rem', fontWeight: 800, color: 'var(--gray-900)' }}>
            Campanhas Promocionais
          </h2>
          <p style={{ fontSize: '0.85rem', color: 'var(--gray-500)' }}>
            Organização temática de ofertas para divulgação direcionada.
          </p>
        </div>
        <button
          onClick={fetchCampaigns}
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

      {loading ? (
        <p style={{ textAlign: 'center', color: 'var(--gray-500)', padding: '3rem' }}>Carregando campanhas...</p>
      ) : campaigns.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '4rem 0', background: 'white', borderRadius: 'var(--radius-md)', border: '1px dashed var(--gray-300)' }}>
          <p style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--gray-700)' }}>
            Nenhuma campanha configurada.
          </p>
          <p style={{ fontSize: '0.85rem', color: 'var(--gray-500)', marginTop: '0.25rem' }}>
            As campanhas permitem agrupar ofertas por sazonidade (ex: Black Friday, Dia dos Pais, Gamer Week).
          </p>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '1.25rem' }}>
          {campaigns.map((camp) => (
            <div
              key={camp.id}
              style={{
                background: 'white',
                borderRadius: 'var(--radius-md)',
                padding: '1.25rem',
                border: '1px solid var(--gray-200)',
                boxShadow: 'var(--shadow-sm)',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--gray-500)', textTransform: 'uppercase' }}>
                  {camp.target_category || 'Geral'}
                </span>
                <span style={{ fontSize: '0.75rem', fontWeight: 600, color: camp.is_active ? 'var(--success)' : 'var(--gray-500)' }}>
                  {camp.is_active ? '● Ativa' : '○ Inativa'}
                </span>
              </div>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--gray-900)', marginBottom: '0.4rem' }}>
                {camp.name}
              </h3>
              <p style={{ fontSize: '0.85rem', color: 'var(--gray-600)', marginBottom: '1rem' }}>
                {camp.description || 'Sem descrição.'}
              </p>
              <div style={{ fontSize: '0.8rem', color: 'var(--gray-500)', borderTop: '1px solid var(--gray-100)', paddingTop: '0.75rem' }}>
                Produtos vinculados: <strong>{camp.products_count || 0}</strong>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
