import os
import sys
import django
import urllib.parse
import re

sys.path.append(os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.catalog.models import ProductOffer

def fix():
    updated = 0
    for p in ProductOffer.objects.all():
        url = p.product_url or ''
        if not url or '/p/MLB' in url or 'mercadolivre.com.br/p/' in url:
            clean_term = urllib.parse.quote_plus(p.title.strip())
            p.product_url = f"https://www.mercadolivre.com.br/jm/search?as_word={clean_term}"
            p.save(update_fields=['product_url'])
            updated += 1
            print(f"Atualizado #{p.id}: {p.title} -> {p.product_url}")
    print(f"Total de produtos atualizados com URLs reais do Mercado Livre: {updated}")

if __name__ == '__main__':
    fix()
