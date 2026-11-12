from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SearchRunViewSet,
    ProductPriceHistoryView,
    PriceAlertViewSet,
    AutomationConfigView,
    TriggerSearchCycleView,
    TriggerPriceMonitoringView,
)

router = DefaultRouter()
router.register(r'runs', SearchRunViewSet, basename='search-run')
router.register(r'alerts', PriceAlertViewSet, basename='price-alert')

urlpatterns = [
    path('config/', AutomationConfigView.as_view(), name='automation_config'),
    path('run-search/', TriggerSearchCycleView.as_view(), name='trigger_search_cycle'),
    path('run-monitor/', TriggerPriceMonitoringView.as_view(), name='trigger_price_monitoring'),
    path('products/<int:product_id>/price-history/', ProductPriceHistoryView.as_view(), name='product_price_history'),
    path('', include(router.urls)),
]
