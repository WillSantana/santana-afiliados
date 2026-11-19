import React, { useCallback, useEffect, useState } from 'react';
import { api } from '../services/api';
import WhatsAppConfigModal from '../components/WhatsAppConfigModal';
import GroupDropdown from '../components/GroupDropdown';
import { Icon } from '../components/Icons';

const statusLabels = {
  ignored: 'Já existia ao iniciar',
  pending: 'Na fila',
  preparing: 'Preparando afiliado',
  processing: 'Processando',
  prepared: 'Pronta para envio',
  published: 'Publicada',
  skipped: 'Ignorada (duplicada)',
  failed: 'Falha no processamento',
  uncertain: 'Envio incerto',
};

const statusColors = {
  published: '#166534',
  pending: '#1d4ed8',
  preparing: '#b45309',
  processing: '#7c3aed',
  prepared: '#0369a1',
  failed: '#b91c1c',
  uncertain: '#b45309',
  ignored: '#6b7280',
  skipped: '#6b7280',
};

const statusBgColors = {
  published: '#dcfce7',
  pending: '#dbeafe',
  preparing: '#fef3c7',
  processing: '#f3e8ff',
  prepared: '#e0f2fe',
  failed: '#fee2e2',
  uncertain: '#fef3c7',
  ignored: '#f3f4f6',
  skipped: '#f3f4f6',
};

