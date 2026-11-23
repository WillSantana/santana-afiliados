"""
Provedor de automação de ofertas e links de afiliado para a Amazon (Brasil).
Mantém o mesmo contrato de saída do provedor do Mercado Livre para reutilizar
fila, filtro de qualidade, balanceamento entre grupos e envio no WhatsApp.
"""

import logging
import re
import time
from urllib.parse import parse_qs, urlsplit

from django.conf import settings

from .product_urls import (
    STORE_AMAZON,
    extract_amazon_asin,
    extract_amazon_item_id,
    is_amazon_url,
    parse_brl_price,
)

logger = logging.getLogger(__name__)


def _first_element(browser, selectors):
    from selenium.common.exceptions import WebDriverException
    from selenium.webdriver.common.by import By

    for selector in selectors:
        try:
            for el in browser.find_elements(By.CSS_SELECTOR, selector):
                if el.is_displayed():
                    return el
        except WebDriverException:
            continue
    return None


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


def _check_amazon_captcha(browser):
    from .affiliate_watcher import AffiliateAutomationError

    current_url = (browser.current_url or '').lower()
    page_source = (browser.page_source or '')[:4000].lower()
    if (
        'validatecaptcha' in current_url
        or 'captchacharacters' in page_source
        or 'digite os caracteres' in page_source
        or 'enter the characters you see below' in page_source
    ):
        raise AffiliateAutomationError(
            'A Amazon solicitou verificação anti-robô (CAPTCHA). Resolva no Chrome dedicado para continuar.'
        )


def resolve_amazon_product_page(browser, source_link, original_message=''):
    from selenium.common.exceptions import TimeoutException
    from selenium.webdriver.support.ui import WebDriverWait
    from .affiliate_watcher import AffiliateAutomationError

    browser.get(source_link)
    try:
        WebDriverWait(browser, 15).until(
            lambda driver: 'amazon.com.br' in (urlsplit(driver.current_url).hostname or '').lower()
            and (
                _element_text(driver, ('#productTitle',))
                or _element_attribute(driver, ('meta[property="og:title"]',), 'content')
                or 'validatecaptcha' in (driver.current_url or '').lower()
            )
        )
    except TimeoutException:
        pass

    _check_amazon_captcha(browser)

    current_url = browser.current_url or ''
    asin = (
        extract_amazon_asin(current_url)
        or _element_attribute(browser, ('input#ASIN', 'input[name="ASIN"]'), 'value').upper()
        or extract_amazon_asin(_element_attribute(browser, ('link[rel="canonical"]',), 'href'))
    )
    if not asin or not re.fullmatch(r'[A-Z0-9]{10}', asin):
        raise AffiliateAutomationError(
            f'O link da Amazon não resolveu para uma página de produto válida (destino: {current_url[:100]}).'
        )

    product_url = f'https://www.amazon.com.br/dp/{asin}'
    item_id = f'AMZN{asin}'

    title = _element_text(browser, ('#productTitle', 'span#productTitle'))
    if not title:
        title = _element_attribute(browser, ('meta[property="og:title"]',), 'content')
    title = re.sub(r'\s*:\s*Amazon\.com\.br.*$', '', title, flags=re.IGNORECASE).strip()
    if not title or len(title) < 4:
        raise AffiliateAutomationError('Não foi possível confirmar o título do produto na Amazon.')

    price_text = _element_text(
        browser,
        (
            '#corePriceDisplay_desktop_feature_div .priceToPay .a-offscreen',
            '#corePrice_feature_div .a-price .a-offscreen',
            '.a-price.priceToPay .a-offscreen',
            '#priceblock_dealprice',
            '#priceblock_ourprice',
            '#price_inside_buybox',
            '.a-price .a-offscreen',
        ),
    )
    price = parse_brl_price(price_text)
    if price is None:
        whole = _element_text(browser, ('#corePriceDisplay_desktop_feature_div .a-price-whole', '.priceToPay .a-price-whole'))
        frac = _element_text(browser, ('#corePriceDisplay_desktop_feature_div .a-price-fraction', '.priceToPay .a-price-fraction'))
        if whole:
            clean_whole = re.sub(r'[^\d]', '', whole)
            clean_frac = re.sub(r'[^\d]', '', frac) or '00'
            price = parse_brl_price(f'{clean_whole},{clean_frac}')
    if price is None:
        raise AffiliateAutomationError('Não foi possível confirmar o preço atual na página da Amazon.')

    original_text = _element_text(
        browser,
        (
            '#corePriceDisplay_desktop_feature_div .basisPrice .a-offscreen',
            '.basisPrice .a-text-price .a-offscreen',
            '.a-text-price[data-a-strike="true"] .a-offscreen',
            '#listPrice',
        ),
    )
    original_price = parse_brl_price(original_text)
    if original_price is not None and original_price <= price:
        original_price = None

    thumbnail = (
        _element_attribute(browser, ('#landingImage', '#imgBlkFront'), 'data-old-hires')
        or _element_attribute(browser, ('#landingImage', '#imgBlkFront'), 'src')
        or _element_attribute(browser, ('meta[property="og:image"]',), 'content')
    )
    if not thumbnail.startswith('https://'):
        thumbnail = ''

    rating = None
    rating_text = (
        _element_attribute(browser, ('#acrPopover',), 'title')
        or _element_text(browser, ('#acrPopover .a-size-base', '[data-hook="rating-out-of-five"]', '#averageCustomerReviews .a-icon-alt'))
    )
    if rating_text:
        match_rating = re.search(r'(\d(?:[.,]\d)?)', rating_text)
        if match_rating:
            try:
                parsed_rating = float(match_rating.group(1).replace(',', '.'))
                if 0.0 < parsed_rating <= 5.0:
                    rating = parsed_rating
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
        'store': STORE_AMAZON,
    }


