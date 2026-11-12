"""
Views de Métricas e Indicadores Consolidados
Especificação V1.0 - Seções 3.9 e 4.7
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Count, Sum, Q
from django.utils import timezone
from apps.catalog.models import ProductOffer, ProductStatus
from apps.publications.models import Publication, PublicationStatus
from .models import DailyMetricSnapshot
from .serializers import DailyMetricSnapshotSerializer


class AnalyticsOverviewView(APIView):
    """
    Retorna os indicadores operacionais consolidados e comparação com metas hipotéticas.
    GET /api/analytics/
    """

    def get(self, request):
        # 1. Contagens do Catálogo
        products_found = ProductOffer.objects.count()
        products_approved = ProductOffer.objects.filter(status=ProductStatus.APPROVED).count()
        products_rejected = ProductOffer.objects.filter(status=ProductStatus.REJECTED).count()
        products_pending = ProductOffer.objects.filter(status=ProductStatus.PENDING).count()
        
        # Links cadastrados
        links_registered = ProductOffer.objects.exclude(
            Q(affiliate_url__isnull=True) | Q(affiliate_url__exact='')
        ).count()

        # Ofertas publicadas
        offers_published = Publication.objects.filter(
            status=PublicationStatus.PUBLISHED
        ).count()

        # Cliques rastreados
        total_clicks = Publication.objects.aggregate(
            total=Sum('clicks_count')
        )['total'] or 0

        # Snapshot de métricas históricas
        recent_snapshots = DailyMetricSnapshot.objects.all()[:7]
        history_serializer = DailyMetricSnapshotSerializer(recent_snapshots, many=True)

        # Totais acumulados dos snapshots
        snapshot_aggregates = DailyMetricSnapshot.objects.aggregate(
            total_sales=Sum('sales'),
            total_estimated_comm=Sum('estimated_commission'),
            total_approved_comm=Sum('approved_commission'),
            total_history_clicks=Sum('clicks')
        )

        sales = snapshot_aggregates['total_sales'] or 0
        all_clicks = total_clicks + (snapshot_aggregates['total_history_clicks'] or 0)
        conversion_rate = round((sales / all_clicks * 100), 2) if all_clicks > 0 else 0.0

        estimated_comm = float(snapshot_aggregates['total_estimated_comm'] or 0.00)
        approved_comm = float(snapshot_aggregates['total_approved_comm'] or 0.00)

        # Distribuição por Categoria
        category_distribution = list(
            ProductOffer.objects.values('category').annotate(total=Count('id'))
        )

        # Metas Hipotéticas (Seção 3.9)
        targets = {
            "daily_offers": 5,
            "daily_clicks": 30,
            "target_conversion": 3.0,
            "daily_sales": 1,
            "average_commission": 8.00,
            "monthly_projection": 240.00,
            "future_targets": [300.00, 500.00, 1000.00, 2000.00]
        }

        return Response({
            "metrics": {
                "products_found": products_found,
                "products_approved": products_approved,
                "products_rejected": products_rejected,
                "products_pending": products_pending,
                "links_registered": links_registered,
                "offers_published": offers_published,
                "clicks": all_clicks,
                "sales": sales,
                "conversion_rate": conversion_rate,
                "estimated_commission": estimated_comm,
                "approved_commission": approved_comm,
            },
            "category_distribution": category_distribution,
            "illustrative_targets": targets,
            "recent_history": history_serializer.data,
            "timestamp": timezone.now().isoformat()
        })