export default function AutomationPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [groups, setGroups] = useState([]);
  const [isConfigModalOpen, setIsConfigModalOpen] = useState(false);
  const [selectedMessage, setSelectedMessage] = useState(null);
  const [statusFilter, setStatusFilter] = useState('all');

  const loadGroups = useCallback(async () => {
    try {
      const config = await api.getWhatsAppGroups();
      setGroups(config.groups || []);
    } catch (err) {
      setError(err.message);
    }
  }, []);

  const loadData = useCallback(async () => {
    try {
      setError('');
      const res = await api.getIncomingOffers();
      setData(res);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    loadGroups();
    const timer = window.setInterval(loadData, 8000);
    return () => window.clearInterval(timer);
  }, [loadData, loadGroups]);

  const handleSaveGroups = async (updatedGroups) => {
    const saved = await api.saveWhatsAppGroups(updatedGroups);
    setGroups(saved.groups || []);
    await loadData();
    return saved.groups || [];
  };

  const results = data?.results || [];
  const filteredResults = results.filter((item) => {
    if (statusFilter === 'all') return true;
    if (statusFilter === 'pending') return item.status === 'pending' || item.status === 'preparing' || item.status === 'processing';
    if (statusFilter === 'published') return item.status === 'published';
    if (statusFilter === 'failed') return item.status === 'failed' || item.status === 'uncertain';
    return item.status === statusFilter;
  });

  return (
    <div style={{ paddingBottom: '3rem' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h2 style={{ fontSize: '1.35rem', fontWeight: 800, color: 'var(--gray-900)', margin: 0 }}>
            Ofertas Encontradas nos Grupos
          </h2>
          <p style={{ fontSize: '0.85rem', color: 'var(--gray-500)', margin: '0.25rem 0 0 0' }}>
            Captura automática nos grupos de origem, mensagens originais e status do fluxo.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button
            type="button"
            onClick={() => setIsConfigModalOpen(true)}
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
            <Icon name="settings" size={15} />
            Configurar grupos
          </button>
          <button
            type="button"
            onClick={() => {
              loadData();
              loadGroups();
            }}
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
            <Icon name="refresh" size={15} />
            Atualizar
          </button>
        </div>
      </div>

      {/* Resumo da Configuração */}
      <section style={{ background: 'white', borderRadius: 'var(--radius-md)', padding: '1.25rem', border: '1px solid var(--gray-200)', marginBottom: '1.5rem' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 210px), 1fr))', gap: '0.85rem', alignItems: 'center' }}>
          <GroupDropdown
            icon="📥"
            label="Origem Monitorada"
            groups={data?.source_groups || []}
            emptyText="Nenhuma origem configurada"
            accent="blue"
          />
          <GroupDropdown
            icon="📤"
            label="Destinos de Envio"
            groups={data?.target_groups || []}
            emptyText="Nenhum destino cadastrado"
            accent="green"
          />
          <div>
            <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--gray-500)', textTransform: 'uppercase' }}>Limite Diário</div>
            <div style={{ fontWeight: 700, color: 'var(--gray-800)', marginTop: '0.2rem' }}>
              {data?.today_sent || 0} / {data?.daily_limit ?? 20} ofertas enviadas
            </div>
          </div>
          <div>
            <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--gray-500)', textTransform: 'uppercase' }}>Status do Bot Local</div>
            <div style={{ fontWeight: 700, color: data?.bot_running ? '#16a34a' : '#dc2626', marginTop: '0.2rem' }}>
              {data?.bot_running ? 'Ativo e monitorando' : 'Parado'}
            </div>
          </div>
        </div>
      </section>

      {error && (
        <div style={{ padding: '0.8rem 1rem', marginBottom: '1rem', background: '#fef2f2', color: '#b91c1c', borderRadius: 'var(--radius-sm)', fontSize: '0.85rem' }}>
          {error}
        </div>
      )}

      {/* Filtros por Status */}
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
        {[
          { id: 'all', label: 'Todas as Ofertas' },
          { id: 'pending', label: 'Na Fila' },
          { id: 'published', label: 'Publicadas' },
          { id: 'failed', label: 'Falhas' },
        ].map((f) => (
          <button
            key={f.id}
            type="button"
            onClick={() => setStatusFilter(f.id)}
            style={{
              padding: '0.4rem 0.8rem',
              borderRadius: '20px',
              border: statusFilter === f.id ? '2px solid #2563eb' : '1px solid var(--gray-300)',
              background: statusFilter === f.id ? '#eff6ff' : 'white',
              color: statusFilter === f.id ? '#1e40af' : 'var(--gray-600)',
              fontSize: '0.8rem',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Tabela de Ofertas Encontradas */}
      <section style={{ background: 'white', borderRadius: 'var(--radius-md)', padding: '1.5rem', border: '1px solid var(--gray-200)' }}>
        {loading ? (
          <p style={{ color: 'var(--gray-500)' }}>Carregando ofertas...</p>
        ) : !filteredResults.length ? (
          <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--gray-500)' }}>
            <Icon name="search" size={32} color="var(--gray-400)" />
            <p style={{ marginTop: '0.5rem', fontWeight: 600 }}>Nenhuma oferta encontrada neste filtro.</p>
            <p style={{ fontSize: '0.8rem', color: 'var(--gray-400)' }}>
              Quando mensagens com links meli.la ou do Mercado Livre forem postadas nos grupos monitorados, elas aparecerão aqui.
            </p>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
              <thead>
                <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--gray-200)', color: 'var(--gray-600)' }}>
                  <th style={{ padding: '0.65rem' }}>Produto Identificado</th>
                    <th style={{ padding: '0.65rem' }}>Anúncio Individual</th>
                  <th style={{ padding: '0.65rem' }}>Mensagem Original</th>
                  <th style={{ padding: '0.65rem' }}>Origem</th>
                  <th style={{ padding: '0.65rem' }}>Horário</th>
                  <th style={{ padding: '0.65rem' }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {filteredResults.map((offer) => (
                  <tr key={offer.id} style={{ borderBottom: '1px solid var(--gray-100)' }}>
                    <td style={{ padding: '0.65rem', maxWidth: '240px' }}>
                      <div style={{ fontWeight: 600, color: 'var(--gray-900)' }}>
                        {offer.product_title || 'Identificação em andamento'}
                      </div>
                      {offer.product_price && (
                        <div style={{ fontSize: '0.78rem', color: '#16a34a', fontWeight: 700 }}>
                          R$ {offer.product_price}
                          {offer.product_original_price && (
                            <span style={{ color: 'var(--gray-400)', textDecoration: 'line-through', marginLeft: '0.4rem', fontWeight: 400 }}>
                              R$ {offer.product_original_price}
                            </span>
                          )}
                        </div>
                      )}
                      {offer.coupon && (
                        <div style={{ fontSize: '0.72rem', color: '#b45309', fontWeight: 600 }}>
                          🎟️ Cupom: {offer.coupon}
                        </div>
                      )}
                    </td>
                    <td style={{ padding: '0.65rem', maxWidth: '180px' }}>
                      <a
                          href={offer.product_url || offer.source_link}
                        target="_blank"
                        rel="noreferrer"
                        style={{ color: '#2563eb', wordBreak: 'break-all', fontSize: '0.78rem' }}
                      >
                          {offer.product_url || offer.source_link}
                      </a>
                    </td>
                    <td style={{ padding: '0.65rem', maxWidth: '200px' }}>
                      {offer.original_message ? (
                        <div>
                          <div style={{
                            fontSize: '0.75rem',
                            color: 'var(--gray-600)',
                            maxHeight: '40px',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                          }}>
                            {offer.original_message}
                          </div>
                          <button
                            type="button"
                            onClick={() => setSelectedMessage({ title: offer.product_title, text: offer.original_message, link: offer.source_link })}
                            style={{
                              background: 'none',
                              border: 'none',
                              color: '#2563eb',
                              fontSize: '0.72rem',
                              fontWeight: 600,
                              cursor: 'pointer',
                              padding: 0,
                              marginTop: '0.2rem',
                            }}
                          >
                            Ver texto completo
                          </button>
                        </div>
                      ) : (
                        <span style={{ color: 'var(--gray-400)', fontSize: '0.75rem' }}>Link isolado</span>
                      )}
                    </td>
                    <td style={{ padding: '0.65rem', whiteSpace: 'nowrap' }}>
                      <span style={{ padding: '0.2rem 0.4rem', background: '#eff6ff', color: '#1e40af', borderRadius: '4px', fontSize: '0.75rem', fontWeight: 600 }}>
                        {offer.source_group}
                      </span>
                    </td>
                    <td style={{ padding: '0.65rem', color: 'var(--gray-600)', fontSize: '0.78rem', whiteSpace: 'nowrap' }}>
                      {new Date(offer.received_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}
                    </td>
                    <td style={{ padding: '0.65rem' }}>
                      <span style={{
                        padding: '0.2rem 0.5rem',
                        borderRadius: '4px',
                        fontSize: '0.75rem',
                        fontWeight: 700,
                        background: statusBgColors[offer.status] || '#f3f4f6',
                        color: statusColors[offer.status] || 'var(--gray-700)',
                        display: 'inline-block',
                      }}>
                        {statusLabels[offer.status] || offer.status}
                      </span>
                      {offer.error_message && (
                        <div style={{ marginTop: '0.25rem', fontSize: '0.72rem', color: '#b91c1c', maxWidth: '240px' }}>
                          {offer.error_message}
                        </div>
                      )}
                      {offer.affiliate_url && (
                        <div style={{ marginTop: '0.25rem', fontSize: '0.72rem' }}>
                          <a href={offer.affiliate_url} target="_blank" rel="noreferrer" style={{ color: '#16a34a', fontWeight: 600 }}>
                            Link afiliado gerado →
                          </a>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Modal para visualizar mensagem original completa */}
      {selectedMessage && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 9999,
          padding: '1rem',
        }}>
          <div style={{
            background: 'white',
            borderRadius: 'var(--radius-md)',
            padding: '1.5rem',
            maxWidth: '550px',
            width: '100%',
            maxHeight: '80vh',
            display: 'flex',
            flexDirection: 'column',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700 }}>Mensagem Original do WhatsApp</h3>
              <button
                type="button"
                onClick={() => setSelectedMessage(null)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--gray-500)' }}
              >
                <Icon name="x" size={20} />
              </button>
            </div>
            {selectedMessage.title && (
              <div style={{ fontWeight: 600, marginBottom: '0.5rem', color: 'var(--gray-800)', fontSize: '0.9rem' }}>
                {selectedMessage.title}
              </div>
            )}
            <div style={{
              background: 'var(--gray-50)',
              border: '1px solid var(--gray-200)',
              borderRadius: 'var(--radius-sm)',
              padding: '1rem',
              overflowY: 'auto',
              whiteSpace: 'pre-wrap',
              fontSize: '0.85rem',
              color: 'var(--gray-800)',
              flex: 1,
              fontFamily: 'inherit',
            }}>
              {selectedMessage.text}
            </div>
            <div style={{ marginTop: '1rem', display: 'flex', justifyContent: 'flex-end' }}>
              <button
                type="button"
                onClick={() => setSelectedMessage(null)}
                style={{
                  padding: '0.5rem 1rem',
                  background: '#2563eb',
                  color: 'white',
                  border: 'none',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '0.85rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                Fechar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal de Configuração de Grupos */}
      <WhatsAppConfigModal
        isOpen={isConfigModalOpen}
        onClose={() => setIsConfigModalOpen(false)}
        groups={groups}
        onSaveGroups={handleSaveGroups}
        activeGroupId=""
        onSelectActiveGroup={() => {}}
      />
    </div>
  );
}
