"""
Modelos de Campanhas
Especificação V1.0 - Seção 3.11 (GET /api/campaigns/)
"""

from django.db import models
from apps.catalog.models import ProductOffer


class Campaign(models.Model):
    name = models.CharField(max_length=150, verbose_name="Nome da campanha")
    description = models.TextField(blank=True, verbose_name="Descrição do objetivo")
    target_category = models.CharField(max_length=50, blank=True, verbose_name="Categoria alvo")
    is_active = models.BooleanField(default=True, verbose_name="Ativa")
    products = models.ManyToManyField(
        ProductOffer,
        blank=True,
        related_name='campaigns',
        verbose_name="Produtos participantes"
    )
    start_date = models.DateField(null=True, blank=True, verbose_name="Data inicial")
    end_date = models.DateField(null=True, blank=True, verbose_name="Data final")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Campanha"
        verbose_name_plural = "Campanhas"
        ordering = ['-created_at']

    def __str__(self):
        return self.name
