import logging
import os
import re
import tempfile
import time
from datetime import timedelta
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.catalog.models import ProductOffer, ProductStatus
from .models import (
    IncomingAffiliateOffer,
    IncomingOfferStatus,
    Publication,
    PublicationStatus,
)
from .product_urls import extract_item_id, is_marketplace_url, parse_brl_price

logger = logging.getLogger(__name__)

AFFILIATE_LINKBUILDER_URL = (
    'https://www.mercadolivre.com.br/afiliados/linkbuilder#hub'
)
MELI_SHORT_LINK_RE = re.compile(
    r'https?://(?:www\.)?meli\.la/[A-Za-z0-9]+',
    re.IGNORECASE,
)
COUPON_PATTERNS = (
    re.compile(r'\bcupom\s*[:\-]\s*([A-Za-z0-9_-]{3,40})', re.IGNORECASE),
    re.compile(r'\b(?:c[oó]digo|use|aplique)\s+(?:o\s+)?cupom\s*[:\-]?\s*([A-Za-z0-9_-]{3,40})', re.IGNORECASE),
)


class AffiliateAutomationError(Exception):
    pass


class WhatsAppSendUncertainError(AffiliateAutomationError):
    pass


def extract_short_links(text):
    links = set()
    for candidate in MELI_SHORT_LINK_RE.findall(text or ''):
        parsed = urlsplit(candidate)
        hostname = (parsed.hostname or '').lower()
        if parsed.scheme == 'https' and hostname in ('meli.la', 'www.meli.la'):
            links.add(urlunsplit(('https', hostname, parsed.path.rstrip('/'), '', '')))
    return links


def extract_coupon(text):
    coupons = set()
    for pattern in COUPON_PATTERNS:
        coupons.update(match.group(1).strip() for match in pattern.finditer(text or ''))
    return coupons.pop() if len(coupons) == 1 else ''


def open_automation_browser():
    try:
        from selenium import webdriver
        from selenium.common.exceptions import TimeoutException, WebDriverException
        from selenium.webdriver.support.ui import WebDriverWait
    except ImportError as exc:
        raise AffiliateAutomationError(
            'Selenium não está instalado. No backend, execute: '
            'python -m pip install -r requirements.txt'
        ) from exc

    debugger_address = getattr(
        settings,
        'AFFILIATE_BOT_CHROME_DEBUGGER_ADDRESS',
        '127.0.0.1:9222',
    ).strip()
    debugger_host, separator, debugger_port = debugger_address.rpartition(':')
    if (
        not separator
        or debugger_host.strip('[]').lower() not in ('127.0.0.1', 'localhost')
        or not debugger_port.isdecimal()
        or not 1 <= int(debugger_port) <= 65535
    ):
        raise AffiliateAutomationError(
            'Configure o Chrome de depuração com host local e porta válida, como 127.0.0.1:9222.'
        )

    options = webdriver.ChromeOptions()
    options.add_experimental_option('debuggerAddress', debugger_address)
    browser = None
    try:
        browser = webdriver.Chrome(options=options)
        WebDriverWait(browser, 180).until(
            lambda driver: next(
                (
                    handle
                    for handle in driver.window_handles
                    if _is_whatsapp_tab(driver, handle)
                ),
                False,
            )
        )
        return browser
    except TimeoutException as exc:
        if browser:
            browser.service.stop()
        raise AffiliateAutomationError(
            'Não encontrei uma aba autenticada do WhatsApp Web no Chrome de depuração. '
            'Abra https://web.whatsapp.com/, conclua o login e reinicie o monitor.'
        ) from exc
    except WebDriverException as exc:
        if browser:
            browser.service.stop()
        logger.exception('Falha ao iniciar o Chrome exclusivo da automação.')
        raise AffiliateAutomationError(
            'Não foi possível conectar ao Chrome. Inicie o perfil dedicado com depuração '
            'em 127.0.0.1:9222 e mantenha-o aberto.'
        ) from exc


