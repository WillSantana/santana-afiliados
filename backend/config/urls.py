"""
URL configuration for Santana Afiliados Bot.
Especificação V1.2 - Seção 14
"""

from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import health_check

urlpatterns = [
    path('admin/', admin.site.urls),

    # Autenticação JWT
    path('api/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Health Check
    path('api/health/', health_check, name='health_check'),

    # Endpoints do Catálogo e Produtos
    path('api/products/', include('apps.catalog.urls')),

    # Execução de Busca no Mercado Livre
    path('api/search/', include('apps.integrations.mercadolivre.urls')),

    # Motor de Automação, Histórico de Pesquisas e Monitoramento de Preços (V1.2)
    path('api/automation/', include('apps.automation.urls')),

    # Campanhas
    path('api/campaigns/', include('apps.campaigns.urls')),

    # Publicações
    path('api/publications/', include('apps.publications.urls')),

    # Analytics e Indicadores
    path('api/analytics/', include('apps.analytics.urls')),

    # Gestão de Afiliados
    path('api/affiliates/', include('apps.affiliates.urls')),
]
