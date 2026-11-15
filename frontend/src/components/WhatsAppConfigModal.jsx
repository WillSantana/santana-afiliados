import React, { useEffect, useState } from 'react';
import { Icon } from './Icons';

let nextLocalGroupKey = 0;
const groupKey = (group) => group.id ?? group._uiKey ?? group.name;
const withUiKey = (group) => ({
  ...group,
  _uiKey: group._uiKey || (group.id != null ? `server-${group.id}` : `local-${++nextLocalGroupKey}`),
});
const toApiGroup = ({ name, jid, role }) => ({ name: name.trim(), jid: jid?.trim() || null, role });

export default function WhatsAppConfigModal({
  isOpen,
  onClose,
  groups,
  onSaveGroups,
  activeGroupId,
  onSelectActiveGroup,
}) {
  const [groupList, setGroupList] = useState(groups || []);
  const [newGroupName, setNewGroupName] = useState('');
  const [newGroupId, setNewGroupId] = useState('');
  const [newGroupRole, setNewGroupRole] = useState('destination');
  const [showAddForm, setShowAddForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setGroupList((groups || []).map(withUiKey));
      setError('');
      setHasChanges(false);
    }
  }, [groups, isOpen]);

  if (!isOpen) return null;

  const saveGroups = async (updated) => {
    setSaving(true);
    setError('');
    try {
      const saved = await onSaveGroups(updated.map(toApiGroup));
      setGroupList((saved || []).map(withUiKey));
      setHasChanges(false);
      return true;
    } catch (saveError) {
      setError(saveError.message);
      return false;
    } finally {
      setSaving(false);
    }
  };

  const handleAddGroup = (event) => {
    event.preventDefault();
    const name = newGroupName.trim();
    const jid = newGroupId.trim();
    if (!name) return;
    if (newGroupRole === 'destination' && !/^[\d-]+@g\.us$/.test(jid)) {
      setError('Informe um JID válido para o grupo de destino, por exemplo 123456789@g.us.');
      return;
    }
    if (jid && !/^[\d-]+@g\.us$/.test(jid)) {
      setError('O JID deve estar no formato 123456789@g.us.');
      return;
    }
    if (groupList.some((group) => group.jid && group.jid === jid)) {
      setError('Este JID já está cadastrado.');
      return;
    }
    const updated = [
      ...groupList,
      withUiKey({ name, jid: jid || null, role: newGroupRole }),
    ];
    setGroupList(updated);
    setHasChanges(true);
    setError('');
    setNewGroupName('');
    setNewGroupId('');
    setShowAddForm(false);
  };

  const handleRemoveGroup = (groupToRemove) => {
    const updated = groupList.filter((group) => groupKey(group) !== groupKey(groupToRemove));
    setGroupList(updated);
    setHasChanges(true);
    if (activeGroupId === groupToRemove.jid) {
      const nextDestination = updated.find((group) => group.role === 'destination' && group.jid);
      onSelectActiveGroup(nextDestination?.jid || '');
    }
  };

  const handleChangeRole = (group, role) => {
    const updated = groupList.map((item) => (
      groupKey(item) === groupKey(group) ? { ...item, role } : item
    ));
    setGroupList(updated);
    setHasChanges(true);
    setError('');
  };

  const handleUpdateGroup = (group, changes) => {
    const updated = groupList.map((item) => (
      groupKey(item) === groupKey(group) ? { ...item, ...changes } : item
    ));
    setGroupList(updated);
    setHasChanges(true);
    setError('');
  };

  const handleClose = () => {
    if (hasChanges && !window.confirm('Há alterações de grupos que ainda não foram salvas. Deseja descartá-las?')) {
      return;
    }
    onClose();
  };

  return (
    <div className="modal-overlay" onClick={handleClose}>
      <div
        className="modal-content modern-card"
        onClick={(event) => event.stopPropagation()}
        style={{ maxWidth: '620px', maxHeight: '90vh', overflowY: 'auto' }}
      >
        <div className="modal-header">
          <div className="modal-title-wrap">
            <span className="modal-icon-badge primary" style={{ background: '#dcfce7', color: '#16a34a' }}>
              <Icon name="whatsapp" size={22} />
            </span>
            <div>
              <h3>Grupos do WhatsApp</h3>
              <p className="modal-subtitle">
                Cadastre as origens monitoradas e todos os destinos das ofertas.
              </p>
            </div>
          </div>
          <button className="modal-close-btn" onClick={handleClose} aria-label="Fechar">
            <Icon name="x" size={18} />
          </button>
        </div>

        <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          <section style={{ background: '#f8fafc', padding: '1rem', borderRadius: '10px', border: '1px solid #e2e8f0' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
              <h4 style={{ margin: 0 }}>Grupos cadastrados ({groupList.length})</h4>
              <button
                type="button"
                className="btn-text-action"
                onClick={() => {
                  setError('');
                  setShowAddForm(!showAddForm);
                }}
              >
                <Icon name={showAddForm ? 'x' : 'plus'} size={13} />
                {showAddForm ? 'Cancelar' : 'Adicionar grupo'}
              </button>
            </div>
            <p style={{ marginTop: 0, color: '#64748b', fontSize: '0.8rem' }}>
              Use o nome exatamente como aparece no WhatsApp para as origens; o JID é opcional nelas e obrigatório nos destinos.
            </p>
            {hasChanges && (
              <p style={{ marginTop: 0, color: '#b45309', fontSize: '0.8rem' }}>
                Há alterações não salvas.
              </p>
            )}

            {showAddForm && (
              <form onSubmit={handleAddGroup} style={{ background: '#fff', border: '1px solid #cbd5e1', borderRadius: '8px', padding: '0.75rem', marginBottom: '1rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.8rem', fontWeight: 600 }}>
                  Nome do grupo
                  <input
                    type="text"
                    required
                    className="modern-input"
                    placeholder="Ex.: Santana_Indica"
                    value={newGroupName}
                    onChange={(event) => setNewGroupName(event.target.value)}
                  />
                </label>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.8rem', fontWeight: 600 }}>
                  JID do grupo
                  <input
                    type="text"
                    className="modern-input"
                    placeholder={newGroupRole === 'destination' ? '123456789@g.us' : 'Opcional para a origem'}
                    value={newGroupId}
                    onChange={(event) => setNewGroupId(event.target.value)}
                  />
                </label>
                <label style={{ display: 'block', marginBottom: '0.75rem', fontSize: '0.8rem', fontWeight: 600 }}>
                  Uso do grupo
                  <select
                    className="modern-input"
                    value={newGroupRole}
                    onChange={(event) => setNewGroupRole(event.target.value)}
                  >
                    <option value="destination">Destino — receberá as ofertas</option>
                    <option value="source">Origem — grupo monitorado</option>
                  </select>
                </label>
                <button type="submit" className="btn-primary" disabled={saving}>
                  <Icon name="check" size={14} />
                  {saving ? 'Salvando...' : 'Salvar grupo'}
                </button>
              </form>
            )}

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {groupList.map((group) => {
                const isActive = group.jid && activeGroupId === group.jid;
                return (
                  <div
                    key={groupKey(group)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      gap: '0.75rem',
                      padding: '0.65rem 0.85rem',
                      background: isActive ? '#f0fdf4' : '#fff',
                      border: isActive ? '1.5px solid #22c55e' : '1px solid #e2e8f0',
                      borderRadius: '8px',
                    }}
                  >
                    <div style={{ flex: 1, minWidth: 0, display: 'grid', gap: '0.25rem' }}>
                      <input
                        type="text"
                        aria-label={`Nome do grupo ${group.name}`}
                        className="modern-input"
                        value={group.name}
                        disabled={saving}
                        onChange={(event) => handleUpdateGroup(group, { name: event.target.value })}
                        style={{ padding: '0.35rem 0.5rem' }}
                      />
                      <input
                        type="text"
                        aria-label={`JID do grupo ${group.name}`}
                        className="modern-input"
                        placeholder="123456789@g.us"
                        value={group.jid || ''}
                        disabled={saving}
                        onChange={(event) => handleUpdateGroup(group, { jid: event.target.value })}
                        style={{ padding: '0.35rem 0.5rem', fontFamily: 'monospace' }}
                      />
                    </div>
                    <select
                      aria-label={`Uso do grupo ${group.name}`}
                      className="modern-input"
                      value={group.role}
                      disabled={saving}
                      onChange={(event) => handleChangeRole(group, event.target.value)}
                      style={{ width: '170px', padding: '0.35rem' }}
                    >
                      <option value="source">Origem monitorada</option>
                      <option value="destination">Destino de publicação</option>
                    </select>
                    {group.role === 'destination' && group.jid && !isActive && (
                      <button
                        type="button"
                        className="btn-action"
                        onClick={() => onSelectActiveGroup(group.jid)}
                        title="Usar este grupo para a mensagem de teste"
                      >
                        Teste
                      </button>
                    )}
                    {isActive && <span className="pill pill-approved">Teste</span>}
                    <button
                      type="button"
                      onClick={() => handleRemoveGroup(group)}
                      className="btn-action btn-reject"
                      disabled={saving}
                      title="Remover grupo"
                    >
                      <Icon name="trash" size={13} />
                    </button>
                  </div>
                );
              })}
              {!groupList.length && <p style={{ color: '#64748b' }}>Nenhum grupo cadastrado.</p>}
            </div>
            {error && (
              <p role="alert" style={{ color: '#b91c1c', marginBottom: 0 }}>{error}</p>
            )}
          </section>

          <p style={{ margin: 0, color: '#92400e', fontSize: '0.82rem' }}>
            O monitor percorre as origens em sequência a cada ciclo e envia ofertas novas a todos os destinos. Ao adicionar uma origem com o monitor ativo, as mensagens que já estão nela são registradas como histórico e ignoradas.
          </p>
        </div>

        <div className="modal-footer" style={{ marginTop: '1.25rem' }}>
          <button
            type="button"
            className="btn-secondary"
            onClick={() => saveGroups(groupList)}
            disabled={saving || !hasChanges}
          >
            {saving ? 'Salvando...' : 'Salvar grupos'}
          </button>
          <button type="button" className="btn-primary" onClick={handleClose} style={{ width: '100%' }}>
            <Icon name="check" size={16} />
            Concluir
          </button>
        </div>
      </div>
    </div>
  );
}
