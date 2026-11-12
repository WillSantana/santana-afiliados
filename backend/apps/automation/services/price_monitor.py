"""
Serviço de Monitoramento de Preços e Alertas de Queda
Especificação V1.2 - Seções 3.1-B, 9.3, 10
"""

import logging
from decimal import Decimal
from django.utils import timezone
from apps.catalog.models import ProductOffer, ProductStatus
from apps.integrations.mercadolivre.client import MercadoLivreAPIClient
from apps.automation.models import ProductPriceHistory, PriceAlert, AutomationConfig

logger = logging.getLogger(__name__)


class PriceMonitorService:
    """
    Monitora periodicamente anúncios prioritários (aprovados, com link ou publicados),
    registra histórico imutável e dispara alertas de queda de preço >= threshold.
    """

    def __init__(self):
        self.client = MercadoLivreAPIClient()

    def get_priority_products(self, limit: int = 50):
        """
        Retorna os produtos prioritários para checagem:
        1. Aprovados ou Publicados
        2. Com link de afiliado
        3. Com score elevado
        """
        return ProductOffer.objects.filter(
            status__in=[ProductStatus.APPROVED, ProductStatus.PUBLISHED, ProductStatus.PENDING]
        ).order_by('-score', '-updated_at')[:limit]

    def check_product_price(self, product: ProductOffer, threshold_percent: Decimal = None):
        """
        Consulta o anúncio na API, compara preços, registra histórico e emite alertas.
        """
        if threshold_percent is None:
            config = AutomationConfig.get_settings()
            threshold_percent = config.price_drop_threshold

        item_data = self.client.get_item_details(product.item_id)
        if not item_data:
            logger.warning(f"[PriceMonitor] Não foi possível consultar detalhes de {product.item_id}")
            return None

        new_price_float = item_data.get('price')
        if new_price_float is None:
            return None

        new_price = Decimal(str(new_price_float))
        old_price = product.price

        # 1. Registra observação no histórico imutável (Seção 9.3)
        history_entry = ProductPriceHistory.objects.create(
            product=product,
            price=new_price,
            original_price=Decimal(str(item_data.get('original_price'))) if item_data.get('original_price') else product.original_price,
            recorded_at=timezone.now(),
            source='mercadolivre_api_monitor'
        )

        alert_created = None

        # 2. Verifica se houve alteração de preço
        if new_price != old_price:
            product.price = new_price
            if item_data.get('original_price'):
                product.original_price = Decimal(str(item_data.get('original_price')))

            # 3. Verifica queda percentual
            if old_price > 0 and new_price < old_price:
                drop_amount = old_price - new_price
                drop_percentage = (drop_amount / old_price) * 100

                if drop_percentage >= threshold_percent:
                    logger.info(
                        f"[PriceMonitor] 🚨 ALERTA: Queda de {drop_percentage:.1f}% detectada para {product.item_id} "
                        f"(R$ {old_price} -> R$ {new_price})"
                    )
                    # Cria alerta sem republicar automaticamente (Regra mandatória Seção 10)
                    alert_created = PriceAlert.objects.create(
                        product=product,
                        old_price=old_price,
                        new_price=new_price,
                        discount_percentage=round(drop_percentage, 2),
                        requires_new_approval=True
                    )

            # Recalcula a pontuação
            product.calculate_score()
            product.save()

        return {
            "product_id": product.item_id,
            "old_price": float(old_price),
            "new_price": float(new_price),
            "alert_created": alert_created is not None,
            "history_id": history_entry.id
        }

    def run_monitoring_cycle(self, limit: int = 40):
        """
        Executa uma rodada completa de monitoramento sobre os anúncios prioritários.
        """
        config = AutomationConfig.get_settings()
        if not config.price_monitoring_enabled:
            logger.info("[PriceMonitor] Monitoramento de preços está pausado.")
            return {"status": "skipped", "reason": "price_monitoring_disabled"}

        priority_products = self.get_priority_products(limit=limit)
        results = []

        logger.info(f"[PriceMonitor] Iniciando ciclo de monitoramento para {priority_products.count()} anúncios...")

        for prod in priority_products:
            res = self.check_product_price(prod, threshold_percent=config.price_drop_threshold)
            if res:
                results.append(res)

        return {
            "checked_count": len(results),
            "alerts_count": sum(1 for r in results if r.get('alert_created')),
            "results": results
        }
