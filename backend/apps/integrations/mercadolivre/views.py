"""
Views para execução de busca e ingestão de dados
Especificação V1.0 - Seção 3.11 (POST /api/search/run/)
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services import ProductDiscoveryService
from .client import MercadoLivreAPIClient, MercadoLivreSearchError
from .tasks import search_all_categories_task


class SearchRunView(APIView):
    """
    Executa busca de anúncios no Mercado Livre.
    POST /api/search/run/
    Payload opcional:
    {
        "category": "technology",
        "query": "fone bluetooth",
        "limit": 20,
        "async": false
    }
    """

    def post(self, request):
        client = MercadoLivreAPIClient()
        try:
            client._require_access_token()
        except MercadoLivreSearchError as e:
            return Response({'message': str(e)}, status=e.status_code)

        category = request.data.get('category')
        query = request.data.get('query')
        limit = int(request.data.get('limit', 20))
        run_async = request.data.get('async', False)

        if run_async:
            search_all_categories_task.delay()
            return Response({
                'message': 'Busca agendada em segundo plano com sucesso via Celery.',
                'status': 'queued'
            }, status=status.HTTP_202_ACCEPTED)

        service = ProductDiscoveryService()
        try:
            if category:
                results = service.run_search_for_category(category_key=category, custom_query=query, limit=limit)
            elif query:
                results = service.run_search_for_category(category_key='technology', custom_query=query, limit=limit)
            else:
                results = service.run_all_categories(limit_per_term=limit)
        except MercadoLivreSearchError as e:
            return Response({'message': str(e)}, status=e.status_code)

        return Response({
            'message': 'Busca concluída com sucesso.',
            'results': results
        }, status=status.HTTP_200_OK)
