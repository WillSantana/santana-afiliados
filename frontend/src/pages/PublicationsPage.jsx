import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { Icon } from '../components/Icons';
import { useToast } from '../components/Toast';
import WhatsAppConfigModal from '../components/WhatsAppConfigModal';

export default function PublicationsPage() {
  const { addToast } = useToast();
  const [publications, setPublications] = useState([]);
  const [loading, setLoading] = useState(false);
  const [copiedId, setCopiedId] = useState(null);
  const [whatsappConfig, setWhatsappConfig] = useState(null);
  const [testingConnection, setTestingConnection] = useState(false);
  const [dispatchingNext, setDispatchingNext] = useState(false);
  const [isConfigModalOpen, setIsConfigModalOpen] = useState(false);

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

  const fetchPublicationsAndConfig = async () => {
    setLoading(true);
    try {
      const [pubData, cfgData] = await Promise.all([
        api.getPublications(),
        api.getWhatsAppConfig().catch(() => null),
      ]);
      setPublications(pubData.results || pubData);
      if (cfgData) setWhatsappConfig(cfgData);
    } catch (err) {
      console.error(err);
      addToast(`Erro ao carregar dados: ${err.message}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  const fetchGroups = async () => {
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
  };

  useEffect(() => {
    fetchPublicationsAndConfig();
    fetchGroups();
  }, []);

  const handleCopy = (id, text) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    addToast('Texto da publicação copiado para o WhatsApp!', 'success');
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
        addToast(res.message || 'A publicação foi enviada parcialmente; não tente reenviar sem conferir os grupos.', 'error');
        fetchPublicationsAndConfig();
      } else if (res.dispatched === false) {
        addToast(res.message, 'info');
      } else {
        addToast(res.message || 'Próxima oferta disparada com sucesso!', 'success');
        fetchPublicationsAndConfig();
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
    <div className="publications-wrapper">
      {/* Top Header */}
      <div className="section-header">
        <div>
          <h2>Central de Publicações & Disparo WhatsApp</h2>
          <p className="section-subtitle">
            Gerenciamento e envio de postagens com fotos e links de afiliado rastreados para seus grupos de ofertas.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.65rem' }}>
          <button
            type="button"
            className="btn-secondary"
            onClick={fetchPublicationsAndConfig}
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
            title="Envia a próxima oferta para todos os grupos cadastrados como destino"
          >
            <Icon name="zap" size={16} />
            <span>{dispatchingNext ? 'Disparando...' : 'Disparar Próxima'}</span>
          </button>
        </div>
      </div>

      {/* WhatsApp Gateway Integration Status Banner */}
      <div className="whatsapp-gateway-panel">
        <div className="gateway-panel-left">
          <div className={`gateway-status-icon ${isEnabled ? 'online' : 'simulated'}`}>
            <Icon name="whatsapp" size={24} />
          </div>
          <div>
            <div className="gateway-title-row">
              <span className="gateway-name">Gateway WhatsApp: <strong>{gatewayName}</strong></span>
              <span className={`pill ${isEnabled ? 'pill-approved' : 'pill-pending'}`}>
                {isEnabled ? '🟢 Envio Real Ativo' : '🟡 Modo Simulação / Local'}
              </span>
            </div>
            <div className="gateway-meta-row" style={{ marginTop: '4px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontWeight: 600, color: '#334155' }}>Grupo do teste:</span>
              <select
                className="modern-input"
                style={{
                  padding: '3px 8px',
                  fontSize: '0.82rem',
                  height: 'auto',
                  borderRadius: '6px',
                  border: '1px solid #cbd5e1',
                  background: '#ffffff',
                  fontWeight: 500,
                  color: '#0f172a',
                  cursor: 'pointer'
                }}
                value={activeGroupId}
                onChange={(e) => handleSelectActiveGroup(e.target.value)}
              >
                {!testGroups.length && <option value="">Cadastre um destino com JID</option>}
                {testGroups.map((g) => (
                  <option key={g.id || g.jid} value={g.jid}>
                    {g.name}
                  </option>
                ))}
              </select>
              <span>•</span>
              <span style={{ fontSize: '0.78rem', color: '#64748b' }}>
                As ofertas serão enviadas para todos os grupos cadastrados como destino.
              </span>
            </div>
          </div>
        </div>

        <div className="gateway-panel-right" style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <button
            type="button"
            className="btn-secondary"
            onClick={() => setIsConfigModalOpen(true)}
            style={{ fontSize: '0.82rem', padding: '6px 12px' }}
            title="Adicionar, remover ou trocar os grupos do WhatsApp"
          >
            <Icon name="settings" size={15} />
            <span>Configurar Grupos</span>
          </button>
          <button
            type="button"
            className="btn-test-whatsapp"
            onClick={handleTestConnection}
            disabled={testingConnection}
          >
            <Icon name={testingConnection ? 'refresh' : 'check'} size={15} className={testingConnection ? 'spin' : ''} />
            <span>{testingConnection ? 'Testando...' : 'Testar Conexão'}</span>
          </button>
        </div>
      </div>

      {/* Publications List */}
      {loading ? (
        <div className="catalog-loading-state">
          <div className="loading-spinner"></div>
          <p>Carregando publicações...</p>
        </div>
      ) : publications.length === 0 ? (
        <div className="catalog-empty-state">
          <div className="empty-icon-circle whatsapp-circle">
            <Icon name="whatsapp" size={32} />
          </div>
          <h3>Nenhuma publicação registrada</h3>
          <p>
            Acesse a aba <strong>Catálogo & Triagem</strong>, selecione uma oferta aprovada e clique no botão <strong>Post WhatsApp</strong> para criar sua primeira mensagem ou clique em <strong>Disparar Próxima</strong> acima.
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
                    <span>WhatsApp VIP • #{pub.id}</span>
                  </div>
                  <span className={`pill ${isPub ? 'pill-approved' : 'pill-pending'}`}>
                    {isPub ? 'Publicado' : 'Pendente de Envio'}
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
                    <span><strong>{pub.clicks_count}</strong> cliques</span>
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

      {/* Modal de Configuração do Número e dos Grupos */}
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
