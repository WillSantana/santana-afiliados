import React, { useState } from 'react';
import { api } from '../services/api';
import { Icon } from './Icons';
import { useToast } from './Toast';

export default function PublicationPreviewModal({ product, onClose, onPublished }) {
  const { addToast } = useToast();
  const [copied, setCopied] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [publishSuccess, setPublishSuccess] = useState(false);
  const [feedbackMessage, setFeedbackMessage] = useState(null);

  const savedGroups = (() => {
    try {
      const g = JSON.parse(localStorage.getItem('santana_whatsapp_groups'));
      if (Array.isArray(g) && g.length > 0) return g;
    } catch {}
    return [];
  })();

  const defaultGroupId = localStorage.getItem('santana_active_group_id') || savedGroups[0]?.id;
  const [selectedGroup, setSelectedGroup] = useState(defaultGroupId);

  if (!product) return null;

  const link = product.affiliate_url || '[INSIRA O LINK DE AFILIADO ANTES DE PUBLICAR]';
  const categoryLabel = {
    technology: 'Tecnologia e Games',
    fashion: 'Moda Masculina',
    home: 'Casa e Utilidades',
    beauty: 'Beleza e Cuidados',
  }[product.category] || 'Ofertas';

  const previewText = `🔥 *OFERTA IMPERDÍVEL!*
🛍️ *${product.title}*

Uma excelente oportunidade em *${categoryLabel}* com excelente custo-benefício e avaliação recomendada!

💰 *Preço Especial:* R$ ${Number(product.price).toFixed(2)}
📦 *Consulte as condições de frete no anúncio*

👉 *Acesse a oferta oficial aqui:*
${link}

⚖️ _Transparência: Este é um link de afiliado oficial do Mercado Livre e podemos receber comissão se você comprar._`;

  const handleCopy = () => {
    navigator.clipboard.writeText(previewText);
    setCopied(true);
    addToast('Texto da oferta copiado com sucesso!', 'success');
    setTimeout(() => setCopied(false), 2500);
  };

  const handlePublish = async () => {
    if (!product.affiliate_url) {
      addToast('Atenção: É obrigatório associar um link oficial de afiliado antes de publicar!', 'error');
      return;
    }
    if (!selectedGroup) {
      addToast('Cadastre e selecione o JID real do grupo do WhatsApp antes de publicar.', 'error');
      return;
    }
    setPublishing(true);
    setFeedbackMessage(null);
    try {
      // 1. Gera ou recupera rascunho de publicação
      const pub = await api.generatePublication(product.id);
      // 2. Dispara no gateway de WhatsApp para o grupo selecionado
      const res = await api.publishPublication(pub.id, selectedGroup);
      
      setPublishSuccess(true);
      const isSimulated = res.dispatch?.simulated;
      const msg = res.message || 'Publicação concluída com sucesso!';
      setFeedbackMessage({ type: isSimulated ? 'info' : 'success', text: msg });
      addToast(msg, isSimulated ? 'info' : 'success');

      setTimeout(() => {
        if (onPublished) onPublished();
        onClose();
      }, 2000);
    } catch (err) {
      setFeedbackMessage({ type: 'error', text: `Falha ao publicar: ${err.message}` });
      addToast(`Erro no envio: ${err.message}`, 'error');
    } finally {
      setPublishing(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content modern-card" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '580px' }}>
        <div className="modal-header">
          <div className="modal-title-wrap">
            <span className="modal-icon-badge whatsapp">
              <Icon name="whatsapp" size={20} />
            </span>
            <div>
              <h3>Publicação WhatsApp</h3>
              <p className="modal-subtitle">Mensagem formatada com conformidade legal e link seguro.</p>
            </div>
          </div>
          <button className="modal-close-btn" onClick={onClose}>
            <Icon name="x" size={18} />
          </button>
        </div>

        <div className="modal-body">
          {/* WhatsApp Chat Preview Simulation */}
          <div className="whatsapp-preview-box">
            <div className="whatsapp-header">
              <span className="whatsapp-avatar">⚡</span>
              <div>
                <div className="whatsapp-sender">Canal Santana Ofertas VIP</div>
                <div className="whatsapp-status">mensagens instantâneas</div>
              </div>
            </div>

            <div className="whatsapp-bubble">
              {product.thumbnail && (
                <div className="whatsapp-thumb-wrapper">
                  <img src={product.thumbnail} alt="" className="whatsapp-thumb-img" referrerPolicy="no-referrer" />
                </div>
              )}
              <pre className="whatsapp-text">{previewText}</pre>
              <div className="whatsapp-timestamp">
                {new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })} ✓✓
              </div>
            </div>
          </div>

          {/* Seletor de Grupo de Destino */}
          <div style={{ marginTop: '1rem', background: '#f8fafc', padding: '0.65rem 0.85rem', borderRadius: '8px', border: '1px solid #e2e8f0', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem' }}>
            <label style={{ fontSize: '0.82rem', fontWeight: 600, color: '#334155', display: 'flex', alignItems: 'center', gap: '6px', margin: 0, whiteSpace: 'nowrap' }}>
              <Icon name="users" size={15} color="#16a34a" />
              Destino:
            </label>
            <select
              className="modern-input"
              style={{ flex: 1, padding: '0.35rem 0.6rem', fontSize: '0.82rem', height: 'auto' }}
              value={selectedGroup}
              onChange={(e) => setSelectedGroup(e.target.value)}
            >
              {!savedGroups.length && (
                <option value="">Cadastre um grupo real nas configurações do WhatsApp</option>
              )}
              {savedGroups.map((g) => (
                <option key={g.id} value={g.id}>
                  {g.name}
                </option>
              ))}
            </select>
          </div>

          {feedbackMessage && (
            <div className={`status-banner-box ${feedbackMessage.type}`} style={{ marginTop: '1rem' }}>
              <Icon name={feedbackMessage.type === 'error' ? 'x' : 'check'} size={18} />
              <span>{feedbackMessage.text}</span>
            </div>
          )}

          {!product.affiliate_url && (
            <div className="warning-banner" style={{ marginTop: '1rem' }}>
              <Icon name="info" size={18} />
              <div>
                <strong>Atenção:</strong> Esta oferta ainda não tem link de afiliado. Configure o link para que os cliques sejam monetizados.
              </div>
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button type="button" className="btn-secondary" onClick={onClose}>
            Fechar
          </button>
          <button type="button" className="btn-outline-copy" onClick={handleCopy}>
            <Icon name={copied ? 'check' : 'copy'} size={16} />
            {copied ? 'Copiado!' : 'Copiar Texto'}
          </button>
          <button
            type="button"
            className="btn-whatsapp-publish"
            onClick={handlePublish}
            disabled={publishing || publishSuccess || !product.affiliate_url || !selectedGroup}
          >
            <Icon name={publishSuccess ? 'check' : 'whatsapp'} size={16} />
            {publishSuccess ? 'Disparado!' : publishing ? 'Enviando...' : 'Publicar Agora'}
          </button>
        </div>
      </div>
    </div>
  );
}
