from rest_framework import viewsets
from .models import AffiliateLink
from .serializers import AffiliateLinkSerializer


class AffiliateLinkViewSet(viewsets.ModelViewSet):
    queryset = AffiliateLink.objects.all()
    serializer_class = AffiliateLinkSerializer
