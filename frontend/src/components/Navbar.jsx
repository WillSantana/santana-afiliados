import React, { useState } from 'react';
import { Icon } from './Icons';

export default function Navbar({ activeTab, setActiveTab }) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const tabs = [
    { id: 'dashboard', label: 'Dashboard', icon: 'zap' },
    { id: 'automation', label: 'Ofertas Encontradas', icon: 'automation' },
    { id: 'affiliates', label: 'Links de Afiliados', icon: 'link' },
    { id: 'publications', label: 'Publicações por Grupo', icon: 'whatsapp' },
    { id: 'catalog', label: 'Catálogo', icon: 'catalog' },
  ];

  const handleTabClick = (tabId) => {
    setActiveTab(tabId);
    setMobileMenuOpen(false);
  };

  return (
    <header className="modern-navbar">
      <div className="navbar-container">
        {/* Brand */}
        <div className="navbar-brand">
          <div className="brand-logo-icon">
            <Icon name="zap" size={20} color="#ffffff" />
          </div>
          <div className="brand-text-block">
            <div className="brand-title">
              <span>Santana</span> Afiliados
            </div>
            <div className="brand-status-tag">
              <span className="live-pulse-dot"></span>
              <span>Monitor de ofertas WhatsApp</span>
            </div>
          </div>
        </div>

        {/* Desktop Navigation Links */}
        <nav className="navbar-desktop-nav">
          {tabs.map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                className={`nav-link-btn ${isActive ? 'active' : ''}`}
                onClick={() => handleTabClick(tab.id)}
              >
                <Icon name={tab.icon} size={17} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Desktop Action & Mobile Hamburger */}
        <div className="navbar-actions">
          {/* Hamburger Menu Toggle (Mobile) */}
          <button
            type="button"
            className="mobile-menu-toggle"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label="Menu"
          >
            <Icon name={mobileMenuOpen ? 'x' : 'menu'} size={22} />
          </button>
        </div>
      </div>

      {/* Mobile Drawer Menu */}
      {mobileMenuOpen && (
        <div className="mobile-drawer">
          <nav className="mobile-nav-list">
            {tabs.map((tab) => {
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  className={`mobile-nav-link ${isActive ? 'active' : ''}`}
                  onClick={() => handleTabClick(tab.id)}
                >
                  <Icon name={tab.icon} size={20} />
                  <span>{tab.label}</span>
                  {isActive && <span className="mobile-active-dot"></span>}
                </button>
              );
            })}
          </nav>
        </div>
      )}
    </header>
  );
}
