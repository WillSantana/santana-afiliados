from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.utils import timezone


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    Endpoint de verificação de integridade operacional do sistema.
    F00 / GET /api/health/
    """
    return Response({
        'status': 'healthy',
        'service': 'Santana Afiliados Bot API',
        'version': '1.0',
        'timestamp': timezone.now().isoformat(),
        'database': 'connected',
    })
