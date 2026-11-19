import React, { useEffect, useRef, useState } from 'react';

const PALETTES = {
  blue: {
    border: '#bfdbfe',
    bg: '#eff6ff',
    bgHover: '#dbeafe',
    text: '#1e40af',
    badgeBg: '#2563eb',
    dot: '#2563eb',
  },
  green: {
    border: '#bbf7d0',
    bg: '#f0fdf4',
    bgHover: '#dcfce7',
    text: '#15803d',
    badgeBg: '#16a34a',
    dot: '#16a34a',
  },
};

export default function GroupDropdown({
  label,
  icon = '',
  groups = [],
  emptyText = 'Nenhum grupo cadastrado',
  accent = 'blue',
}) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const containerRef = useRef(null);
  const palette = PALETTES[accent] || PALETTES.blue;

  useEffect(() => {
    if (!open) return undefined;
    const handleClickOutside = (event) => {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [open]);

  const normalizedQuery = search.trim().toLowerCase();
  const filteredGroups = normalizedQuery
    ? groups.filter((name) => String(name).toLowerCase().includes(normalizedQuery))
    : groups;

  const count = groups.length;

  return (
    <div ref={containerRef} style={{ position: 'relative', width: '100%' }}>
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        aria-expanded={open}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '0.75rem',
          padding: '0.65rem 0.9rem',
          background: open ? palette.bgHover : palette.bg,
          border: `1px solid ${palette.border}`,
          borderRadius: '8px',
          cursor: 'pointer',
          textAlign: 'left',
          transition: 'background 0.15s ease',
        }}
      >
        <span
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            fontSize: '0.82rem',
            fontWeight: 700,
            color: palette.text,
            textTransform: 'uppercase',
            letterSpacing: '0.02em',
          }}
        >
          {icon ? <span>{icon}</span> : null}
          <span>{label}</span>
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexShrink: 0 }}>
          <span
            style={{
              padding: '0.15rem 0.55rem',
              borderRadius: '999px',
              background: palette.badgeBg,
              color: 'white',
              fontSize: '0.75rem',
              fontWeight: 700,
            }}
          >
            {count} {count === 1 ? 'grupo' : 'grupos'}
          </span>
          <span
            style={{
              fontSize: '0.85rem',
              color: palette.text,
              fontWeight: 700,
              transform: open ? 'rotate(180deg)' : 'rotate(0deg)',
              transition: 'transform 0.15s ease',
              display: 'inline-block',
            }}
          >
            ▾
          </span>
        </span>
      </button>

      {open && (
        <div
          style={{
            position: 'absolute',
            top: 'calc(100% + 6px)',
            left: 0,
            right: 0,
            zIndex: 30,
            background: 'white',
            border: `1px solid ${palette.border}`,
            borderRadius: '8px',
            boxShadow: '0 10px 25px rgba(15, 23, 42, 0.12)',
            overflow: 'hidden',
          }}
        >
          {count > 5 && (
            <div style={{ padding: '0.5rem', borderBottom: '1px solid #f1f5f9', background: '#f8fafc' }}>
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Filtrar grupo..."
                style={{
                  width: '100%',
                  padding: '0.4rem 0.6rem',
                  fontSize: '0.8rem',
                  border: '1px solid #cbd5e1',
                  borderRadius: '6px',
                  outline: 'none',
                  boxSizing: 'border-box',
                }}
              />
            </div>
          )}

          {filteredGroups.length === 0 ? (
            <div style={{ padding: '0.85rem 1rem', fontSize: '0.82rem', color: '#64748b' }}>
              {count === 0 ? emptyText : 'Nenhum grupo corresponde ao filtro.'}
            </div>
          ) : (
            <ul
              style={{
                listStyle: 'none',
                margin: 0,
                padding: '0.35rem 0',
                maxHeight: '240px',
                overflowY: 'auto',
              }}
            >
              {filteredGroups.map((name, idx) => (
                <li
                  key={`${name}-${idx}`}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.55rem',
                    padding: '0.48rem 0.9rem',
                    fontSize: '0.83rem',
                    fontWeight: 600,
                    color: '#1e293b',
                    borderBottom: idx < filteredGroups.length - 1 ? '1px solid #f8fafc' : 'none',
                  }}
                >
                  <span
                    style={{
                      width: '7px',
                      height: '7px',
                      borderRadius: '50%',
                      background: palette.dot,
                      flexShrink: 0,
                    }}
                  />
                  <span style={{ wordBreak: 'break-word' }}>{name}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
