from rest_framework import viewsets
from .models import Campaign
from .serializers import CampaignSerializer


class CampaignViewSet(viewsets.ModelViewSet):
    """
    CRUD de Campanhas Promocionais.
    GET /api/campaigns/
    """
    queryset = Campaign.objects.all()
    serializer_class = CampaignSerializer
