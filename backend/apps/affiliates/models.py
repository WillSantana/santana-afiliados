"""
Modelos para Gestão de Links e Rastreamento de Afiliados
Especificação V1.0 - Seção 2.1 e 3.1 (F06, F10)
"""

from django.db import models
from apps.catalog.models import ProductOffer


class AffiliateLink(models.Model):
    """
    Associação formal de link de afiliado oficial a um anúncio do catálogo.
    """
    product = models.OneToOneField(
        ProductOffer,
        on_delete=models.CASCADE,
        related_name='affiliate_entry',
        verbose_name="Produto correspondente"
    )
    affiliate_url = models.URLField(
        max_length=1000,
        verbose_name="URL de Afiliado Oficial"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Link ativo e válido"
    )
    clicks = models.PositiveIntegerField(
        default=0,
        verbose_name="Cliques computados"
    )
    last_verified_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Última checagem de validade"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Criado em"
    )

    class Meta:
        verbose_name = "Link de Afiliado"
        verbose_name_plural = "Links de Afiliados"

    def __str__(self):
        return f"Link Afiliado: {self.product.item_id}"