def _is_whatsapp_tab(browser, handle):
    from selenium.common.exceptions import WebDriverException

    try:
        browser.switch_to.window(handle)
        return 'web.whatsapp.com' in browser.current_url
    except WebDriverException:
        return False


def disconnect_automation_browser(browser):
    if browser:
        browser.service.stop()


def open_whatsapp_group(browser, group_name, timeout=30):
    from selenium.common.exceptions import (
        ElementClickInterceptedException,
        NoSuchElementException,
        TimeoutException,
        WebDriverException,
    )
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait

    def click_group_result(element, search=None):
        try:
            target = element.find_element(
                By.XPATH,
                './ancestor::*[@data-testid="cell-frame-container"][1]',
            )
        except NoSuchElementException:
            target = element
        try:
            target.click()
        except ElementClickInterceptedException:
            browser.execute_script('arguments[0].click()', target)

        try:
            WebDriverWait(browser, timeout).until(
                lambda driver: current_group(driver) == group_name
            )
        except TimeoutException:
            browser.execute_script('arguments[0].click()', target)
            try:
                WebDriverWait(browser, timeout).until(
                    lambda driver: current_group(driver) == group_name
                )
            except TimeoutException:
                if search is None:
                    raise
                search.send_keys(Keys.ENTER)
                WebDriverWait(browser, timeout).until(
                    lambda driver: current_group(driver) == group_name
                )

    def current_group(driver):
        selectors = (
            '#main header [data-testid="conversation-info-header-chat-title"]',
            '#main header span[title]',
        )
        for selector in selectors:
            for element in driver.find_elements(By.CSS_SELECTOR, selector):
                title = (element.get_attribute('title') or element.text or '').strip()
                if title:
                    return title
        return ''

    if current_group(browser) == group_name:
        return

    for element in browser.find_elements(By.CSS_SELECTOR, '#pane-side [title]'):
        try:
            if (element.get_attribute('title') or '').strip() == group_name:
                click_group_result(element)
                return
        except WebDriverException:
            continue

    search_selectors = (
        '#side div[contenteditable="true"]',
        '#side [role="searchbox"]',
        '[aria-label="Pesquisar ou começar uma nova conversa"]',
        '[aria-label="Search or start new chat"]',
        '[aria-label="Pesquisar"]',
        '[aria-label="Search"]',
    )
    search = None
    for selector in search_selectors:
        for element in browser.find_elements(By.CSS_SELECTOR, selector):
            if element.is_displayed() and element.is_enabled():
                search = element
                break
        if search:
            break
    if not search:
        raise AffiliateAutomationError(
            'Não encontrei a busca de conversas do WhatsApp Web. A interface pode ter mudado.'
        )

    search.click()
    search.send_keys(Keys.CONTROL, 'a')
    search.send_keys(Keys.BACKSPACE)
    search.send_keys(group_name)

    def exact_result(driver):
        for selector in ('#pane-side [title]', '#side [title]', '[role="listitem"] [title]'):
            for element in driver.find_elements(By.CSS_SELECTOR, selector):
                try:
                    if (
                        (element.get_attribute('title') or '').strip() == group_name
                        and element.is_displayed()
                    ):
                        return element
                except WebDriverException:
                    continue
        return False

    try:
        result = WebDriverWait(browser, timeout).until(exact_result)
        click_group_result(result, search)
    except WebDriverException as exc:
        selected_group = current_group(browser) or 'nenhum grupo identificado'
        raise AffiliateAutomationError(
            f'Não consegui abrir e confirmar o grupo de origem “{group_name}”. '
            f'Grupo atual no WhatsApp: “{selected_group}”.'
        ) from exc


def _current_group_name(browser):
    from selenium.webdriver.common.by import By

    selectors = (
        '#main header [data-testid="conversation-info-header-chat-title"]',
        '#main header span[title]',
    )
    for selector in selectors:
        for element in browser.find_elements(By.CSS_SELECTOR, selector):
            title = (element.get_attribute('title') or element.text or '').strip()
            if title:
                return title
    return ''


