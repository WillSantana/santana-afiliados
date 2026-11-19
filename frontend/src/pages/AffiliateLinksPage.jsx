import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';
import { Icon } from '../components/Icons';
import { useToast } from '../components/Toast';

export default function AffiliateLinksPage() {
  const { addToast } = useToast();
  const [links, setLinks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [copiedId, setCopiedId] = useState(null);

  const loadAffiliateLinks = useCallback(async () => {
    try {
      setError('');
      const data = await api.getAffiliateLinks();
      setLinks(data.results || []);
    } catch (err) {
      setError(err.message || 'Falha ao carregar links de afiliados');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAffiliateLinks();
    const timer = setInterval(loadAffiliateLinks, 10000);
    return () => clearInterval(timer);
  }, [loadAffiliateLinks]);

  const handleCopy = (id, url) => {
    navigator.clipboard.writeText(url);
    setCopiedId(id);
    addToast('Link de afiliado copiado para a área de transferência!', 'success');
    setTimeout(() => setCopiedId(null), 2500);
  };

  const filteredLinks = links.filter((item) => {
    const term = searchTerm.toLowerCase();
    return (
      item.product_title?.toLowerCase().includes(term) ||
      item.item_id?.toLowerCase().includes(term) ||
      item.affiliate_url?.toLowerCase().includes(term) ||
      item.source_link?.toLowerCase().includes(term)
    );
  });

  return (
    <div style={{ paddingBottom: '3rem' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h2 style={{ fontSize: '1.35rem', fontWeight: 800, color: 'var(--gray-900)', margin: 0 }}>
            Links de Afiliados Oficiais
          </h2>
          <p style={{ fontSize: '0.85rem', color: 'var(--gray-500)', margin: '0.25rem 0 0 0' }}>
            Registro de todos os links de afiliados gerados e validados no Mercado Livre.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button
            type="button"
            onClick={loadAffiliateLinks}
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

      {/* Busca e Resumo */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div style={{ position: 'relative', width: '300px' }}>
          <input
            type="text"
            placeholder="Buscar por produto, MLB ou link..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{
              width: '100%',
              padding: '0.5rem 0.8rem 0.5rem 2rem',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--gray-300)',
              fontSize: '0.85rem',
            }}
          />
          <div style={{ position: 'absolute', left: '0.6rem', top: '0.55rem', color: 'var(--gray-400)' }}>
            <Icon name="search" size={15} />
          </div>
        </div>
        <div style={{ fontSize: '0.85rem', color: 'var(--gray-600)', fontWeight: 600 }}>
          Total gerado: {links.length} link(s)
        </div>
      </div>

      {error && (
        <div style={{ padding: '0.8rem 1rem', marginBottom: '1rem', background: '#fef2f2', color: '#b91c1c', borderRadius: 'var(--radius-sm)', fontSize: '0.85rem' }}>
          {error}
        </div>
      )}

      {/* Tabela de Links de Afiliados */}
      <section style={{ background: 'white', borderRadius: 'var(--radius-md)', padding: '1.5rem', border: '1px solid var(--gray-200)' }}>
        {loading ? (
          <p style={{ color: 'var(--gray-500)' }}>Carregando links de afiliados...</p>
        ) : !filteredLinks.length ? (
          <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--gray-500)' }}>
            <Icon name="link" size={32} color="var(--gray-400)" />
            <p style={{ marginTop: '0.5rem', fontWeight: 600 }}>Nenhum link de afiliado encontrado.</p>
            <p style={{ fontSize: '0.8rem', color: 'var(--gray-400)' }}>
              Quando ofertas do Mercado Livre forem capturadas nos grupos de origem, os links oficiais gerados aparecerão aqui.
            </p>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
              <thead>
                <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--gray-200)', color: 'var(--gray-600)' }}>
                  <th style={{ padding: '0.65rem' }}>Produto</th>
                  <th style={{ padding: '0.65rem' }}>Anúncio Individual</th>
                  <th style={{ padding: '0.65rem' }}>Link de Afiliado (Oficial)</th>
                  <th style={{ padding: '0.65rem' }}>Data de Geração</th>
                  <th style={{ padding: '0.65rem' }}>Validação</th>
                  <th style={{ padding: '0.65rem', textAlign: 'center' }}>Ações</th>
                </tr>
              </thead>
              <tbody>
                {filteredLinks.map((item) => (
                  <tr key={item.id} style={{ borderBottom: '1px solid var(--gray-100)' }}>
                    <td style={{ padding: '0.65rem', maxWidth: '240px' }}>
                      <div style={{ fontWeight: 600, color: 'var(--gray-900)' }}>{item.product_title}</div>
                      {item.item_id && (
                        <div style={{ fontSize: '0.72rem', color: 'var(--gray-400)' }}>ID: {item.item_id}</div>
                      )}
                    </td>
                    <td style={{ padding: '0.65rem', maxWidth: '200px' }}>
                      <a
                        href={item.product_url || item.source_link}
                        target="_blank"
                        rel="noreferrer"
                        style={{ color: '#2563eb', wordBreak: 'break-all', fontSize: '0.8rem' }}
                      >
                        {item.product_url || item.source_link}
                      </a>
                    </td>
                    <td style={{ padding: '0.65rem', maxWidth: '220px' }}>
                      <a
                        href={item.affiliate_url}
                        target="_blank"
                        rel="noreferrer"
                        style={{ fontWeight: 700, color: '#16a34a', wordBreak: 'break-all', fontSize: '0.82rem' }}
                      >
                        {item.affiliate_url}
                      </a>
                    </td>
                    <td style={{ padding: '0.65rem', color: 'var(--gray-600)', fontSize: '0.8rem', whiteSpace: 'nowrap' }}>
                      {item.generated_at ? new Date(item.generated_at).toLocaleString() : '—'}
                    </td>
                    <td style={{ padding: '0.65rem', whiteSpace: 'nowrap' }}>
                      <span style={{
                        padding: '0.2rem 0.5rem',
                        borderRadius: '4px',
                        fontSize: '0.75rem',
                        fontWeight: 700,
                        background: item.is_valid ? '#dcfce7' : '#fef3c7',
                        color: item.is_valid ? '#166534' : '#b45309',
                      }}>
                        {item.validation_status}
                      </span>
                    </td>
                    <td style={{ padding: '0.65rem', textAlign: 'center' }}>
                      <button
                        type="button"
                        onClick={() => handleCopy(item.id, item.affiliate_url)}
                        style={{
                          padding: '0.35rem 0.65rem',
                          background: copiedId === item.id ? '#16a34a' : 'white',
                          color: copiedId === item.id ? 'white' : 'var(--gray-700)',
                          border: '1px solid var(--gray-300)',
                          borderRadius: 'var(--radius-sm)',
                          fontSize: '0.75rem',
                          fontWeight: 600,
                          cursor: 'pointer',
                        }}
                      >
                        {copiedId === item.id ? 'Copiado!' : 'Copiar'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
