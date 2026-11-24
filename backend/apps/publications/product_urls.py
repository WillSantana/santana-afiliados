import re
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit


ITEM_ID_PATTERN = re.compile(r'/MLB-?(\d+)(?:[-/?#]|$)', re.IGNORECASE)
AMAZON_ASIN_PATTERN = re.compile(
    r'/(?:dp|gp/product|gp/aw/d|d)/([A-Z0-9]{10})(?:[/?#]|$)',
    re.IGNORECASE,
)
SHOPEE_DASH_ID_PATTERN = re.compile(r'-i\.(\d+)\.(\d+)(?:[/?#]|$)', re.IGNORECASE)
SHOPEE_PATH_ID_PATTERN = re.compile(r'/(?:product|opaanlp)/(\d+)/(\d+)(?:[/?#]|$)', re.IGNORECASE)
TIKTOK_PRODUCT_ID_PATTERN = re.compile(
    r'/(?:view/product|shop/pdp/[^/?#]+|product)/(\d{10,24})(?:[/?#]|$)',
    re.IGNORECASE,
)

STORE_MERCADOLIVRE = 'mercadolivre'
STORE_AMAZON = 'amazon'
STORE_SHOPEE = 'shopee'
STORE_TIKTOK = 'tiktok'

STORE_DISPLAY_NAMES = {
    STORE_MERCADOLIVRE: 'Mercado Livre',
    STORE_AMAZON: 'Amazon',
    STORE_SHOPEE: 'Shopee',
    STORE_TIKTOK: 'TikTok Shop',
}

STORE_PREPOSITION_LABELS = {
    STORE_MERCADOLIVRE: 'NO MERCADO LIVRE',
    STORE_AMAZON: 'NA AMAZON',
    STORE_SHOPEE: 'NA SHOPEE',
    STORE_TIKTOK: 'NO TIKTOK SHOP',
}


def parse_brl_price(value):
    normalized = re.sub(r'[^\d,.]', '', value or '')
    if not normalized:
        return None

    if ',' in normalized:
        normalized = normalized.replace('.', '').replace(',', '.')
    elif normalized.count('.') > 1:
        normalized = normalized.replace('.', '')

    try:
        price = Decimal(normalized)
    except InvalidOperation:
        return None

    return price if price > 0 else None


def extract_item_id(url):
    try:
        parsed = urlsplit(url)
    except Exception:
        return None
    match = ITEM_ID_PATTERN.search(parsed.path)
    if match:
        return f'MLB{match.group(1)}'
    query_match = re.search(r'(?:item_id|wid|itemId)=MLB-?(\d+)', parsed.query, re.IGNORECASE)
    if query_match:
        return f'MLB{query_match.group(1)}'
    return None


def is_marketplace_url(url):
    try:
        parsed = urlsplit(url)
    except (ValueError, TypeError):
        return False

    hostname = (parsed.hostname or '').lower()
    return parsed.scheme in ('https', 'http') and (
        hostname in ('meli.la', 'www.meli.la', 'mercadolivre.com.br', 'mercadolivre.com')
        or hostname.endswith('.mercadolivre.com.br')
        or hostname.endswith('.mercadolivre.com')
    )


def is_amazon_url(url):
    try:
        parsed = urlsplit(url)
    except (ValueError, TypeError):
        return False

    hostname = (parsed.hostname or '').lower()
    return parsed.scheme in ('https', 'http') and (
        hostname in ('amzn.to', 'www.amzn.to', 'a.co', 'www.a.co', 'amazon.com.br', 'www.amazon.com.br')
        or hostname.endswith('.amazon.com.br')
    )


def extract_amazon_asin(url):
    try:
        parsed = urlsplit(url)
    except Exception:
        return None
    match = AMAZON_ASIN_PATTERN.search(parsed.path or '')
    if match:
        return match.group(1).upper()
    return None


def extract_amazon_item_id(url):
    asin = extract_amazon_asin(url)
    return f'AMZN{asin}' if asin else None


def is_shopee_url(url):
    try:
        parsed = urlsplit(url)
    except (ValueError, TypeError):
        return False

    hostname = (parsed.hostname or '').lower()
    return parsed.scheme in ('https', 'http') and (
        hostname in (
            's.shopee.com.br',
            'shopee.com.br',
            'www.shopee.com.br',
            'shope.ee',
            'www.shope.ee',
            'shp.ee',
        )
        or hostname.endswith('.shopee.com.br')
    )


def extract_shopee_ids(url):
    try:
        parsed = urlsplit(url)
    except Exception:
        return None
    path = parsed.path or ''
    match = SHOPEE_DASH_ID_PATTERN.search(path) or SHOPEE_PATH_ID_PATTERN.search(path)
    if match:
        return match.group(1), match.group(2)
    return None


def extract_shopee_item_id(url):
    ids = extract_shopee_ids(url)
    if not ids:
        return None
    return f'SHP{ids[0]}_{ids[1]}'


def is_tiktok_url(url):
    try:
        parsed = urlsplit(url)
    except (ValueError, TypeError):
        return False

    hostname = (parsed.hostname or '').lower()
    path = (parsed.path or '').lower()
    if parsed.scheme not in ('https', 'http'):
        return False
    if hostname in ('vt.tiktok.com', 'vm.tiktok.com', 'shop.tiktok.com'):
        return True
    if hostname in ('tiktok.com', 'www.tiktok.com', 'm.tiktok.com'):
        return (
            '/shop/' in path
            or '/view/product/' in path
            or '/t/' in path
            or 'product_id=' in (parsed.query or '').lower()
        )
    return False


def extract_tiktok_product_id(url):
    try:
        parsed = urlsplit(url)
    except Exception:
        return None
    match = TIKTOK_PRODUCT_ID_PATTERN.search(parsed.path or '')
    if match:
        return match.group(1)
    query_match = re.search(r'(?:^|&)product_id=(\d{10,24})(?:&|$)', parsed.query or '', re.IGNORECASE)
    if query_match:
        return query_match.group(1)
    return None


def extract_tiktok_item_id(url):
    prod_id = extract_tiktok_product_id(url)
    return f'TTK{prod_id}' if prod_id else None


def detect_store_from_url(url):
    if is_marketplace_url(url):
        return STORE_MERCADOLIVRE
    if is_amazon_url(url):
        return STORE_AMAZON
    if is_shopee_url(url):
        return STORE_SHOPEE
    if is_tiktok_url(url):
        return STORE_TIKTOK
    return None


def get_store_display_name(store):
    return STORE_DISPLAY_NAMES.get((store or '').lower(), 'Mercado Livre')


def get_store_headline_suffix(store):
    return STORE_PREPOSITION_LABELS.get((store or '').lower(), 'NO MERCADO LIVRE')
