import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { Icon } from './Icons';
import { useToast } from './Toast';

export default function PublicationPreviewModal({ product, onClose, onPublished }) {
  const { addToast } = useToast();
  const [copied, setCopied] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [publishSuccess, setPublishSuccess] = useState(false);
  const [feedbackMessage, setFeedbackMessage] = useState(null);

  const [groups, setGroups] = useState([]);
  const [groupsError, setGroupsError] = useState('');

  useEffect(() => {
    api.getWhatsAppGroups()
      .then((config) => setGroups(config.groups || []))
      .catch((error) => setGroupsError(error.message));
  }, []);

  const destinationGroups = groups.filter(
    (group) => group.role === 'destination' && group.jid,
  );

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
    if (!destinationGroups.length) {
      addToast('Cadastre ao menos um grupo de destino com JID nas configurações do WhatsApp.', 'error');
      return;
    }
    setPublishing(true);
    setFeedbackMessage(null);
    try {
      // 1. Gera ou recupera rascunho de publicação
      const pub = await api.generatePublication(product.id);
      // 2. Dispara no gateway de WhatsApp para o grupo selecionado
      const res = await api.publishPublication(pub.id);
      if (res.partial) {
        setPublishSuccess(true);
        const deliveries = res.dispatch?.deliveries || [];
        const sentTo = deliveries.filter((delivery) => delivery.success).map((delivery) => delivery.group_name);
        const failedAt = deliveries.find((delivery) => !delivery.success)?.group_name;
        const details = [
          sentTo.length ? `Enviado para: ${sentTo.join(', ')}.` : '',
          failedAt ? `Falhou em: ${failedAt}.` : '',
        ].filter(Boolean).join(' ');
        const message = `${res.message || 'Publicação parcial.'} ${details}`.trim();
        setFeedbackMessage({ type: 'error', text: message });
        addToast(message, 'error');
        if (onPublished) onPublished();
        return;
      }

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

          <div style={{ marginTop: '1rem', background: '#f8fafc', padding: '0.75rem 0.85rem', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
            <strong style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Icon name="users" size={15} color="#16a34a" />
              Destinos desta oferta
            </strong>
            {groupsError ? (
              <p role="alert" style={{ color: '#b91c1c', marginBottom: 0 }}>{groupsError}</p>
            ) : destinationGroups.length ? (
              <ul style={{ margin: '0.5rem 0 0', paddingLeft: '1.25rem' }}>
                {destinationGroups.map((group) => (
                  <li key={group.id || group.jid}>{group.name}</li>
                ))}
              </ul>
            ) : (
              <p style={{ marginBottom: 0 }}>Cadastre grupos de destino com JID nas configurações do WhatsApp.</p>
            )}
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
            disabled={publishing || publishSuccess || !product.affiliate_url || !destinationGroups.length || Boolean(groupsError)}
          >
            <Icon name={publishSuccess ? 'check' : 'whatsapp'} size={16} />
            {publishSuccess ? (feedbackMessage?.type === 'error' ? 'Envio parcial' : 'Disparado!') : publishing ? 'Enviando...' : 'Publicar Agora'}
          </button>
        </div>
      </div>
    </div>
  );
}
