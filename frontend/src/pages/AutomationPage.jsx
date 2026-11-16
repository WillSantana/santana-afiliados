import React, { useCallback, useEffect, useState } from 'react';
import { api } from '../services/api';
import WhatsAppConfigModal from '../components/WhatsAppConfigModal';

const statusLabels = {
  ignored: 'Já existia ao iniciar',
  pending: 'Na fila',
  preparing: 'Preparando produto e afiliado',
  processing: 'Processando',
  prepared: 'Pronta para envio',
  published: 'Publicada',
  skipped: 'Ignorada',
  failed: 'Falha antes do envio',
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
};

export default function AutomationPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [groups, setGroups] = useState([]);
  const [isConfigModalOpen, setIsConfigModalOpen] = useState(false);

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
      setData(await api.getIncomingOffers());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    loadGroups();
    const timer = window.setInterval(loadData, 10000);
    return () => window.clearInterval(timer);
  }, [loadData, loadGroups]);

  const handleSaveGroups = async (updatedGroups) => {
    const saved = await api.saveWhatsAppGroups(updatedGroups);
    setGroups(saved.groups || []);
    await loadData();
    return saved.groups || [];
  };

  const statuses = data?.statuses || {};

  return (
    <div style={{ paddingBottom: '3rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h2 style={{ fontSize: '1.35rem', fontWeight: 800, color: 'var(--gray-900)' }}>
            Monitor de ofertas do WhatsApp
          </h2>
          <p style={{ fontSize: '0.85rem', color: 'var(--gray-500)' }}>
            Recebe links meli.la, cria links de afiliado e publica no grupo de destino.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button
            type="button"
            onClick={() => setIsConfigModalOpen(true)}
            style={{
              padding: '0.5rem 0.9rem',
              background: 'white',
              border: '1px solid var(--gray-300)',
              borderRadius: 'var(--radius-sm)',
              fontSize: '0.85rem',
              fontWeight: 600,
            }}
          >
            Configurar grupos
          </button>
          <button
            type="button"
            onClick={() => {
              loadData();
              loadGroups();
            }}
            style={{
              padding: '0.5rem 0.9rem',
              background: 'white',
              border: '1px solid var(--gray-300)',
              borderRadius: 'var(--radius-sm)',
              fontSize: '0.85rem',
              fontWeight: 600,
            }}
          >
            Atualizar
          </button>
        </div>
      </div>

      <section style={{ background: 'white', borderRadius: 'var(--radius-md)', padding: '1.5rem', border: '1px solid var(--gray-200)', marginBottom: '1.5rem' }}>
        <h3 style={{ marginTop: 0 }}>Configuração do fluxo</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
          <div>
            <strong>Origens monitoradas</strong>
            <div>{data?.source_groups?.join(', ') || 'Não configurado'}</div>
          </div>
          <div><strong>Destinos</strong><div>{data?.target_groups?.join(', ') || 'Nenhum grupo cadastrado'}</div></div>
          <div><strong>Limite diário</strong><div>{data?.today_sent || 0} / {data?.daily_limit ?? 20} ofertas</div></div>
        </div>
        <p style={{ marginBottom: 0, color: 'var(--gray-600)', fontSize: '0.85rem' }}>
          O monitor roda no terminal, não no servidor web. Ele percorre as origens em sequência; por isso, quanto mais grupos forem configurados, maior será o intervalo entre leituras do mesmo grupo. Inicie o Chrome dedicado em
          <code> 127.0.0.1:9222</code>, autentique o WhatsApp Web e execute:
        </p>
        <pre style={{ overflowX: 'auto', padding: '0.8rem', background: 'var(--gray-50)', borderRadius: 'var(--radius-sm)' }}>
          <code>cd backend; .\venv\Scripts\python.exe manage.py monitor_whatsapp_offers --send</code>
        </pre>
        <p style={{ marginBottom: 0, color: '#92400e', fontSize: '0.82rem' }}>
          Use somente o perfil Chrome dedicado iniciado pelo script do projeto. A porta de depuração dá acesso à sessão do navegador e deve permanecer vinculada a localhost.
        </p>
      </section>

      {error && (
        <div role="alert" style={{ padding: '0.8rem 1rem', marginBottom: '1rem', background: '#fef2f2', color: '#b91c1c', borderRadius: 'var(--radius-sm)' }}>
          Não foi possível carregar as ofertas recebidas: {error}
        </div>
      )}

      <section style={{ background: 'white', borderRadius: 'var(--radius-md)', padding: '1.5rem', border: '1px solid var(--gray-200)' }}>
        <h3 style={{ marginTop: 0 }}>Fila e histórico recente</h3>
        {loading ? (
          <p>Carregando ofertas...</p>
        ) : !data?.results?.length ? (
          <p style={{ color: 'var(--gray-500)' }}>Nenhum link novo foi registrado. Links já visíveis ao iniciar o monitor são ignorados para evitar republicar o histórico.</p>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
              <thead>
                <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--gray-200)' }}>
                  <th style={{ padding: '0.65rem' }}>Oferta</th>
                  <th style={{ padding: '0.65rem' }}>Origem</th>
                  <th style={{ padding: '0.65rem' }}>Cupom</th>
                  <th style={{ padding: '0.65rem' }}>Recebida</th>
                  <th style={{ padding: '0.65rem' }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {data.results.map((offer) => (
                  <tr key={offer.id} style={{ borderBottom: '1px solid var(--gray-100)' }}>
                    <td style={{ padding: '0.65rem' }}>
                      <div style={{ fontWeight: 600 }}>{offer.product_title || 'Link recebido'}</div>
                      <a href={offer.source_link} target="_blank" rel="noreferrer">Abrir link de origem</a>
                    </td>
                    <td style={{ padding: '0.65rem' }}>{offer.source_group}</td>
                    <td style={{ padding: '0.65rem' }}>{offer.coupon || '—'}</td>
                    <td style={{ padding: '0.65rem' }}>{new Date(offer.received_at).toLocaleString()}</td>
                    <td style={{ padding: '0.65rem', fontWeight: 700, color: statusColors[offer.status] || 'var(--gray-600)' }}>
                      {statusLabels[offer.status] || offer.status}
                      {['failed', 'prepared', 'uncertain'].includes(offer.status) && offer.error_message && (
                        <div style={{ maxWidth: '320px', marginTop: '0.25rem', fontWeight: 400, fontSize: '0.75rem' }}>
                          {offer.error_message}
                        </div>
                      )}
                      {offer.affiliate_url && (
                        <div style={{ marginTop: '0.25rem', fontWeight: 400, fontSize: '0.75rem' }}>
                          <a href={offer.affiliate_url} target="_blank" rel="noreferrer">Link de afiliado validado</a>
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
