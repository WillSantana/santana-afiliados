"""
Provedor de automação de ofertas e links de afiliado para o TikTok Shop.
Mantém o mesmo contrato de saída dos provedores do Mercado Livre, Amazon e Shopee
para reutilizar fila, filtro de qualidade, balanceamento por loja/grupo e envio no WhatsApp.
"""

import json
import logging
import re
import time
from urllib.parse import urlsplit

from .product_urls import (
    STORE_TIKTOK,
    extract_tiktok_product_id,
    is_tiktok_url,
    parse_brl_price,
)

logger = logging.getLogger(__name__)

TIKTOK_AFFILIATE_PORTAL_URL = 'https://affiliate.tiktok.com/product/marketplace'
TIKTOK_SHORT_LINK_RE = re.compile(
    r'https://(?:vt\.tiktok\.com|vm\.tiktok\.com|shop\.tiktok\.com|www\.tiktok\.com/t)/[A-Za-z0-9_/?=&-]+',
    re.IGNORECASE,
)


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


def _check_tiktok_gate(browser):
    from .affiliate_watcher import AffiliateAutomationError

    current_url = (browser.current_url or '').lower()
    page_snippet = (browser.page_source or '')[:4000].lower()
    if (
        'captcha' in current_url
        or 'captcha_verify' in page_snippet
        or 'verificação de segurança' in page_snippet
        or 'drag the slider' in page_snippet
        or 'arraste o controle deslizante' in page_snippet
    ):
        raise AffiliateAutomationError(
            'O TikTok Shop solicitou verificação anti-robô (CAPTCHA). Resolva no Chrome dedicado para continuar.'
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


def resolve_tiktok_product_page(browser, source_link, original_message=''):
    from selenium.common.exceptions import TimeoutException
    from selenium.webdriver.support.ui import WebDriverWait
    from .affiliate_watcher import AffiliateAutomationError

    browser.get(source_link)
    try:
        WebDriverWait(browser, 15).until(
            lambda driver: 'tiktok.com' in (urlsplit(driver.current_url).hostname or '').lower()
            and (
                extract_tiktok_product_id(driver.current_url or '')
                or _element_text(driver, ('h1',))
                or _element_attribute(driver, ('meta[property="og:title"]',), 'content')
            )
        )
    except TimeoutException:
        pass
    time.sleep(2.5)
    _check_tiktok_gate(browser)

    current_url = browser.current_url or ''
    prod_id = (
        extract_tiktok_product_id(current_url)
        or extract_tiktok_product_id(_element_attribute(browser, ('link[rel="canonical"]',), 'href'))
    )
    if not prod_id:
        match_body = re.search(r'"product_id"\s*:\s*"(\d{10,24})"', (browser.page_source or '')[:50000])
        if match_body:
            prod_id = match_body.group(1)
    if not prod_id:
        raise AffiliateAutomationError(
            f'O link do TikTok não resolveu para um produto válido do TikTok Shop (destino: {current_url[:100]}).'
        )

    product_url = f'https://shop.tiktok.com/view/product/{prod_id}'
    item_id = f'TTK{prod_id}'

    ld = _extract_json_ld_product(browser)
    title = (
        (ld.get('name') or '').strip()
        or _element_text(browser, ('h1', '[data-testid="pdp-title"]', '[class*="product-title"]'))
        or _element_attribute(browser, ('meta[property="og:title"]',), 'content')
        or (browser.title or '')
    )
    title = re.sub(r'\s*\|\s*TikTok.*$', '', title, flags=re.IGNORECASE).strip()
    if not title or len(title) < 4:
        raise AffiliateAutomationError('Não foi possível confirmar o título do produto no TikTok Shop.')

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
                '[data-testid="pdp-price"]',
                '[class*="sale-price"]',
                '[class*="price"]',
            ),
        ) or _element_attribute(browser, ('meta[property="product:price:amount"]',), 'content')
        match_p = re.search(r'R?\$?\s*(\d[\d.,]*)', price_text or '')
        if match_p:
            price = parse_brl_price(match_p.group(1))

    if price is None:
        raise AffiliateAutomationError('Não foi possível confirmar o preço atual na página do TikTok Shop.')

    if original_price is None:
        orig_text = _element_text(browser, ('[class*="origin-price"]', '[class*="market-price"]', 'del', 's'))
        match_o = re.search(r'R?\$?\s*(\d[\d.,]*)', orig_text or '')
        if match_o:
            candidate_orig = parse_brl_price(match_o.group(1))
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

    return {
        'item_id': item_id,
        'title': title[:255],
        'price': price,
        'original_price': original_price,
        'product_url': product_url,
        'thumbnail': thumbnail,
        'rating': rating,
        'store': STORE_TIKTOK,
    }


