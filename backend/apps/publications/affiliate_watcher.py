import logging
import os
import random
import re
import tempfile
import time
import unicodedata
from datetime import timedelta
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlencode, urlsplit, urlunsplit

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
from .product_urls import (
    STORE_AMAZON,
    STORE_MERCADOLIVRE,
    STORE_SHOPEE,
    STORE_TIKTOK,
    detect_store_from_url,
    extract_item_id,
    get_store_headline_suffix,
    is_amazon_url,
    is_marketplace_url,
    is_shopee_url,
    is_tiktok_url,
    parse_brl_price,
)

logger = logging.getLogger(__name__)

AFFILIATE_LINKBUILDER_URL = (
    'https://www.mercadolivre.com.br/afiliados/linkbuilder#hub'
)
MELI_LINK_PATTERN = re.compile(
    r'https?://(?:[a-zA-Z0-9.-]+\.)?(?:meli\.la|mercadolivre\.com\.br|mercadolivre\.com)(?:/[^\s<>"]*)?',
    re.IGNORECASE,
)
AMAZON_LINK_PATTERN = re.compile(
    r'https?://(?:[a-zA-Z0-9.-]+\.)?(?:amzn\.to|a\.co|amazon\.com\.br)(?:/[^\s<>"]*)?',
    re.IGNORECASE,
)
SHOPEE_LINK_PATTERN = re.compile(
    r'https?://(?:[a-zA-Z0-9.-]+\.)?(?:s\.shopee\.com\.br|shopee\.com\.br|shope\.ee|shp\.ee)(?:/[^\s<>"]*)?',
    re.IGNORECASE,
)
TIKTOK_LINK_PATTERN = re.compile(
    r'https?://(?:[a-zA-Z0-9.-]+\.)?(?:vt\.tiktok\.com|vm\.tiktok\.com|shop\.tiktok\.com|tiktok\.com)(?:/[^\s<>"]*)?',
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


class GroupAdminOnlySkip(Exception):
    """Grupo trancado para administradores: pular envio sem registrar falha."""


_ADMIN_ONLY_SKIP_UNTIL = {}


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


def get_enabled_stores():
    raw = getattr(settings, 'AFFILIATE_BOT_ENABLED_STORES', 'mercadolivre,amazon,shopee')
    stores = {
        part.strip().lower()
        for part in str(raw or '').split(',')
        if part.strip()
    }
    return stores or {STORE_MERCADOLIVRE}


def parse_store_daily_quotas(raw=None):
    """
    Interpreta cotas diárias por loja no formato 'mercadolivre=10,amazon=10,shopee=10'.
    """
    if raw is None:
        raw = getattr(settings, 'AFFILIATE_BOT_STORE_DAILY_QUOTAS', '')
    quotas = {}
    for chunk in str(raw or '').split(','):
        part = chunk.strip()
        if not part or '=' not in part:
            continue
        store_key, limit_str = part.split('=', 1)
        store_key = store_key.strip().lower()
        try:
            limit_val = int(limit_str.strip())
        except ValueError:
            continue
        if store_key and limit_val > 0:
            quotas[store_key] = limit_val
    return quotas


def extract_shopee_links(text):
    """
    Identifica links curtos (s.shopee.com.br, shope.ee, shp.ee) e links de produto da Shopee Brasil.
    """
    if not text:
        return set()
    raw_matches = SHOPEE_LINK_PATTERN.findall(text)
    links = set()
    for candidate in raw_matches:
        cleaned = candidate.rstrip('.,;:!?)>]}"\'')
        if not is_shopee_url(cleaned):
            continue
        try:
            parsed = urlsplit(cleaned)
        except Exception:
            continue
        hostname = (parsed.hostname or '').lower()
        path = (parsed.path or '').rstrip('/')
        if not path or path == '/':
            continue
        normalized = urlunsplit(('https', hostname, path, '', ''))
        links.add(normalized)
    return links


def extract_amazon_links(text):
    """
    Identifica links curtos (amzn.to, a.co) e links de produto da Amazon Brasil.
    """
    if not text:
        return set()
    raw_matches = AMAZON_LINK_PATTERN.findall(text)
    links = set()
    for candidate in raw_matches:
        cleaned = candidate.rstrip('.,;:!?)>]}"\'')
        if not is_amazon_url(cleaned):
            continue
        try:
            parsed = urlsplit(cleaned)
        except Exception:
            continue
        hostname = (parsed.hostname or '').lower()
        path = (parsed.path or '').rstrip('/')
        if not path or path == '/':
            continue
        if hostname in ('amzn.to', 'www.amzn.to', 'a.co', 'www.a.co'):
            normalized = urlunsplit(('https', hostname, path, '', ''))
        else:
            normalized = urlunsplit(('https', hostname, path, '', ''))
        links.add(normalized)
    return links


def extract_tiktok_links(text):
    """
    Identifica links do TikTok Shop (vt.tiktok.com, vm.tiktok.com, shop.tiktok.com, tiktok.com/shop/...).
    """
    if not text:
        return set()
    raw_matches = TIKTOK_LINK_PATTERN.findall(text)
    links = set()
    for candidate in raw_matches:
        cleaned = candidate.rstrip('.,;:!?)>]}"\'')
        if not is_tiktok_url(cleaned):
            continue
        try:
            parsed = urlsplit(cleaned)
        except Exception:
            continue
        hostname = (parsed.hostname or '').lower()
        path = (parsed.path or '').rstrip('/')
        if not path or path == '/':
            continue
        normalized = urlunsplit(('https', hostname, path, '', ''))
        links.add(normalized)
    return links


def extract_offer_links(text):
    enabled = get_enabled_stores()
    links = set()
    if STORE_MERCADOLIVRE in enabled:
        links.update(extract_mercadolivre_links(text))
    if STORE_AMAZON in enabled:
        links.update(extract_amazon_links(text))
    if STORE_SHOPEE in enabled:
        links.update(extract_shopee_links(text))
    if STORE_TIKTOK in enabled:
        links.update(extract_tiktok_links(text))
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

    # Também recolhe abas temporárias remanescentes de produtos/Link Builder
    # para impedir acúmulo no Chrome dedicado (sem tocar no WhatsApp Web nem no painel).
    temp_url_markers = (
        'mercadolivre.com.br/afiliados/linkbuilder',
        'produto.mercadolivre.com.br/',
        'mercadolivre.com.br/p/',
        'mercadolivre.com.br/social/',
        'meli.la/',
        'amazon.com.br/dp/',
        'amzn.to/',
    )
    for handle in handles:
        if handle == fallback_tab or handle in tabs_to_close:
            continue
        try:
            browser.switch_to.window(handle)
            url = (browser.current_url or '').lower()
            if any(marker in url for marker in temp_url_markers):
                tabs_to_close.append(handle)
        except Exception:
            continue

    for handle in tabs_to_close:
        try:
            current_handles = list(browser.window_handles)
            if len(current_handles) <= 1 or handle not in current_handles:
                continue
            browser.switch_to.window(handle)
            try:
                browser.execute_script('window.onbeforeunload = null;')
            except Exception:
                pass
            try:
                browser.close()
            except Exception:
                try:
                    browser.execute_script('window.close();')
                except Exception:
                    pass
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
    if not name or not isinstance(name, str):
        return ''
    cleaned = re.sub(r'[\u200e\u200f\u202a-\u202e\ufe0f]+', '', name)
    # Remove emojis/símbolos fora do BMP (no cabeçalho do WhatsApp Web eles são
    # renderizados como <img> e não aparecem no innerText).
    cleaned = ''.join(ch for ch in cleaned if ord(ch) <= 0xFFFF)
    # Remove acentos para tolerar pequenas variações (ex.: "promoçoes" vs "Promoções")
    cleaned = ''.join(
        ch for ch in unicodedata.normalize('NFKD', cleaned)
        if not unicodedata.combining(ch)
    )
    # Normaliza espaços em torno de símbolos (&, -, /, |) — ex.: "Vendas&rolos" == "Vendas & Rolos"
    cleaned = re.sub(r'\s*([&/\-|])\s*', r' \1 ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip().lower()
    return cleaned


DEFAULT_BLOCKED_SEND_GROUPS = frozenset({
    'geral',
    'sti geral',
})


def _blocked_send_group_names():
    blocked = set(DEFAULT_BLOCKED_SEND_GROUPS)
    extra = getattr(settings, 'AFFILIATE_BOT_BLOCKED_GROUPS', '') or ''
    for item in str(extra).split(','):
        normalized = _normalize_group_name(item)
        if normalized:
            blocked.add(normalized)
    return blocked


def is_blocked_send_group(group_name):
    normalized = _normalize_group_name(group_name)
    if not normalized:
        return False
    blocked = _blocked_send_group_names()
    if normalized in blocked:
        return True
    if 'sti geral' in normalized:
        return True
    return False


def _is_group_match(actual_name, expected_name):
    actual = _normalize_group_name(actual_name)
    expected = _normalize_group_name(expected_name)
    if not actual or not expected:
        return False
    if actual == expected:
        return True
    # Permite correspondência apenas quando o nome real no WhatsApp começa com o nome
    # configurado em fronteira de palavra (ex.: "COMPRAS & VENDAS PRESENCIAL & ONLINE"
    # para "COMPRAS & VENDAS PRESENCIAL"), nunca quando o chat aberto é um trecho curto
    # como "Geral" (comunidade STI) dentro de "Catira Geral Nova Contagem".
    if len(expected) >= 8 and actual.startswith(expected):
        next_char = actual[len(expected):len(expected) + 1]
        if not next_char or not next_char.isalnum():
            return True
    return False


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
                const target = el.closest('[role="row"], [role="listitem"], [role="gridcell"]') || el;
                target.scrollIntoView({ block: 'center' });
                for (const node of [el, target]) {
                    node.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true, view: window }));
                    node.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true, view: window }));
                    node.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
                }
            """, element)
        except Exception:
            try:
                element.click()
            except Exception:
                browser.execute_script('arguments[0].click()', element)

        try:
            WebDriverWait(browser, 6).until(
                lambda driver: _is_group_match(_current_group_name(driver), group_name)
            )
        except TimeoutException:
            if search is not None:
                try:
                    search.send_keys(Keys.ENTER)
                    WebDriverWait(browser, 4).until(
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

    # 2. Rolar a lista lateral (#pane-side) antes de usar a busca — é mais rápido
    # e não depende do filtro reativo da caixa de busca em segundo plano.
    pane = None
    for sel in ('#pane-side', '[data-testid="chat-list"]'):
        found = browser.find_elements(By.CSS_SELECTOR, sel)
        if found:
            pane = found[0]
            break

    if pane is not None:
        try:
            browser.execute_script('arguments[0].scrollTop = 0', pane)
            time.sleep(0.2)
        except WebDriverException:
            pass
        last_scroll = -1
        for _ in range(30):
            for element in browser.find_elements(By.CSS_SELECTOR, '#pane-side span[title]'):
                try:
                    title = element.get_attribute('title') or ''
                    if _is_group_match(title, group_name):
                        click_group_result(element)
                        if _is_group_match(_current_group_name(browser), group_name):
                            return
                except WebDriverException:
                    continue
            try:
                current_scroll = browser.execute_script(
                    'const p = arguments[0]; p.scrollTop += 600; return p.scrollTop;',
                    pane,
                )
            except WebDriverException:
                break
            if current_scroll == last_scroll:
                break
            last_scroll = current_scroll
            time.sleep(0.2)

    # 3. Fallback: usar a busca do WhatsApp caso o grupo esteja muito abaixo na lista
    search_selectors = (
        '#side input[role="textbox"]',
        '[aria-label="Pesquisar ou começar uma nova conversa"]',
        '[aria-label="Search or start new chat"]',
        '#side [role="searchbox"]',
        '#side div[contenteditable="true"]',
        '[aria-label="Pesquisar"]',
        '[aria-label="Search"]',
    )

    def find_search_input():
        for selector in search_selectors:
            for element in browser.find_elements(By.CSS_SELECTOR, selector):
                try:
                    if element.is_displayed() and element.is_enabled():
                        return element
                except WebDriverException:
                    continue
        return None

    def clear_search_box():
        try:
            current_search = find_search_input()
            if current_search:
                try:
                    current_search.send_keys(Keys.CONTROL, 'a')
                    current_search.send_keys(Keys.BACKSPACE)
                    current_search.send_keys(Keys.ESCAPE)
                except Exception:
                    pass
            browser.execute_script("""
                document.querySelectorAll('[data-animate-modal-popup],[data-testid="intro-md-beta-logo-dark"]').forEach(el => el.style.display='none');
                const selectors = [
                    'button[aria-label="End icon button"]',
                    '#side button[aria-label="Cancelar pesquisa"]',
                    '#side button[aria-label="Cancel search"]',
                    '#side button[aria-label="Voltar"]',
                    '#side button[aria-label="Back"]',
                    '#side [data-icon="x-alt"]',
                ];
                for (const sel of selectors) {
                    const btn = document.querySelector(sel);
                    if (btn) btn.click();
                }
            """)
            time.sleep(0.25)
        except Exception:
            pass

    def exact_result(driver):
        for element in driver.find_elements(By.CSS_SELECTOR, '#pane-side span[title], #side span[title]'):
            try:
                title = element.get_attribute('title') or ''
                if _is_group_match(title, group_name) and element.is_displayed():
                    return element
            except WebDriverException:
                continue
        return False

    # Remove caracteres fora do plano BMP apenas na digitação da busca do ChromeDriver
    full_query = ''.join(ch for ch in group_name if ord(ch) <= 0xFFFF).strip() or group_name
    full_query = re.sub(r'\s+', ' ', full_query)
    words = full_query.split()
    short_query = ' '.join(words[:2]) if len(words) >= 3 else ''
    queries = [full_query] + ([short_query] if short_query and short_query != full_query else [])

    for query in queries:
        clear_search_box()
        search = find_search_input()
        if not search:
            raise AffiliateAutomationError(
                'Não encontrei a busca de conversas do WhatsApp Web. A interface pode ter mudado.'
            )

        try:
            search.click()
        except Exception:
            try:
                browser.execute_script("arguments[0].focus(); arguments[0].click();", search)
            except Exception:
                pass

        time.sleep(0.2)
        try:
            search.send_keys(Keys.CONTROL, 'a')
            search.send_keys(Keys.BACKSPACE)
            search.send_keys(query)
        except Exception:
            browser.execute_script("arguments[0].focus();", search)
            from selenium.webdriver.common.action_chains import ActionChains
            ActionChains(browser).key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).send_keys(Keys.BACKSPACE).send_keys(query).perform()

        try:
            result = WebDriverWait(browser, min(timeout, 10)).until(exact_result)
            click_group_result(result, search)
            clear_search_box()
            if _is_group_match(_current_group_name(browser), group_name):
                return
        except WebDriverException:
            clear_search_box()

    selected_group = _current_group_name(browser) or 'nenhum grupo identificado'
    raise AffiliateAutomationError(
        f'Não consegui abrir e confirmar o grupo “{group_name}”. '
        f'Grupo atual no WhatsApp: “{selected_group}”.'
    )


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
            links = extract_offer_links(text)
            for anchor in message.find_elements(By.CSS_SELECTOR, 'a[href]'):
                href = anchor.get_attribute('href') or ''
                links.update(extract_offer_links(href))
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
                store=detect_store_from_url(link) or STORE_MERCADOLIVRE,
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
                    'store': detect_store_from_url(link) or STORE_MERCADOLIVRE,
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
    from selenium.common.exceptions import StaleElementReferenceException

    for _ in range(3):
        try:
            element = _first_element(browser, selectors)
            return (element.text or '').strip() if element else ''
        except StaleElementReferenceException:
            time.sleep(0.2)
    return ''


def _element_attribute(browser, selectors, attribute):
    from selenium.common.exceptions import StaleElementReferenceException

    for _ in range(3):
        try:
            element = _first_element(browser, selectors)
            return (element.get_attribute(attribute) or '').strip() if element else ''
        except StaleElementReferenceException:
            time.sleep(0.2)
    return ''


def _product_title_matches_message(title, message):
    stopwords = {
        'de', 'do', 'da', 'dos', 'das', 'para', 'com', 'sem', 'por', 'em',
        'no', 'na', 'nos', 'nas', 'ao', 'aos', 'um', 'uma', 'ou', 'que',
        'off', 'oferta', 'ofertas', 'promocao', 'cupom', 'frete', 'gratis',
        'mercado', 'livre', 'mercadolivre', 'https', 'http', 'meli', 'la',
        'reais', 'rs', 'link', 'clique', 'confira', 'produto', 'novo',
        'cor', 'preto', 'branco', 'azul', 'cinza', 'bivolt', 'un', 'und',
    }

    def tokens(value):
        normalized = unicodedata.normalize('NFKD', (value or '').casefold())
        normalized = ''.join(char for char in normalized if not unicodedata.combining(char))
        return {
            token
            for token in re.findall(r'[a-z0-9]+', normalized)
            if len(token) >= 2 and token not in stopwords
        }

    title_tokens = tokens(title)
    message_tokens = tokens(message)
    if not title_tokens or not message_tokens:
        return False
    overlap = title_tokens & message_tokens
    if len(overlap) >= 2:
        return True
    return len(overlap) / len(title_tokens) >= 0.35


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
        def _unwrap_marketplace_href(raw_href):
            candidate = (raw_href or '').strip()
            if not candidate:
                return ''
            if is_marketplace_url(candidate):
                return candidate
            try:
                qs = parse_qs(urlsplit(candidate).query)
                for key in ('url', 'fallback', 'redirect', 'u'):
                    for val in qs.get(key, ()):
                        decoded = unquote(val).strip()
                        if is_marketplace_url(decoded):
                            return decoded
            except Exception:
                pass
            return ''

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
            featured_links = []
            for anchor in anchors:
                label = ' '.join((anchor.get('label') or '').split()).casefold()
                raw_href = (anchor.get('href') or '').strip()
                href = _unwrap_marketplace_href(raw_href)
                if not href:
                    continue
                item_id = extract_item_id(href)
                if not item_id:
                    continue
                parts = urlsplit(href)
                product_url = urlunsplit((parts.scheme, parts.netloc, parts.path, '', ''))
                if not ProductOffer.is_valid_listing_permalink(product_url, item_id):
                    continue
                if 'ir para produto' in label or 'ir para o produto' in label:
                    links.append(product_url)
                elif 'card-featured' in raw_href:
                    featured_links.append(product_url)
            return list(dict.fromkeys(links or featured_links))

        try:
            links = WebDriverWait(browser, 30, poll_frequency=0.5).until(
                lambda driver: primary_offer_links(driver) or False
            )
        except TimeoutException:
            links = []
        if not links:
            raise AffiliateAutomationError(
                'A página social não mostrou o botão “Ir para produto” da oferta principal.'
            )
        if not expected_text.strip():
            raise AffiliateAutomationError(
                'A oferta veio de uma página social sem mensagem para confirmar o produto.'
            )

        matched = False
        last_candidate_title = ''
        for product_link in links:
            browser.get(product_link)
            try:
                WebDriverWait(browser, 15).until(
                    lambda driver: '/social/' not in urlsplit(driver.current_url).path.lower()
                    and (
                        _element_text(driver, ('h1.ui-pdp-title',))
                        or _element_attribute(driver, ('meta[property="og:title"]',), 'content')
                    )
                )
            except TimeoutException:
                continue
            candidate_title = _element_text(
                browser, ('h1.ui-pdp-title',)
            ) or _element_attribute(
                browser, ('meta[property="og:title"]',), 'content'
            ) or _element_text(
                browser, ('h1.andes-typography', 'h1')
            )
            candidate_title = re.sub(
                r'\s*\|\s*Mercado\s*Livre.*$', '', candidate_title, flags=re.IGNORECASE
            ).strip()
            last_candidate_title = candidate_title
            if _product_title_matches_message(candidate_title, expected_text):
                current_url = browser.current_url
                matched = True
                break
        if not matched:
            raise AffiliateAutomationError(
                'A oferta principal da página social não corresponde ao produto descrito na mensagem do WhatsApp'
                + (f' (título encontrado: “{last_candidate_title[:80]}”).' if last_candidate_title else '.')
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

    rating = None
    rating_text = _element_text(
        browser,
        (
            '.ui-pdp-review__rating',
            '[class*="ui-pdp-review__rating"]',
            '.ui-review-capability__rating__average',
        ),
    ) or _element_attribute(browser, ('meta[itemprop="ratingValue"]',), 'content')
    if rating_text:
        match_rating = re.search(r'(\d(?:[.,]\d)?)', rating_text)
        if match_rating:
            try:
                parsed_rating = float(match_rating.group(1).replace(',', '.'))
                if 0.0 < parsed_rating <= 5.0:
                    rating = parsed_rating
            except ValueError:
                rating = None

    availability_text = _element_text(
        browser,
        (
            '.ui-pdp-buybox__quantity__available',
            '.ui-pdp-stock-information',
            '.andes-message__text',
        ),
    ).lower()
    in_stock = not any(
        phrase in availability_text
        for phrase in (
            'anúncio pausado',
            'anuncio pausado',
            'produto esgotado',
            'sem estoque',
            'não disponível',
            'nao disponivel',
            'publicação finalizada',
        )
    )

    return {
        'item_id': item_id,
        'title': title[:255],
        'price': price,
        'original_price': original_price,
        'product_url': product_url,
        'thumbnail': thumbnail,
        'rating': rating,
        'in_stock': in_stock,
    }


def _title_token_set(title):
    cleaned = _normalize_group_name(title or '')
    return {tok for tok in re.findall(r'[a-z0-9]{3,}', cleaned)}


def is_recently_published_product(item_id, title='', cooldown_hours=None):
    """
    Deduplicação e Cooldown (padrão 24h): impede postar o mesmo produto (item_id)
    ou produto com título muito similar (>= 85% de sobreposição de palavras) em menos de 24h.
    """
    if cooldown_hours is None:
        cooldown_hours = max(1, int(getattr(settings, 'AFFILIATE_BOT_PRODUCT_COOLDOWN_HOURS', 24)))
    cutoff = timezone.now() - timedelta(hours=cooldown_hours)
    recent_qs = IncomingAffiliateOffer.objects.filter(
        status__in=(IncomingOfferStatus.PUBLISHED, IncomingOfferStatus.UNCERTAIN),
        published_at__gte=cutoff,
        product__isnull=False,
    ).select_related('product')

    if item_id and recent_qs.filter(product__item_id=item_id).exists():
        return True, f'Oferta ignorada: produto {item_id} já publicado nas últimas {cooldown_hours}h.'

    candidate_tokens = _title_token_set(title)
    if len(candidate_tokens) >= 3:
        for recent in recent_qs[:120]:
            other_tokens = _title_token_set(getattr(recent.product, 'title', ''))
            if len(other_tokens) < 3:
                continue
            overlap = len(candidate_tokens & other_tokens) / max(len(candidate_tokens), len(other_tokens))
            if overlap >= 0.85:
                return True, f'Oferta ignorada: produto muito similar já publicado nas últimas {cooldown_hours}h.'
    return False, ''


def evaluate_offer_quality(details, coupon=''):
    """
    Módulo de Curadoria Inteligente:
    - Disponibilidade em estoque (in_stock)
    - Preço mínimo (padrão R$ 20,00)
    - Nota mínima do produto quando disponível (padrão 4,0)
    - Desconto real mínimo (padrão 25% OFF) OU cupom ativo
    - Deduplicação e Cooldown 24h (item_id ou título similar)
    Retorna (approved: bool, reason: str).
    """
    min_discount_pct = float(getattr(settings, 'AFFILIATE_BOT_MIN_DISCOUNT_PCT', 25))
    min_price = float(getattr(settings, 'AFFILIATE_BOT_MIN_PRICE', 20.0))
    min_rating = float(getattr(settings, 'AFFILIATE_BOT_MIN_RATING', 4.0))

    if details.get('in_stock') is False:
        return False, 'Oferta ignorada: produto fora de estoque ou anúncio pausado.'

    price_val = float(details['price'])
    if price_val < min_price:
        return (
            False,
            f'Oferta ignorada: preço R$ {price_val:.2f} abaixo do mínimo configurado (R$ {min_price:.2f}).',
        )

    rating = details.get('rating')
    if rating is not None and float(rating) < min_rating:
        return (
            False,
            f'Oferta ignorada: avaliação {float(rating):.1f} abaixo do mínimo configurado ({min_rating:.1f}).',
        )

    original_val = details.get('original_price')
    discount_pct = 0.0
    if original_val and float(original_val) > price_val:
        discount_pct = ((float(original_val) - price_val) / float(original_val)) * 100.0

    has_coupon = bool((coupon or '').strip())
    if not has_coupon and discount_pct < min_discount_pct:
        if discount_pct <= 0:
            return (
                False,
                f'Oferta ignorada: sem desconto verificável na página e sem cupom (mínimo {min_discount_pct:.0f}% OFF).',
            )
        return (
            False,
            f'Oferta ignorada: desconto de {round(discount_pct)}% OFF abaixo do mínimo ({min_discount_pct:.0f}% OFF) e sem cupom.',
        )

    dup, dup_reason = is_recently_published_product(
        details.get('item_id'),
        details.get('title', ''),
    )
    if dup:
        return False, dup_reason

    return True, ''


def _offer_queue_priority(offer):
    score = 0
    if offer.product_id and getattr(offer.product, 'discount_percentage', 0):
        score += min(int(offer.product.discount_percentage), 90)
    if (offer.coupon or '').strip():
        score += 25
    text = (offer.original_message or '').lower()
    pct_matches = [int(m) for m in re.findall(r'(\d{1,2})\s*%\s*(?:off|de desconto|desconto)?', text)]
    if pct_matches:
        score += min(max(pct_matches), 80)
    if any(kw in text for kw in ('menor preço', 'menor preco', 'oferta relâmpago', 'oferta relampago', 'imperdível', 'imperdivel', 'baixou', 'cupom')):
        score += 10
    return score


def select_next_pending_offer(queryset):
    """
    Seleciona a próxima oferta da fila equilibrando a quantidade entre lojas
    (priorizando a loja com menos envios hoje) e, dentro dela, maiores descontos e cupons.
    """
    from django.db.models import Count

    candidates = list(queryset.select_related('product').order_by('received_at', 'id')[:50])
    if not candidates:
        return None

    today = timezone.localdate()
    store_counts_rows = (
        IncomingAffiliateOffer.objects.filter(
            status__in=(IncomingOfferStatus.PUBLISHED, IncomingOfferStatus.UNCERTAIN),
            published_at__date=today,
        )
        .values('store')
        .annotate(total=Count('id'))
    )
    store_today_counts = {row['store']: row['total'] for row in store_counts_rows}
    store_quotas = parse_store_daily_quotas()

    def _quota_exceeded_rank(item):
        s_key = item.store or STORE_MERCADOLIVRE
        quota = store_quotas.get(s_key)
        if quota is None:
            return 0
        return 1 if store_today_counts.get(s_key, 0) >= quota else 0

    candidates.sort(
        key=lambda item: (
            _quota_exceeded_rank(item),
            store_today_counts.get(item.store or STORE_MERCADOLIVRE, 0),
            -_offer_queue_priority(item),
            item.received_at,
            item.id,
        )
    )
    return candidates[0]


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

    if is_blocked_send_group(target_group):
        raise AffiliateAutomationError(
            f'Envio bloqueado por segurança para o grupo “{target_group}”.'
        )

    browser.switch_to.window(whatsapp_tab)
    open_whatsapp_group(browser, target_group)
    opened_group = _current_group_name(browser)
    if is_blocked_send_group(opened_group):
        raise AffiliateAutomationError(
            f'Envio cancelado: o grupo aberto no WhatsApp (“{opened_group}”) está bloqueado para envio.'
        )
    if not _is_group_match(opened_group, target_group):
        raise AffiliateAutomationError(f'Grupo de destino “{target_group}” não pôde ser confirmado no WhatsApp.')

    # Detecção rápida de grupo fechado / somente administradores (pula sem gerar erro)
    try:
        footer_text = (browser.execute_script("""
            const footer = document.querySelector('#main footer');
            return footer ? (footer.innerText || '').trim().toLowerCase() : '';
        """) or '')
        if any(phrase in footer_text for phrase in (
            'somente admins',
            'apenas admins',
            'somente administradores',
            'apenas administradores',
            'only admins',
            'você não pode enviar mensagens',
            'voce nao pode enviar mensagens',
            "you can't send messages",
        )):
            raise GroupAdminOnlySkip(
                f'Grupo “{target_group}” está trancado para administradores; envio pulado.'
            )
    except GroupAdminOnlySkip:
        raise
    except Exception:
        pass

    def _type_full_message():
        _clear_message_composer(browser)
        comp = _message_composer(browser)
        if not comp:
            comp = WebDriverWait(browser, 15).until(_message_composer)
        comp.click()
        lines = message.splitlines()
        for index, line in enumerate(lines):
            if line:
                comp.send_keys(line)
            if index < len(lines) - 1:
                comp.send_keys(Keys.SHIFT, Keys.ENTER)
        # Espaço final ajuda o WhatsApp Web a disparar a prévia do link
        comp.send_keys(Keys.SPACE)
        return comp

    try:
        composer = WebDriverWait(browser, 12).until(_message_composer)
    except TimeoutException as exc:
        if _is_group_match(_current_group_name(browser), target_group):
            raise GroupAdminOnlySkip(
                f'Grupo “{target_group}” sem caixa de mensagem disponível (trancado para administradores); envio pulado.'
            ) from exc
        raise AffiliateAutomationError(
            f'Campo de mensagem não ficou disponível em “{target_group}”.'
        ) from exc
    _type_full_message()

    # Aguarda até 12s pela prévia com imagem no WhatsApp Web; se não carregar, tenta mais uma vez
    preview_ready = False
    try:
        WebDriverWait(browser, 12, poll_frequency=0.5).until(_has_link_preview_image)
        preview_ready = True
    except TimeoutException:
        logger.warning('Prévia de imagem não carregou na 1ª tentativa para “%s”; tentando novamente.', target_group)
        try:
            _clear_message_composer(browser)
            comp = _message_composer(browser)
            if comp:
                comp.click()
                comp.send_keys(affiliate_url, Keys.SPACE)
                try:
                    WebDriverWait(browser, 8, poll_frequency=0.5).until(_has_link_preview_image)
                except TimeoutException:
                    pass
            _type_full_message()
            WebDriverWait(browser, 10, poll_frequency=0.5).until(_has_link_preview_image)
            preview_ready = True
        except TimeoutException:
            preview_ready = False

    if not preview_ready or not _has_link_preview_image(browser):
        _clear_message_composer(browser)
        raise AffiliateAutomationError(
            'Prévia de imagem não carregou no WhatsApp; envio cancelado para não enviar apenas texto.'
        )

    time.sleep(1)

    active_group = _current_group_name(browser)
    if is_blocked_send_group(active_group):
        raise AffiliateAutomationError(
            f'Envio cancelado: o grupo ativo no WhatsApp (“{active_group}”) está bloqueado para envio.'
        )
    if not _is_group_match(active_group, target_group):
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


def select_balanced_target_groups(target_groups, store=None, max_lead=None):
    """
    Ordena os grupos destino do menor para o maior número de envios bem-sucedidos hoje
    (separado por loja quando `store` for informado) e prioriza os grupos que estão até
    `max_lead` envios acima do menor grupo saudável, mantendo equilíbrio igual por grupo e por loja.
    Retorna (priority_groups, overflow_groups).
    """
    from django.db.models import Count, Q
    from .models import PublicationDelivery, PublicationDeliveryStatus

    if max_lead is None:
        max_lead = max(0, int(getattr(settings, 'AFFILIATE_BOT_MAX_GROUP_LEAD', 1)))

    now_mono = time.monotonic()
    eligible = []
    for item in target_groups:
        group_name = item['name'] if isinstance(item, dict) else item
        if not group_name or is_blocked_send_group(group_name):
            continue
        skip_until = _ADMIN_ONLY_SKIP_UNTIL.get(group_name, 0.0)
        if skip_until > now_mono:
            continue
        eligible.append(item)

    if len(eligible) <= 1:
        return eligible, []

    today = timezone.localdate()
    now = timezone.now()
    cooldown_minutes = max(5, int(getattr(settings, 'AFFILIATE_BOT_GROUP_COOLDOWN_MINUTES', 60)))
    cooldown_threshold = max(2, int(getattr(settings, 'AFFILIATE_BOT_GROUP_COOLDOWN_FAILURES', 3)))
    cooldown_cutoff = now - timedelta(minutes=cooldown_minutes)

    eligible_names = [item['name'] if isinstance(item, dict) else item for item in eligible]

    # Circuit breaker: se um grupo falhou N vezes seguidas recentemente (ex.: fechado só p/ admins
    # ou nome não encontrado), entra em pausa automática por `cooldown_minutes` para não gerar
    # dezenas de falhas repetidas nem desperdiçar tempo de envio.
    recent_global = (
        PublicationDelivery.objects.filter(
            target_group_name__in=eligible_names,
            sent_at__gte=now - timedelta(hours=6),
        )
        .order_by('-sent_at', '-id')
        .values_list('target_group_name', 'status', 'sent_at')
    )
    consecutive_failures = {}
    last_failure_at = {}
    stopped_counting = set()
    for g_name, g_status, g_sent_at in recent_global:
        if g_name in stopped_counting:
            continue
        if g_status == PublicationDeliveryStatus.FAILED:
            consecutive_failures[g_name] = consecutive_failures.get(g_name, 0) + 1
            if g_name not in last_failure_at:
                last_failure_at[g_name] = g_sent_at
        else:
            stopped_counting.add(g_name)

    cooled_down_names = {
        g_name
        for g_name, fail_count in consecutive_failures.items()
        if fail_count >= cooldown_threshold
        and last_failure_at.get(g_name)
        and last_failure_at[g_name] >= cooldown_cutoff
    }
    if cooled_down_names:
        active_eligible = [
            item for item in eligible
            if (item['name'] if isinstance(item, dict) else item) not in cooled_down_names
        ]
        if active_eligible:
            logger.info(
                'Grupos em pausa automática (cooldown %s min após %s+ falhas seguidas): %s',
                cooldown_minutes,
                cooldown_threshold,
                ', '.join(sorted(cooled_down_names)),
            )
            eligible = active_eligible
            eligible_names = [item['name'] if isinstance(item, dict) else item for item in eligible]

    deliveries_qs = PublicationDelivery.objects.filter(
        target_group_name__in=eligible_names,
    )
    if store:
        deliveries_qs = deliveries_qs.filter(
            Q(incoming_offer__store=store)
            | Q(incoming_offer__isnull=True, publication__product__store=store)
        )

    counts_rows = (
        deliveries_qs.filter(status=PublicationDeliveryStatus.SUCCESS)
        .values('target_group_name')
        .annotate(
            today_count=Count('id', filter=Q(sent_at__date=today)),
            total_count=Count('id'),
        )
    )
    today_counts = {row['target_group_name']: row['today_count'] for row in counts_rows}
    total_counts = {row['target_group_name']: row['total_count'] for row in counts_rows}

    last_status_by_group = {}
    recent_today = (
        deliveries_qs.filter(sent_at__date=today)
        .order_by('-sent_at', '-id')
        .values_list('target_group_name', 'status')
    )
    for g_name, g_status in recent_today:
        if g_name not in last_status_by_group:
            last_status_by_group[g_name] = g_status

    ranked = sorted(
        eligible,
        key=lambda item: (
            today_counts.get(item['name'] if isinstance(item, dict) else item, 0),
            total_counts.get(item['name'] if isinstance(item, dict) else item, 0),
            (item['name'] if isinstance(item, dict) else item).casefold(),
        ),
    )

    healthy_counts = [
        today_counts.get(item['name'] if isinstance(item, dict) else item, 0)
        for item in ranked
        if last_status_by_group.get(item['name'] if isinstance(item, dict) else item)
        != PublicationDeliveryStatus.FAILED
    ]
    baseline = (
        min(healthy_counts)
        if healthy_counts
        else today_counts.get(ranked[0]['name'] if isinstance(ranked[0], dict) else ranked[0], 0)
    )

    priority_groups = []
    overflow_groups = []
    for item in ranked:
        g_name = item['name'] if isinstance(item, dict) else item
        if today_counts.get(g_name, 0) <= baseline + max_lead:
            priority_groups.append(item)
        else:
            overflow_groups.append(item)

    if not priority_groups:
        return ranked, []
    return priority_groups, overflow_groups


def resolve_whatsapp_dispatch_url(affiliate_url, store, inbox=None, channel=''):
    """
    Compliance por loja:
    - Amazon: roteia para a página individual na Vitrine Pública (https://.../oferta/<id>)
      para que o Referer chegue à Amazon a partir do site público cadastrado.
    - Mercado Livre / Shopee / TikTok: envia o link direto de afiliado com Sub-ID.
    """
    tracked_url = apply_tracking_subid(
        affiliate_url,
        store=store or STORE_MERCADOLIVRE,
        channel=channel,
    )
    if (store or '').strip().lower() == STORE_AMAZON and inbox is not None and getattr(inbox, 'id', None):
        from .vitrine_sync import build_vitrine_offer_url
        vitrine_url = build_vitrine_offer_url(inbox.id)
        if vitrine_url:
            return vitrine_url
    return tracked_url


def sync_vip_group_members_count(browser, whatsapp_tab):
    """
    Lê a quantidade atual de membros do grupo VIP (ex: Garimpo de Ofertas) no WhatsApp Web
    e salva em WhatsAppGroup (total + referência de início do dia para calcular entradas hoje).
    """
    from .models import WhatsAppGroup

    vip_group_name = (getattr(settings, 'AFFILIATE_BOT_VIP_GROUP_NAME', 'Garimpo de Ofertas') or '').strip()
    if not vip_group_name:
        return None

    group_obj = None
    for candidate in WhatsAppGroup.objects.all():
        if _is_group_match(candidate.name, vip_group_name):
            group_obj = candidate
            break
    if not group_obj:
        return None

    try:
        browser.switch_to.window(whatsapp_tab)
        try:
            ActionChains(browser).send_keys(Keys.ESCAPE).perform()
            time.sleep(0.25)
            ActionChains(browser).send_keys(Keys.ESCAPE).perform()
            time.sleep(0.25)
        except Exception:
            pass

        current_header = browser.execute_script(
            """
            const h = document.querySelector('#main header');
            return h ? (h.innerText || '').split('\\n')[0].trim() : '';
            """
        ) or ''
        if not _is_group_match(current_header, group_obj.name):
            open_whatsapp_group(browser, group_obj.name)
            time.sleep(1.0)

        # Clica no cabeçalho da conversa para abrir os Dados do Grupo
        browser.execute_script(
            """
            const header = document.querySelector('#main header');
            if (!header) return false;
            const clickable = header.querySelector('[role="button"]') || header;
            clickable.click();
            return true;
            """
        )
        time.sleep(1.8)

        raw_text = browser.execute_script(
            """
            const panels = Array.from(document.querySelectorAll('section, aside, [data-testid="chat-info-drawer"], #main, #app'));
            const texts = panels.map(el => (el.innerText || '')).filter(Boolean);
            return texts.join('\\n');
            """
        ) or ''

        # Fecha o painel de informações do grupo com ESC
        try:
            ActionChains(browser).send_keys(Keys.ESCAPE).perform()
            time.sleep(0.3)
        except Exception:
            pass

        match = re.search(
            r'(\d[\d\.\,]*)\s*(?:membros?|participantes?|members?|participants?)',
            raw_text,
            flags=re.IGNORECASE,
        )
        if not match:
            return None

        count_digits = re.sub(r'[^\d]', '', match.group(1))
        if not count_digits:
            return None
        members_count = int(count_digits)

        today = timezone.localdate()
        update_fields = ['members_count', 'members_updated_at', 'updated_at']
        group_obj.members_count = members_count
        group_obj.members_updated_at = timezone.now()
        if group_obj.members_day_start_date != today or group_obj.members_day_start_count is None:
            group_obj.members_day_start_date = today
            group_obj.members_day_start_count = members_count
            update_fields.extend(['members_day_start_date', 'members_day_start_count'])
        group_obj.save(update_fields=update_fields)
        logger.info('Membros do grupo VIP “%s” sincronizados: %s', group_obj.name, members_count)
        return members_count
    except Exception:
        logger.warning('Não foi possível ler o número de membros do grupo VIP.', exc_info=True)
        return None


def publish_offer_in_whatsapp(browser, whatsapp_tab, target_groups, message, affiliate_url, inbox=None, publication=None):
    """
    Publica a oferta nos grupos de destino autorizados, aplicando distribuição equilibrada
    entre grupos, controle de duplicidade por grupo e registro individual no PublicationDelivery.
    """
    from .models import PublicationDelivery, PublicationDeliveryStatus

    if not target_groups:
        raise AffiliateAutomationError('Nenhum grupo de destino configurado para publicação.')

    offer_store = None
    if inbox is not None and getattr(inbox, 'store', None):
        offer_store = inbox.store
    elif publication is not None and getattr(publication, 'product', None):
        offer_store = getattr(publication.product, 'store', None)

    priority_groups, overflow_groups = select_balanced_target_groups(target_groups, store=offer_store)
    deliveries_result = []

    def _dispatch_batch(batch):
        batch_success = 0
        for item in batch:
            group_name = item['name'] if isinstance(item, dict) else item
            group_jid = item.get('jid') if isinstance(item, dict) else None

            if is_blocked_send_group(group_name):
                logger.warning('Envio bloqueado por segurança para o grupo “%s”; pulando.', group_name)
                continue

            # Controle de duplicidade: verificar se este produto já foi enviado com sucesso a este grupo
            if publication and PublicationDelivery.objects.filter(
                publication=publication,
                target_group_name=group_name,
                status=PublicationDeliveryStatus.SUCCESS,
            ).exists():
                logger.info('Oferta já enviada anteriormente para “%s”; pulando para evitar duplicidade.', group_name)
                continue

            try:
                vip_group_name = (getattr(settings, 'AFFILIATE_BOT_VIP_GROUP_NAME', 'Garimpo de Ofertas') or '').strip()
                vip_invite_link = (getattr(settings, 'AFFILIATE_BOT_VIP_INVITE_LINK', '') or '').strip()
                vip_daily_limit = max(1, int(getattr(settings, 'AFFILIATE_BOT_VIP_DAILY_LIMIT', 12)))
                bait_min_discount = float(getattr(settings, 'AFFILIATE_BOT_BAIT_MIN_DISCOUNT_PCT', 40))
                bait_max_per_group = max(1, int(getattr(settings, 'AFFILIATE_BOT_BAIT_MAX_PER_GROUP_DAY', 3)))
                is_vip_group = _is_group_match(group_name, vip_group_name) if vip_group_name else False

                today_date = timezone.localdate()
                open_group_daily_limit = max(1, int(getattr(settings, 'AFFILIATE_BOT_OPEN_GROUP_DAILY_LIMIT', 10)))
                group_cooldown_minutes = max(0, int(getattr(settings, 'AFFILIATE_BOT_GROUP_MIN_COOLDOWN_MINUTES', 15)))
                group_daily_limit = vip_daily_limit if is_vip_group else open_group_daily_limit

                group_sent_today = PublicationDelivery.objects.filter(
                    target_group_name=group_name,
                    status=PublicationDeliveryStatus.SUCCESS,
                    sent_at__date=today_date,
                ).count()

                if group_sent_today >= group_daily_limit:
                    logger.info(
                        'Grupo “%s” atingiu limite diário (%s/%s); pulando.',
                        group_name,
                        group_sent_today,
                        group_daily_limit,
                    )
                    continue

                if (getattr(settings, 'AFFILIATE_BOT_VIP_PEAK_WINDOWS', '') or '').strip():
                    active_peak_win = get_active_vip_peak_window(group_daily_limit)
                    if not active_peak_win:
                        logger.info('Grupo “%s” fora dos horários de pico configurados; pulando.', group_name)
                        continue
                    win_start, win_end, win_quota = active_peak_win
                    group_sent_window = PublicationDelivery.objects.filter(
                        target_group_name=group_name,
                        status=PublicationDeliveryStatus.SUCCESS,
                        sent_at__gte=win_start,
                        sent_at__lte=win_end,
                    ).count()
                    if group_sent_window >= win_quota:
                        logger.info(
                            'Grupo “%s” atingiu cota da janela atual (%s/%s); reservando saldo para próximos períodos.',
                            group_name,
                            group_sent_window,
                            win_quota,
                        )
                        continue

                if group_cooldown_minutes > 0:
                    cooldown_since = timezone.now() - timedelta(minutes=group_cooldown_minutes)
                    if PublicationDelivery.objects.filter(
                        target_group_name=group_name,
                        status=PublicationDeliveryStatus.SUCCESS,
                        sent_at__gte=cooldown_since,
                    ).exists():
                        logger.info(
                            'Grupo “%s” recebeu oferta há menos de %s min; aguardando intervalo anti-spam.',
                            group_name,
                            group_cooldown_minutes,
                        )
                        continue

                # Calcula desconto e define se envia como Oferta Isca (captação VIP) ou normal
                offer_discount_pct = 0
                prod_obj = publication.product if publication and getattr(publication, 'product', None) else None
                if prod_obj and prod_obj.original_price and prod_obj.price and prod_obj.original_price > prod_obj.price:
                    offer_discount_pct = round(
                        ((float(prod_obj.original_price) - float(prod_obj.price)) / float(prod_obj.original_price)) * 100
                    )

                use_bait = False
                tracking_channel = 'garimpo_vip' if is_vip_group else 'grupo_aberto'
                if (
                    not is_vip_group
                    and vip_invite_link
                    and offer_discount_pct >= bait_min_discount
                    and prod_obj is not None
                ):
                    bait_sent_today = PublicationDelivery.objects.filter(
                        target_group_name=group_name,
                        is_bait=True,
                        status=PublicationDeliveryStatus.SUCCESS,
                        sent_at__date=today_date,
                    ).count()
                    if bait_sent_today < bait_max_per_group:
                        use_bait = True
                        tracking_channel = 'captacao_aberta'

                tracked_url = resolve_whatsapp_dispatch_url(
                    affiliate_url,
                    store=offer_store or STORE_MERCADOLIVRE,
                    inbox=inbox,
                    channel=tracking_channel,
                )
                if use_bait and prod_obj is not None:
                    outgoing_message = build_bait_offer_message(
                        {
                            'title': prod_obj.title,
                            'price': prod_obj.price,
                            'original_price': prod_obj.original_price,
                            'store': offer_store or STORE_MERCADOLIVRE,
                        },
                        inbox.coupon if inbox else '',
                        tracked_url,
                        invite_link=vip_invite_link,
                    )
                else:
                    outgoing_message = (
                        message.replace(affiliate_url, tracked_url)
                        if tracked_url != affiliate_url
                        else message
                    )
                    if not is_vip_group and vip_invite_link and vip_invite_link not in outgoing_message:
                        vip_label = (vip_group_name or 'GARIMPO DE OFERTAS').upper()
                        outgoing_message = (
                            f'{outgoing_message}\n\n'
                            f'🔥 *Receba mais ofertas como essa no nosso grupo VIP {vip_label}:*\n'
                            f'{vip_invite_link}'
                        )

                _publish_offer_to_group(
                    browser,
                    whatsapp_tab,
                    group_name,
                    outgoing_message,
                    tracked_url,
                )
                if publication:
                    PublicationDelivery.objects.create(
                        publication=publication,
                        incoming_offer=inbox,
                        target_group_name=group_name,
                        target_group_jid=group_jid,
                        affiliate_url=tracked_url,
                        is_bait=use_bait,
                        tracking_channel=tracking_channel,
                        status=PublicationDeliveryStatus.SUCCESS,
                        error_message='',
                        sent_at=timezone.now(),
                    )
                deliveries_result.append({'group': group_name, 'success': True})
                batch_success += 1
                _ADMIN_ONLY_SKIP_UNTIL.pop(group_name, None)
                time.sleep(random.uniform(3.0, 7.5))
            except GroupAdminOnlySkip as skip_exc:
                cooldown_sec = max(
                    300,
                    int(getattr(settings, 'AFFILIATE_BOT_GROUP_COOLDOWN_MINUTES', 60)) * 60,
                )
                _ADMIN_ONLY_SKIP_UNTIL[group_name] = time.monotonic() + cooldown_sec
                logger.info('%s (pausa de %s min sem registrar erro).', skip_exc, cooldown_sec // 60)
                continue
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
        return batch_success

    sent_in_priority = _dispatch_batch(priority_groups)
    if sent_in_priority == 0 and overflow_groups:
        logger.info(
            'Nenhum envio concluído no lote prioritário equilibrado; tentando demais grupos em ordem de menor volume.'
        )
        _dispatch_batch(overflow_groups)

    if not deliveries_result:
        return 'Todos os grupos autorizados já haviam recebido esta oferta anteriormente.'

    success_count = sum(1 for d in deliveries_result if d['success'])
    if success_count == 0:
        errors = '; '.join(f"{d['group']}: {d.get('error')}" for d in deliveries_result if not d['success'])
        raise AffiliateAutomationError(f'Falha no envio em todos os grupos: {errors}')

    return f'Oferta enviada com sucesso para {success_count} grupo(s).'


def _shorten_offer_title(title, max_len=72):
    cleaned = re.sub(r'\s+', ' ', (title or '')).strip()
    if len(cleaned) <= max_len:
        return cleaned
    # Tenta cortar em separador natural (vírgula, traço, barra) antes de truncar
    for sep in (' - ', ' | ', ', ', ' / '):
        head = cleaned.split(sep, 1)[0].strip()
        if 18 <= len(head) <= max_len:
            return head
    cut = cleaned[:max_len].rsplit(' ', 1)[0].strip()
    return f'{cut or cleaned[:max_len]}…'


def apply_tracking_subid(affiliate_url, store=STORE_MERCADOLIVRE, channel='standard'):
    """
    Módulo 4 (Rastreamento e Sub-IDs): anexa sub-ID dinâmico (ex.: garimpo_vip vs captacao_aberta)
    em URLs de loja que suportam query params sem quebrar links curtos.
    """
    if not affiliate_url or not channel:
        return affiliate_url
    try:
        parsed = urlsplit(affiliate_url)
    except Exception:
        return affiliate_url

    hostname = (parsed.hostname or '').lower()
    if store == STORE_AMAZON and ('amazon.com.br' in hostname):
        query = parse_qs(parsed.query, keep_blank_values=True)
        query['ascsubtag'] = [channel]
        new_query = urlencode(query, doseq=True)
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, new_query, parsed.fragment))
    if store == STORE_MERCADOLIVRE and ('mercadolivre.com' in hostname):
        query = parse_qs(parsed.query, keep_blank_values=True)
        query['utm_source'] = [channel]
        new_query = urlencode(query, doseq=True)
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, new_query, parsed.fragment))
    return affiliate_url


def get_active_vip_peak_window(vip_daily_limit, now=None):
    """
    Retorna (window_start_dt, window_end_dt, window_quota) se o horário atual estiver dentro
    de uma janela de pico do grupo VIP, dividindo a cota diária entre os períodos do dia
    (ex: 10/dia em 3 janelas => 3 manhã, 3 almoço, 4 noite) para sempre haver publicações.
    """
    raw = (getattr(settings, 'AFFILIATE_BOT_VIP_PEAK_WINDOWS', '') or '').strip()
    if not raw:
        return None
    local_now = timezone.localtime(now or timezone.now())
    parsed_windows = []
    for chunk in raw.split(','):
        part = chunk.strip()
        if '-' not in part:
            continue
        start_s, end_s = part.split('-', 1)
        try:
            sh, sm = [int(x) for x in start_s.strip().split(':')]
            eh, em = [int(x) for x in end_s.strip().split(':')]
        except ValueError:
            continue
        parsed_windows.append((sh, sm, eh, em))

    if not parsed_windows:
        return None

    total_windows = len(parsed_windows)
    base_quota = max(1, vip_daily_limit // total_windows)
    remainder = max(0, vip_daily_limit - (base_quota * total_windows))
    now_mins = local_now.hour * 60 + local_now.minute

    for idx, (sh, sm, eh, em) in enumerate(parsed_windows):
        if (sh * 60 + sm) <= now_mins <= (eh * 60 + em):
            quota = base_quota + (remainder if idx == total_windows - 1 else 0)
            start_dt = local_now.replace(hour=sh, minute=sm, second=0, microsecond=0)
            end_dt = local_now.replace(hour=eh, minute=em, second=59, microsecond=999999)
            return start_dt, end_dt, quota
    return None


def is_within_vip_peak_window(now=None):
    """
    Verifica se o horário atual está dentro das janelas de pico do grupo oficial
    GARIMPO DE OFERTAS (padrão: 08:00-09:00, 12:00-13:30, 19:00-22:00).
    """
    raw = (getattr(settings, 'AFFILIATE_BOT_VIP_PEAK_WINDOWS', '') or '').strip()
    if not raw:
        return True
    return get_active_vip_peak_window(12, now=now) is not None


def build_bait_offer_message(details, coupon, affiliate_url, invite_link=''):
    """
    Módulo 3 (Template de Captação de Membros — Oferta Isca >= 40% OFF -> GARIMPO DE OFERTAS).
    """
    price_val = float(details['price'])
    price = f'{price_val:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    original_val = details.get('original_price')
    short_title = _shorten_offer_title(details.get('title', ''))
    vip_name = getattr(settings, 'AFFILIATE_BOT_VIP_GROUP_NAME', 'GARIMPO DE OFERTAS').upper()

    lines = [f'🔥 *ACHADO DO DIA:* {short_title}']
    if original_val and float(original_val) > price_val:
        original_float = float(original_val)
        original = f'{original_float:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
        lines.append(f'De ~R$ {original}~ por *R$ {price}*')
    else:
        lines.append(f'Por apenas *R$ {price}*')
    if coupon:
        lines.append(f'🎟️ *Use o cupom:* {coupon}')
    lines.append(f'🛒 Link direto: {affiliate_url}')
    lines.append('')
    lines.append(
        '⚠️ *Quer receber mais bugs de preço e cupons relâmpago como esse antes de acabar '
        '(sem spam e sem chat travado)?*'
    )
    if invite_link:
        lines.append(f'Entre no nosso grupo VIP *{vip_name}*: {invite_link}')
    else:
        lines.append(f'Entre no nosso grupo VIP *{vip_name}*!')
    return '\n'.join(lines)


def build_incoming_offer_message(details, coupon, affiliate_url, original_message=''):
    """
    Módulo 2 (Gerador de Copy de Alta Conversão — Template Dinâmico).
    """
    price_val = float(details['price'])
    price = f'{price_val:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    original_val = details.get('original_price')
    discount_pct = 0
    original = ''
    if original_val and float(original_val) > price_val:
        original_float = float(original_val)
        original = f'{original_float:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
        discount_pct = round(((original_float - price_val) / original_float) * 100)

    store_suffix = get_store_headline_suffix(details.get('store', STORE_MERCADOLIVRE))
    if discount_pct >= 45:
        headline = f'🚨 *MENOR PREÇO HISTÓRICO — {discount_pct}% OFF {store_suffix}!*'
    elif discount_pct >= 25:
        headline = f'🔥 *OPORTUNIDADE RELÂMPAGO — {discount_pct}% OFF {store_suffix}!*'
    elif coupon:
        headline = f'🎟️ *CUPOM LIBERADO {store_suffix}!*'
    else:
        headline = f'🔥 *OFERTA SELECIONADA {store_suffix}!*'

    short_title = _shorten_offer_title(details.get('title', ''))
    lines = [
        headline,
        '',
        f'*{short_title}*',
    ]
    if original and discount_pct > 0:
        lines.append(f'De ~R$ {original}~ por *R$ {price}* 💥')
    else:
        lines.append(f'Por apenas *R$ {price}* 💥')

    if coupon:
        lines.append(f'🎟️ *Ative o cupom na página:* {coupon}')

    orig_low = (original_message or '').lower()
    if 'pix' in orig_low:
        lines.append('⚡ *Preço válido no Pix*')

    lines.append(f'👉 {affiliate_url}')
    return '\n'.join(lines)


def _store_product_and_publication(inbox, details, affiliate_url):
    with transaction.atomic():
        store = details.get('store', STORE_MERCADOLIVRE)
        product = ProductOffer.objects.filter(item_id=details['item_id']).first()
        if product is None:
            product = ProductOffer(
                item_id=details['item_id'],
                store=store,
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
            product.store = store
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

        message = build_incoming_offer_message(
            details,
            inbox.coupon,
            affiliate_url,
            original_message=inbox.original_message,
        )
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
                store = detect_store_from_url(inbox.source_link) or inbox.store or STORE_MERCADOLIVRE
                if store == STORE_AMAZON:
                    from .amazon_provider import (
                        generate_amazon_affiliate_link,
                        resolve_amazon_product_page,
                        validate_amazon_affiliate_link,
                    )
                    details = resolve_amazon_product_page(browser, inbox.source_link, inbox.original_message)
                elif store == STORE_SHOPEE:
                    from .shopee_provider import (
                        generate_shopee_affiliate_link,
                        resolve_shopee_product_page,
                        validate_shopee_affiliate_link,
                    )
                    details = resolve_shopee_product_page(browser, inbox.source_link, inbox.original_message)
                elif store == STORE_TIKTOK:
                    from .tiktok_provider import (
                        generate_tiktok_affiliate_link,
                        resolve_tiktok_product_page,
                        validate_tiktok_affiliate_link,
                    )
                    details = resolve_tiktok_product_page(browser, inbox.source_link, inbox.original_message)
                else:
                    details = resolve_product_page(browser, inbox.source_link, inbox.original_message)
                    details.setdefault('store', STORE_MERCADOLIVRE)

                quality_ok, quality_reason = evaluate_offer_quality(details, inbox.coupon)
                if not quality_ok:
                    inbox.status = IncomingOfferStatus.SKIPPED
                    inbox.error_message = quality_reason
                    inbox.processed_at = timezone.now()
                    inbox.save(update_fields=['status', 'error_message', 'processed_at', 'updated_at'])
                    return quality_reason

                if store == STORE_AMAZON:
                    affiliate_url = generate_amazon_affiliate_link(browser, details['product_url'])
                    validate_amazon_affiliate_link(browser, affiliate_url, details['item_id'])
                elif store == STORE_SHOPEE:
                    affiliate_url = generate_shopee_affiliate_link(browser, details['product_url'])
                    validate_shopee_affiliate_link(browser, affiliate_url, details['item_id'])
                elif store == STORE_TIKTOK:
                    affiliate_url = generate_tiktok_affiliate_link(browser, details['product_url'])
                    validate_tiktok_affiliate_link(browser, affiliate_url, details['item_id'])
                else:
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

        # Compliance Amazon: garante que a oferta já está publicada na Vitrine antes do disparo no WhatsApp
        offer_store_final = (inbox.store or (product.store if product else '') or '').strip().lower()
        if offer_store_final == STORE_AMAZON and getattr(settings, 'AFFILIATE_BOT_VITRINE_BASE_URL', ''):
            try:
                from .vitrine_sync import sync_vitrine_to_github
                if not inbox.affiliate_url:
                    inbox.affiliate_url = affiliate_url
                pushed_now = sync_vitrine_to_github(max_age_hours=48, extra_offer=inbox)
                if pushed_now:
                    time.sleep(12)
            except Exception:
                logger.warning('Falha ao pré-sincronizar oferta Amazon na vitrine antes do envio.', exc_info=True)

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
        try:
            from .vitrine_sync import export_vitrine_json
            export_vitrine_json(max_age_hours=48)
        except Exception:
            logger.warning('Falha ao atualizar ofertas.json da vitrine após publicação.', exc_info=True)
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


def parse_publish_windows(raw_windows=None):
    """
    Interpreta janelas de envio no formato '08:00=20,12:30=20,15:30=20,19:30=20,21:00=20'.
    Retorna lista ordenada de tuplas (hora, minuto, limite).
    """
    if raw_windows is None:
        raw_windows = getattr(settings, 'AFFILIATE_BOT_PUBLISH_WINDOWS', '')
    text = (raw_windows or '').strip()
    if not text:
        return []
    windows = []
    for chunk in text.split(','):
        part = chunk.strip()
        if not part or '=' not in part:
            continue
        time_part, limit_part = part.split('=', 1)
        time_bits = time_part.strip().split(':')
        if len(time_bits) != 2:
            continue
        try:
            hour = int(time_bits[0])
            minute = int(time_bits[1])
            limit = int(limit_part.strip())
        except ValueError:
            continue
        if 0 <= hour <= 23 and 0 <= minute <= 59 and limit > 0:
            windows.append((hour, minute, limit))
    windows.sort(key=lambda item: (item[0], item[1]))
    return windows


def current_publish_window_status(now=None, raw_windows=None):
    """
    Verifica se o horário atual está dentro de uma janela de envio ativa
    e se a cota dessa janela ainda não foi atingida.
    """
    windows = parse_publish_windows(raw_windows)
    if not windows:
        return {
            'enabled': False,
            'can_publish': True,
            'window_label': None,
            'window_sent': 0,
            'window_limit': None,
            'next_window_label': None,
            'reason': '',
        }

    local_now = timezone.localtime(now or timezone.now())
    active_index = None
    for idx, (hour, minute, _limit) in enumerate(windows):
        start_dt = local_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if local_now >= start_dt:
            active_index = idx

    if active_index is None:
        first_h, first_m, _ = windows[0]
        next_label = f'{first_h:02d}:{first_m:02d}'
        return {
            'enabled': True,
            'can_publish': False,
            'window_label': None,
            'window_sent': 0,
            'window_limit': 0,
            'next_window_label': next_label,
            'reason': f'Fora da janela de publicação; próxima janela às {next_label}.',
        }

    hour, minute, limit = windows[active_index]
    window_label = f'{hour:02d}:{minute:02d}'
    window_start = local_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if active_index + 1 < len(windows):
        next_h, next_m, _ = windows[active_index + 1]
        window_end = local_now.replace(hour=next_h, minute=next_m, second=0, microsecond=0)
        next_label = f'{next_h:02d}:{next_m:02d}'
    else:
        window_end = (window_start + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        first_h, first_m, _ = windows[0]
        next_label = f'amanhã às {first_h:02d}:{first_m:02d}'

    window_sent = IncomingAffiliateOffer.objects.filter(
        status__in=(IncomingOfferStatus.PUBLISHED, IncomingOfferStatus.UNCERTAIN),
        published_at__gte=window_start,
        published_at__lt=window_end,
    ).count()

    if window_sent >= limit:
        return {
            'enabled': True,
            'can_publish': False,
            'window_label': window_label,
            'window_sent': window_sent,
            'window_limit': limit,
            'next_window_label': next_label,
            'reason': f'Janela das {window_label} atingiu o limite ({window_sent}/{limit}); próxima janela: {next_label}.',
        }

    return {
        'enabled': True,
        'can_publish': True,
        'window_label': window_label,
        'window_sent': window_sent,
        'window_limit': limit,
        'next_window_label': next_label,
        'reason': '',
    }

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