def generate_amazon_affiliate_link(browser, product_url):
    """
    Gera o link de afiliado da Amazon usando a barra SiteStripe (conta logada no Chrome dedicado).
    Se a barra SiteStripe não estiver disponível mas AFFILIATE_BOT_AMAZON_TAG estiver configurada
    no .env, monta o link direto com a tag de associado.
    """
    from selenium.common.exceptions import TimeoutException, WebDriverException
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from .affiliate_watcher import AffiliateAutomationError

    asin = extract_amazon_asin(product_url)
    current_asin = extract_amazon_asin(browser.current_url or '')
    if not current_asin or (asin and current_asin != asin):
        browser.get(product_url)
        time.sleep(1.5)
    _check_amazon_captcha(browser)

    # 1. Tenta via SiteStripe (barra oficial da Amazon Associados no topo da página)
    sitestripe_btn = _first_element(
        browser,
        (
            '#amzn-ss-get-link-button',
            '#amzn-ss-text-link a',
            '#amzn-ss-text-link',
            'button[id*="amzn-ss-get-link"]',
            '[data-amzn-ss-link-type="text"]',
        ),
    )
    if sitestripe_btn is None:
        # Procura por texto no container da SiteStripe
        try:
            for btn in browser.find_elements(By.CSS_SELECTOR, '#amzn-ss-wrap a, #amzn-ss-wrap button'):
                label = (btn.text or btn.get_attribute('title') or '').strip().lower()
                if btn.is_displayed() and any(k in label for k in ('obter link', 'get link', 'texto', 'text')):
                    sitestripe_btn = btn
                    break
        except WebDriverException:
            sitestripe_btn = None

    if sitestripe_btn is not None:
        try:
            sitestripe_btn.click()
        except Exception:
            browser.execute_script('arguments[0].click();', sitestripe_btn)

        def read_sitestripe_link(driver):
            for sel in (
                '#amzn-ss-text-shortlink-textarea',
                '#amzn-ss-text-fulllink-textarea',
                'textarea[id*="amzn-ss"]',
                'input[id*="amzn-ss-text"]',
            ):
                try:
                    for field in driver.find_elements(By.CSS_SELECTOR, sel):
                        val = (field.get_attribute('value') or field.text or '').strip()
                        if val.startswith('https://') and is_amazon_url(val):
                            return val
                except WebDriverException:
                    continue
            return False

        try:
            generated = WebDriverWait(browser, 12, poll_frequency=0.5).until(read_sitestripe_link)
            if generated:
                return generated.strip()
        except TimeoutException:
            logger.warning('SiteStripe foi aberto, mas o link não apareceu dentro de 12s.')

    # 2. Fallback seguro usando a tag de associado configurada no .env (se houver)
    amazon_tag = (getattr(settings, 'AFFILIATE_BOT_AMAZON_TAG', '') or '').strip()
    if amazon_tag and asin:
        return f'https://www.amazon.com.br/dp/{asin}?tag={amazon_tag}'

    raise AffiliateAutomationError(
        'Não foi possível gerar o link de afiliado da Amazon. '
        'Confirme que está logado na sua conta Amazon Associados no Chrome dedicado (barra SiteStripe) '
        'ou configure AFFILIATE_BOT_AMAZON_TAG no .env.'
    )


def validate_amazon_affiliate_link(browser, affiliate_url, expected_item_id):
    from .affiliate_watcher import AffiliateAutomationError

    if not affiliate_url or not is_amazon_url(affiliate_url):
        raise AffiliateAutomationError('O link gerado não é um link válido da Amazon.')

    parsed = urlsplit(affiliate_url)
    hostname = (parsed.hostname or '').lower()
    if hostname in ('amzn.to', 'www.amzn.to', 'a.co', 'www.a.co'):
        browser.get(affiliate_url)
        time.sleep(1.5)
        _check_amazon_captcha(browser)
        resolved_item_id = extract_amazon_item_id(browser.current_url or '')
        if resolved_item_id and resolved_item_id != expected_item_id:
            raise AffiliateAutomationError(
                f'O link afiliado da Amazon redirecionou para outro produto ({resolved_item_id}) diferente do original ({expected_item_id}).'
            )
        return True

    query = parse_qs(parsed.query)
    if not query.get('tag'):
        raise AffiliateAutomationError('O link completo da Amazon não contém o parâmetro tag de afiliado.')
    resolved_item_id = extract_amazon_item_id(affiliate_url)
    if resolved_item_id and resolved_item_id != expected_item_id:
        raise AffiliateAutomationError(
            f'O link afiliado da Amazon aponta para {resolved_item_id}, diferente de {expected_item_id}.'
        )
    return True
