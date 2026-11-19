import React, { useState } from 'react';
import MainLayout from './layouts/MainLayout';
import DashboardPage from './pages/DashboardPage';
import CatalogPage from './pages/CatalogPage';
import AutomationPage from './pages/AutomationPage';
import AffiliateLinksPage from './pages/AffiliateLinksPage';
import PublicationsPage from './pages/PublicationsPage';
import { ToastProvider } from './components/Toast';
import { useProducts } from './hooks/useProducts';

function MainApp() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const {
    products,
    loading,
    filters,
    setFilters,
    reload,
    approve,
    reject,
    associateAffiliateLink,
  } = useProducts();

  return (
    <MainLayout
      activeTab={activeTab}
      setActiveTab={setActiveTab}
    >
      {activeTab === 'dashboard' && (
        <DashboardPage onNavigateTab={setActiveTab} />
      )}

      {activeTab === 'automation' && <AutomationPage />}

      {activeTab === 'affiliates' && <AffiliateLinksPage />}

      {activeTab === 'publications' && <PublicationsPage />}

      {activeTab === 'catalog' && (
        <CatalogPage
          products={products}
          loading={loading}
          filters={filters}
          setFilters={setFilters}
          onApprove={approve}
          onReject={reject}
          onAssociateAffiliateLink={associateAffiliateLink}
          onReload={reload}
        />
      )}
    </MainLayout>
  );
}

export default function App() {
  return (
    <ToastProvider>
      <MainApp />
    </ToastProvider>
  );
}
