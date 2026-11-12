from django.test import SimpleTestCase, TestCase
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from .models import ProductOffer
from .serializers import ProductOfferSerializer
from .views import ProductOfferViewSet


class ProductOfferUrlTests(SimpleTestCase):
    def test_serializer_preserves_the_api_permalink(self):
        product = ProductOffer(
            item_id='MLB3401928374',
            title='Mouse gamer',
            price='69.90',
            product_url='https://produto.mercadolivre.com.br/MLB-3401928374#origin=share',
        )

        self.assertEqual(
            ProductOfferSerializer(product).data['product_url'],
            'https://produto.mercadolivre.com.br/MLB-3401928374#origin=share',
        )

    def test_rejects_search_and_catalog_urls(self):
        self.assertFalse(
            ProductOffer.is_valid_listing_permalink('https://lista.mercadolivre.com.br/fone')
        )
        self.assertFalse(
            ProductOffer.is_valid_listing_permalink(
                'https://www.mercadolivre.com.br/p/MLB123456',
                'MLB123456',
            )
        )

    def test_accepts_direct_listing_permalink(self):
        self.assertTrue(
            ProductOffer.is_valid_listing_permalink(
                'https://produto.mercadolivre.com.br/MLB-123456789'
            )
        )


class ProductCatalogListingTests(TestCase):
    def test_catalog_hides_fake_search_and_generated_links(self):
        ProductOffer.objects.create(
            item_id='MLB111111111',
            title='Demonstração com link inventado',
            price='10.00',
            product_url='https://www.mercadolivre.com.br/p/MLB111111111',
        )
        ProductOffer.objects.create(
            item_id='MLB222222222',
            title='Demonstração com link de busca',
            price='10.00',
            product_url='https://lista.mercadolivre.com.br/produto',
        )
        ProductOffer.objects.create(
            item_id='MLB333333333',
            title='Anúncio encontrado pela API',
            price='10.00',
            product_url='https://produto.mercadolivre.com.br/MLB-333333333',
        )

        view = ProductOfferViewSet()
        view.request = Request(APIRequestFactory().get('/api/products/'))

        self.assertEqual(
            list(view.get_queryset().values_list('item_id', flat=True)),
            ['MLB333333333'],
        )
