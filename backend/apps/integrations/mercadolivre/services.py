"""
Serviços de Busca, Deduplicação e Ingestão de Produtos
Especificação V1.0 - Seções 3.1 (F01, F02, F03, F04, F05), 3.2, 3.4
"""

import logging
from django.conf import settings
from apps.catalog.models import ProductOffer, ProductStatus, CategoryChoices
from .client import MercadoLivreAPIClient

logger = logging.getLogger(__name__)


DEFAULT_CATEGORY_IMAGES = {
    'technology': 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=600&q=80',
    'fashion': 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=600&q=80',
    'home': 'https://images.unsplash.com/photo-1584622650111-993a426fbf0a?auto=format&fit=crop&w=600&q=80',
    'beauty': 'https://images.unsplash.com/photo-1621607512214-68297480165e?auto=format&fit=crop&w=600&q=80',
}


class ProductDiscoveryService:
    """
    Coordena a busca automatizada, filtragem e persistência com deduplicação.
    """

    def __init__(self):
        self.client = MercadoLivreAPIClient()

    def run_search_for_category(self, category_key: str, custom_query: str = None, limit: int = 50):
        """
        Executa a busca para uma categoria específica ou termo customizado.
        """
        terms = [custom_query] if custom_query else settings.SEARCH_TERMS.get(category_key, [])
        all_created = 0
        all_updated = 0

        for term in terms:
            items = self.client.search_items(query=term, limit=limit)
            created, updated = self.process_and_save_items(items, category_key)
            all_created += created
            all_updated += updated

        return {
            'category': category_key,
            'items_created': all_created,
            'items_updated': all_updated,
        }

    def run_all_categories(self, limit_per_term: int = 20):
        """
        Executa a busca em todas as categorias configuradas (Seção 3.4).
        """
        results = {}
        for category_key in settings.SEARCH_TERMS.keys():
            res = self.run_search_for_category(category_key, limit=limit_per_term)
            results[category_key] = res
        return results

    def process_and_save_items(self, raw_items: list, category_key: str):
        """
        Processa itens brutos da API, aplica deduplicação (F03) e calcula a pontuação.
        """
        created_count = 0
        updated_count = 0

        for item in raw_items:
            item_id = item.get('id')
            if not item_id:
                continue

            title = item.get('title', '').strip()
            price = item.get('price')
            if price is None:
                continue

            original_price = item.get('original_price')
            product_url = (item.get('permalink') or '').strip()
            if not ProductOffer.is_valid_listing_permalink(product_url, item_id):
                logger.warning("Item %s ignorado porque a API não retornou um link direto válido.", item_id)
                continue
            thumbnail = item.get('thumbnail', '')
            if not thumbnail or 'img-not-available' in thumbnail:
                thumbnail = DEFAULT_CATEGORY_IMAGES.get(category_key, DEFAULT_CATEGORY_IMAGES['technology'])
            elif thumbnail.startswith('http://'):
                thumbnail = thumbnail.replace('http://', 'https://')
            condition = item.get('condition', 'new')
            
            # Dados do vendedor
            seller_data = item.get('seller', {})
            seller_id = str(seller_data.get('id', ''))
            seller_reputation = seller_data.get('seller_reputation', {}).get('level_id', 'unknown')
            if not seller_reputation or seller_reputation == 'unknown':
                # Verifica formato power_seller_status
                seller_reputation = seller_data.get('seller_reputation', {}).get('power_seller_status', 'unknown') or 'unknown'

            # Mapeamento e normalização da reputação
            if '5_green' in seller_reputation or 'platinum' in seller_reputation or 'gold' in seller_reputation:
                seller_reputation = 'green'

            # Deduplicação (F03): atualiza se já existir, sem duplicar o item_id
            product, created = ProductOffer.objects.get_or_create(
                item_id=item_id,
                defaults={
                    'title': title,
                    'category': category_key,
                    'price': price,
                    'original_price': original_price,
                    'product_url': product_url,
                    'thumbnail': thumbnail,
                    'seller_id': seller_id,
                    'seller_reputation': seller_reputation,
                    'condition': condition,
                    'status': ProductStatus.PENDING,
                }
            )

            if not created:
                # Atualização de anúncio existente sem alterar status ou link de afiliado caso já aprovado
                product.title = title
                product.price = price
                product.original_price = original_price
                product.product_url = product_url
                product.thumbnail = thumbnail
                product.seller_reputation = seller_reputation
                product.condition = condition
                product.calculate_score()
                product.save()
                updated_count += 1
            else:
                product.calculate_score()
                product.save()
                created_count += 1

        return created_count, updated_count
