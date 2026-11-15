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
    match = ITEM_ID_PATTERN.search(urlsplit(url).path)
    return f'MLB{match.group(1)}' if match else None


def is_marketplace_url(url):
    try:
        parsed = urlsplit(url)
    except ValueError:
        return False

    hostname = (parsed.hostname or '').lower()
    return parsed.scheme == 'https' and (
        hostname == 'mercadolivre.com.br'
        or hostname.endswith('.mercadolivre.com.br')
    )
