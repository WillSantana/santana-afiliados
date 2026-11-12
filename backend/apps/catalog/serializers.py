"""
Serializers para o modelo ProductOffer
Especificação V1.0 - Seção 4.6 (Formato JSON de saída)
"""

from rest_framework import serializers
from .models import ProductOffer, ProductStatus


class ProductOfferSerializer(serializers.ModelSerializer):
    """
    Serializer padrão com suporte integral ao formato de saída da Seção 4.6.
    """
    product_id = serializers.CharField(source='item_id', read_only=True)
    discount_percentage = serializers.ReadOnlyField()
    missing_information = serializers.ReadOnlyField()
    approval_required = serializers.SerializerMethodField()
    publication_allowed = serializers.SerializerMethodField()

    class Meta:
        model = ProductOffer
        fields = [
            'id',
            'product_id',
            'item_id',
            'title',
            'category',
            'price',
            'original_price',
            'discount_percentage',
            'product_url',
            'affiliate_url',
            'thumbnail',
            'seller_id',
            'seller_reputation',
            'condition',
            'score',
            'classification',
            'status',
            'rejection_reason',
            'approval_required',
            'publication_allowed',
            'missing_information',
            'approved_at',
            'published_at',
            'discovered_at',
            'updated_at',
        ]
        read_only_fields = [
            'id', 'product_id', 'score', 'classification',
            'approved_at', 'published_at', 'discovered_at', 'updated_at'
        ]

    def get_approval_required(self, obj):
        # Requer aprovação se estiver pendente
        return obj.status == ProductStatus.PENDING

    def get_publication_allowed(self, obj):
        # Só é permitido publicar se estiver aprovado E tiver link de afiliado válido
        return obj.status == ProductStatus.APPROVED and bool(obj.affiliate_url)


class AffiliateLinkUpdateSerializer(serializers.Serializer):
    affiliate_url = serializers.URLField(required=True)


class RejectionSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default='')
