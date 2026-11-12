"""
Views do Catálogo de Produtos
Especificação V1.0 - Seções 3.1, 3.7 e 3.11
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from .models import ProductOffer, ProductStatus
from .serializers import (
    ProductOfferSerializer,
    AffiliateLinkUpdateSerializer,
    RejectionSerializer
)


class ProductOfferViewSet(viewsets.ModelViewSet):
    """
    CRUD completo e ações de aprovação, rejeição e associação de link de afiliado.
    Endpoints:
    - GET /api/products/
    - POST /api/products/
    - GET /api/products/{id}/
    - PATCH /api/products/{id}/
    - POST /api/products/{id}/approve/
    - POST /api/products/{id}/reject/
    - POST /api/products/{id}/affiliate-link/
    """
    queryset = ProductOffer.objects.all()
    serializer_class = ProductOfferSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtros
        category = self.request.query_params.get('category')
        product_status = self.request.query_params.get('status')
        min_score = self.request.query_params.get('min_score')
        search_query = self.request.query_params.get('q')

        if category:
            queryset = queryset.filter(category=category)
        if product_status:
            queryset = queryset.filter(status=product_status)
        if min_score:
            try:
                queryset = queryset.filter(score__gte=int(min_score))
            except ValueError:
                pass
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(item_id__icontains=search_query)
            )

        invalid_product_ids = [
            product_id
            for product_id, item_id, product_url in queryset.values_list('id', 'item_id', 'product_url')
            if not ProductOffer.is_valid_listing_permalink(product_url, item_id)
        ]
        if invalid_product_ids:
            queryset = queryset.exclude(id__in=invalid_product_ids)

        return queryset

    def perform_create(self, serializer):
        product = serializer.save()
        product.calculate_score()
        product.save()

    def perform_update(self, serializer):
        product = serializer.save()
        product.calculate_score()
        product.save()

    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None):
        """
        Aprova manualmente a oferta.
        POST /api/products/{id}/approve/
        """
        product = self.get_object()
        product.approve()
        serializer = self.get_serializer(product)
        return Response({
            'message': 'Oferta aprovada com sucesso.',
            'product': serializer.data
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, pk=None):
        """
        Rejeita a oferta com justificativa opcional.
        POST /api/products/{id}/reject/
        """
        product = self.get_object()
        serializer_input = RejectionSerializer(data=request.data)
        serializer_input.is_valid(raise_exception=True)
        reason = serializer_input.validated_data.get('reason', '')
        
        product.reject(reason=reason)
        serializer = self.get_serializer(product)
        return Response({
            'message': 'Oferta rejeitada com sucesso.',
            'product': serializer.data
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='affiliate-link')
    def affiliate_link(self, request, pk=None):
        """
        Associa o link oficial de afiliado e recalcula o score da oferta.
        POST /api/products/{id}/affiliate-link/
        """
        product = self.get_object()
        serializer_input = AffiliateLinkUpdateSerializer(data=request.data)
        serializer_input.is_valid(raise_exception=True)
        affiliate_url = serializer_input.validated_data['affiliate_url']

        product.set_affiliate_link(affiliate_url)
        serializer = self.get_serializer(product)
        return Response({
            'message': 'Link de afiliado associado com sucesso.',
            'product': serializer.data
        }, status=status.HTTP_200_OK)
