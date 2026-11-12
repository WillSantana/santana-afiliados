from django.contrib import admin
from .models import ProductOffer


@admin.register(ProductOffer)
class ProductOfferAdmin(admin.ModelAdmin):
    list_display = (
        'item_id',
        'title',
        'category',
        'price',
        'original_price',
        'score',
        'classification',
        'status',
        'discovered_at',
    )
    list_filter = ('category', 'status', 'classification', 'condition')
    search_fields = ('item_id', 'title', 'seller_id')
    readonly_fields = ('score', 'classification', 'discovered_at', 'updated_at', 'approved_at', 'published_at')
    ordering = ('-score', '-discovered_at')
