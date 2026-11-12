from django.urls import path
from .views import SearchRunView

urlpatterns = [
    path('run/', SearchRunView.as_view(), name='search_run'),
]
