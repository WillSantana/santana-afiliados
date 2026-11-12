from rest_framework import serializers
from .models import Campaign
from apps.catalog.serializers import ProductOfferSerializer


class CampaignSerializer(serializers.ModelSerializer):
    products_count = serializers.IntegerField(source='products.count', read_only=True)

    class Meta:
        model = Campaign
        fields = [
            'id',
            'name',
            'description',
            'target_category',
            'is_active',
            'products_count',
            'start_date',
            'end_date',
            'created_at',
        ]
