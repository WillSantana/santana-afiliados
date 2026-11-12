/**
 * Camada de Serviços da API - Santana Afiliados Bot
 * Especificação V1.2 - Seção 14
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

async function request(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  try {
    const response = await fetch(url, { ...options, headers });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.message || errorData.error || errorData.detail || `Erro HTTP ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error(`Erro ao comunicar com ${url}:`, error);
    throw error;
  }
}

export const api = {
  // Health
  checkHealth: () => request('/health/'),

  // Catálogo de Produtos
  getProducts: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/products/${query ? `?${query}` : ''}`);
  },
  getProduct: (id) => request(`/products/${id}/`),
  createProduct: (data) => request('/products/', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  updateProduct: (id, data) => request(`/products/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  approveProduct: (id) => request(`/products/${id}/approve/`, {
    method: 'POST',
  }),
  rejectProduct: (id, reason = '') => request(`/products/${id}/reject/`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  }),
  setAffiliateLink: (id, affiliateUrl) => request(`/products/${id}/affiliate-link/`, {
    method: 'POST',
    body: JSON.stringify({ affiliate_url: affiliateUrl }),
  }),

  // Motor de Automação & Monitoramento (V1.2)
  getAutomationConfig: () => request('/automation/config/'),
  updateAutomationConfig: (data) => request('/automation/config/', {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  getSearchRuns: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/automation/runs/${query ? `?${query}` : ''}`);
  },
  getPriceAlerts: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/automation/alerts/${query ? `?${query}` : ''}`);
  },
  acknowledgeAlert: (alertId) => request(`/automation/alerts/${alertId}/acknowledge/`, {
    method: 'POST',
  }),
  getProductPriceHistory: (productId) => request(`/automation/products/${productId}/price-history/`),
  triggerSearchCycle: (cycleIndex = 0) => request('/automation/run-search/', {
    method: 'POST',
    body: JSON.stringify({ cycle_index: cycleIndex }),
  }),
  triggerPriceMonitoring: (limit = 40) => request('/automation/run-monitor/', {
    method: 'POST',
    body: JSON.stringify({ limit }),
  }),

  // Busca e Ingestão Manual Mercado Livre
  runSearch: (payload = {}) => request('/search/run/', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),

  // Publicações Promocionais & WhatsApp Dispatch
  getPublications: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/publications/${query ? `?${query}` : ''}`);
  },
  generatePublication: (productId, customBenefit = '') => request('/publications/generate/', {
    method: 'POST',
    body: JSON.stringify({ product_id: productId, custom_benefit: customBenefit }),
  }),
  publishPublication: (id, groupId = '') => request(`/publications/${id}/publish/`, {
    method: 'POST',
    body: JSON.stringify({ group_id: groupId || undefined }),
  }),
  getWhatsAppConfig: () => request('/publications/whatsapp-config/'),
  testWhatsAppConnection: (groupId = '') => request('/publications/test-whatsapp/', {
    method: 'POST',
    body: JSON.stringify({ group_id: groupId || undefined }),
  }),
  dispatchNextOffer: (groupId = '') => request('/publications/dispatch-next/', {
    method: 'POST',
    body: JSON.stringify({ group_id: groupId || undefined }),
  }),

  // Campanhas
  getCampaigns: () => request('/campaigns/'),

  // Analytics e Indicadores
  getAnalytics: () => request('/analytics/'),
};

export default api;
