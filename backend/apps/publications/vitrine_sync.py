"""
Exportador automático da Vitrine Pública de Ofertas (vitrine/public/ofertas.json).
Mantém apenas ofertas publicadas nas últimas 48 horas (limpeza automática) e permite
integração direta com Vercel / Netlify / GitHub Pages sem banco pago.
"""

import json
import logging
import subprocess
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from .models import IncomingAffiliateOffer, IncomingOfferStatus
from .product_urls import get_store_display_name

logger = logging.getLogger(__name__)


def get_vitrine_json_path():
    project_root = Path(settings.BASE_DIR).parent
    return project_root / 'vitrine' / 'public' / 'ofertas.json'


def build_vitrine_offer_url(offer_id):
    base_url = (getattr(settings, 'AFFILIATE_BOT_VITRINE_BASE_URL', '') or '').strip().rstrip('/')
    if not base_url or not offer_id:
        return ''
    return f'{base_url}/oferta/{offer_id}'


def _serialize_vitrine_offer(offer):
    prod = offer.product
    if not prod:
        return None
    price_val = float(prod.price) if prod.price is not None else 0.0
    orig_val = float(prod.original_price) if prod.original_price is not None else None
    discount_pct = 0
    if orig_val and orig_val > price_val > 0:
        discount_pct = round(((orig_val - price_val) / orig_val) * 100)

    return {
        'id': str(offer.id),
        'item_id': prod.item_id,
        'title': prod.title,
        'price': round(price_val, 2),
        'original_price': round(orig_val, 2) if orig_val else None,
        'discount_pct': discount_pct,
        'coupon': (offer.coupon or '').strip(),
        'store': offer.store or prod.store or 'mercadolivre',
        'store_label': get_store_display_name(offer.store or prod.store),
        'category': prod.category or 'other',
        'thumbnail': prod.thumbnail or '',
        'affiliate_url': offer.affiliate_url or prod.affiliate_url or prod.product_url,
        'published_at': (offer.published_at or timezone.now()).isoformat(),
    }


def build_vitrine_offers_payload(max_age_hours=48, limit=120, extra_offer=None):
    cutoff = timezone.now() - timedelta(hours=max_age_hours)
    qs = (
        IncomingAffiliateOffer.objects.filter(
            status=IncomingOfferStatus.PUBLISHED,
            published_at__gte=cutoff,
            product__isnull=False,
        )
        .select_related('product')
        .order_by('-published_at', '-id')[:limit]
    )

    items = []
    seen_item_ids = set()

    if extra_offer is not None and getattr(extra_offer, 'product', None):
        serialized = _serialize_vitrine_offer(extra_offer)
        if serialized:
            items.append(serialized)
            seen_item_ids.add(serialized['item_id'])

    for offer in qs:
        prod = offer.product
        if not prod or prod.item_id in seen_item_ids:
            continue
        seen_item_ids.add(prod.item_id)
        serialized = _serialize_vitrine_offer(offer)
        if serialized:
            items.append(serialized)

    return {
        'generated_at': timezone.now().isoformat(),
        'max_age_hours': max_age_hours,
        'vip_group_name': getattr(settings, 'AFFILIATE_BOT_VIP_GROUP_NAME', 'Garimpo de Ofertas'),
        'vip_invite_link': getattr(settings, 'AFFILIATE_BOT_VIP_INVITE_LINK', ''),
        'total': len(items),
        'offers': items,
    }


def export_vitrine_json(max_age_hours=48, extra_offer=None):
    payload = build_vitrine_offers_payload(max_age_hours=max_age_hours, extra_offer=extra_offer)
    target = get_vitrine_json_path()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding='utf-8',
        )
    except Exception:
        logger.warning('Falha ao gravar vitrine/public/ofertas.json.', exc_info=True)
    return payload


def sync_vitrine_to_github(max_age_hours=48, extra_offer=None):
    """
    Exporta vitrine/public/ofertas.json e, se houver mudanças reais e
    AFFILIATE_BOT_VITRINE_AUTO_PUSH estiver ativo, faz commit e push apenas
    desse arquivo para disparar o redeploy automático na Vercel.
    """
    export_vitrine_json(max_age_hours=max_age_hours, extra_offer=extra_offer)
    auto_push = str(getattr(settings, 'AFFILIATE_BOT_VITRINE_AUTO_PUSH', '') or '').strip().lower() in (
        '1', 'true', 'yes', 'on',
    )
    if not auto_push:
        return False

    repo_root = Path(settings.BASE_DIR).parent
    rel_json = 'vitrine/public/ofertas.json'
    try:
        diff_res = subprocess.run(
            ['git', 'diff', '--quiet', '--', rel_json],
            cwd=str(repo_root),
            capture_output=True,
            timeout=15,
        )
        if diff_res.returncode == 0:
            return False

        subprocess.run(
            ['git', 'add', '--', rel_json],
            cwd=str(repo_root),
            check=True,
            capture_output=True,
            timeout=15,
        )
        subprocess.run(
            ['git', 'commit', '-m', 'chore(vitrine): atualiza ofertas.json automaticamente', '--', rel_json],
            cwd=str(repo_root),
            check=True,
            capture_output=True,
            timeout=20,
        )
        subprocess.run(
            ['git', 'push', 'origin', 'main'],
            cwd=str(repo_root),
            check=True,
            capture_output=True,
            timeout=45,
        )
        logger.info('Vitrine sincronizada com GitHub/Vercel (%s).', rel_json)
        return True
    except Exception as exc:
        logger.warning('Não foi possível sincronizar vitrine/public/ofertas.json com o GitHub: %s', exc)
        return False