def read_group_offers(browser, group_name):
    from selenium.common.exceptions import StaleElementReferenceException
    from selenium.webdriver.common.by import By

    if not group_name:
        raise AffiliateAutomationError('Configure AFFILIATE_BOT_SOURCE_GROUP no .env.')
    open_whatsapp_group(browser, group_name)

    offers = {}
    messages = browser.find_elements(By.CSS_SELECTOR, '#main div[data-testid="msg-container"]')
    for message in messages:
        try:
            text = message.text or ''
            links = extract_short_links(text)
            for anchor in message.find_elements(By.CSS_SELECTOR, 'a[href]'):
                links.update(extract_short_links(anchor.get_attribute('href') or ''))
            for link in links:
                offers.setdefault(link, extract_coupon(text))
        except StaleElementReferenceException:
            continue
    return offers


def record_startup_baseline(links, source_group):
    IncomingAffiliateOffer.objects.bulk_create(
        [
            IncomingAffiliateOffer(
                source_link=link,
                source_group=source_group,
                status=IncomingOfferStatus.IGNORED,
            )
            for link in links
        ],
        ignore_conflicts=True,
    )


def prune_old_offer_records(retention_days=180):
    cutoff = timezone.now() - timedelta(days=retention_days)
    terminal_statuses = (
        IncomingOfferStatus.IGNORED,
        IncomingOfferStatus.PUBLISHED,
        IncomingOfferStatus.SKIPPED,
        IncomingOfferStatus.FAILED,
        IncomingOfferStatus.UNCERTAIN,
    )
    deleted, _ = IncomingAffiliateOffer.objects.filter(
        status__in=terminal_statuses,
        received_at__lt=cutoff,
    ).delete()
    return deleted


def mark_stale_processing_as_uncertain(stale_after_minutes=10):
    now = timezone.now()
    cutoff = now - timedelta(minutes=stale_after_minutes)
    uncertain = IncomingAffiliateOffer.objects.filter(
        status=IncomingOfferStatus.PROCESSING,
        updated_at__lt=cutoff,
    ).update(
        status=IncomingOfferStatus.UNCERTAIN,
        error_message='O monitor encerrou durante o processamento; envio não repetido automaticamente.',
        processed_at=now,
        published_at=now,
        updated_at=now,
    )
    failed_preparations = IncomingAffiliateOffer.objects.filter(
        status=IncomingOfferStatus.PREPARING,
        updated_at__lt=cutoff,
    ).update(
        status=IncomingOfferStatus.FAILED,
        error_message='O monitor encerrou durante a preparação; nenhuma mensagem foi enviada.',
        processed_at=now,
        updated_at=now,
    )
    return uncertain + failed_preparations


def record_new_offers(offers, source_group):
    created = []
    for link, coupon in offers.items():
        try:
            record, was_created = IncomingAffiliateOffer.objects.get_or_create(
                source_link=link,
                defaults={
                    'source_group': source_group,
                    'coupon': coupon,
                    'status': IncomingOfferStatus.PENDING,
                },
            )
            if was_created:
                created.append(record)
        except Exception:
            logger.exception('Falha ao registrar link recebido %s.', link)
            raise
    return created


def _first_element(browser, selectors):
    from selenium.webdriver.common.by import By

    for selector in selectors:
        elements = browser.find_elements(By.CSS_SELECTOR, selector)
        if elements:
            return elements[0]
    return None


def _element_text(browser, selectors):
    element = _first_element(browser, selectors)
    return (element.text or '').strip() if element else ''


def _element_attribute(browser, selectors, attribute):
    element = _first_element(browser, selectors)
    return (element.get_attribute(attribute) or '').strip() if element else ''


