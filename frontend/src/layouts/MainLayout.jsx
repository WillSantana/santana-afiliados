import React from 'react';
import Navbar from '../components/Navbar';
import { Icon } from '../components/Icons';

const SIDEBAR_ITEMS = [
  { id: 'dashboard', label: 'Início', icon: 'zap' },
  { id: 'automation', label: 'Enviar ofertas', icon: 'automation' },
  { id: 'publications', label: 'Grupos e envios', icon: 'whatsapp' },
  { id: 'affiliates', label: 'Links afiliados', icon: 'link' },
  { id: 'catalog', label: 'Produtos e catálogo', icon: 'catalog' },
];

export default function MainLayout({ children, activeTab, setActiveTab }) {
  return (
    <div className="app-shell">
      {/* Sidebar fixa no Desktop (estilo Ripply) */}
      <aside className="app-sidebar" aria-label="Menu principal">
        <div className="sidebar-brand">
          <div className="sidebar-logo-mark">
            <Icon name="zap" size={18} color="#ffffff" />
          </div>
          <div className="sidebar-brand-name">
            Santana<span>Afiliados</span>
          </div>
        </div>

        <nav className="sidebar-nav">
          {SIDEBAR_ITEMS.map((item) => {
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                type="button"
                className={`sidebar-nav-item ${isActive ? 'active' : ''}`}
                onClick={() => setActiveTab(item.id)}
              >
                <Icon name={item.icon} size={17} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        <div className="sidebar-footer">
          <div className="sidebar-user-card">
            <div className="sidebar-user-avatar">W</div>
            <div className="sidebar-user-meta">
              <div className="sidebar-user-name">Wilson Santana</div>
              <div className="sidebar-user-sub">Automação Multi-Loja</div>
            </div>
          </div>
        </div>
      </aside>

      {/* Conteúdo principal + Navbar mobile */}
      <div className="app-main-wrap">
        <div className="mobile-only-navbar">
          <Navbar activeTab={activeTab} setActiveTab={setActiveTab} />
        </div>

        <main className="main-content">
          <div className="layout-container">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
