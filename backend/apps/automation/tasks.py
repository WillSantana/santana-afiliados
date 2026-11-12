"""
Tarefas Celery do Motor de Automação
Especificação V1.2 - Seção 11
"""

from celery import shared_task
import logging
from .services.search_runner import SearchRunnerService
from .services.price_monitor import PriceMonitorService

logger = logging.getLogger(__name__)


@shared_task(name='apps.automation.tasks.run_product_search')
def run_product_search(cycle_index: int = 0):
    """
    Executa ciclo programado de busca de produtos nas 4 categorias.
    Agendado 6 vezes por dia (08h, 10h, 12h, 14h, 16h, 18h).
    """
    logger.info(f"[Task] Iniciando ciclo programado de busca (índice: {cycle_index})...")
    runner = SearchRunnerService()
    return runner.run_scheduled_cycle(cycle_index=cycle_index)


@shared_task(name='apps.automation.tasks.run_price_monitoring')
def run_price_monitoring(limit: int = 40):
    """
    Executa ciclo programado de monitoramento de preços.
    Agendado a cada 2 horas (08:30 às 20:30).
    """
    logger.info("[Task] Iniciando ciclo de monitoramento de preços...")
    monitor = PriceMonitorService()
    return monitor.run_monitoring_cycle(limit=limit)