def resolve_product_page(browser, short_url):
    from selenium.common.exceptions import TimeoutException
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait

    browser.get(short_url)
    try:
        WebDriverWait(browser, 30).until(
            lambda driver: (urlsplit(driver.current_url).hostname or '').lower()
            not in ('meli.la', 'www.meli.la')
        )
    except TimeoutException as exc:
        raise AffiliateAutomationError('O link meli.la não redirecionou para um anúncio.') from exc

    current_url = browser.current_url
    if '/social/avisodeoferta' in current_url:
        product_link = None
        for anchor in browser.find_elements(By.CSS_SELECTOR, 'a[href]'):
            if 'ir para produto' in (anchor.text or '').strip().casefold():
                product_link = anchor.get_attribute('href')
                break
        if not product_link:
            raise AffiliateAutomationError(
                'A página intermediária não forneceu um link direto para o produto.'
            )
        current_url = product_link

    parts = urlsplit(current_url)
    product_url = urlunsplit((parts.scheme, parts.netloc, parts.path, '', ''))
    item_id = extract_item_id(product_url)
    if not item_id or not is_marketplace_url(product_url):
        destination = f'{parts.hostname or "destino desconhecido"}{parts.path}'
        raise AffiliateAutomationError(
            'O link recebido não resolveu para um anúncio direto válido do Mercado Livre '
            f'(destino: {destination}).'
        )
    if not ProductOffer.is_valid_listing_permalink(product_url, item_id):
        raise AffiliateAutomationError('O anúncio redirecionou para uma página de busca ou catálogo.')

    browser.get(product_url)
    title = _element_text(browser, ('h1.ui-pdp-title', 'h1'))
    if not title:
        title = _element_attribute(
            browser,
            ('meta[property="og:title"]',),
            'content',
        )
    title = re.sub(r'\s*\|\s*Mercado\s*Livre.*$', '', title, flags=re.IGNORECASE).strip()
    if not title or len(title) < 5:
        raise AffiliateAutomationError('Não foi possível confirmar o título na página do anúncio.')

    price_container = _first_element(
        browser,
        (
            '.ui-pdp-price__second-line',
            '.ui-pdp-price__main-container',
            '[data-testid="price-part"]',
        ),
    )

    def amount_from(container):
        if not container:
            return None
        fractions = container.find_elements(By.CSS_SELECTOR, '.andes-money-amount__fraction')
        cents = container.find_elements(By.CSS_SELECTOR, '.andes-money-amount__cents')
        if not fractions:
            return None
        value = fractions[0].text.strip()
        if cents and cents[0].text.strip():
            value = f'{value},{cents[0].text.strip()}'
        return parse_brl_price(value)

    price = amount_from(price_container)
    if price is None:
        price = parse_brl_price(
            _element_attribute(browser, ('meta[itemprop="price"]',), 'content')
        )
    if price is None:
        raise AffiliateAutomationError('Não foi possível confirmar um preço atual na página do anúncio.')
    original_price = amount_from(
        _first_element(
            browser,
            (
                '.ui-pdp-price__original-value',
                '.andes-money-amount--previous',
            ),
        )
    )
    if original_price is not None and original_price <= price:
        original_price = None

    thumbnail = _element_attribute(browser, ('meta[property="og:image"]',), 'content')
    if not thumbnail.startswith('https://'):
        thumbnail = ''

    return {
        'item_id': item_id,
        'title': title[:255],
        'price': price,
        'original_price': original_price,
        'product_url': product_url,
        'thumbnail': thumbnail,
    }


def _collect_short_links(browser):
    from selenium.common.exceptions import StaleElementReferenceException
    from selenium.webdriver.common.by import By

    links = set()
    for element in browser.find_elements(By.CSS_SELECTOR, 'input, textarea, a'):
        try:
            for value in (
                element.get_attribute('value') or '',
                element.get_attribute('href') or '',
                element.text or '',
            ):
                links.update(extract_short_links(value))
        except StaleElementReferenceException:
            continue
    return links


