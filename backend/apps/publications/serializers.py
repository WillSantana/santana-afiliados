from rest_framework import serializers
from .models import Publication, PublicationStatus, PublicationDelivery
from .models import IncomingAffiliateOffer
from apps.catalog.serializers import ProductOfferSerializer


class PublicationDeliverySerializer(serializers.ModelSerializer):
    product_title = serializers.SerializerMethodField()

    class Meta:
        model = PublicationDelivery
        fields = [
            'id',
            'publication',
            'incoming_offer',
            'product_title',
            'target_group_name',
            'target_group_jid',
            'affiliate_url',
            'status',
            'error_message',
            'sent_at',
            'created_at',
        ]

    def get_product_title(self, delivery):
        if delivery.publication and delivery.publication.product:
            return delivery.publication.product.title
        if delivery.incoming_offer and delivery.incoming_offer.product:
            return delivery.incoming_offer.product.title
        return 'Oferta'


class PublicationSerializer(serializers.ModelSerializer):
    product_details = ProductOfferSerializer(source='product', read_only=True)
    deliveries = PublicationDeliverySerializer(many=True, read_only=True)

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
            'deliveries',
            'published_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'clicks_count', 'published_at', 'created_at', 'updated_at']


class GeneratePublicationSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(required=True)
    custom_benefit = serializers.CharField(required=False, allow_blank=True)


class IncomingAffiliateOfferSerializer(serializers.ModelSerializer):
    product_title = serializers.SerializerMethodField()
    product_price = serializers.SerializerMethodField()
    product_original_price = serializers.SerializerMethodField()
    product_url = serializers.SerializerMethodField()
    affiliate_url = serializers.SerializerMethodField()
    deliveries_count = serializers.SerializerMethodField()
    deliveries_success_count = serializers.SerializerMethodField()

    class Meta:
        model = IncomingAffiliateOffer
        fields = [
            'id',
            'source_link',
            'source_group',
            'original_message',
            'coupon',
            'status',
            'product_title',
            'product_price',
            'product_original_price',
            'product_url',
            'affiliate_url',
            'error_message',
            'deliveries_count',
            'deliveries_success_count',
            'received_at',
            'processed_at',
            'published_at',
        ]

    def get_product_title(self, offer):
        return offer.product.title if offer.product_id else ''

    def get_product_price(self, offer):
        return str(offer.product.price) if offer.product_id and offer.product.price else None

    def get_product_original_price(self, offer):
        return str(offer.product.original_price) if offer.product_id and offer.product.original_price else None

    def get_product_url(self, offer):
        return offer.product.product_url if offer.product_id else ''

    def get_affiliate_url(self, offer):
        if offer.affiliate_url:
            return offer.affiliate_url
        return offer.product.affiliate_url if offer.product_id else ''

    def get_deliveries_count(self, offer):
        return offer.deliveries.count()

    def get_deliveries_success_count(self, offer):
        return offer.deliveries.filter(status='success').count()

