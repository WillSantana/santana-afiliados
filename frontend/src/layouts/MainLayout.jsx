import React from 'react';
import Navbar from '../components/Navbar';

export default function MainLayout({ children, activeTab, setActiveTab }) {
  return (
    <div className="app-layout">
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
      />

      <main className="main-content">
        <div className="layout-container">
          {children}
        </div>
      </main>

      <footer className="modern-footer">
        <div className="layout-container footer-inner">
          <div className="footer-left">
            <strong>Santana Afiliados Bot</strong> • Automação Comercial & Inteligência de Ofertas
          </div>
          <div className="footer-right">
            Automação de ofertas recebidas no WhatsApp
          </div>
        </div>
      </footer>
    </div>
  );
}
