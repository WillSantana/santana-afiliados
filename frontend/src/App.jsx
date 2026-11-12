import React, { useState } from 'react';
import MainLayout from './layouts/MainLayout';
import CatalogPage from './pages/CatalogPage';
import AutomationPage from './pages/AutomationPage';
import PublicationsPage from './pages/PublicationsPage';
import AnalyticsPage from './pages/AnalyticsPage';
import CampaignsPage from './pages/CampaignsPage';
import SearchModal from './components/SearchModal';
import { ToastProvider } from './components/Toast';
import { useProducts } from './hooks/useProducts';

function MainApp() {
  const [activeTab, setActiveTab] = useState('catalog');
  const [isSearchOpen, setIsSearchOpen] = useState(false);

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
      onOpenSearch={() => setIsSearchOpen(true)}
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

      {isSearchOpen && (
        <SearchModal
          onClose={() => setIsSearchOpen(false)}
          onSearchCompleted={reload}
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