def generate_tiktok_affiliate_link(browser, product_url):
    """
    Gera link de afiliado via TikTok Shop Affiliate Center no Chrome dedicado.
    """
    from selenium.common.exceptions import TimeoutException, WebDriverException
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from .affiliate_watcher import AffiliateAutomationError

    prod_id = extract_tiktok_product_id(product_url)
    browser.get(TIKTOK_AFFILIATE_PORTAL_URL)
    time.sleep(3)
    _check_tiktok_gate(browser)

    if 'login' in (browser.current_url or '').lower() or 'signin' in (browser.current_url or '').lower():
        raise AffiliateAutomationError(
            'Faça login no TikTok Shop Affiliate Center (https://affiliate.tiktok.com/) no Chrome dedicado.'
        )

    def find_search_input(driver):
        for sel in (
            'input[placeholder*="pesquis" i]',
            'input[placeholder*="search" i]',
            'input[placeholder*="link" i]',
            'input[type="search"]',
            'input[type="text"]',
        ):
            try:
                for el in driver.find_elements(By.CSS_SELECTOR, sel):
                    if el.is_displayed() and el.is_enabled():
                        return el
            except WebDriverException:
                continue
        return False

    try:
        search_input = WebDriverWait(browser, 15).until(find_search_input)
    except TimeoutException as exc:
        raise AffiliateAutomationError(
            'Não encontrei a busca de produtos no TikTok Shop Affiliate Center. Confirme o login no Chrome dedicado.'
        ) from exc

    query_term = prod_id or product_url
    search_input.click()
    search_input.send_keys(Keys.CONTROL, 'a')
    search_input.send_keys(Keys.BACKSPACE)
    search_input.send_keys(query_term, Keys.ENTER)
    time.sleep(3)

    # Procura botão de copiar/obter link de afiliado
    clicked = False
    for btn in browser.find_elements(By.CSS_SELECTOR, 'button, a'):
        try:
            label = (btn.text or '').strip().lower()
            if btn.is_displayed() and btn.is_enabled() and any(
                kw in label for kw in ('copiar link', 'copy link', 'obter link', 'get link', 'promover', 'promote')
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
            'Não encontrei o botão de gerar/copiar link de afiliado no TikTok Shop Affiliate Center.'
        )

    def read_generated_link(driver):
        for sel in ('textarea', 'input[type="text"]', 'input'):
            try:
                for field in driver.find_elements(By.CSS_SELECTOR, sel):
                    val = (field.get_attribute('value') or field.text or '').strip()
                    match = TIKTOK_SHORT_LINK_RE.search(val)
                    if match:
                        return match.group(0)
            except WebDriverException:
                continue
        try:
            body_text = driver.execute_script('return document.body ? document.body.innerText : ""') or ''
            match = TIKTOK_SHORT_LINK_RE.search(body_text)
            if match:
                return match.group(0)
        except Exception:
            pass
        return False

    try:
        affiliate_url = WebDriverWait(browser, 12, poll_frequency=0.5).until(read_generated_link)
        if affiliate_url:
            return affiliate_url.strip()
    except TimeoutException as exc:
        raise AffiliateAutomationError(
            'O TikTok Shop Affiliate Center não exibiu o link gerado em 12 segundos.'
        ) from exc

    raise AffiliateAutomationError('Não foi possível obter o link de afiliado do TikTok Shop.')


def validate_tiktok_affiliate_link(browser, affiliate_url, expected_item_id):
    from .affiliate_watcher import AffiliateAutomationError

    if not affiliate_url or not is_tiktok_url(affiliate_url):
        raise AffiliateAutomationError('O link gerado não é um link válido do TikTok Shop.')
    return True
