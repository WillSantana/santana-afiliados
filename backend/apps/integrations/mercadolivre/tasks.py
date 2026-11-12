"""
Tarefas Assíncronas Celery para busca periódica de produtos
Especificação V1.0 - Seção 2.5
"""

from celery import shared_task
import logging
from .services import ProductDiscoveryService

logger = logging.getLogger(__name__)


@shared_task(name='mercadolivre.search_all_categories_task')
def search_all_categories_task():
    """
    Executa busca em segundo plano em todas as categorias pré-definidas.
    """
    logger.info("Iniciando busca assíncrona de anúncios no Mercado Livre...")
    service = ProductDiscoveryService()
    results = service.run_all_categories()
    logger.info(f"Busca assíncrona finalizada com sucesso: {results}")
    return results


@shared_task(name='mercadolivre.search_category_task')
def search_category_task(category_key, custom_query=None):
    """
    Executa busca assíncrona em uma categoria específica.
    """
    service = ProductDiscoveryService()
    return service.run_search_for_category(category_key=category_key, custom_query=custom_query)
