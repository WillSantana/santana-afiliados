import React, { useState } from 'react';
import MainLayout from './layouts/MainLayout';
import CatalogPage from './pages/CatalogPage';
import AutomationPage from './pages/AutomationPage';
import PublicationsPage from './pages/PublicationsPage';
import AnalyticsPage from './pages/AnalyticsPage';
import CampaignsPage from './pages/CampaignsPage';
import { ToastProvider } from './components/Toast';
import { useProducts } from './hooks/useProducts';

function MainApp() {
  const [activeTab, setActiveTab] = useState('catalog');
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

      {activeTab === 'automation' && <AutomationPage />}
      {activeTab === 'publications' && <PublicationsPage />}
      {activeTab === 'analytics' && <AnalyticsPage />}
      {activeTab === 'campaigns' && <CampaignsPage />}

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
