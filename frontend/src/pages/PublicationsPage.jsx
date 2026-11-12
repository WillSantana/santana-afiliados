import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { Icon } from '../components/Icons';
import { useToast } from '../components/Toast';
import WhatsAppConfigModal from '../components/WhatsAppConfigModal';

const INITIAL_GROUPS = [];

export default function PublicationsPage() {
  const { addToast } = useToast();
  const [publications, setPublications] = useState([]);
  const [loading, setLoading] = useState(false);
  const [copiedId, setCopiedId] = useState(null);
  const [whatsappConfig, setWhatsappConfig] = useState(null);
  const [testingConnection, setTestingConnection] = useState(false);
  const [dispatchingNext, setDispatchingNext] = useState(false);
  const [isConfigModalOpen, setIsConfigModalOpen] = useState(false);

  // Estado do número e grupos de WhatsApp
  const [phoneNumber, setPhoneNumber] = useState(() => {
    return localStorage.getItem('santana_whatsapp_phone') || '';
  });

  const [groups, setGroups] = useState(() => {
    try {
      const saved = JSON.parse(localStorage.getItem('santana_whatsapp_groups'));
      if (Array.isArray(saved) && saved.length > 0) return saved;
    } catch {}
    return INITIAL_GROUPS;
  });

  const [activeGroupId, setActiveGroupId] = useState(() => {
    return localStorage.getItem('santana_active_group_id') || groups[0]?.id || '';
  });

  const handleSavePhoneNumber = (newPhone) => {
    setPhoneNumber(newPhone);
    localStorage.setItem('santana_whatsapp_phone', newPhone);
    addToast('Número de WhatsApp atualizado com sucesso!', 'success');
  };

  const handleSaveGroups = (newGroups) => {
    setGroups(newGroups);
    localStorage.setItem('santana_whatsapp_groups', JSON.stringify(newGroups));
    addToast('Lista de grupos de WhatsApp atualizada!', 'success');
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

  useEffect(() => {
    fetchPublicationsAndConfig();
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
      const res = await api.dispatchNextOffer(activeGroupId);
      addToast(res.message || 'Próxima oferta disparada com sucesso!', 'success');
      fetchPublicationsAndConfig();
    } catch (err) {
      addToast(`Não foi possível disparar: ${err.message}`, 'error');
    } finally {
      setDispatchingNext(false);
    }
  };

  const isEnabled = whatsappConfig?.enabled;
  const gatewayName = (whatsappConfig?.gateway_type || 'evolution').toUpperCase();
  const currentGroupObj = groups.find((g) => g.id === activeGroupId) || groups[0];

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
            title="Envia a próxima oferta aprovada da fila para o grupo selecionado"
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
              <span style={{ fontSize: '0.8rem', color: '#64748b', display: 'inline-flex', alignItems: 'center', gap: '4px', marginLeft: '6px' }}>
                📱 <strong>{phoneNumber}</strong>
              </span>
            </div>
            <div className="gateway-meta-row" style={{ marginTop: '4px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontWeight: 600, color: '#334155' }}>Grupo Ativo:</span>
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
                {groups.map((g) => (
                  <option key={g.id} value={g.id}>
                    {g.name}
                  </option>
                ))}
              </select>
              <span>•</span>
              <span style={{ fontSize: '0.78rem', color: '#64748b' }}>
                JID: <code>{activeGroupId}</code>
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
            title="Cadastrar novos grupos ou alterar seu número transmissor"
          >
            <Icon name="settings" size={15} />
            <span>Configurar Grupos & Número</span>
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
        phoneNumber={phoneNumber}
        onSavePhoneNumber={handleSavePhoneNumber}
        groups={groups}
        onSaveGroups={handleSaveGroups}
        activeGroupId={activeGroupId}
        onSelectActiveGroup={handleSelectActiveGroup}
      />
    </div>
  );
}
