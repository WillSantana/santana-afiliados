function escapeHtml(str) {
  return String(str || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function formatBRL(value) {
  const num = Number(value);
  if (!Number.isFinite(num)) return '';
  return `R$ ${num.toFixed(2).replace('.', ',')}`;
}

export default async function handler(req, res) {
  const host = req.headers['x-forwarded-host'] || req.headers.host || 'santana-afiliados.vercel.app';
  const proto = req.headers['x-forwarded-proto'] || 'https';
  const origin = `${proto}://${host}`;
  const rawId = Array.isArray(req.query.id) ? req.query.id[0] : (req.query.id || '');
  const offerId = String(rawId).trim();

  try {
    const [indexRes, offersRes] = await Promise.all([
      fetch(`${origin}/index.html`),
      fetch(`${origin}/ofertas.json`),
    ]);

    let html = indexRes.ok
      ? await indexRes.text()
      : '<!doctype html><html lang="pt-BR"><head><title>Garimpo de Ofertas</title></head><body><div id="root"></div></body></html>';

    let offer = null;
    if (offersRes.ok && offerId) {
      const payload = await offersRes.json();
      offer = (payload.offers || []).find((item) => String(item.id) === offerId) || null;
    }

    if (offer) {
      const priceStr = formatBRL(offer.price);
      const origStr = offer.original_price && offer.original_price > offer.price
        ? ` (De ${formatBRL(offer.original_price)})`
        : '';
      const discountPrefix = offer.discount_pct > 0 ? `${offer.discount_pct}% OFF • ` : '';
      const ogTitle = `${discountPrefix}${offer.title}`;
      const ogDesc = `Por ${priceStr}${origStr} na ${offer.store_label}. Oferta verificada no Garimpo de Ofertas.`;
      const ogImage = offer.thumbnail || '';
      const ogUrl = `${origin}/oferta/${encodeURIComponent(offerId)}`;

      html = html
        .replace(/<title>[\s\S]*?<\/title>/i, `<title>${escapeHtml(ogTitle)} | Garimpo de Ofertas</title>`)
        .replace(
          /<meta\s+property="og:title"\s+content="[^"]*"\s*\/?>/i,
          `<meta property="og:title" content="${escapeHtml(ogTitle)}" />`,
        )
        .replace(
          /<meta\s+property="og:description"\s+content="[^"]*"\s*\/?>/i,
          `<meta property="og:description" content="${escapeHtml(ogDesc)}" />`,
        )
        .replace(
          /<meta\s+property="og:image"\s+content="[^"]*"\s*\/?>/i,
          `<meta property="og:image" content="${escapeHtml(ogImage)}" />\n    <meta property="og:url" content="${escapeHtml(ogUrl)}" />`,
        );
    }

    res.setHeader('Content-Type', 'text/html; charset=utf-8');
    res.setHeader('Cache-Control', 'public, s-maxage=60, stale-while-revalidate=300');
    return res.status(200).send(html);
  } catch {
    return res.redirect(302, `/index.html`);
  }
}
