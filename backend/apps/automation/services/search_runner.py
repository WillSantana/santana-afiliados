"""
Serviço de Execução de Ciclos de Pesquisa Programada com Rotação de Termos
Especificação V1.2 - Seções 3.1-A, 6.2, 9.2 e 11
"""

import logging
from django.utils import timezone
from django.conf import settings
from apps.integrations.mercadolivre.services import ProductDiscoveryService
from apps.integrations.mercadolivre.client import MercadoLivreAPIClient
from apps.automation.models import SearchRun, SearchRunStatus, AutomationConfig

logger = logging.getLogger(__name__)


class SearchRunnerService:
    """
    Coordena a execução dos 6 ciclos diários de pesquisa de novos produtos,
    rotacionando termos das 4 categorias comerciais e auditando em SearchRun.
    """

    def __init__(self):
        self.discovery_service = ProductDiscoveryService()
        self.client = MercadoLivreAPIClient()

    def run_cycle_for_term(self, category: str, term: str, limit: int = 50) -> SearchRun:
        """
        Executa a pesquisa de um termo e persiste o registro de auditoria SearchRun.
        """
        search_run = SearchRun.objects.create(
            category=category,
            search_term=term,
            status=SearchRunStatus.RUNNING,
            started_at=timezone.now()
        )

        try:
            logger.info(f"[SearchRunner] Iniciando ciclo para categoria '{category}', termo '{term}'...")
            items = self.client.search_items(query=term, limit=limit)
            products_found = len(items)

            created, updated = self.discovery_service.process_and_save_items(items, category)

            search_run.products_found = products_found
            search_run.products_created = created
            search_run.products_updated = updated
            search_run.status = SearchRunStatus.COMPLETED
            search_run.finished_at = timezone.now()
            search_run.save()

            logger.info(
                f"[SearchRunner] Concluído '{term}': {products_found} encontrados, "
                f"{created} novos, {updated} atualizados em {search_run.duration_seconds}s."
            )
        except Exception as e:
            logger.exception(f"[SearchRunner] Erro durante a pesquisa de '{term}': {str(e)}")
            search_run.status = SearchRunStatus.FAILED
            search_run.error_message = str(e)
            search_run.finished_at = timezone.now()
            search_run.save()

        return search_run

    def run_scheduled_cycle(self, cycle_index: int = 0):
        """
        Executa um dos 6 ciclos diários (0 a 5), selecionando termos rotativos
        para cada uma das 4 categorias.
        """
        config = AutomationConfig.get_settings()
        if not config.searches_enabled:
            logger.info("[SearchRunner] Pesquisas automáticas estão pausadas na configuração.")
            return {"status": "skipped", "reason": "searches_disabled"}

        results = []
        search_terms = getattr(settings, 'SEARCH_TERMS', {})

        for category, terms in search_terms.items():
            if not terms:
                continue
            # Seleciona o termo da vez rotacionando pelo índice do ciclo
            term_index = cycle_index % len(terms)
            chosen_term = terms[term_index]

            run_record = self.run_cycle_for_term(category=category, term=chosen_term, limit=50)
            results.append({
                "category": category,
                "term": chosen_term,
                "created": run_record.products_created,
                "updated": run_record.products_updated,
                "status": run_record.status
            })

        return {"cycle_index": cycle_index, "runs": results}
