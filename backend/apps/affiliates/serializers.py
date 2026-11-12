from rest_framework import serializers
from .models import AffiliateLink


class AffiliateLinkSerializer(serializers.ModelSerializer):
    product_title = serializers.CharField(source='product.title', read_only=True)
    product_item_id = serializers.CharField(source='product.item_id', read_only=True)

    class Meta:
        model = AffiliateLink
        fields = [
            'id',
            'product',
            'product_title',
            'product_item_id',
            'affiliate_url',
            'is_active',
            'clicks',
            'last_verified_at',
            'created_at',
        ]
        read_only_fields = ['id', 'clicks', 'last_verified_at', 'created_at']