def generate_affiliate_link(browser, product_url):
    from selenium.common.exceptions import TimeoutException
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait

    browser.get(AFFILIATE_LINKBUILDER_URL)
    if not is_marketplace_url(browser.current_url):
        raise AffiliateAutomationError(
            'O gerador de afiliados redirecionou para fora do Mercado Livre; interrompi a operação.'
        )
    try:
        field = WebDriverWait(browser, 30).until(
            lambda driver: driver.find_element(By.ID, 'url-0')
        )
    except TimeoutException as exc:
        raise AffiliateAutomationError(
            'O gerador de afiliados não ficou disponível. Faça login/verificação manualmente '
            'na janela dedicada e reinicie o monitor.'
        ) from exc

    field.clear()
    field.send_keys(product_url)
    buttons = WebDriverWait(browser, 30).until(
        lambda driver: next(
            (
                button for button in driver.find_elements(
                    By.XPATH,
                    "//button[normalize-space()='Gerar']",
                )
                if button.is_displayed() and button.is_enabled()
            ),
            False,
        )
    )
    before = _collect_short_links(browser)
    buttons.click()

    def new_link(driver):
        new_links = _collect_short_links(driver) - before
        if len(new_links) > 1:
            raise AffiliateAutomationError(
                'O gerador retornou mais de um link novo; não escolhi um link arbitrariamente.'
            )
        return next(iter(new_links), False)

    try:
        link = WebDriverWait(browser, 30).until(new_link)
    except TimeoutException as exc:
        raise AffiliateAutomationError(
            'O gerador não retornou um novo link meli.la.'
        ) from exc
    if len(extract_short_links(link)) != 1:
        raise AffiliateAutomationError('O link gerado não passou na validação do domínio meli.la.')
    return link


def validate_affiliate_link(browser, affiliate_url, expected_item_id):
    if len(extract_short_links(affiliate_url)) != 1:
        raise AffiliateAutomationError(
            'O link de afiliado não é um link meli.la válido.'
        )
    affiliate_details = resolve_product_page(browser, affiliate_url)
    if affiliate_details['item_id'] != expected_item_id:
        raise AffiliateAutomationError(
            'O link de afiliado redirecionou para um anúncio diferente do produto original.'
        )
    return affiliate_details


def _message_composer(browser):
    from selenium.webdriver.common.by import By

    for element in browser.find_elements(
        By.CSS_SELECTOR,
        '#main footer div[contenteditable="true"]',
    ):
        if element.is_displayed() and element.is_enabled():
            return element
    return None


def _clear_message_composer(browser):
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait

    composer = _message_composer(browser)
    if not composer:
        raise AffiliateAutomationError('Campo de mensagem do grupo não encontrado.')
    composer.click()
    composer.send_keys(Keys.CONTROL, 'a')
    composer.send_keys(Keys.BACKSPACE)
    WebDriverWait(browser, 5).until(
        lambda driver: bool(_message_composer(driver))
        and not _message_composer(driver).text.strip()
    )


def _has_link_preview_image(browser):
    script = """
    const main = document.querySelector('#main');
    const footer = main && main.querySelector('footer');
    if (!footer) return false;
    const editor = footer.querySelector('div[contenteditable="true"]');
    return Array.from(footer.querySelectorAll('img')).some(img => {
      if (editor && editor.contains(img)) return false;
      const rect = img.getBoundingClientRect();
      const style = window.getComputedStyle(img);
      return rect.width >= 70 && rect.height >= 55 &&
        style.display !== 'none' && style.visibility !== 'hidden' &&
        img.complete && img.naturalWidth >= 70 && img.naturalHeight >= 55;
    });
    """
    return bool(browser.execute_script(script))


def _send_button(browser):
    from selenium.common.exceptions import WebDriverException
    from selenium.webdriver.common.by import By

    selectors = (
        '#main footer button[aria-label="Enviar"]',
        '#main footer button[aria-label="Send"]',
        '#main footer [data-testid="send"]',
        '#main footer [data-icon="send"]',
        '#main footer [data-icon="wds-ic-send-filled"]',
    )
    for selector in selectors:
        for element in browser.find_elements(By.CSS_SELECTOR, selector):
            if not element.is_displayed() or not element.is_enabled():
                continue
            if element.tag_name == 'button':
                return element
            try:
                return element.find_element(By.XPATH, './ancestor::button[1]')
            except WebDriverException:
                continue
    return False


