"""
Modelos de Publicações Promocionais
Especificação V1.0 - Seções 3.8, 4.4, 4.5
"""

from django.db import models
from django.utils import timezone
from apps.catalog.models import ProductOffer, ProductStatus


class PublicationStatus(models.TextChoices):
    PENDING_APPROVAL = 'pending_approval', 'Aguardando aprovação'
    APPROVED = 'approved', 'Aprovada para envio'
    PUBLISHED = 'published', 'Publicada no canal'
    CANCELLED = 'cancelled', 'Cancelada'


class Publication(models.Model):
    """
    Registro formal de mensagem promocional pronta para envio ou já enviada.
    """
    product = models.ForeignKey(
        ProductOffer,
        on_delete=models.CASCADE,
        related_name='publications',
        verbose_name="Produto associado"
    )
    title = models.CharField(
        max_length=120,
        default="OFERTA DO DIA!",
        verbose_name="Título da postagem"
    )
    message_text = models.TextField(
        verbose_name="Texto formatado para WhatsApp"
    )
    channel = models.CharField(
        max_length=32,
        default='whatsapp',
        verbose_name="Canal de divulgação"
    )
    status = models.CharField(
        max_length=32,
        choices=PublicationStatus.choices,
        default=PublicationStatus.PENDING_APPROVAL,
        verbose_name="Status da publicação"
    )
    clicks_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Total de cliques rastreados"
    )
    published_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Data de publicação efetiva"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data de criação"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Última atualização"
    )

    class Meta:
        verbose_name = "Publicação"
        verbose_name_plural = "Publicações"
        ordering = ['-created_at']

    def __str__(self):
        return f"Pub #{self.id} - {self.product.title[:40]} ({self.status})"

    @classmethod
    def generate_message_text(cls, product: ProductOffer, custom_benefit: str = None) -> str:
        """
        Gera o texto padronizado conforme modelo da Seção 3.8:
        ■ OFERTA DO DIA!
        ■ [NOME DO PRODUTO]
        [DESCRIÇÃO DO BENEFÍCIO]
        ■ Preço: R$ XX,XX
        ■ Consulte as condições de entrega.
        ■ Confira a oferta:
        [LINK DE AFILIADO]
        Publicidade: este é um link de afiliado e posso receber comissão se você comprar.
        """
        link = product.affiliate_url or product.direct_product_url
        benefit = custom_benefit or f"Uma ótima opção com excelente custo-benefício na categoria {product.get_category_display()}."
        
        msg = (
            f"■ OFERTA DO DIA!\n"
            f"■ {product.title}\n\n"
            f"{benefit}\n\n"
            f"■ Preço: R$ {product.price:.2f}\n"
            f"■ Consulte as condições de entrega.\n\n"
            f"■ Confira a oferta:\n"
            f"{link}\n\n"
            f"Publicidade: este é um link de afiliado e posso receber comissão se você comprar."
        )
        return msg

    def mark_as_published(self):
        self.status = PublicationStatus.PUBLISHED
        self.published_at = timezone.now()
        self.product.status = ProductStatus.PUBLISHED
        self.product.published_at = timezone.now()
        self.product.save(update_fields=['status', 'published_at', 'updated_at'])
        self.save(update_fields=['status', 'published_at', 'updated_at'])
