from unittest.mock import patch

import requests
from django.test import SimpleTestCase, override_settings
from rest_framework.test import APIRequestFactory

from .client import (
    MercadoLivreAPIClient,
    MercadoLivreAuthorizationError,
    MercadoLivreConfigurationError,
    MercadoLivreSearchError,
)
from .views import SearchRunView


class MercadoLivreAPIClientTests(SimpleTestCase):
    @override_settings(MERCADOLIVRE_ACCESS_TOKEN='test-token')
    def test_sends_configured_access_token_as_bearer(self):
        headers = MercadoLivreAPIClient()._get_headers()

        self.assertEqual(headers['Authorization'], 'Bearer test-token')

    @override_settings(MERCADOLIVRE_ACCESS_TOKEN='test-token')
    @patch('apps.integrations.mercadolivre.client.requests.get')
    def test_returns_the_permalink_from_the_api(self, mock_get):
        response = requests.Response()
        response.status_code = 200
        response._content = (
            b'{"results":[{"id":"MLB123456789","permalink":'
            b'"https://produto.mercadolivre.com.br/MLB-123456789"}]}'
        )
        mock_get.return_value = response

        items = MercadoLivreAPIClient().search_items('produto')

        self.assertEqual(
            items[0]['permalink'],
            'https://produto.mercadolivre.com.br/MLB-123456789',
        )

    @override_settings(MERCADOLIVRE_ACCESS_TOKEN='test-token')
    @patch('apps.integrations.mercadolivre.client.requests.get')
    def test_api_error_does_not_return_fake_fallback_items(self, mock_get):
        response = requests.Response()
        response.status_code = 403
        mock_get.return_value = response

        with self.assertRaises(MercadoLivreAuthorizationError):
            MercadoLivreAPIClient().search_items('produto')

    @override_settings(MERCADOLIVRE_ACCESS_TOKEN='')
    def test_search_without_token_explains_configuration_requirement(self):
        with self.assertRaises(MercadoLivreConfigurationError):
            MercadoLivreAPIClient().search_items('produto')

    @override_settings(MERCADOLIVRE_ACCESS_TOKEN='')
    def test_search_endpoint_explains_when_token_is_missing(self):
        request = APIRequestFactory().post(
            '/api/search/run/',
            {'category': 'technology', 'query': 'produto'},
            format='json',
        )

        response = SearchRunView.as_view()(request)

        self.assertEqual(response.status_code, 503)
        self.assertIn('token OAuth', response.data['message'])

    @override_settings(MERCADOLIVRE_ACCESS_TOKEN='test-token')
    @patch('apps.integrations.mercadolivre.views.ProductDiscoveryService.run_search_for_category')
    def test_search_endpoint_surfaces_api_failure(self, mock_search):
        mock_search.side_effect = MercadoLivreSearchError('API Mercado Livre indisponível.')
        request = APIRequestFactory().post(
            '/api/search/run/',
            {'category': 'technology', 'query': 'produto'},
            format='json',
        )

        response = SearchRunView.as_view()(request)

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.data['message'], 'API Mercado Livre indisponível.')