def _publish_offer_to_group(browser, whatsapp_tab, target_group, message, affiliate_url):
    from selenium.common.exceptions import TimeoutException, WebDriverException
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait

    browser.switch_to.window(whatsapp_tab)
    open_whatsapp_group(browser, target_group)
    if _current_group_name(browser) != target_group:
        raise AffiliateAutomationError('Grupo de destino não confirmado; envio cancelado.')

    composer = WebDriverWait(browser, 20).until(_message_composer)
    if composer.text.strip():
        raise AffiliateAutomationError(
            'Há um rascunho existente no grupo de destino. Revise-o antes de continuar.'
        )

    preview_ready = False
    for attempt in range(1, 4):
        _clear_message_composer(browser)
        composer = _message_composer(browser)
        composer.click()
        composer.send_keys(affiliate_url, Keys.SPACE)
        try:
            WebDriverWait(browser, 20, poll_frequency=0.5).until(
                _has_link_preview_image
            )
            preview_ready = True
            break
        except TimeoutException:
            logger.warning(
                'Prévia com imagem não apareceu (tentativa %s/3).',
                attempt,
            )

    if not preview_ready:
        raise AffiliateAutomationError(
            'A prévia com imagem não apareceu após 3 tentativas; a oferta não foi enviada.'
        )

    _clear_message_composer(browser)
    composer = WebDriverWait(browser, 10).until(_message_composer)
    for index, line in enumerate(message.splitlines()):
        if line:
            composer.send_keys(line)
        if index < len(message.splitlines()) - 1:
            composer.send_keys(Keys.SHIFT, Keys.ENTER)

    if _current_group_name(browser) != target_group:
        raise AffiliateAutomationError('O grupo mudou antes do envio; publicação cancelada.')
    try:
        WebDriverWait(browser, 20, poll_frequency=0.5).until(
            _has_link_preview_image
        )
    except TimeoutException as exc:
        raise AffiliateAutomationError(
            'A prévia com imagem desapareceu ao preparar a mensagem; oferta não enviada.'
        ) from exc

    button = WebDriverWait(browser, 15).until(_send_button)
    try:
        button.click()
    except WebDriverException as exc:
        raise WhatsAppSendUncertainError(
            'O clique de envio teve resultado incerto; verifique o grupo antes de retomar.'
        ) from exc

    try:
        WebDriverWait(browser, 20).until(
            lambda driver: bool(_message_composer(driver))
            and not _message_composer(driver).text.strip()
        )
    except TimeoutException as exc:
        raise WhatsAppSendUncertainError(
            'O WhatsApp não confirmou que a mensagem saiu do campo; verifique o grupo antes de retomar.'
        ) from exc

    return True


def publish_offer_in_whatsapp(browser, whatsapp_tab, target_groups, message, affiliate_url):
    sent_groups = []
    for target_group in target_groups:
        try:
            _publish_offer_to_group(
                browser,
                whatsapp_tab,
                target_group,
                message,
                affiliate_url,
            )
        except Exception as exc:
            if sent_groups:
                raise WhatsAppSendUncertainError(
                    f'A oferta já foi enviada para {", ".join(sent_groups)}, mas houve '
                    f'falha no grupo “{target_group}”: {exc}'
                ) from exc
            raise
        sent_groups.append(target_group)
    if not sent_groups:
        raise AffiliateAutomationError('Nenhum grupo de destino está configurado.')
    return sent_groups


