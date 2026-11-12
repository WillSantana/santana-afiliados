export function getMercadoLivreItemUrl(product) {
  if (!product?.product_url) return '';

  try {
    const url = new URL(product.product_url);
    const hostname = url.hostname.toLowerCase();
    const isMercadoLivre = hostname === 'mercadolivre.com.br' || hostname.endsWith('.mercadolivre.com.br');
    const isSearchPage = hostname.startsWith('lista.') || /\/(jm\/search|lista)(\/|$)/i.test(url.pathname);
    if (!isMercadoLivre || isSearchPage || url.searchParams.has('as_word')) {
      return '';
    }

    const itemId = /^MLB(\d+)$/i.exec(product.item_id || '');
    const catalogUrl = /^\/p\/MLB-?(\d+)\/?$/i.exec(url.pathname);
    if (itemId && catalogUrl && itemId[1] === catalogUrl[1]) return '';

    return url.href;
  } catch {
    return '';
  }
}
