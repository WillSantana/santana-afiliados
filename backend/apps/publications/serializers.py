from rest_framework import serializers
from .models import Publication, PublicationStatus
from apps.catalog.serializers import ProductOfferSerializer


class PublicationSerializer(serializers.ModelSerializer):
    product_details = ProductOfferSerializer(source='product', read_only=True)

    class Meta:
        model = Publication
        fields = [
            'id',
            'product',
            'product_details',
            'title',
            'message_text',
            'channel',
            'status',
            'clicks_count',
            'published_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'clicks_count', 'published_at', 'created_at', 'updated_at']


class GeneratePublicationSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(required=True)
    custom_benefit = serializers.CharField(required=False, allow_blank=True)