def build_incoming_offer_message(details, coupon, affiliate_url):
    price = f'{details["price"]:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    lines = [
        '🔥 SANTANA INDICA 🔥',
        '',
        f'🛍️ {details["title"]}',
    ]
    if details.get('original_price'):
        original = f'{details["original_price"]:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
        lines.extend(('', f'De R$ {original}'))
    lines.extend(('', f'🔥 Por R$ {price}'))
    if coupon:
        lines.extend(('', f'🎟️ Cupom: {coupon}'))
    lines.extend((
        '',
        f'👉 {affiliate_url}',
        '',
        'Confira preço, disponibilidade e condições no anúncio.',
        'Este é um link de afiliado; posso receber comissão por compras realizadas.',
    ))
    return '\n'.join(lines)


def _store_product_and_publication(inbox, details, affiliate_url):
    with transaction.atomic():
        product = ProductOffer.objects.filter(item_id=details['item_id']).first()
        if product and product.status in (ProductStatus.PUBLISHED, ProductStatus.REJECTED):
            return None, None, 'O anúncio já foi publicado ou foi rejeitado no catálogo.'
        if product and product.publications.filter(status=PublicationStatus.PUBLISHED).exists():
            return None, None, 'Já existe uma publicação enviada para este anúncio.'

        if product is None:
            product = ProductOffer(
                item_id=details['item_id'],
                category='other',
                title=details['title'],
                price=details['price'],
                original_price=details.get('original_price'),
                product_url=details['product_url'],
                thumbnail=details['thumbnail'],
                seller_reputation='unknown',
                condition='unknown',
            )
        else:
            product.title = details['title']
            product.price = details['price']
            product.original_price = details.get('original_price')
            product.product_url = details['product_url']
            product.thumbnail = details['thumbnail']

        product.affiliate_url = affiliate_url
        product.status = ProductStatus.APPROVED
        product.calculate_score()
        product.save()

        message = build_incoming_offer_message(details, inbox.coupon, affiliate_url)
        publication = inbox.publication
        if publication is None:
            publication = Publication.objects.create(
                product=product,
                title='SANTANA INDICA',
                message_text=message,
                status=PublicationStatus.APPROVED,
            )
        else:
            publication.product = product
            publication.title = 'SANTANA INDICA'
            publication.message_text = message
            publication.status = PublicationStatus.APPROVED
            publication.save(update_fields=['product', 'title', 'message_text', 'status', 'updated_at'])
        inbox.product = product
        inbox.publication = publication
        inbox.save(update_fields=['product', 'publication', 'updated_at'])
        return product, publication, ''


