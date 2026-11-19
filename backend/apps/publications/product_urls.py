import re
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit


ITEM_ID_PATTERN = re.compile(r'/MLB-?(\d+)(?:[-/?#]|$)', re.IGNORECASE)


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
