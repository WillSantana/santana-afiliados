"""
Modelo de dados ProductOffer
Especificação V1.0 - Seções 3.6 e 3.7
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from urllib.parse import urlsplit
import re


class CategoryChoices(models.TextChoices):
    TECHNOLOGY = 'technology', 'Tecnologia e games'
    FASHION = 'fashion', 'Moda masculina'
    HOME = 'home', 'Casa e utilidades'
    BEAUTY = 'beauty', 'Beleza e cuidados pessoais'


class ProductStatus(models.TextChoices):
    PENDING = 'pending', 'Aguardando aprovação'
    APPROVED = 'approved', 'Aprovado pelo administrador'
    REJECTED = 'rejected', 'Rejeitado pelo administrador'
    PUBLISHED = 'published', 'Publicação realizada'


class ProductOffer(models.Model):
    """
    Entidade central de oportunidade comercial do Santana Afiliados Bot.
    """
    item_id = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        verbose_name="Identificador único (MLB)"
    )
    title = models.CharField(
        max_length=255,
        verbose_name="Nome do produto"
    )
    category = models.CharField(
        max_length=32,
        choices=CategoryChoices.choices,
        default=CategoryChoices.TECHNOLOGY,
        verbose_name="Categoria"
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Preço atual"
    )
    original_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Preço original/anterior"
    )
    product_url = models.URLField(
        max_length=1000,
        verbose_name="URL original do produto"
    )
    affiliate_url = models.URLField(
        max_length=1000,
        null=True,
        blank=True,
        verbose_name="URL oficial de afiliado"
    )
    thumbnail = models.URLField(
        max_length=1000,
        null=True,
        blank=True,
        verbose_name="URL da imagem (thumbnail)"
    )
    seller_id = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        verbose_name="Identificador do vendedor"
    )
    seller_reputation = models.CharField(
        max_length=64,
        default='unknown',
        verbose_name="Reputação do vendedor"
    )
    condition = models.CharField(
        max_length=32,
        default='new',
        verbose_name="Condição do produto"
    )
    score = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="Pontuação de oportunidade (0-100)"
    )
    classification = models.CharField(
        max_length=64,
        default='pending',
        verbose_name="Classificação comercial"
    )
    status = models.CharField(
        max_length=32,
        choices=ProductStatus.choices,
        default=ProductStatus.PENDING,
        db_index=True,
        verbose_name="Estado do produto"
    )
    
    # Histórico e auditoria
    rejection_reason = models.TextField(
        null=True,
        blank=True,
        verbose_name="Motivo da rejeição"
    )
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Data de aprovação"
    )
    published_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Data de publicação"
    )
    discovered_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data de descoberta"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Última atualização"
    )

    class Meta:
        verbose_name = "Oferta de Produto"
        verbose_name_plural = "Ofertas de Produtos"
        ordering = ['-score', '-discovered_at']

    def __str__(self):
        return f"{self.item_id} - {self.title[:50]} (R$ {self.price})"

    @staticmethod
    def is_valid_listing_permalink(product_url, item_id=None):
        try:
            parsed_url = urlsplit(product_url)
        except ValueError:
            return False

        hostname = (parsed_url.hostname or '').lower()
        if parsed_url.scheme != 'https' or not (
            hostname == 'mercadolivre.com.br'
            or hostname.endswith('.mercadolivre.com.br')
        ):
            return False
        if hostname.startswith('lista.') or 'as_word' in parsed_url.query.lower():
            return False
        if re.search(r'/jm/search(?:/|$)', parsed_url.path, re.IGNORECASE):
            return False
        catalog_match = re.fullmatch(r'/p/MLB-?(\d+)/?', parsed_url.path, re.IGNORECASE)
        if catalog_match and item_id and catalog_match.group(1) == item_id[3:]:
            return False
        return bool(parsed_url.path.strip('/'))

    @property
    def direct_product_url(self):
        return self.product_url

    @property
    def discount_percentage(self):
        """Calcula percentual de desconto se original_price existir e for maior que price."""
        if self.original_price and self.original_price > self.price:
            diff = self.original_price - self.price
            return round((diff / self.original_price) * 100, 1)
        return 0

    @property
    def missing_information(self):
        """Lista campos essenciais ainda pendentes."""
        missing = []
        if not self.affiliate_url:
            missing.append("affiliate_url")
        if self.seller_reputation == "unknown":
            missing.append("seller_reputation")
        return missing

    def calculate_score(self):
        """
        Calcula pontuação de oportunidade de acordo com a Seção 3.3 da especificação:
        - Preço dentro do orçamento (até R$ 200): 20 pts
        - Reputação do vendedor (verde): 20 pts
        - Produto novo e ativo: 15 pts
        - Competitividade do preço (desconto verificável): até 20 pts
        - Comissão cadastrada e confirmada: 15 pts
        - Atratividade comercial (título, foto, relevância): 10 pts
        Total máx: 100 pts.
        """
        calculated_score = 0

        # 1. Preço dentro do orçamento (até R$ 200 preferencial)
        if self.price <= 200:
            calculated_score += 20
        elif self.price <= 350:
            calculated_score += 10

        # 2. Reputação do vendedor
        if self.seller_reputation in ['green', 'platinum', 'gold']:
            calculated_score += 20
        elif self.seller_reputation == 'silver':
            calculated_score += 10

        # 3. Produto novo e ativo
        if self.condition == 'new':
            calculated_score += 15

        # 4. Competitividade do preço (desconto real verificado)
        discount = self.discount_percentage
        if discount >= 20:
            calculated_score += 20
        elif discount >= 10:
            calculated_score += 15
        elif discount > 0:
            calculated_score += 10

        # 5. Comissão cadastrada e confirmada
        if self.affiliate_url:
            calculated_score += 15

        # 6. Atratividade comercial (presença de foto, thumbnail e dados essenciais)
        if self.thumbnail and len(self.title) > 10:
            calculated_score += 10

        self.score = min(calculated_score, 100)

        # Atualiza a classificação textual conforme faixas da Seção 3.3
        if self.score >= 85:
            self.classification = "excellent"
        elif self.score >= 70:
            self.classification = "good"
        elif self.score >= 50:
            self.classification = "moderate"
        else:
            self.classification = "low"

        return self.score

    def approve(self):
        """Aprova a oferta para preparação de publicação."""
        self.status = ProductStatus.APPROVED
        self.approved_at = timezone.now()
        self.rejection_reason = None
        self.save(update_fields=['status', 'approved_at', 'rejection_reason', 'updated_at'])

    def reject(self, reason=""):
        """Rejeita a oferta pelo administrador."""
        self.status = ProductStatus.REJECTED
        self.rejection_reason = reason
        self.save(update_fields=['status', 'rejection_reason', 'updated_at'])

    def set_affiliate_link(self, affiliate_url):
        """Associa link de afiliado oficial e recalcula a pontuação."""
        self.affiliate_url = affiliate_url
        self.calculate_score()
        self.save(update_fields=['affiliate_url', 'score', 'classification', 'updated_at'])