def process_offer(inbox, browser, whatsapp_tab, affiliate_tab, target_groups, publish=True):
    prior_status = IncomingAffiliateOffer.objects.filter(
        pk=inbox.pk,
    ).values_list('status', flat=True).first()
    if prior_status not in (
        IncomingOfferStatus.PENDING,
        IncomingOfferStatus.PREPARED,
    ):
        return 'Oferta não estava mais pendente.'

    claimed = IncomingAffiliateOffer.objects.filter(
        pk=inbox.pk,
        status=prior_status,
    ).update(
        status=(
            IncomingOfferStatus.PROCESSING
            if publish
            else IncomingOfferStatus.PREPARING
        ),
        error_message='',
        updated_at=timezone.now(),
    )
    if not claimed:
        return 'Oferta não estava mais pendente.'
    inbox.refresh_from_db()

    was_prepared = prior_status == IncomingOfferStatus.PREPARED
    send_attempted = False
    try:
        if was_prepared:
            if not (
                inbox.product_id
                and inbox.publication_id
                and inbox.product.affiliate_url
            ):
                raise AffiliateAutomationError(
                    'A oferta marcada como pronta não possui produto, publicação e link afiliado completos.'
                )
            product = inbox.product
            publication = inbox.publication
            affiliate_url = product.affiliate_url
            details = None
        else:
            browser.switch_to.window(affiliate_tab)
            details = resolve_product_page(browser, inbox.source_link)
            affiliate_url = generate_affiliate_link(browser, details['product_url'])
            validate_affiliate_link(browser, affiliate_url, details['item_id'])
            product, publication, skip_reason = _store_product_and_publication(
                inbox,
                details,
                affiliate_url,
            )
            if skip_reason:
                inbox.status = IncomingOfferStatus.SKIPPED
                inbox.error_message = skip_reason
                inbox.processed_at = timezone.now()
                inbox.save(update_fields=['status', 'error_message', 'processed_at', 'updated_at'])
                return skip_reason

        title = details['title'] if details else product.title
        if not publish:
            inbox.status = IncomingOfferStatus.PREPARED
            inbox.error_message = ''
            inbox.processed_at = timezone.now()
            inbox.save(update_fields=['status', 'error_message', 'processed_at', 'updated_at'])
            return f'Oferta preparada sem envio: {title}'

        try:
            publish_offer_in_whatsapp(
                browser,
                whatsapp_tab,
                target_groups,
                publication.message_text,
                affiliate_url,
            )
        except WhatsAppSendUncertainError:
            send_attempted = True
            raise
        send_attempted = True

        now = timezone.now()
        publication.mark_as_published()
        inbox.status = IncomingOfferStatus.PUBLISHED
        inbox.error_message = ''
        inbox.processed_at = now
        inbox.published_at = now
        inbox.save(update_fields=[
            'status', 'error_message', 'processed_at', 'published_at', 'updated_at',
        ])
        return f'Oferta publicada: {title}'
    except Exception as exc:
        logger.exception('Falha ao processar oferta recebida %s.', inbox.source_link)
        inbox.status = (
            IncomingOfferStatus.UNCERTAIN
            if send_attempted
            else (
                IncomingOfferStatus.PREPARED
                if was_prepared and publish
                else IncomingOfferStatus.FAILED
            )
        )
        inbox.error_message = str(exc)[:1000]
        inbox.processed_at = timezone.now()
        fields = ['status', 'error_message', 'processed_at', 'updated_at']
        if send_attempted:
            inbox.published_at = inbox.processed_at
            fields.append('published_at')
        inbox.save(update_fields=fields)
        return f'Oferta não publicada: {exc}'


def daily_publication_count():
    today = timezone.localdate()
    return IncomingAffiliateOffer.objects.filter(
        status__in=(IncomingOfferStatus.PUBLISHED, IncomingOfferStatus.UNCERTAIN),
        published_at__date=today,
    ).count()

def wait_for_publish_window():
    last_publication = IncomingAffiliateOffer.objects.filter(
        status__in=(IncomingOfferStatus.PUBLISHED, IncomingOfferStatus.UNCERTAIN),
        published_at__isnull=False,
    ).order_by('-published_at').first()
    minimum_interval = max(
        0,
        getattr(settings, 'AFFILIATE_BOT_MIN_INTERVAL_SECONDS', 120),
    )
    if not last_publication:
        return
    available_at = last_publication.published_at + timedelta(seconds=minimum_interval)
    remaining = (available_at - timezone.now()).total_seconds()
    if remaining > 0:
        logger.info('Limite de intervalo entre publicações; aguardando %.0f segundos.', remaining)
        time.sleep(remaining)


def acquire_process_lock():
    lock_dir = Path(tempfile.gettempdir()) / 'SantanaAfiliadosBot'
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_file = (lock_dir / 'whatsapp-offer-monitor.lock').open('a+b')
    lock_file.seek(0, os.SEEK_END)
    if lock_file.tell() == 0:
        lock_file.write(b'\0')
        lock_file.flush()
    lock_file.seek(0)
    try:
        if os.name == 'nt':
            import msvcrt

            msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (OSError, BlockingIOError) as exc:
        lock_file.close()
        raise AffiliateAutomationError(
            'Já existe um monitor de ofertas em execução neste computador.'
        ) from exc
    return lock_file


def release_process_lock(lock_file):
    if not lock_file:
        return
    try:
        lock_file.seek(0)
        if os.name == 'nt':
            import msvcrt

            msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
    finally:
        lock_file.close()
