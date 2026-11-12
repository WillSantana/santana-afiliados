"""
Views REST do Motor de Automação
Especificação V1.2 - Seção 14
"""

from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from apps.catalog.models import ProductOffer
from .models import SearchRun, ProductPriceHistory, PriceAlert, AutomationConfig
from .serializers import (
    SearchRunSerializer,
    ProductPriceHistorySerializer,
    PriceAlertSerializer,
    AutomationConfigSerializer,
)
from .services.search_runner import SearchRunnerService
from .services.price_monitor import PriceMonitorService


class SearchRunViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/search/runs/
    Consulta histórico de execuções de pesquisa programadas e manuais.
    """
    queryset = SearchRun.objects.all()
    serializer_class = SearchRunSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        category = self.request.query_params.get('category')
        run_status = self.request.query_params.get('status')
        if category:
            queryset = queryset.filter(category=category)
        if run_status:
            queryset = queryset.filter(status=run_status)
        return queryset


class ProductPriceHistoryView(APIView):
    """
    GET /api/products/{id}/price-history/
    Retorna a linha do tempo imutável de observações de preço de um produto.
    """

    def get(self, request, product_id):
        product = get_object_or_404(ProductOffer, pk=product_id)
        history = ProductPriceHistory.objects.filter(product=product).order_by('-recorded_at')
        serializer = ProductPriceHistorySerializer(history, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PriceAlertViewSet(viewsets.ModelViewSet):
    """
    GET /api/alerts/
    Gerenciamento de alertas de redução expressiva de preço (>= 5%).
    """
    queryset = PriceAlert.objects.all()
    serializer_class = PriceAlertSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        acknowledged = self.request.query_params.get('is_acknowledged')
        if acknowledged is not None:
            val = acknowledged.lower() in ('true', '1')
            queryset = queryset.filter(is_acknowledged=val)
        return queryset

    @action(detail=True, methods=['post'], url_path='acknowledge')
    def acknowledge(self, request, pk=None):
        """
        Marca o alerta como revisado pelo administrador.
        """
        alert = self.get_object()
        alert.is_acknowledged = True
        alert.save(update_fields=['is_acknowledged'])
        return Response({
            'message': 'Alerta marcado como revisado.',
            'alert': PriceAlertSerializer(alert).data
        })


class AutomationConfigView(APIView):
    """
    GET /api/automation/config/
    PATCH /api/automation/config/
    Permite visualizar e ajustar controles do motor de automação.
    """

    def get(self, request):
        config = AutomationConfig.get_settings()
        return Response(AutomationConfigSerializer(config).data)

    def patch(self, request):
        config = AutomationConfig.get_settings()
        serializer = AutomationConfigSerializer(config, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class TriggerSearchCycleView(APIView):
    """
    POST /api/automation/run-search/
    Dispara imediatamente um ciclo de busca rotativo das 4 categorias.
    """

    def post(self, request):
        cycle_index = int(request.data.get('cycle_index', 0))
        runner = SearchRunnerService()
        result = runner.run_scheduled_cycle(cycle_index=cycle_index)
        return Response(result, status=status.HTTP_200_OK)


class TriggerPriceMonitoringView(APIView):
    """
    POST /api/automation/run-monitor/
    Dispara imediatamente o ciclo de checagem e monitoramento de preços.
    """

    def post(self, request):
        limit = int(request.data.get('limit', 40))
        monitor = PriceMonitorService()
        result = monitor.run_monitoring_cycle(limit=limit)
        return Response(result, status=status.HTTP_200_OK)
