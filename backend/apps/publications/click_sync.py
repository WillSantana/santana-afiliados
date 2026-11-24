"""
Sincronização de cliques oficiais diretamente dos painéis autenticados
no Chrome dedicado (Mercado Livre Afiliados, Amazon Associados, Shopee e TikTok Shop).
"""

import logging
import re
import time

from django.conf import settings
from django.utils import timezone

from .models import StoreClickStats
from .product_urls import STORE_AMAZON, STORE_MERCADOLIVRE, STORE_SHOPEE, STORE_TIKTOK

logger = logging.getLogger(__name__)

PURE_INT_LINE_RE = re.compile(r'^\d[\d.,]*$')


def _parse_int(raw):
    digits = re.sub(r'[^\d]', '', str(raw or ''))
    return int(digits) if digits else None


def _clean_lines(text):
    return [line.strip() for line in (text or '').splitlines() if line.strip()]


def _extract_value_after_label(lines, labels, after_section=None):
    """
    Procura uma linha exatamente igual a um dos `labels` (case-insensitive)
    e retorna o inteiro puro da linha imediatamente seguinte (ignorando datas como '25Oct').
    Se `after_section` for informado, só considera ocorrências após essa seção.
    """
    start_idx = 0
    if after_section:
        needle = after_section.lower()
        for idx, line in enumerate(lines):
            if needle in line.lower():
                start_idx = idx
                break

    normalized_labels = {lbl.lower().rstrip(':') for lbl in labels}
    for idx in range(start_idx, len(lines) - 1):
        current = lines[idx].lower().rstrip(':').strip()
        if current in normalized_labels:
            next_line = lines[idx + 1].strip()
            if PURE_INT_LINE_RE.fullmatch(next_line):
                return _parse_int(next_line)
    return None


def _extract_clicks_from_text(text, after_section=None):
    lines = _clean_lines(text)
    val = _extract_value_after_label(lines, ('cliques', 'clicks'), after_section=after_section)
    if val is not None:
        return val
    # Fallback para texto inline "Cliques: 56"
    if after_section and after_section.lower() in (text or '').lower():
        pos = (text or '').lower().find(after_section.lower())
        text = text[pos:]
    match = re.search(r'\bcliques?\s*:\s*(\d[\d.,]*)(?!\s*[a-zA-Z])', text or '', re.IGNORECASE)
    if match:
        return _parse_int(match.group(1))
    return None


def _sync_mercadolivre_clicks(browser):
    browser.get('https://www.mercadolivre.com.br/afiliados/hub#hub')
    time.sleep(5)
    text = browser.execute_script('return document.body ? document.body.innerText : ""') or ''
    lines = _clean_lines(text)
    clicks = _extract_clicks_from_text(text, after_section='ir para métricas')
    if clicks is None:
        clicks = _extract_clicks_from_text(text)
    orders = _extract_value_after_label(lines, ('pedidos', 'orders'), after_section='ir para métricas')
    if clicks is None:
        return None, None, 'Não foi possível localizar o contador de cliques no painel do Mercado Livre (confira o login).'
    return clicks, orders, ''


def _sync_amazon_clicks(browser):
    browser.get('https://associados.amazon.com.br/home')
    time.sleep(5)
    text = browser.execute_script('return document.body ? document.body.innerText : ""') or ''
    lines = _clean_lines(text)
    clicks = _extract_clicks_from_text(text, after_section='resumo para este')
    if clicks is None:
        clicks = _extract_clicks_from_text(text, after_section='summary for this')
    orders = _extract_value_after_label(
        lines,
        ('total de produtos pedidos', 'total ordered items'),
        after_section='resumo para este',
    )
    if clicks is None:
        return None, None, 'Não foi possível localizar o contador de cliques na Central de Associados Amazon (confira o login).'
    return clicks, orders, ''


def _sync_shopee_clicks(browser):
    browser.get('https://affiliate.shopee.com.br/dashboard')
    time.sleep(4)
    text = browser.execute_script('return document.body ? document.body.innerText : ""') or ''
    lines = _clean_lines(text)
    clicks = _extract_clicks_from_text(text)
    orders = _extract_value_after_label(lines, ('pedido', 'pedidos', 'orders'))
    if clicks is None:
        return None, None, 'Não foi possível localizar o contador de cliques no Portal de Afiliados Shopee (confira o login).'
    return clicks, orders, ''


def _sync_tiktok_clicks(browser):
    browser.get('https://affiliate.tiktok.com/')
    time.sleep(4)
    text = browser.execute_script('return document.body ? document.body.innerText : ""') or ''
    clicks = _extract_clicks_from_text(text)
    if clicks is None:
        return None, None, 'Não foi possível localizar o contador de cliques no TikTok Shop Affiliate (confira o login).'
    return clicks, None, ''


def sync_official_click_stats(browser=None, fallback_tab=None, stores=None):
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    owns_browser = browser is None
    if owns_browser:
        debugger_address = getattr(settings, 'AFFILIATE_BOT_CHROME_DEBUGGER_ADDRESS', '127.0.0.1:9222')
        opts = Options()
        opts.debugger_address = debugger_address
        browser = webdriver.Chrome(options=opts)

    original_handle = fallback_tab or browser.current_window_handle
    browser.switch_to.new_window('tab')
    temp_tab = browser.current_window_handle

    handlers = (
        (STORE_MERCADOLIVRE, _sync_mercadolivre_clicks),
        (STORE_AMAZON, _sync_amazon_clicks),
        (STORE_SHOPEE, _sync_shopee_clicks),
        (STORE_TIKTOK, _sync_tiktok_clicks),
    )
    if stores is not None:
        allowed = set(stores)
        handlers = tuple((k, fn) for k, fn in handlers if k in allowed)

    results = {}
    now = timezone.now()
    try:
        for store_key, fn in handlers:
            try:
                clicks, orders, err = fn(browser)
                obj, _ = StoreClickStats.objects.get_or_create(store=store_key)
                if clicks is not None:
                    obj.clicks_month = clicks
                    if orders is not None:
                        obj.orders_month = orders
                    obj.sync_error = ''
                else:
                    obj.sync_error = err[:500]
                obj.last_synced_at = now
                obj.save()
                results[store_key] = {
                    'clicks_month': obj.clicks_month,
                    'orders_month': obj.orders_month,
                    'error': obj.sync_error,
                }
            except Exception as exc:
                logger.exception('Erro ao sincronizar cliques da loja %s.', store_key)
                obj, _ = StoreClickStats.objects.get_or_create(store=store_key)
                obj.sync_error = str(exc)[:500]
                obj.last_synced_at = now
                obj.save()
                results[store_key] = {
                    'clicks_month': obj.clicks_month,
                    'orders_month': obj.orders_month,
                    'error': obj.sync_error,
                }
    finally:
        try:
            if temp_tab in browser.window_handles and len(browser.window_handles) > 1:
                browser.switch_to.window(temp_tab)
                browser.close()
        except Exception:
            pass
        try:
            if original_handle in browser.window_handles:
                browser.switch_to.window(original_handle)
        except Exception:
            pass
    return results
