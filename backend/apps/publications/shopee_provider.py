"""
Provedor de automação de ofertas e links de afiliado para a Shopee Brasil.
Mantém o mesmo contrato de saída dos provedores do Mercado Livre e da Amazon
para reutilizar fila, filtro de qualidade, balanceamento por loja/grupo e envio no WhatsApp.
"""

import hashlib
import json
import logging
import re
import time
import urllib.request
from decimal import Decimal
from urllib.parse import urlsplit

from django.conf import settings

from .product_urls import (
    STORE_SHOPEE,
    extract_shopee_ids,
    is_shopee_url,
    parse_brl_price,
)

logger = logging.getLogger(__name__)

SHOPEE_CUSTOM_LINK_URL = 'https://affiliate.shopee.com.br/offer/custom_link'
SHOPEE_OPEN_API_ENDPOINT = 'https://open-api.affiliate.shopee.com.br/graphql'
SHOPEE_SHORT_LINK_RE = re.compile(
    r'https://(?:s\.shopee\.com\.br|shope\.ee|shp\.ee)/[A-Za-z0-9_-]+',
    re.IGNORECASE,
)


def has_shopee_open_api_credentials():
    app_id = (getattr(settings, 'AFFILIATE_BOT_SHOPEE_APP_ID', '') or '').strip()
    secret = (getattr(settings, 'AFFILIATE_BOT_SHOPEE_SECRET', '') or '').strip()
    return bool(app_id and secret)


def build_shopee_open_api_headers(payload_str, timestamp=None):
    app_id = (getattr(settings, 'AFFILIATE_BOT_SHOPEE_APP_ID', '') or '').strip()
    secret = (getattr(settings, 'AFFILIATE_BOT_SHOPEE_SECRET', '') or '').strip()
    ts = str(int(timestamp if timestamp is not None else time.time()))
    raw_sig = f'{app_id}{ts}{payload_str}{secret}'
    signature = hashlib.sha256(raw_sig.encode('utf-8')).hexdigest()
    return {
        'Content-Type': 'application/json',
        'Authorization': f'SHA256 Credential={app_id},Timestamp={ts},Signature={signature}',
    }


