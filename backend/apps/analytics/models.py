"""
Modelos de Indicadores Comerciais e Histórico Diário
Especificação V1.0 - Seções 3.9 e 4.7
"""

from django.db import models


class DailyMetricSnapshot(models.Model):
    """
    Registro diário consolidado para acompanhamento de metas e evolução temporal.
    """
    date = models.DateField(unique=True, verbose_name="Data de referência")
    products_found = models.PositiveIntegerField(default=0)
    products_approved = models.PositiveIntegerField(default=0)
    products_rejected = models.PositiveIntegerField(default=0)
    links_registered = models.PositiveIntegerField(default=0)
    offers_published = models.PositiveIntegerField(default=0)
    clicks = models.PositiveIntegerField(default=0)
    sales = models.PositiveIntegerField(default=0)
    estimated_commission = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    approved_commission = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    class Meta:
        verbose_name = "Snapshot Diário de Métricas"
        verbose_name_plural = "Snapshots Diários de Métricas"
        ordering = ['-date']

    def __str__(self):
        return f"Métricas {self.date} - Vendas: {self.sales} | Comissões: R$ {self.approved_commission}"

    @property
    def conversion_rate(self):
        if self.clicks > 0:
            return round((self.sales / self.clicks) * 100, 2)
        return 0.0
