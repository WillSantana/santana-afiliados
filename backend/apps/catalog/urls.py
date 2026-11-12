from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductOfferViewSet

router = DefaultRouter()
router.register(r'', ProductOfferViewSet, basename='product')

urlpatterns = [
    path('', include(router.urls)),
]
