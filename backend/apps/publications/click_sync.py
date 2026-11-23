"""
Sincronização de cliques oficiais diretamente dos painéis autenticados
no Chrome dedicado (Mercado Livre Afiliados e Amazon Associados).
"""

import logging
import re
import time

from django.conf import settings
from django.utils import timezone

from .models import StoreClickStats
from .product_urls import STORE_AMAZON, STORE_MERCADOLIVRE

logger = logging.getLogger(__name__)


def _parse_int(raw):
    digits = re.sub(r'[^\d]', '', str(raw or ''))
    return int(digits) if digits else None


def _extract_clicks_from_text(text):
    """
    Procura padrões comuns de cliques nos painéis de afiliados em PT-BR e EN.
    Retorna inteiro ou None se não encontrar.
    """
    if not text:
        return None
    patterns = (
        r'cliques?\s*[:\n\r\t ]+(\d[\d.,]*)',
        r'(\d[\d.,]*)\s*[\n\r\t ]+cliques?\b',
        r'clicks?\s*[:\n\r\t ]+(\d[\d.,]*)',
        r'(\d[\d.,]*)\s*[\n\r\t ]+clicks?\b',
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            val = _parse_int(match.group(1))
            if val is not None:
                return val
    return None


def _sync_mercadolivre_clicks(browser):
    browser.get('https://www.mercadolivre.com.br/afiliados/hub#hub')
    time.sleep(4)
    text = browser.execute_script('return document.body ? document.body.innerText : ""') or ''
    clicks = _extract_clicks_from_text(text)
    if clicks is None:
        return None, 'Não foi possível localizar o contador de cliques no painel do Mercado Livre (confira o login).'
    return clicks, ''


def _sync_amazon_clicks(browser):
    browser.get('https://associados.amazon.com.br/p/planning/home')
    time.sleep(4)
    if 'não foi possível encontrar' in (browser.title or '').lower():
        browser.get('https://associados.amazon.com.br/')
        time.sleep(4)
    text = browser.execute_script('return document.body ? document.body.innerText : ""') or ''
    clicks = _extract_clicks_from_text(text)
    if clicks is None:
        return None, 'Não foi possível localizar o contador de cliques na Central de Associados Amazon (confira o login).'
    return clicks, ''


def sync_official_click_stats():
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    debugger_address = getattr(settings, 'AFFILIATE_BOT_CHROME_DEBUGGER_ADDRESS', '127.0.0.1:9222')
    opts = Options()
    opts.debugger_address = debugger_address

    browser = webdriver.Chrome(options=opts)
    original_handle = browser.current_window_handle
    browser.switch_to.new_window('tab')
    temp_tab = browser.current_window_handle

    results = {}
    now = timezone.now()
    try:
        for store_key, fn in (
            (STORE_MERCADOLIVRE, _sync_mercadolivre_clicks),
            (STORE_AMAZON, _sync_amazon_clicks),
        ):
            try:
                clicks, err = fn(browser)
                obj, _ = StoreClickStats.objects.get_or_create(store=store_key)
                if clicks is not None:
                    obj.clicks_month = clicks
                    obj.sync_error = ''
                else:
                    obj.sync_error = err[:500]
                obj.last_synced_at = now
                obj.save()
                results[store_key] = {
                    'clicks_month': obj.clicks_month,
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
