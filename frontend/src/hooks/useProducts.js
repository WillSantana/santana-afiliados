import { useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';

export function useProducts(initialFilters = {}) {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState(initialFilters);

  const fetchProducts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getProducts(filters);
      // Suporta paginação do DRF (data.results) ou lista direta
      setProducts(data.results || data);
    } catch (err) {
      setError(err.message || 'Falha ao carregar ofertas');
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    fetchProducts();
  }, [fetchProducts]);

  const approve = async (id) => {
    try {
      await api.approveProduct(id);
      await fetchProducts();
      return true;
    } catch (err) {
      alert(`Erro ao aprovar produto: ${err.message}`);
      return false;
    }
  };

  const reject = async (id, reason) => {
    try {
      await api.rejectProduct(id, reason);
      await fetchProducts();
      return true;
    } catch (err) {
      alert(`Erro ao rejeitar produto: ${err.message}`);
      return false;
    }
  };

  const associateAffiliateLink = async (id, url) => {
    try {
      await api.setAffiliateLink(id, url);
      await fetchProducts();
      return true;
    } catch (err) {
      alert(`Erro ao associar link: ${err.message}`);
      return false;
    }
  };

  return {
    products,
    loading,
    error,
    filters,
    setFilters,
    reload: fetchProducts,
    approve,
    reject,
    associateAffiliateLink,
  };
}