def _call_shopee_graphql(query, variables=None):
    from .affiliate_watcher import AffiliateAutomationError

    body = {'query': query}
    if variables:
        body['variables'] = variables
    payload_str = json.dumps(body, separators=(',', ':'), ensure_ascii=False)
    headers = build_shopee_open_api_headers(payload_str)
    req = urllib.request.Request(
        SHOPEE_OPEN_API_ENDPOINT,
        data=payload_str.encode('utf-8'),
        headers=headers,
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode('utf-8', errors='replace')
    except Exception as exc:
        raise AffiliateAutomationError(f'Falha ao consultar Open API da Shopee: {exc}') from exc

    try:
        parsed = json.loads(raw)
    except Exception as exc:
        raise AffiliateAutomationError('Resposta inválida da Open API da Shopee.') from exc

    if parsed.get('errors'):
        msg = parsed['errors'][0].get('message') or str(parsed['errors'][0])
        raise AffiliateAutomationError(f'Open API da Shopee retornou erro: {msg}')
    return parsed.get('data') or {}


def _resolve_shopee_shortlink_http(source_link):
    req = urllib.request.Request(
        source_link,
        headers={'User-Agent': 'Mozilla/5.0'},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.geturl() or source_link
    except Exception:
        return source_link


def _resolve_shopee_via_open_api(source_link):
    from .affiliate_watcher import AffiliateAutomationError

    resolved_url = _resolve_shopee_shortlink_http(source_link)
    ids = extract_shopee_ids(resolved_url) or extract_shopee_ids(source_link)
    if not ids:
        raise AffiliateAutomationError(
            f'Não foi possível identificar shop_id/item_id da oferta Shopee ({resolved_url[:100]}).'
        )

    shop_id, prod_id = ids
    product_url = f'https://shopee.com.br/product/{shop_id}/{prod_id}'
    item_id = f'SHP{shop_id}_{prod_id}'

    query = (
        'query($itemId: Int64) {'
        ' productOfferV2(itemId: $itemId, limit: 1) {'
        '  nodes { itemId productName priceMin priceMax priceDiscountRate ratingStar imageUrl productLink offerLink }'
        ' }'
        '}'
    )
    data = _call_shopee_graphql(query, {'itemId': int(prod_id)})
    nodes = ((data.get('productOfferV2') or {}).get('nodes')) or []
    if not nodes:
        raise AffiliateAutomationError(f'Produto Shopee {prod_id} não encontrado na Open API de Afiliados.')

    node = nodes[0]
    title = (node.get('productName') or '').strip()
    price = parse_brl_price(str(node.get('priceMin') or node.get('priceMax') or ''))
    if not title or price is None:
        raise AffiliateAutomationError('Dados incompletos retornados pela Open API da Shopee.')

    original_price = None
    discount_rate = node.get('priceDiscountRate')
    if discount_rate:
        try:
            pct = float(discount_rate)
            if 0 < pct < 95:
                original_price = (price / Decimal(str(1.0 - pct / 100.0))).quantize(Decimal('0.01'))
        except Exception:
            original_price = None

    rating = None
    if node.get('ratingStar'):
        try:
            r_val = float(str(node['ratingStar']).replace(',', '.'))
            if 0.0 < r_val <= 5.0:
                rating = r_val
        except ValueError:
            rating = None

    thumbnail = str(node.get('imageUrl') or '')
    if not thumbnail.startswith('https://'):
        thumbnail = ''

    return {
        'item_id': item_id,
        'title': title[:255],
        'price': price,
        'original_price': original_price,
        'product_url': product_url,
        'thumbnail': thumbnail,
        'rating': rating,
        'store': STORE_SHOPEE,
        'preset_affiliate_url': (node.get('offerLink') or '').strip(),
    }


def _generate_shopee_link_via_open_api(product_url):
    from .affiliate_watcher import AffiliateAutomationError

    mutation = (
        'mutation($originUrl: String!) {'
        ' generateShortLink(input: { originUrl: $originUrl, subIds: ["santana_whatsapp"] }) { shortLink }'
        '}'
    )
    data = _call_shopee_graphql(mutation, {'originUrl': product_url})
    short_link = ((data.get('generateShortLink') or {}).get('shortLink') or '').strip()
    if not short_link or not is_shopee_url(short_link):
        raise AffiliateAutomationError('Open API da Shopee não retornou um shortLink válido.')
    return short_link


def _element_text(browser, selectors):
    from selenium.common.exceptions import WebDriverException
    from selenium.webdriver.common.by import By

    for selector in selectors:
        try:
            for el in browser.find_elements(By.CSS_SELECTOR, selector):
                text = (el.text or el.get_attribute('textContent') or '').strip()
                if text:
                    return text
        except WebDriverException:
            continue
    return ''


def _element_attribute(browser, selectors, attr):
    from selenium.common.exceptions import WebDriverException
    from selenium.webdriver.common.by import By

    for selector in selectors:
        try:
            for el in browser.find_elements(By.CSS_SELECTOR, selector):
                val = (el.get_attribute(attr) or '').strip()
                if val:
                    return val
        except WebDriverException:
            continue
    return ''


def _check_shopee_gate(browser):
    from .affiliate_watcher import AffiliateAutomationError

    current_url = (browser.current_url or '').lower()
    page_snippet = (browser.page_source or '')[:4000].lower()
    if (
        'verify/captcha' in current_url
        or 'verificação de segurança' in page_snippet
        or 'deslize para concluir' in page_snippet
        or 'slide to complete' in page_snippet
    ):
        raise AffiliateAutomationError(
            'A Shopee solicitou verificação anti-robô (CAPTCHA). Resolva no Chrome dedicado para continuar.'
        )
    if '/buyer/login' in current_url or 'shopee.com.br/account/signin' in current_url:
        raise AffiliateAutomationError(
            'A Shopee exigiu login no Chrome dedicado. Faça login em shopee.com.br e tente novamente.'
        )


def _extract_json_ld_product(browser):
    try:
        scripts = browser.execute_script(
            'return Array.from(document.querySelectorAll(\'script[type="application/ld+json"]\')).map(s => s.textContent || "");'
        ) or []
    except Exception:
        return {}

    for raw in scripts:
        try:
            data = json.loads(raw)
        except Exception:
            continue
        items = data if isinstance(data, list) else [data]
        for entry in items:
            if isinstance(entry, dict) and entry.get('@type') == 'Product':
                return entry
    return {}


def resolve_shopee_product_page(browser, source_link, original_message=''):
    if has_shopee_open_api_credentials():
        return _resolve_shopee_via_open_api(source_link)

    from selenium.common.exceptions import TimeoutException
    from selenium.webdriver.support.ui import WebDriverWait
    from .affiliate_watcher import AffiliateAutomationError

    browser.get(source_link)
    try:
        WebDriverWait(browser, 15).until(
            lambda driver: 'shopee.com.br' in (urlsplit(driver.current_url).hostname or '').lower()
            and (
                extract_shopee_ids(driver.current_url or '')
                or 'verify/captcha' in (driver.current_url or '').lower()
                or '/buyer/login' in (driver.current_url or '').lower()
            )
        )
    except TimeoutException:
        pass
    time.sleep(2.5)
    _check_shopee_gate(browser)

    current_url = browser.current_url or ''
    ids = (
        extract_shopee_ids(current_url)
        or extract_shopee_ids(_element_attribute(browser, ('link[rel="canonical"]',), 'href'))
    )
    if not ids:
        raise AffiliateAutomationError(
            f'O link da Shopee não resolveu para uma página de produto válida (destino: {current_url[:100]}).'
        )

    shop_id, prod_id = ids
    product_url = f'https://shopee.com.br/product/{shop_id}/{prod_id}'
    item_id = f'SHP{shop_id}_{prod_id}'

    ld = _extract_json_ld_product(browser)

    title = (
        (ld.get('name') or '').strip()
        or _element_text(browser, ('h1', '[data-testid="pdp_product_title"]', 'div.WBVL_7 span'))
        or _element_attribute(browser, ('meta[property="og:title"]',), 'content')
        or (browser.title or '')
    )
    title = re.sub(r'\s*\|\s*Shopee\s*Brasil.*$', '', title, flags=re.IGNORECASE).strip()
    if not title or len(title) < 4:
        raise AffiliateAutomationError('Não foi possível confirmar o título do produto na Shopee.')

    price = None
    original_price = None
    offers = ld.get('offers') if isinstance(ld.get('offers'), dict) else {}
    if offers:
        price = parse_brl_price(str(offers.get('price') or offers.get('lowPrice') or ''))
        high_price = parse_brl_price(str(offers.get('highPrice') or ''))
        if high_price and price and high_price > price:
            original_price = high_price

    if price is None:
        price_text = _element_text(
            browser,
            (
                '.IZPeQz',
                '.pqTWkA',
                '[data-testid="pdp_product_price"]',
                'div[class*="price"]',
            ),
        ) or _element_attribute(browser, ('meta[property="product:price:amount"]',), 'content')
        # Se houver faixa "R$ 50,00 - R$ 80,00", pega o primeiro preço
        first_price_match = re.search(r'R?\$?\s*(\d[\d.,]*)', price_text or '')
        if first_price_match:
            price = parse_brl_price(first_price_match.group(1))

    if price is None:
        raise AffiliateAutomationError('Não foi possível confirmar o preço atual na página da Shopee.')

    if original_price is None:
        orig_text = _element_text(browser, ('.ZA5sW5', '.Y3DvsN', 'del', 's'))
        orig_match = re.search(r'R?\$?\s*(\d[\d.,]*)', orig_text or '')
        if orig_match:
            candidate_orig = parse_brl_price(orig_match.group(1))
            if candidate_orig and candidate_orig > price:
                original_price = candidate_orig

    thumbnail = ''
    ld_image = ld.get('image')
    if isinstance(ld_image, list) and ld_image:
        thumbnail = str(ld_image[0])
    elif isinstance(ld_image, str):
        thumbnail = ld_image
    if not thumbnail.startswith('https://'):
        thumbnail = _element_attribute(browser, ('meta[property="og:image"]',), 'content')
    if not thumbnail.startswith('https://'):
        thumbnail = ''

    rating = None
    agg = ld.get('aggregateRating') if isinstance(ld.get('aggregateRating'), dict) else {}
    if agg.get('ratingValue'):
        try:
            val = float(str(agg['ratingValue']).replace(',', '.'))
            if 0.0 < val <= 5.0:
                rating = val
        except ValueError:
            rating = None
    if rating is None:
        rating_text = _element_text(browser, ('.F9RHbS', '.OitLRu', '[class*="rating"]'))
        match_r = re.search(r'(\d[.,]\d)', rating_text or '')
        if match_r:
            try:
                val = float(match_r.group(1).replace(',', '.'))
                if 0.0 < val <= 5.0:
                    rating = val
            except ValueError:
                rating = None

    return {
        'item_id': item_id,
        'title': title[:255],
        'price': price,
        'original_price': original_price,
        'product_url': product_url,
        'thumbnail': thumbnail,
        'rating': rating,
        'store': STORE_SHOPEE,
    }


def generate_shopee_affiliate_link(browser, product_url):
    """
    Gera o link curto de afiliado usando a Open API oficial da Shopee (quando
    AFFILIATE_BOT_SHOPEE_APP_ID e AFFILIATE_BOT_SHOPEE_SECRET estiverem configurados)
    ou via Portal de Afiliados da Shopee Brasil no Chrome dedicado.
    """
    if has_shopee_open_api_credentials():
        return _generate_shopee_link_via_open_api(product_url)

    from selenium.common.exceptions import TimeoutException, WebDriverException
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from .affiliate_watcher import AffiliateAutomationError

    browser.get(SHOPEE_CUSTOM_LINK_URL)
    time.sleep(3)
    _check_shopee_gate(browser)

    if 'login' in (browser.current_url or '').lower() or 'signin' in (browser.current_url or '').lower():
        raise AffiliateAutomationError(
            'Faça login no Portal de Afiliados da Shopee (https://affiliate.shopee.com.br/) no Chrome dedicado.'
        )

    def find_url_input(driver):
        for sel in (
            'textarea.ant-input',
            'textarea',
            'input[placeholder*="link" i]',
            'input[placeholder*="url" i]',
            'input.ant-input',
        ):
            try:
                for el in driver.find_elements(By.CSS_SELECTOR, sel):
                    if el.is_displayed() and el.is_enabled():
                        return el
            except WebDriverException:
                continue
        return False

    try:
        url_input = WebDriverWait(browser, 15).until(find_url_input)
    except TimeoutException as exc:
        raise AffiliateAutomationError(
            'Não encontrei o campo de URL no gerador de links da Shopee. Confirme se está logado em affiliate.shopee.com.br.'
        ) from exc

    url_input.click()
    url_input.send_keys(Keys.CONTROL, 'a')
    url_input.send_keys(Keys.BACKSPACE)
    url_input.send_keys(product_url)
    time.sleep(0.5)

    clicked = False
    for btn in browser.find_elements(By.CSS_SELECTOR, 'button'):
        try:
            label = (btn.text or '').strip().lower()
            if btn.is_displayed() and btn.is_enabled() and any(
                kw in label for kw in ('obter link', 'gerar link', 'get link', 'obter')
            ):
                try:
                    btn.click()
                except Exception:
                    browser.execute_script('arguments[0].click();', btn)
                clicked = True
                break
        except WebDriverException:
            continue

    if not clicked:
        raise AffiliateAutomationError(
            'Não encontrei o botão "Obter link" no Portal de Afiliados da Shopee.'
        )

    def read_generated_link(driver):
        # Procura em inputs/textareas primeiro, depois no texto do modal/página
        for sel in ('textarea', 'input[type="text"]', 'input'):
            try:
                for field in driver.find_elements(By.CSS_SELECTOR, sel):
                    val = (field.get_attribute('value') or field.text or '').strip()
                    match = SHOPEE_SHORT_LINK_RE.search(val)
                    if match:
                        return match.group(0)
            except WebDriverException:
                continue
        try:
            body_text = driver.execute_script('return document.body ? document.body.innerText : ""') or ''
            match = SHOPEE_SHORT_LINK_RE.search(body_text)
            if match:
                return match.group(0)
        except Exception:
            pass
        return False

    try:
        affiliate_url = WebDriverWait(browser, 15, poll_frequency=0.5).until(read_generated_link)
        if affiliate_url:
            return affiliate_url.strip()
    except TimeoutException as exc:
        raise AffiliateAutomationError(
            'O Portal de Afiliados da Shopee não retornou o link curto em 15 segundos.'
        ) from exc

    raise AffiliateAutomationError('Não foi possível obter o link de afiliado da Shopee.')


def validate_shopee_affiliate_link(browser, affiliate_url, expected_item_id):
    from .affiliate_watcher import AffiliateAutomationError

    if not affiliate_url or not is_shopee_url(affiliate_url):
        raise AffiliateAutomationError('O link gerado não é um link válido da Shopee.')
    if not SHOPEE_SHORT_LINK_RE.match(affiliate_url):
        raise AffiliateAutomationError('O link da Shopee não está no formato curto oficial de afiliado (s.shopee.com.br / shope.ee).')
    return True
