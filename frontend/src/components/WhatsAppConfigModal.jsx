import React, { useState } from 'react';
import { Icon } from './Icons';

export default function WhatsAppConfigModal({
  isOpen,
  onClose,
  phoneNumber,
  onSavePhoneNumber,
  groups,
  onSaveGroups,
  activeGroupId,
  onSelectActiveGroup,
}) {
  const [phone, setPhone] = useState(phoneNumber || '');
  const [groupList, setGroupList] = useState(groups || []);
  const [newGroupName, setNewGroupName] = useState('');
  const [newGroupId, setNewGroupId] = useState('');
  const [showAddForm, setShowAddForm] = useState(false);
  const [showQRCodeHelp, setShowQRCodeHelp] = useState(false);

  if (!isOpen) return null;

  const handleSavePhone = (e) => {
    e.preventDefault();
    onSavePhoneNumber(phone.trim());
  };

  const handleAddGroup = (e) => {
    e.preventDefault();
    if (!newGroupName.trim()) return;

    const finalId = newGroupId.trim();
    if (!/^\d+@g\.us$/.test(finalId)) {
      alert('Informe o ID real do grupo no formato 123456789@g.us.');
      return;
    }

    const updated = [
      ...groupList,
      { id: finalId, name: newGroupName.trim(), isDefault: groupList.length === 0 },
    ];
    setGroupList(updated);
    onSaveGroups(updated);
    setNewGroupName('');
    setNewGroupId('');
    setShowAddForm(false);
  };

  const handleRemoveGroup = (idToRemove) => {
    if (groupList.length <= 1) {
      alert('Você precisa manter pelo menos 1 grupo cadastrado.');
      return;
    }
    const updated = groupList.filter((g) => g.id !== idToRemove);
    setGroupList(updated);
    onSaveGroups(updated);
    if (activeGroupId === idToRemove && updated.length > 0) {
      onSelectActiveGroup(updated[0].id);
    }
  };

  const handleSetDefault = (id) => {
    const updated = groupList.map((g) => ({
      ...g,
      isDefault: g.id === id,
    }));
    setGroupList(updated);
    onSaveGroups(updated);
    onSelectActiveGroup(id);
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal-content modern-card"
        onClick={(e) => e.stopPropagation()}
        style={{ maxWidth: '620px', maxHeight: '90vh', overflowY: 'auto' }}
      >
        <div className="modal-header">
          <div className="modal-title-wrap">
            <span className="modal-icon-badge primary" style={{ background: '#dcfce7', color: '#16a34a' }}>
              <Icon name="whatsapp" size={22} />
            </span>
            <div>
              <h3>Configuração do WhatsApp & Grupos</h3>
              <p className="modal-subtitle">
                Defina o seu número de WhatsApp e escolha os grupos onde as ofertas serão enviadas.
              </p>
            </div>
          </div>
          <button className="modal-close-btn" onClick={onClose}>
            <Icon name="x" size={18} />
          </button>
        </div>

        <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Seção 1: Número de Telefone do WhatsApp */}
          <div className="config-section-card" style={{ background: '#f8fafc', padding: '1rem', borderRadius: '10px', border: '1px solid #e2e8f0' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.6rem' }}>
              <h4 style={{ margin: 0, fontSize: '0.95rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Icon name="zap" size={16} color="#3b82f6" />
                Seu Número / Celular Conectado
              </h4>
              <button
                type="button"
                className="btn-text-action"
                onClick={() => setShowQRCodeHelp(!showQRCodeHelp)}
                style={{ fontSize: '0.8rem' }}
              >
                <Icon name="info" size={13} />
                Como ler o QR Code?
              </button>
            </div>

            {showQRCodeHelp && (
              <div style={{ background: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: '8px', padding: '0.75rem', fontSize: '0.82rem', marginBottom: '0.75rem', color: '#1e3a8a', lineHeight: 1.5 }}>
                <strong>Como funciona a conexão via QR Code:</strong>
                <ol style={{ paddingLeft: '1.2rem', margin: '0.4rem 0 0' }}>
                  <li>O WhatsApp não conecta apenas digitando o número; ele exige leitura de <strong>QR Code</strong> (como no WhatsApp Web).</li>
                  <li>Quando a Evolution API estiver rodando no Docker, abra <code>http://localhost:8080/instance/connect/santana-bot</code>.</li>
                  <li>No seu celular, abra <strong>WhatsApp &gt; Aparelhos Conectados &gt; Conectar Aparelho</strong> e aponte para o QR Code.</li>
                  <li>Pronto! Todas as mensagens serão enviadas a partir desse seu número.</li>
                </ol>
              </div>
            )}

            <form onSubmit={handleSavePhone} style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              <input
                type="text"
                className="modern-input"
                placeholder="Ex: +55 (DDD) 9XXXX-XXXX"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                style={{ flex: 1 }}
              />
              <button type="submit" className="btn-secondary" style={{ whiteSpace: 'nowrap' }}>
                <Icon name="check" size={14} />
                Salvar Número
              </button>
            </form>
            <span style={{ fontSize: '0.75rem', color: '#64748b', display: 'block', marginTop: '4px' }}>
              Identificador do aparelho transmissor para controle e logs do sistema.
            </span>
          </div>

          {/* Seção 2: Grupos de WhatsApp Cadastrados */}
          <div className="config-section-card" style={{ background: '#f8fafc', padding: '1rem', borderRadius: '10px', border: '1px solid #e2e8f0' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
              <h4 style={{ margin: 0, fontSize: '0.95rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Icon name="users" size={16} color="#16a34a" />
                Grupos de Ofertas Autorizados ({groupList.length})
              </h4>
              <button
                type="button"
                className="btn-text-action"
                onClick={() => setShowAddForm(!showAddForm)}
                style={{ fontSize: '0.8rem', fontWeight: 600 }}
              >
                <Icon name={showAddForm ? 'x' : 'plus'} size={13} />
                {showAddForm ? 'Cancelar' : '+ Adicionar Novo Grupo'}
              </button>
            </div>

            {/* Formulário para Adicionar Grupo */}
            {showAddForm && (
              <form onSubmit={handleAddGroup} style={{ background: '#ffffff', border: '1px solid #cbd5e1', borderRadius: '8px', padding: '0.75rem', marginBottom: '1rem' }}>
                <div style={{ marginBottom: '0.5rem' }}>
                  <label style={{ fontSize: '0.8rem', fontWeight: 600, color: '#334155', display: 'block', marginBottom: '3px' }}>
                    Nome Amigável do Grupo
                  </label>
                  <input
                    type="text"
                    required
                    className="modern-input"
                    placeholder="Ex: 🔥 Achadinhos VIP • Grupo 1"
                    value={newGroupName}
                    onChange={(e) => setNewGroupName(e.target.value)}
                  />
                </div>
                <div style={{ marginBottom: '0.75rem' }}>
                  <label style={{ fontSize: '0.8rem', fontWeight: 600, color: '#334155', display: 'block', marginBottom: '3px' }}>
                    ID real do Grupo / JID
                  </label>
                  <input
                    type="text"
                    className="modern-input"
                    placeholder="Ex: 123456789@g.us"
                    value={newGroupId}
                    onChange={(e) => setNewGroupId(e.target.value)}
                  />
                  <span style={{ fontSize: '0.73rem', color: '#64748b' }}>
                    * Informe o JID real do grupo fornecido pelo gateway do WhatsApp.
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
                  <button type="button" className="btn-secondary" onClick={() => setShowAddForm(false)}>
                    Cancelar
                  </button>
                  <button type="submit" className="btn-primary">
                    <Icon name="check" size={14} />
                    Cadastrar Grupo
                  </button>
                </div>
              </form>
            )}

            {/* Lista dos Grupos */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {groupList.map((g) => {
                const isSelected = activeGroupId === g.id;
                return (
                  <div
                    key={g.id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '0.65rem 0.85rem',
                      background: isSelected ? '#f0fdf4' : '#ffffff',
                      border: isSelected ? '1.5px solid #22c55e' : '1px solid #e2e8f0',
                      borderRadius: '8px',
                      transition: 'all 0.15s ease',
                    }}
                  >
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontWeight: 600, fontSize: '0.9rem', color: '#0f172a' }}>{g.name}</span>
                        {isSelected && (
                          <span className="pill pill-approved" style={{ fontSize: '0.7rem', padding: '1px 7px' }}>
                            ✓ Grupo Ativo
                          </span>
                        )}
                        {g.isDefault && (
                          <span className="pill" style={{ fontSize: '0.7rem', padding: '1px 7px', background: '#e0e7ff', color: '#4338ca' }}>
                            Padrão
                          </span>
                        )}
                      </div>
                      <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '2px', fontFamily: 'monospace' }}>
                        JID: {g.id}
                      </div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                      {!isSelected && (
                        <button
                          type="button"
                          className="btn-action"
                          onClick={() => handleSetDefault(g.id)}
                          style={{ fontSize: '0.78rem', padding: '4px 10px' }}
                          title="Definir como grupo ativo principal"
                        >
                          Selecionar
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => handleRemoveGroup(g.id)}
                        className="btn-action btn-reject"
                        style={{ padding: '4px 8px' }}
                        title="Remover grupo da lista"
                      >
                        <Icon name="trash" size={13} />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        <div className="modal-footer" style={{ marginTop: '1.25rem' }}>
          <button type="button" className="btn-primary" onClick={onClose} style={{ width: '100%' }}>
            <Icon name="check" size={16} />
            Concluir & Voltar à Central
          </button>
        </div>
      </div>
    </div>
  );
}
