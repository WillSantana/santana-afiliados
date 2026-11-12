"""
Serializers para o Motor de Automação
Especificação V1.2 - Seções 9.2, 9.3, 10 e 14
"""

from rest_framework import serializers
from .models import SearchRun, ProductPriceHistory, PriceAlert, AutomationConfig


class SearchRunSerializer(serializers.ModelSerializer):
    duration_seconds = serializers.ReadOnlyField()

    class Meta:
        model = SearchRun
        fields = '__all__'


class ProductPriceHistorySerializer(serializers.ModelSerializer):
    product_title = serializers.CharField(source='product.title', read_only=True)
    product_item_id = serializers.CharField(source='product.item_id', read_only=True)

    class Meta:
        model = ProductPriceHistory
        fields = [
            'id',
            'product',
            'product_title',
            'product_item_id',
            'price',
            'original_price',
            'recorded_at',
            'source',
        ]


class PriceAlertSerializer(serializers.ModelSerializer):
    product_title = serializers.CharField(source='product.title', read_only=True)
    product_item_id = serializers.CharField(source='product.item_id', read_only=True)
    thumbnail = serializers.CharField(source='product.thumbnail', read_only=True)

    class Meta:
        model = PriceAlert
        fields = [
            'id',
            'product',
            'product_title',
            'product_item_id',
            'thumbnail',
            'old_price',
            'new_price',
            'discount_percentage',
            'is_acknowledged',
            'requires_new_approval',
            'created_at',
        ]


class AutomationConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutomationConfig
        fields = '__all__'
