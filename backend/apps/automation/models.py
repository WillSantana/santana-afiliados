"""
Modelos de Automação, Histórico e Alertas
Especificação V1.2 - Seções 9.2, 9.3, 9.4 e 10
"""

from django.db import models
from django.utils import timezone
from apps.catalog.models import ProductOffer


class SearchRunStatus(models.TextChoices):
    RUNNING = 'running', 'Em execução'
    COMPLETED = 'completed', 'Concluído com sucesso'
    FAILED = 'failed', 'Falha na execução'


class SearchRun(models.Model):
    """
    Histórico e auditoria de cada ciclo de pesquisa programada ou manual (Seção 9.2).
    """
    category = models.CharField(max_length=64, verbose_name="Categoria")
    search_term = models.CharField(max_length=128, verbose_name="Termo pesquisado")
    started_at = models.DateTimeField(default=timezone.now, verbose_name="Início")
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name="Fim")
    products_found = models.PositiveIntegerField(default=0, verbose_name="Produtos encontrados")
    products_created = models.PositiveIntegerField(default=0, verbose_name="Novos produtos criados")
    products_updated = models.PositiveIntegerField(default=0, verbose_name="Produtos atualizados")
    status = models.CharField(
        max_length=32,
        choices=SearchRunStatus.choices,
        default=SearchRunStatus.RUNNING,
        verbose_name="Status"
    )
    error_message = models.TextField(null=True, blank=True, verbose_name="Mensagem de erro")

    class Meta:
        verbose_name = "Ciclo de Pesquisa (SearchRun)"
        verbose_name_plural = "Ciclos de Pesquisa (SearchRuns)"
        ordering = ['-started_at']

    def __str__(self):
        return f"[{self.category}] '{self.search_term}' em {self.started_at.strftime('%d/%m/%Y %H:%M')} ({self.status})"

    @property
    def duration_seconds(self):
        if self.finished_at and self.started_at:
            return round((self.finished_at - self.started_at).total_seconds(), 2)
        return 0


class ProductPriceHistory(models.Model):
    """
    Histórico imutável de observações de preço para cada anúncio (Seção 9.3).
    """
    product = models.ForeignKey(
        ProductOffer,
        on_delete=models.CASCADE,
        related_name='price_history',
        verbose_name="Produto"
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Preço observado"
    )
    original_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Preço original/tabela"
    )
    recorded_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        verbose_name="Data/hora da observação"
    )
    source = models.CharField(
        max_length=128,
        default='mercadolivre_api_monitor',
        verbose_name="Origem do dado"
    )

    class Meta:
        verbose_name = "Histórico de Preço"
        verbose_name_plural = "Históricos de Preços"
        ordering = ['-recorded_at']

    def __str__(self):
        return f"{self.product.item_id} -> R$ {self.price} em {self.recorded_at.strftime('%d/%m/%Y %H:%M')}"


class PriceAlert(models.Model):
    """
    Alerta de variação significativa de preço (Seção 10).
    Ex: queda de 5% ou mais em produto aprovado/publicado.
    """
    product = models.ForeignKey(
        ProductOffer,
        on_delete=models.CASCADE,
        related_name='price_alerts',
        verbose_name="Produto"
    )
    old_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Preço anterior de referência"
    )
    new_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Novo preço observado"
    )
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="Percentual de redução"
    )
    is_acknowledged = models.BooleanField(
        default=False,
        verbose_name="Revisado pelo administrador"
    )
    requires_new_approval = models.BooleanField(
        default=True,
        verbose_name="Exige nova aprovação para publicar"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Criado em"
    )

    class Meta:
        verbose_name = "Alerta de Preço"
        verbose_name_plural = "Alertas de Preços"
        ordering = ['-created_at']

    def __str__(self):
        return f"Alerta {self.product.item_id}: -{self.discount_percentage}% (R$ {self.old_price} -> R$ {self.new_price})"


class AutomationConfig(models.Model):
    """
    Configuração administrativa do motor de automação (Seção 11 e 13).
    """
    searches_enabled = models.BooleanField(default=True, verbose_name="Pesquisas automáticas ativas")
    price_monitoring_enabled = models.BooleanField(default=True, verbose_name="Monitoramento de preços ativo")
    price_drop_threshold = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=5.00,
        verbose_name="Gatilho de alerta de queda de preço (%)"
    )
    preferential_price_max = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=200.00,
        verbose_name="Preço preferencial máximo (R$)"
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuração do Motor de Automação"
        verbose_name_plural = "Configurações do Motor de Automação"

    @classmethod
    def get_settings(cls):
        obj, _ = cls.objects.get_or_create(id=1)
        return obj
