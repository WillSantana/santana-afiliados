"""
Cliente de comunicação com a API Oficial do Mercado Livre
Especificação V1.0 - Seções 3.5 e 4.2
"""

import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class MercadoLivreSearchError(Exception):
    status_code = 502


class MercadoLivreConfigurationError(MercadoLivreSearchError):
    status_code = 503


class MercadoLivreAuthorizationError(MercadoLivreSearchError):
    status_code = 503


class MercadoLivreAPIClient:
    """
    Cliente REST para consultas reais no Mercado Livre.
    """

    def __init__(self):
        self.base_url = getattr(settings, 'MERCADOLIVRE_API_URL', 'https://api.mercadolibre.com')
        self.site_id = getattr(settings, 'MERCADOLIVRE_SITE_ID', 'MLB')
        self.access_token = getattr(settings, 'MERCADOLIVRE_ACCESS_TOKEN', '')

    def _get_headers(self):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'application/json',
        }
        if self.access_token:
            headers['Authorization'] = f'Bearer {self.access_token}'
        return headers

    def _require_access_token(self):
        if not self.access_token:
            raise MercadoLivreConfigurationError(
                "A busca real exige um token OAuth do Mercado Livre. "
                "Configure MERCADOLIVRE_ACCESS_TOKEN no arquivo .env da raiz do projeto "
                "e reinicie o backend."
            )

    def search_items(self, query: str, limit: int = 50, sort: str = 'relevance'):
        """
        Executa pesquisa de anúncios no Mercado Livre.
        """
        self._require_access_token()

        url = f"{self.base_url}/sites/{self.site_id}/search"
        params = {
            'q': query,
            'limit': min(limit, 50),
            'sort': sort,
        }

        try:
            response = requests.get(
                url,
                headers=self._get_headers(),
                params=params,
                timeout=10
            )

            response.raise_for_status()
            data = response.json()
            results = data.get('results', [])
            for item in results:
                thumb = item.get('thumbnail', '')
                if thumb.startswith('http://'):
                    item['thumbnail'] = thumb.replace('http://', 'https://')
            return results
        except requests.HTTPError as e:
            response_status = e.response.status_code if e.response is not None else 'desconhecido'
            logger.error("API Mercado Livre retornou HTTP %s", response_status)
            if response_status == 401 or response_status == 403:
                raise MercadoLivreAuthorizationError(
                    "O Mercado Livre recusou a autorização da busca. Confira se o token OAuth "
                    "está válido e pertence ao aplicativo configurado."
                ) from e
            raise MercadoLivreSearchError(
                f"A API do Mercado Livre retornou HTTP {response_status}. "
                "A busca não foi concluída e nenhum produto de demonstração foi incluído."
            ) from e
        except requests.RequestException as e:
            logger.error(f"Falha de conexão com a API do Mercado Livre: {str(e)}")
            raise MercadoLivreSearchError(
                "Não foi possível conectar à API do Mercado Livre. "
                "Verifique sua conexão e tente novamente."
            ) from e

    def get_item_details(self, item_id: str):
        url = f"{self.base_url}/items/{item_id}"
        try:
            response = requests.get(url, headers=self._get_headers(), timeout=10)
            if response.status_code == 200:
                data = response.json()
                thumb = data.get('thumbnail', '')
                if thumb.startswith('http://'):
                    data['thumbnail'] = thumb.replace('http://', 'https://')
                return data
            return None
        except requests.RequestException as e:
            logger.error(f"Erro ao buscar detalhes do item {item_id}: {str(e)}")
            return None
