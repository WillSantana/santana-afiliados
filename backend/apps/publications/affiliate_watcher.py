import logging
import os
import re
import tempfile
import time
import unicodedata
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
MELI_LINK_PATTERN = re.compile(
    r'https?://(?:[a-zA-Z0-9.-]+\.)?(?:meli\.la|mercadolivre\.com\.br|mercadolivre\.com)(?:/[^\s<>"]*)?',
    re.IGNORECASE,
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


def extract_mercadolivre_links(text):
    """
    Identifica links meli.la e links tradicionais do Mercado Livre,
    limpando pontuações adjacentes comuns no WhatsApp.
    """
    if not text:
        return set()
    raw_matches = MELI_LINK_PATTERN.findall(text)
    links = set()
    for candidate in raw_matches:
        cleaned = candidate.rstrip('.,;:!?)>]}"\'')
        try:
            parsed = urlsplit(cleaned)
        except Exception:
            continue
        hostname = (parsed.hostname or '').lower()
        if not (
            hostname in ('meli.la', 'www.meli.la', 'mercadolivre.com.br', 'mercadolivre.com')
            or hostname.endswith('.mercadolivre.com.br')
            or hostname.endswith('.mercadolivre.com')
        ):
            continue
        if hostname in ('meli.la', 'www.meli.la'):
            normalized = urlunsplit(('https', hostname, parsed.path.rstrip('/'), '', ''))
        else:
            normalized = urlunsplit(('https', hostname, parsed.path.rstrip('/'), parsed.query, ''))
        links.add(normalized)
    return links


def extract_short_links(text):
    return extract_mercadolivre_links(text)


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


def close_automation_tab(browser, tab_handle=None, fallback_tab=None, handles_before=None):
    """
    Fecha a aba auxiliar do Mercado Livre (e quaisquer abas extras abertas
    durante o fluxo) para liberar memória/cache do navegador, preservando
    sempre a aba do WhatsApp Web.
    """
    if not browser:
        return
    try:
        raw_handles = browser.window_handles
        handles = list(raw_handles) if isinstance(raw_handles, (list, tuple, set)) else []
    except Exception:
        return

    tabs_to_close = []
    if tab_handle and tab_handle != fallback_tab and tab_handle in handles:
        tabs_to_close.append(tab_handle)
    if handles_before is not None:
        for handle in handles:
            if (
                handle not in handles_before
                and handle != fallback_tab
                and handle not in tabs_to_close
            ):
                tabs_to_close.append(handle)

    for handle in tabs_to_close:
        try:
            current_handles = list(browser.window_handles)
            if len(current_handles) <= 1 or handle not in current_handles:
                continue
            browser.switch_to.window(handle)
            browser.close()
        except Exception:
            logger.debug('Não foi possível fechar aba auxiliar %s.', handle, exc_info=True)

    if fallback_tab:
        try:
            current_handles = list(browser.window_handles)
            if fallback_tab in current_handles:
                browser.switch_to.window(fallback_tab)
        except Exception:
            logger.debug('Não foi possível retornar para a aba principal %s.', fallback_tab, exc_info=True)


def _normalize_group_name(name):
    if not name:
        return ''
    cleaned = re.sub(r'[\u200e\u200f\u202a-\u202e]+', '', name)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip().lower()
    return cleaned


def _is_group_match(name1, name2):
    n1 = _normalize_group_name(name1)
    n2 = _normalize_group_name(name2)
    if not n1 or not n2:
        return False
    return n1 == n2 or n1 in n2 or n2 in n1


def _current_group_name(browser):
    try:
        title = browser.execute_script("""
            const el = document.querySelector('#main header [data-testid="conversation-info-header-chat-title"]') ||
                       document.querySelector('#main header h2') ||
                       document.querySelector('#main header [role="button"] span[title]');
            return el ? (el.innerText || el.getAttribute('title') || '').trim() : '';
        """)
        return title or ''
    except Exception:
        return ''


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
            browser.execute_script("""
                const el = arguments[0];
                el.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true, view: window }));
                el.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true, view: window }));
                el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
            """, element)
        except Exception:
            try:
                element.click()
            except Exception:
                browser.execute_script('arguments[0].click()', element)

        try:
            WebDriverWait(browser, 8).until(
                lambda driver: _is_group_match(_current_group_name(driver), group_name)
            )
        except TimeoutException:
            if search is not None:
                try:
                    search.send_keys(Keys.ENTER)
                    WebDriverWait(browser, 5).until(
                        lambda driver: _is_group_match(_current_group_name(driver), group_name)
                    )
                except Exception:
                    pass

    # Se já está no grupo desejado, não precisa reabrir
    if _is_group_match(_current_group_name(browser), group_name):
        return

    # 1. Tentar encontrar diretamente na lista visível sem precisar buscar
    for element in browser.find_elements(By.CSS_SELECTOR, '#pane-side span[title]'):
        try:
            title = element.get_attribute('title') or ''
            if _is_group_match(title, group_name):
                click_group_result(element)
                if _is_group_match(_current_group_name(browser), group_name):
                    return
        except WebDriverException:
            continue

    # 2. Se não estiver visível diretamente, usar a busca do WhatsApp
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

    # Limpar qualquer busca anterior antes de digitar
    try:
        browser.execute_script("""
            document.querySelectorAll('[data-animate-modal-popup],[data-testid="intro-md-beta-logo-dark"]').forEach(el => el.style.display='none');
            const closeBtn = document.querySelector('button[aria-label="End icon button"], #side button[aria-label="Cancelar pesquisa"], #side [data-icon="x-alt"]');
            if (closeBtn) closeBtn.click();
            const inputs = document.querySelectorAll('#side input[role="textbox"], #side [role="searchbox"], #side div[contenteditable="true"]');
            inputs.forEach(i => {
                i.value = '';
                i.dispatchEvent(new Event('input', { bubbles: true }));
                i.dispatchEvent(new Event('change', { bubbles: true }));
            });
        """)
        time.sleep(0.2)
    except Exception:
        pass

    # Focar e digitar o nome do grupo na busca
    try:
        browser.execute_script("""
            arguments[0].focus();
            arguments[0].dispatchEvent(new MouseEvent('mousedown', {bubbles: true, cancelable: true, view: window}));
            arguments[0].dispatchEvent(new MouseEvent('mouseup', {bubbles: true, cancelable: true, view: window}));
            arguments[0].dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, view: window}));
        """, search)
    except Exception:
        try:
            search.click()
        except Exception:
            pass

    time.sleep(0.3)
    try:
        search.send_keys(Keys.CONTROL, 'a')
        search.send_keys(Keys.BACKSPACE)
        search.send_keys(group_name)
    except Exception:
        browser.execute_script("arguments[0].focus(); arguments[0].value = '';", search)
        from selenium.webdriver.common.action_chains import ActionChains
        ActionChains(browser).send_keys(group_name).perform()

    def exact_result(driver):
        for element in driver.find_elements(By.CSS_SELECTOR, '#pane-side span[title], #side span[title]'):
            try:
                title = element.get_attribute('title') or ''
                if _is_group_match(title, group_name) and element.is_displayed():
                    return element
            except WebDriverException:
                continue
        return False

    try:
        result = WebDriverWait(browser, timeout).until(exact_result)
        click_group_result(result, search)
        # Limpa a busca para restaurar a lista lateral do WhatsApp
        try:
            browser.execute_script("""
                const closeBtn = document.querySelector('button[aria-label="End icon button"], #side button[aria-label="Cancelar pesquisa"]');
                if (closeBtn) closeBtn.click();
            """)
        except Exception:
            pass
    except WebDriverException as exc:
        selected_group = _current_group_name(browser) or 'nenhum grupo identificado'
        raise AffiliateAutomationError(
            f'Não consegui abrir e confirmar o grupo de origem “{group_name}”. '
            f'Grupo atual no WhatsApp: “{selected_group}”.'
        ) from exc


def discover_all_whatsapp_groups(browser, scroll_rounds=6, pause=1.5):
    """
    Descobre todos os grupos/conversas visíveis na barra lateral do WhatsApp Web.
    Rola a lista várias vezes para carregar mais itens. Retorna lista de nomes únicos,
    filtrando apenas títulos reais de conversas (sem pegar mensagens anteriores ou status).
    """
    from selenium.common.exceptions import WebDriverException
    from selenium.webdriver.common.by import By

    seen = set()
    groups = []

    # Limpa busca prévia para garantir que o chat list completo esteja visível
    try:
        browser.execute_script("""
            const closeBtn = document.querySelector('button[aria-label="End icon button"], #side button[aria-label="Cancelar pesquisa"], #side [data-icon="x-alt"]');
            if (closeBtn) closeBtn.click();
            const inputs = document.querySelectorAll('#side input[role="textbox"], #side [role="searchbox"], #side div[contenteditable="true"]');
            inputs.forEach(i => {
                i.value = '';
                i.dispatchEvent(new Event('input', { bubbles: true }));
                i.dispatchEvent(new Event('change', { bubbles: true }));
            });
        """)
        time.sleep(0.5)
    except Exception:
        pass

    pane = None
    for sel in ('#pane-side', '[data-testid="chat-list"]', '#side'):
        elements = browser.find_elements(By.CSS_SELECTOR, sel)
        if elements:
            pane = elements[0]
            break

    def collect():
        try:
            titles = browser.execute_script("""
                const paneSide = document.querySelector('#pane-side');
                if (!paneSide) return [];
                const rows = paneSide.querySelectorAll('div[role="row"], div[data-testid="cell-frame-container"], div[tabindex="-1"]');
                const chats = [];
                rows.forEach(row => {
                    const titleSpan = row.querySelector('[data-testid="cell-frame-title"] span[title], span[title][dir="auto"]');
                    if (titleSpan) {
                        const title = (titleSpan.getAttribute('title') || titleSpan.innerText || '').trim();
                        if (
                            title &&
                            !title.startsWith('~') &&
                            !title.startsWith('‪') &&
                            !title.includes('\\n') &&
                            !title.includes('http') &&
                            title.length >= 2 &&
                            title.length <= 60 &&
                            !chats.includes(title)
                        ) {
                            chats.push(title);
                        }
                    }
                });
                return chats;
            """)
            for title in (titles or []):
                title = title.strip()
                if title and title not in seen:
                    seen.add(title)
                    groups.append(title)
        except Exception:
            pass

    collect()
    for _ in range(scroll_rounds):
        if pane:
            try:
                browser.execute_script('arguments[0].scrollTop += 800', pane)
            except WebDriverException:
                pass
        else:
            browser.execute_script('window.scrollBy(0,800)')
        time.sleep(pause)
        collect()

    # Volta ao topo
    if pane:
        try:
            browser.execute_script('arguments[0].scrollTop = 0', pane)
        except WebDriverException:
            pass
    return groups


def read_group_offers(browser, group_name):
    from selenium.common.exceptions import StaleElementReferenceException
    from selenium.webdriver.common.by import By

    if not group_name:
        raise AffiliateAutomationError('Configure o grupo de origem no painel ou no .env.')
    open_whatsapp_group(browser, group_name)

    offers = {}
    messages = browser.find_elements(By.CSS_SELECTOR, '#main div[data-testid="msg-container"]')
    for message in messages:
        try:
            text = (message.text or '').strip()
            links = extract_mercadolivre_links(text)
            for anchor in message.find_elements(By.CSS_SELECTOR, 'a[href]'):
                href = anchor.get_attribute('href') or ''
                links.update(extract_mercadolivre_links(href))
            if not links:
                continue
            coupon = extract_coupon(text)
            for link in links:
                offers.setdefault(link, {'coupon': coupon, 'message_text': text})
        except StaleElementReferenceException:
            continue
    return offers


def record_startup_baseline(offers_data, source_group):
    links = offers_data.keys() if isinstance(offers_data, dict) else offers_data
    records = []
    for link in links:
        coupon = ''
        msg = ''
        if isinstance(offers_data, dict) and isinstance(offers_data.get(link), dict):
            coupon = offers_data[link].get('coupon', '')
            msg = offers_data[link].get('message_text', '')
        records.append(
            IncomingAffiliateOffer(
                source_link=link,
                source_group=source_group,
                original_message=msg,
                coupon=coupon,
                status=IncomingOfferStatus.IGNORED,
            )
        )
    IncomingAffiliateOffer.objects.bulk_create(
        records,
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
    from .models import PublicationDelivery, PublicationDeliveryStatus

    created = []
    for link, offer_info in offers.items():
        # When a source is also a destination, don't treat the bot's own
        # successfully published affiliate link as a new incoming offer.
        if PublicationDelivery.objects.filter(
            affiliate_url=link,
            status=PublicationDeliveryStatus.SUCCESS,
        ).exists():
            continue
        coupon = offer_info.get('coupon', '') if isinstance(offer_info, dict) else (offer_info or '')
        message_text = offer_info.get('message_text', '') if isinstance(offer_info, dict) else ''
        try:
            record, was_created = IncomingAffiliateOffer.objects.get_or_create(
                source_link=link,
                defaults={
                    'source_group': source_group,
                    'original_message': message_text,
                    'coupon': coupon,
                    'status': IncomingOfferStatus.PENDING,
                },
            )
            if was_created:
                created.append(record)
            else:
                updated_fields = []
                if not record.original_message and message_text:
                    record.original_message = message_text
                    updated_fields.append('original_message')
                if record.status == IncomingOfferStatus.IGNORED:
                    record.status = IncomingOfferStatus.PENDING
                    record.error_message = ''
                    updated_fields.extend(['status', 'error_message', 'updated_at'])
                    created.append(record)
                if updated_fields:
                    record.save(update_fields=list(set(updated_fields)))
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


def _product_title_matches_message(title, message):
    def tokens(value):
        normalized = unicodedata.normalize('NFKD', (value or '').casefold())
        normalized = ''.join(char for char in normalized if not unicodedata.combining(char))
        return {token for token in re.findall(r'[a-z0-9]+', normalized) if len(token) >= 2}

    title_tokens = tokens(title)
    message_tokens = tokens(message)
    if len(title_tokens) < 4 or not message_tokens:
        return False
    return len(title_tokens & message_tokens) / len(title_tokens) >= 0.55


def resolve_product_page(browser, url, expected_text=''):
    from selenium.common.exceptions import TimeoutException
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait

    browser.get(url)
    initial_host = (urlsplit(browser.current_url).hostname or '').lower()
    if 'meli.la' in initial_host:
        try:
            WebDriverWait(browser, 30).until(
                lambda driver: (urlsplit(driver.current_url).hostname or '').lower()
                not in ('meli.la', 'www.meli.la')
            )
        except TimeoutException as exc:
            raise AffiliateAutomationError('O link meli.la não redirecionou para um anúncio.') from exc

    current_url = browser.current_url
    is_social_page = '/social/' in urlsplit(current_url).path.lower()
    if is_social_page:
        # Perfis sociais exibem recomenda??es al?m da oferta recebida. Use o
        # CTA da oferta principal, nunca qualquer link MLB encontrado na p?gina.
        def primary_offer_links(driver):
            # Read rendered text in-page: Selenium's .text is intermittently
            # empty on Mercado Livre's hydrated React anchors even when the
            # CTA is visibly present.
            anchors = driver.execute_script("""
                return Array.from(document.querySelectorAll('main a[href]')).map(a => ({
                    href: a.href,
                    label: (a.innerText || a.getAttribute('aria-label') || '').trim()
                }));
            """) or []
            links = []
            for anchor in anchors:
                label = ' '.join((anchor.get('label') or '').split()).casefold()
                if 'ir para produto' not in label:
                    continue
                href = (anchor.get('href') or '').strip()
                item_id = extract_item_id(href)
                if not item_id or not is_marketplace_url(href):
                    continue
                parts = urlsplit(href)
                product_url = urlunsplit((parts.scheme, parts.netloc, parts.path, '', ''))
                if ProductOffer.is_valid_listing_permalink(product_url, item_id):
                    links.append(href)
            return list(dict.fromkeys(links))

        try:
            links = WebDriverWait(browser, 30, poll_frequency=0.5).until(
                lambda driver: primary_offer_links(driver) or False
            )
        except TimeoutException:
            links = []
        if not links:
            raise AffiliateAutomationError(
                'A p?gina social n?o mostrou o bot?o ?Ir para produto? da oferta principal.'
            )
        if not expected_text.strip():
            raise AffiliateAutomationError(
                'A oferta veio de uma p?gina social sem mensagem para confirmar o produto.'
            )

        matched = False
        for product_link in links:
            browser.get(product_link)
            try:
                WebDriverWait(browser, 15).until(
                    lambda driver: _element_text(
                        driver, ('h1.ui-pdp-title', 'h1.andes-typography', 'h1')
                    ) or _element_attribute(driver, ('meta[property="og:title"]',), 'content')
                )
            except TimeoutException:
                continue
            candidate_title = _element_text(
                browser, ('h1.ui-pdp-title', 'h1.andes-typography', 'h1')
            ) or _element_attribute(browser, ('meta[property="og:title"]',), 'content')
            candidate_title = re.sub(
                r'\s*\|\s*Mercado\s*Livre.*$', '', candidate_title, flags=re.IGNORECASE
            ).strip()
            if _product_title_matches_message(candidate_title, expected_text):
                current_url = browser.current_url
                matched = True
                break
        if not matched:
            raise AffiliateAutomationError(
                'A oferta principal da p?gina social n?o corresponde ao produto descrito na mensagem do WhatsApp.'
            )

    parts = urlsplit(current_url)
    product_url = urlunsplit((parts.scheme, parts.netloc, parts.path, '', ''))
    item_id = extract_item_id(current_url) or extract_item_id(product_url)
    if not item_id or not is_marketplace_url(product_url):
        destination = f'{parts.hostname or "destino desconhecido"}{parts.path}'
        raise AffiliateAutomationError(
            'O link recebido não resolveu para um anúncio direto válido do Mercado Livre '
            f'(destino: {destination}).'
        )
    if not ProductOffer.is_valid_listing_permalink(product_url, item_id):
        raise AffiliateAutomationError('O anúncio redirecionou para uma página de busca ou inválida.')

    if browser.current_url != product_url and not current_url.startswith(product_url):
        browser.get(product_url)

    title = _element_text(browser, ('h1.ui-pdp-title', 'h1.andes-typography', 'h1'))
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
            '.andes-money-amount--cents-superscript',
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
            _element_attribute(browser, ('meta[itemprop="price"]', 'meta[property="product:price:amount"]'), 'content')
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


def _extract_meli_short_links(text):
    if not text:
        return set()
    return {
        match.group(0).rstrip('.,;:!?)>]}"\'')
        for match in MELI_SHORT_LINK_RE.finditer(text)
    }


def _collect_short_links(browser):
    try:
        candidates = browser.execute_script(
            """
            const values = [];
            document.querySelectorAll('input, textarea, a').forEach(el => {
                if (el.value) values.push(String(el.value));
                const href = el.getAttribute && el.getAttribute('href');
                if (href) values.push(String(href));
                if (el.textContent) values.push(String(el.textContent));
            });
            return values;
            """
        )
    except Exception:
        return set()
    links = set()
    for value in candidates or ():
        links.update(_extract_meli_short_links(value))
    return links


def _set_react_text_value(browser, field, value):
    """Atualiza um campo React disparando os eventos nativos esperados."""
    browser.execute_script(
        """
        const element = arguments[0];
        const value = arguments[1];
        const prototype = element.tagName === 'TEXTAREA'
            ? HTMLTextAreaElement.prototype
            : HTMLInputElement.prototype;
        const setter = Object.getOwnPropertyDescriptor(prototype, 'value').set;
        if (element.value === value && element._valueTracker) {
            element._valueTracker.setValue('');
        }
        setter.call(element, value);
        element.dispatchEvent(new Event('input', { bubbles: true }));
        element.dispatchEvent(new Event('change', { bubbles: true }));
        element.dispatchEvent(new Event('blur', { bubbles: true }));
        """,
        field,
        value,
    )


def generate_affiliate_link(browser, product_url):
    from selenium.common.exceptions import TimeoutException, WebDriverException
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait

    browser.get(AFFILIATE_LINKBUILDER_URL)
    if not is_marketplace_url(browser.current_url):
        raise AffiliateAutomationError(
            'O gerador de afiliados redirecionou para fora do Mercado Livre; faça login no Mercado Livre no perfil dedicado.'
        )

    def find_url_field(driver):
        selectors = (
            (By.ID, 'url-0'),
            (By.CSS_SELECTOR, 'input[name="url"]'),
            (By.CSS_SELECTOR, 'input[type="url"]'),
            (By.CSS_SELECTOR, 'input[placeholder*="Link"]'),
            (By.CSS_SELECTOR, 'input[placeholder*="link"]'),
            (By.CSS_SELECTOR, 'textarea'),
        )
        for by, sel in selectors:
            for el in driver.find_elements(by, sel):
                if el.is_displayed() and el.is_enabled():
                    return el
        return False

    try:
        field = WebDriverWait(browser, 25).until(find_url_field)
    except TimeoutException as exc:
        raise AffiliateAutomationError(
            'O gerador de afiliados do Mercado Livre não carregou o campo de URL. '
            'Certifique-se de que sua conta de afiliado está logada no Chrome dedicado.'
        ) from exc

    # Aguarda a hidratação do React e o carregamento inicial da etiqueta/estado
    # do Link Builder antes de preencher, caso contrário o SSR aceita o texto
    # no DOM mas o clique em "Gerar" é ignorado.
    def linkbuilder_ready(driver):
        try:
            current_field = find_url_field(driver)
            if not current_field:
                return False
            return bool(
                driver.execute_script(
                    """
                    const el = arguments[0];
                    if (document.readyState !== 'complete') return false;
                    const hasReact = Object.keys(el).some(
                        k => k.startsWith('__reactProps') || k.startsWith('__reactFiber') || k.startsWith('__reactEventHandlers')
                    );
                    const bodyText = (document.body && document.body.innerText) || '';
                    return hasReact && bodyText.includes('Etiqueta em uso');
                    """,
                    current_field,
                )
            )
        except WebDriverException:
            return False

    try:
        WebDriverWait(browser, 15).until(linkbuilder_ready)
    except TimeoutException:
        pass
    time.sleep(2)
    field = find_url_field(browser) or field

    # O Link Builder atual usa um textarea controlado pelo React. O setter nativo
    # com eventos de input/change mantém o valor no estado da aplicação e habilita
    # o botão "Gerar" de forma consistente.
    _set_react_text_value(browser, field, product_url)
    if field.get_attribute('value') != product_url:
        try:
            field.click()
        except WebDriverException:
            pass
        field.send_keys(Keys.CONTROL, 'a')
        field.send_keys(Keys.BACKSPACE)
        field.clear()
        field.send_keys(product_url)
        if field.get_attribute('value') != product_url:
            _set_react_text_value(browser, field, product_url)
    time.sleep(1.5)

    def find_generate_button(driver):
        btn_candidates = driver.find_elements(
            By.XPATH,
            "//button[normalize-space()='Gerar' or contains(normalize-space(),'Gerar')]",
        )
        for btn in btn_candidates:
            try:
                if (
                    btn.is_displayed()
                    and btn.is_enabled()
                    and not btn.get_attribute('disabled')
                    and btn.get_attribute('aria-disabled') != 'true'
                ):
                    return btn
            except WebDriverException:
                continue
        # Se o React ainda não habilitou o botão após preencher, reenvia os eventos.
        try:
            current_field = find_url_field(driver)
            if current_field:
                _set_react_text_value(driver, current_field, product_url)
        except WebDriverException:
            pass
        return False

    try:
        button = WebDriverWait(browser, 15).until(find_generate_button)
    except TimeoutException as exc:
        raise AffiliateAutomationError(
            'Botão “Gerar” não encontrado no gerador de afiliados do Mercado Livre.'
        ) from exc

    before = _collect_short_links(browser)

    def click_generate(btn):
        # Em janelas de depuração em segundo plano ou com o botão parcialmente
        # próximo à borda do viewport, btn.click() nativo do Selenium pode ser
        # engolido sem lançar exceção. O click via JS dispara o handler React
        # de forma confiável.
        browser.execute_script("arguments[0].click();", btn)

    click_generate(button)

    def new_link(driver):
        new_links = _collect_short_links(driver) - before
        if new_links:
            return next(iter(new_links), False)
        for el in driver.find_elements(
            By.CSS_SELECTOR,
            "textarea[id*='copyLink'], input[id*='copyLink'], input[readonly], input[value*='meli.la'], textarea[value*='meli.la'], a[href*='meli.la']",
        ):
            val = el.get_attribute('value') or el.get_attribute('href') or el.text or ''
            found = _extract_meli_short_links(val)
            diff = found - before
            if diff:
                return next(iter(diff), False)
        return False

    try:
        link = WebDriverWait(browser, 12).until(new_link)
    except TimeoutException:
        # Segunda tentativa caso o primeiro clique tenha ocorrido durante re-render do React.
        retry_field = find_url_field(browser)
        if retry_field:
            _set_react_text_value(browser, retry_field, product_url)
            time.sleep(1)
        retry_button = find_generate_button(browser)
        if retry_button:
            click_generate(retry_button)
        try:
            link = WebDriverWait(browser, 20).until(new_link)
        except TimeoutException as exc:
            raise AffiliateAutomationError(
                'O gerador de afiliados do Mercado Livre não retornou um novo link de afiliado.'
            ) from exc

    short_candidates = _extract_meli_short_links(link)
    if not short_candidates:
        raise AffiliateAutomationError('O link gerado pelo Mercado Livre não é válido.')
    return next(iter(short_candidates))


def validate_affiliate_link(browser, affiliate_url, expected_item_id, expected_text=''):
    if not affiliate_url or ('meli.la' not in affiliate_url and 'mercadolivre' not in affiliate_url):
        raise AffiliateAutomationError(
            'O link de afiliado não possui domínio válido do Mercado Livre ou meli.la.'
        )
    affiliate_details = resolve_product_page(browser, affiliate_url, expected_text)
    if affiliate_details['item_id'] != expected_item_id:
        raise AffiliateAutomationError(
            f'O link de afiliado redirecionou para um anúncio diferente ({affiliate_details["item_id"]}) do produto original ({expected_item_id}).'
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
        raise AffiliateAutomationError(f'Grupo de destino “{target_group}” não pôde ser confirmado no WhatsApp.')

    composer = WebDriverWait(browser, 20).until(_message_composer)
    _clear_message_composer(browser)
    composer = _message_composer(browser)

    # Digita o link primeiro com espaço para o WhatsApp tentar carregar prévia
    try:
        composer.click()
        composer.send_keys(affiliate_url, Keys.SPACE)
        # Aguarda brevemente a prévia visual sem travar se não carregar
        try:
            WebDriverWait(browser, 4, poll_frequency=0.5).until(_has_link_preview_image)
        except TimeoutException:
            pass
        _clear_message_composer(browser)
        composer = _message_composer(browser)
    except Exception as exc:
        logger.warning('Tentativa de prévia inicial ignorada: %s', exc)

    # Digita a mensagem completa formatada
    for index, line in enumerate(message.splitlines()):
        if line:
            composer.send_keys(line)
        if index < len(message.splitlines()) - 1:
            composer.send_keys(Keys.SHIFT, Keys.ENTER)

    # Aguarda 2 segundos para o WhatsApp renderizar o preview da mensagem antes de enviar
    time.sleep(2)

    if _current_group_name(browser) != target_group:
        raise AffiliateAutomationError(f'O grupo ativo mudou antes do envio; publicação cancelada.')

    button = WebDriverWait(browser, 15).until(_send_button)
    try:
        button.click()
    except WebDriverException:
        browser.execute_script("arguments[0].click();", button)

    try:
        WebDriverWait(browser, 15).until(
            lambda driver: bool(_message_composer(driver))
            and not _message_composer(driver).text.strip()
        )
    except TimeoutException as exc:
        raise WhatsAppSendUncertainError(
            'O WhatsApp não confirmou que a mensagem saiu do campo; verifique o grupo.'
        ) from exc

    return True


def publish_offer_in_whatsapp(browser, whatsapp_tab, target_groups, message, affiliate_url, inbox=None, publication=None):
    """
    Publica a oferta nos grupos de destino autorizados, aplicando controle de duplicidade
    por grupo e registrando individualmente cada envio no modelo PublicationDelivery.
    """
    from .models import PublicationDelivery, PublicationDeliveryStatus

    if not target_groups:
        raise AffiliateAutomationError('Nenhum grupo de destino configurado para publicação.')

    deliveries_result = []

    for item in target_groups:
        group_name = item['name'] if isinstance(item, dict) else item
        group_jid = item.get('jid') if isinstance(item, dict) else None

        # Controle de duplicidade: verificar se este produto já foi enviado com sucesso a este grupo
        if publication and PublicationDelivery.objects.filter(
            publication=publication,
            target_group_name=group_name,
            status=PublicationDeliveryStatus.SUCCESS,
        ).exists():
            logger.info('Oferta já enviada anteriormente para “%s”; pulando para evitar duplicidade.', group_name)
            continue

        try:
            _publish_offer_to_group(
                browser,
                whatsapp_tab,
                group_name,
                message,
                affiliate_url,
            )
            if publication:
                PublicationDelivery.objects.create(
                    publication=publication,
                    incoming_offer=inbox,
                    target_group_name=group_name,
                    target_group_jid=group_jid,
                    affiliate_url=affiliate_url,
                    status=PublicationDeliveryStatus.SUCCESS,
                    error_message='',
                    sent_at=timezone.now(),
                )
            deliveries_result.append({'group': group_name, 'success': True})
            time.sleep(2)
        except Exception as exc:
            logger.exception('Falha ao enviar oferta para o grupo “%s”.', group_name)
            if publication:
                PublicationDelivery.objects.create(
                    publication=publication,
                    incoming_offer=inbox,
                    target_group_name=group_name,
                    target_group_jid=group_jid,
                    affiliate_url=affiliate_url,
                    status=PublicationDeliveryStatus.FAILED,
                    error_message=str(exc)[:500],
                    sent_at=timezone.now(),
                )
            deliveries_result.append({'group': group_name, 'success': False, 'error': str(exc)})

    if not deliveries_result:
        return 'Todos os grupos autorizados já haviam recebido esta oferta anteriormente.'

    success_count = sum(1 for d in deliveries_result if d['success'])
    if success_count == 0:
        errors = '; '.join(f"{d['group']}: {d.get('error')}" for d in deliveries_result if not d['success'])
        raise AffiliateAutomationError(f'Falha no envio em todos os grupos: {errors}')

    return f'Oferta enviada com sucesso para {success_count} grupo(s).'


def build_incoming_offer_message(details, coupon, affiliate_url):
    price = f'{details["price"]:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    lines = [
        '🔥 MELHOR OFERTA 🔥',
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
            if details.get('thumbnail'):
                product.thumbnail = details['thumbnail']

        product.affiliate_url = affiliate_url
        product.status = ProductStatus.APPROVED
        product.calculate_score()
        product.save()

        try:
            from apps.affiliates.models import AffiliateLink
            AffiliateLink.objects.update_or_create(
                product=product,
                defaults={
                    'affiliate_url': affiliate_url,
                    'is_active': True,
                    'last_verified_at': timezone.now(),
                }
            )
        except Exception:
            logger.warning('Falha ao sincronizar registro de AffiliateLink.', exc_info=True)

        message = build_incoming_offer_message(details, inbox.coupon, affiliate_url)
        publication = inbox.publication or product.publications.first()
        if publication is None:
            publication = Publication.objects.create(
                product=product,
                title='Oferta Afiliada',
                message_text=message,
                status=PublicationStatus.APPROVED,
            )
        else:
            publication.product = product
            publication.title = 'Oferta Afiliada'
            publication.message_text = message
            publication.status = PublicationStatus.APPROVED
            publication.save(update_fields=['product', 'title', 'message_text', 'status', 'updated_at'])

        inbox.product = product
        inbox.publication = publication
        inbox.affiliate_url = affiliate_url
        inbox.save(update_fields=['product', 'publication', 'affiliate_url', 'updated_at'])
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
            raw_handles = getattr(browser, 'window_handles', None)
            handles_before = (
                set(raw_handles)
                if isinstance(raw_handles, (list, tuple, set))
                else set()
            )
            opened_temp_tab = False
            working_tab = affiliate_tab
            if not working_tab or (handles_before and working_tab not in handles_before):
                browser.switch_to.new_window('tab')
                working_tab = browser.current_window_handle
                opened_temp_tab = True
            try:
                browser.switch_to.window(working_tab)
                details = resolve_product_page(browser, inbox.source_link, inbox.original_message)
                affiliate_url = generate_affiliate_link(browser, details['product_url'])
                validate_affiliate_link(
                    browser,
                    affiliate_url,
                    details['item_id'],
                    inbox.original_message,
                )
            finally:
                close_automation_tab(
                    browser,
                    tab_handle=working_tab,
                    fallback_tab=whatsapp_tab,
                    handles_before=handles_before if opened_temp_tab else (handles_before - {working_tab}),
                )
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
            inbox.affiliate_url = affiliate_url
            inbox.error_message = ''
            inbox.processed_at = timezone.now()
            inbox.save(update_fields=['status', 'affiliate_url', 'error_message', 'processed_at', 'updated_at'])
            return f'Oferta preparada sem envio: {title}'

        try:
            publish_result = publish_offer_in_whatsapp(
                browser,
                whatsapp_tab,
                target_groups,
                publication.message_text,
                affiliate_url,
                inbox=inbox,
                publication=publication,
            )
        except WhatsAppSendUncertainError:
            send_attempted = True
            raise
        send_attempted = True

        now = timezone.now()
        publication.mark_as_published()
        inbox.status = IncomingOfferStatus.PUBLISHED
        inbox.affiliate_url = affiliate_url
        inbox.error_message = ''
        inbox.processed_at = now
        inbox.published_at = now
        inbox.save(update_fields=[
            'status', 'affiliate_url', 'error_message', 'processed_at', 'published_at', 'updated_at',
        ])
        return f'Oferta publicada: {title} ({publish_result})'
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
