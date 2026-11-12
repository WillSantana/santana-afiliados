from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AffiliateLinkViewSet

router = DefaultRouter()
router.register(r'', AffiliateLinkViewSet, basename='affiliate-link')

urlpatterns = [
    path('', include(router.urls)),
]
