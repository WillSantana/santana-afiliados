import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';
import { Icon } from '../components/Icons';
import { useToast } from '../components/Toast';
import WhatsAppConfigModal from '../components/WhatsAppConfigModal';

export default function PublicationsPage() {
  const { addToast } = useToast();
  const [publications, setPublications] = useState([]);
  const [deliveries, setDeliveries] = useState([]);
  const [loading, setLoading] = useState(false);
  const [copiedId, setCopiedId] = useState(null);
  const [whatsappConfig, setWhatsappConfig] = useState(null);
  const [testingConnection, setTestingConnection] = useState(false);
  const [dispatchingNext, setDispatchingNext] = useState(false);
  const [isConfigModalOpen, setIsConfigModalOpen] = useState(false);
  const [currentView, setCurrentView] = useState('deliveries'); // 'deliveries' ou 'messages'
  const [groups, setGroups] = useState([]);

  const [activeGroupId, setActiveGroupId] = useState(() => {
    return localStorage.getItem('santana_active_group_id') || '';
  });

  const handleSaveGroups = async (newGroups) => {
    try {
      const saved = await api.saveWhatsAppGroups(newGroups);
      setGroups(saved.groups || []);
      if (!saved.groups?.some((group) => group.jid === activeGroupId && group.role === 'destination')) {
        handleSelectActiveGroup(
          saved.groups?.find((group) => group.role === 'destination' && group.jid)?.jid || '',
        );
      }
      addToast('Grupos do WhatsApp atualizados!', 'success');
      return saved.groups || [];
    } catch (err) {
      addToast(`Não foi possível salvar os grupos: ${err.message}`, 'error');
      throw err;
    }
  };

  const handleSelectActiveGroup = (id) => {
    setActiveGroupId(id);
    localStorage.setItem('santana_active_group_id', id);
  };

  const fetchAllData = useCallback(async () => {
    setLoading(true);
    try {
      const [pubData, cfgData, delivData] = await Promise.all([
        api.getPublications(),
        api.getWhatsAppConfig().catch(() => null),
        api.getDeliveries().catch(() => ({ results: [] })),
      ]);
      setPublications(pubData.results || pubData || []);
      if (cfgData) setWhatsappConfig(cfgData);
      setDeliveries(delivData.results || []);
    } catch (err) {
      console.error(err);
      addToast(`Erro ao carregar dados: ${err.message}`, 'error');
    } finally {
      setLoading(false);
    }
  }, [addToast]);

  const fetchGroups = useCallback(async () => {
    try {
      const config = await api.getWhatsAppGroups();
      const configuredGroups = config.groups || [];
      setGroups(configuredGroups);
      if (!configuredGroups.some((group) => group.jid === activeGroupId && group.role === 'destination')) {
        const firstDestination = configuredGroups.find(
          (group) => group.role === 'destination' && group.jid,
        );
        handleSelectActiveGroup(firstDestination?.jid || '');
      }
    } catch (err) {
      addToast(`Erro ao carregar grupos do WhatsApp: ${err.message}`, 'error');
    }
  }, [activeGroupId, addToast]);

  useEffect(() => {
    fetchAllData();
    fetchGroups();
    const timer = setInterval(fetchAllData, 10000);
    return () => clearInterval(timer);
  }, [fetchAllData, fetchGroups]);

  const handleCopy = (id, text) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    addToast('Texto da publicação copiado!', 'success');
    setTimeout(() => setCopiedId(null), 2500);
  };

  const handleTestConnection = async () => {
    setTestingConnection(true);
    try {
      const res = await api.testWhatsAppConnection(activeGroupId);
      if (res.success) {
        addToast(res.message || 'Mensagem de teste enviada com sucesso!', res.simulated ? 'info' : 'success');
      } else {
        addToast(`Erro no teste: ${res.error || 'Falha ao comunicar com gateway'}`, 'error');
      }
    } catch (err) {
      addToast(`Erro no teste de WhatsApp: ${err.message}`, 'error');
    } finally {
      setTestingConnection(false);
    }
  };

  const handleDispatchNext = async () => {
    setDispatchingNext(true);
    try {
      const res = await api.dispatchNextOffer();
      if (res.partial) {
        addToast(res.message || 'A publicação foi enviada parcialmente; confira os grupos.', 'error');
        fetchAllData();
      } else if (res.dispatched === false) {
        addToast(res.message, 'info');
      } else {
        addToast(res.message || 'Próxima oferta disparada com sucesso!', 'success');
        fetchAllData();
      }
    } catch (err) {
      addToast(`Não foi possível disparar: ${err.message}`, 'error');
    } finally {
      setDispatchingNext(false);
    }
  };

  const isEnabled = whatsappConfig?.enabled;
  const gatewayName = (whatsappConfig?.gateway_type || 'evolution').toUpperCase();
  const testGroups = groups.filter((group) => group.role === 'destination' && group.jid);

  return (
    <div className="publications-wrapper" style={{ paddingBottom: '3rem' }}>
      {/* Top Header */}
      <div className="section-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h2 style={{ fontSize: '1.35rem', fontWeight: 800, color: 'var(--gray-900)', margin: 0 }}>
            Central de Publicações nos Grupos
          </h2>
          <p className="section-subtitle" style={{ fontSize: '0.85rem', color: 'var(--gray-500)', margin: '0.25rem 0 0 0' }}>
            Rastreamento individual de cada envio por grupo de WhatsApp autorizado.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.65rem' }}>
          <button
            type="button"
            className="btn-secondary"
            onClick={fetchAllData}
            disabled={loading}
          >
            <Icon name="refresh" size={16} className={loading ? 'spin' : ''} />
            <span>Atualizar</span>
          </button>
          <button
            type="button"
            className="btn-primary"
            onClick={handleDispatchNext}
            disabled={dispatchingNext}
            title="Envia a próxima oferta aprovada para todos os grupos autorizados"
          >
            <Icon name="zap" size={16} />
            <span>{dispatchingNext ? 'Disparando...' : 'Disparar Próxima'}</span>
          </button>
        </div>
      </div>

      {/* WhatsApp Gateway Integration Status Banner */}
      <div className="whatsapp-gateway-panel" style={{ background: 'white', borderRadius: 'var(--radius-md)', padding: '1.25rem', border: '1px solid var(--gray-200)', marginBottom: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div className="gateway-panel-left" style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{
            width: '42px',
            height: '42px',
            borderRadius: '50%',
            background: '#dcfce7',
            color: '#16a34a',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <Icon name="whatsapp" size={24} color="#16a34a" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
              <span style={{ fontWeight: 700, fontSize: '0.95rem', color: 'var(--gray-900)' }}>
                Envio WhatsApp Local (Selenium & WhatsApp Web)
              </span>
              <span style={{ padding: '0.2rem 0.5rem', borderRadius: '4px', fontSize: '0.72rem', fontWeight: 700, background: '#dcfce7', color: '#166534' }}>
                🟢 Ativo no Perfil Dedicado
              </span>
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--gray-500)', marginTop: '0.2rem' }}>
              Cada publicação gera um registro individual por grupo de destino.
            </div>
          </div>
        </div>

        <div className="gateway-panel-right" style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <button
            type="button"
            className="btn-secondary"
            onClick={() => setIsConfigModalOpen(true)}
            style={{ fontSize: '0.82rem', padding: '6px 12px' }}
            title="Adicionar ou remover grupos de destino"
          >
            <Icon name="settings" size={15} />
            <span>Configurar Grupos</span>
          </button>
          <button
            type="button"
            className="btn-test-whatsapp"
            onClick={handleTestConnection}
            disabled={testingConnection}
            style={{ fontSize: '0.82rem', padding: '6px 12px' }}
          >
            <Icon name={testingConnection ? 'refresh' : 'check'} size={15} className={testingConnection ? 'spin' : ''} />
            <span>{testingConnection ? 'Testando...' : 'Testar Conexão'}</span>
          </button>
        </div>
      </div>

      {/* Alternância de Abas: Envios por Grupo vs Rascunhos */}
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.25rem' }}>
        <button
          type="button"
          onClick={() => setCurrentView('deliveries')}
          style={{
            padding: '0.5rem 1rem',
            borderRadius: 'var(--radius-sm)',
            border: currentView === 'deliveries' ? '2px solid #2563eb' : '1px solid var(--gray-300)',
            background: currentView === 'deliveries' ? '#eff6ff' : 'white',
            color: currentView === 'deliveries' ? '#1e40af' : 'var(--gray-700)',
            fontWeight: 700,
            fontSize: '0.85rem',
            cursor: 'pointer',
          }}
        >
          Envios por Grupo ({deliveries.length})
        </button>
        <button
          type="button"
          onClick={() => setCurrentView('messages')}
          style={{
            padding: '0.5rem 1rem',
            borderRadius: 'var(--radius-sm)',
            border: currentView === 'messages' ? '2px solid #2563eb' : '1px solid var(--gray-300)',
            background: currentView === 'messages' ? '#eff6ff' : 'white',
            color: currentView === 'messages' ? '#1e40af' : 'var(--gray-700)',
            fontWeight: 700,
            fontSize: '0.85rem',
            cursor: 'pointer',
          }}
        >
          Mensagens Formatadas ({publications.length})
        </button>
      </div>

      {/* Visualização: Tabela de Envios por Grupo (PublicationDelivery) */}
      {currentView === 'deliveries' && (
        <section style={{ background: 'white', borderRadius: 'var(--radius-md)', padding: '1.5rem', border: '1px solid var(--gray-200)' }}>
          <h3 style={{ margin: '0 0 1rem 0', fontSize: '1rem', fontWeight: 700 }}>
            Histórico de Publicações Realizadas (Registros Individuais)
          </h3>
          {loading ? (
            <p style={{ color: 'var(--gray-500)' }}>Carregando registros de envio...</p>
          ) : !deliveries.length ? (
            <div style={{ textAlign: 'center', padding: '2.5rem', color: 'var(--gray-500)' }}>
              <Icon name="whatsapp" size={32} color="var(--gray-400)" />
              <p style={{ marginTop: '0.5rem', fontWeight: 600 }}>Nenhum envio realizado ainda.</p>
              <p style={{ fontSize: '0.8rem', color: 'var(--gray-400)' }}>
                Quando o monitor publicar uma oferta nos grupos de destino, cada envio para cada grupo será auditado individualmente aqui.
              </p>
            </div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                <thead>
                  <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--gray-200)', color: 'var(--gray-600)' }}>
                    <th style={{ padding: '0.65rem' }}>Oferta Publicada</th>
                    <th style={{ padding: '0.65rem' }}>Grupo de Destino</th>
                    <th style={{ padding: '0.65rem' }}>Link de Afiliado Utilizado</th>
                    <th style={{ padding: '0.65rem' }}>Data e Horário</th>
                    <th style={{ padding: '0.65rem' }}>Status do Envio</th>
                    <th style={{ padding: '0.65rem' }}>Detalhes / Erro</th>
                  </tr>
                </thead>
                <tbody>
                  {deliveries.map((del) => {
                    const isSuccess = del.status === 'success';
                    return (
                      <tr key={del.id} style={{ borderBottom: '1px solid var(--gray-100)' }}>
                        <td style={{ padding: '0.65rem', maxWidth: '220px' }}>
                          <div style={{ fontWeight: 600, color: 'var(--gray-900)' }}>
                            {del.product_title}
                          </div>
                        </td>
                        <td style={{ padding: '0.65rem', whiteSpace: 'nowrap' }}>
                          <span style={{ padding: '0.2rem 0.5rem', background: '#f0fdf4', color: '#166534', borderRadius: '4px', fontWeight: 700, fontSize: '0.78rem' }}>
                            {del.target_group_name}
                          </span>
                          {del.target_group_jid && (
                            <div style={{ fontSize: '0.7rem', color: 'var(--gray-400)', marginTop: '0.1rem' }}>
                              {del.target_group_jid}
                            </div>
                          )}
                        </td>
                        <td style={{ padding: '0.65rem', maxWidth: '200px' }}>
                          <a
                            href={del.affiliate_url}
                            target="_blank"
                            rel="noreferrer"
                            style={{ color: '#16a34a', fontWeight: 600, wordBreak: 'break-all', fontSize: '0.78rem' }}
                          >
                            {del.affiliate_url}
                          </a>
                        </td>
                        <td style={{ padding: '0.65rem', color: 'var(--gray-600)', fontSize: '0.8rem', whiteSpace: 'nowrap' }}>
                          {new Date(del.sent_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}
                        </td>
                        <td style={{ padding: '0.65rem', whiteSpace: 'nowrap' }}>
                          <span style={{
                            padding: '0.2rem 0.5rem',
                            borderRadius: '4px',
                            fontSize: '0.75rem',
                            fontWeight: 700,
                            background: isSuccess ? '#dcfce7' : '#fee2e2',
                            color: isSuccess ? '#166534' : '#b91c1c',
                          }}>
                            {isSuccess ? 'Enviado com Sucesso' : 'Falha no Envio'}
                          </span>
                        </td>
                        <td style={{ padding: '0.65rem', maxWidth: '220px', fontSize: '0.78rem', color: isSuccess ? '#15803d' : '#b91c1c' }}>
                          {del.error_message || (isSuccess ? 'Confirmado no grupo' : '—')}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      {/* Visualização: Cards de Mensagens Prontas / Formatadas */}
      {currentView === 'messages' && (
        <div>
          {loading ? (
            <div className="catalog-loading-state">
              <div className="loading-spinner"></div>
              <p>Carregando publicações...</p>
            </div>
          ) : publications.length === 0 ? (
            <div className="catalog-empty-state" style={{ background: 'white', borderRadius: 'var(--radius-md)', padding: '2rem', textAlign: 'center' }}>
              <div className="empty-icon-circle whatsapp-circle" style={{ margin: '0 auto 1rem auto' }}>
                <Icon name="whatsapp" size={32} />
              </div>
              <h3>Nenhuma publicação registrada</h3>
              <p style={{ color: 'var(--gray-500)', fontSize: '0.85rem' }}>
                Conforme o monitor processa ofertas, as mensagens formatadas ficarão disponíveis aqui.
              </p>
            </div>
          ) : (
            <div className="publications-grid">
              {publications.map((pub) => {
                const isPub = pub.status === 'published';
                const isCopied = copiedId === pub.id;
                const product = pub.product_details;
                return (
                  <div key={pub.id} className="publication-card">
                    <div className="pub-card-header">
                      <div className="pub-channel-badge">
                        <Icon name="whatsapp" size={14} color="#16a34a" />
                        <span>Publicação #{pub.id}</span>
                      </div>
                      <span className={`pill ${isPub ? 'pill-approved' : 'pill-pending'}`}>
                        {isPub ? 'Publicada' : 'Pendente de Envio'}
                      </span>
                    </div>

                    {product?.thumbnail && (
                      <div className="pub-card-thumb-row">
                        <img src={product.thumbnail} alt="" className="pub-mini-thumb" referrerPolicy="no-referrer" />
                        <div className="pub-mini-info">
                          <span className="pub-mini-title">{product.title}</span>
                          <span className="pub-mini-price">R$ {Number(product.price).toFixed(2)}</span>
                        </div>
                      </div>
                    )}

                    <div className="pub-message-box">
                      <pre className="pub-message-text">{pub.message_text}</pre>
                    </div>

                    <div className="pub-card-footer">
                      <div className="pub-metrics">
                        <Icon name="trendingUp" size={14} color="#64748b" />
                        <span><strong>{pub.deliveries?.length || 0}</strong> envio(s)</span>
                      </div>
                      <button
                        type="button"
                        className={`btn-action-copy ${isCopied ? 'copied' : ''}`}
                        onClick={() => handleCopy(pub.id, pub.message_text)}
                      >
                        <Icon name={isCopied ? 'check' : 'copy'} size={15} />
                        <span>{isCopied ? 'Copiado!' : 'Copiar Texto'}</span>
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Modal de Configuração de Grupos */}
      <WhatsAppConfigModal
        isOpen={isConfigModalOpen}
        onClose={() => setIsConfigModalOpen(false)}
        groups={groups}
        onSaveGroups={handleSaveGroups}
        activeGroupId={activeGroupId}
        onSelectActiveGroup={handleSelectActiveGroup}
      />
    </div>
  );
}
