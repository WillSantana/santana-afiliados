from datetime import timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIRequestFactory

from .affiliate_watcher import (
    AffiliateAutomationError,
    build_incoming_offer_message,
    extract_coupon,
    extract_short_links,
    mark_stale_processing_as_uncertain,
    open_automation_browser,
    record_new_offers,
    record_startup_baseline,
)
from .models import (
    IncomingAffiliateOffer,
    IncomingOfferStatus,
    WhatsAppGroup,
    WhatsAppGroupConfiguration,
    WhatsAppGroupRole,
)
from .product_urls import extract_item_id, is_marketplace_url, parse_brl_price
from .services import WhatsAppDispatcherService
from .views import PublicationViewSet


class IncomingOfferParsingTests(SimpleTestCase):
    def test_extracts_only_https_meli_short_links(self):
        links = extract_short_links(
            'Oferta https://meli.la/AbC123 e https://example.com/AbC123 '
            'http://meli.la/not-secure https://meli.la/AbC123.'
        )

        self.assertEqual(links, {'https://meli.la/AbC123'})

    def test_coupon_is_only_kept_when_unambiguous(self):
        self.assertEqual(extract_coupon('Use o cupom OFERTA123'), 'OFERTA123')
        self.assertEqual(extract_coupon('Cupom: ABC123 ou Cupom: XYZ789'), '')

    def test_product_helpers_accept_only_direct_marketplace_urls(self):
        url = 'https://produto.mercadolivre.com.br/MLB-1234567890-item'

        self.assertEqual(extract_item_id(url), 'MLB1234567890')
        self.assertTrue(is_marketplace_url(url))
        self.assertFalse(is_marketplace_url('https://example.com/MLB-1234567890'))
        self.assertEqual(parse_brl_price('R$ 1.299,90'), Decimal('1299.90'))

    def test_auto_post_message_uses_verified_offer_data_and_disclosure(self):
        message = build_incoming_offer_message(
            {
                'title': 'Fone Bluetooth',
                'price': 129.90,
                'original_price': 199.90,
            },
            'OFERTA20',
            'https://meli.la/AbC123',
        )

        self.assertIn('Fone Bluetooth', message)
        self.assertIn('De R$ 199,90', message)
        self.assertIn('Por R$ 129,90', message)
        self.assertIn('Cupom: OFERTA20', message)
        self.assertIn('posso receber comissão', message)

    @override_settings(AFFILIATE_BOT_CHROME_DEBUGGER_ADDRESS='0.0.0.0:9222')
    def test_debugger_must_not_bind_to_network_interfaces(self):
        with self.assertRaisesMessage(AffiliateAutomationError, 'host local'):
            open_automation_browser()


class EvolutionDestinationTests(SimpleTestCase):
    @override_settings(
        WHATSAPP_API_ENABLED=True,
        WHATSAPP_API_URL='http://localhost:8080/message/sendMedia/santana',
        WHATSAPP_API_TOKEN='test-token',
        WHATSAPP_GROUP_ID='target@g.us',
        WHATSAPP_GATEWAY_TYPE='evolution',
    )
    @patch('apps.publications.services.requests.get')
    def test_confirms_group_id_and_exact_name_before_auto_send(self, mock_get):
        response = Mock()
        response.json.return_value = [
            {'id': 'target@g.us', 'subject': 'Ofertas'},
        ]
        mock_get.return_value = response

        dispatcher = WhatsAppDispatcherService()
        result = dispatcher.verify_evolution_destination('Ofertas')

        self.assertEqual(result, {'group_id': 'target@g.us', 'group_name': 'Ofertas'})
        self.assertIn(
            '/group/fetchAllGroups/santana',
            mock_get.call_args.args[0],
        )

    @override_settings(
        WHATSAPP_API_ENABLED=True,
        WHATSAPP_API_URL='http://localhost:8080/message/sendMedia/santana',
        WHATSAPP_API_TOKEN='test-token',
        WHATSAPP_GROUP_ID='target@g.us',
        WHATSAPP_GATEWAY_TYPE='evolution',
    )
    @patch('apps.publications.services.requests.get')
    def test_refuses_a_mismatched_destination_group(self, mock_get):
        response = Mock()
        response.json.return_value = [
            {'id': 'target@g.us', 'subject': 'Grupo diferente'},
        ]
        mock_get.return_value = response

        with self.assertRaisesMessage(ValueError, 'Envio bloqueado'):
            WhatsAppDispatcherService().verify_evolution_destination('Ofertas')

    def test_publication_is_sent_to_every_configured_destination(self):
        publication = Mock(id=12)
        dispatcher = WhatsAppDispatcherService()
        groups = [
            {'name': 'Ofertas A', 'jid': '111@g.us'},
            {'name': 'Ofertas B', 'jid': '222@g.us'},
        ]
        with patch.object(
            dispatcher,
            'send_publication',
            return_value={'success': True, 'simulated': True},
        ) as send_publication:
            result = dispatcher.send_publication_to_groups(publication, groups)

        self.assertTrue(result['success'])
        self.assertEqual(len(result['deliveries']), 2)
        self.assertEqual(
            [call.kwargs['target_group'] for call in send_publication.call_args_list],
            ['111@g.us', '222@g.us'],
        )
        publication.mark_as_published.assert_called_once_with()

    def test_partial_publication_is_terminal_to_avoid_duplicate_sends(self):
        publication = Mock(id=13)
        dispatcher = WhatsAppDispatcherService()
        groups = [
            {'name': 'Ofertas A', 'jid': '111@g.us'},
            {'name': 'Ofertas B', 'jid': '222@g.us'},
        ]
        with patch.object(
            dispatcher,
            'send_publication',
            side_effect=[
                {'success': True, 'simulated': False},
                {'success': False, 'error': 'Gateway indisponível'},
            ],
        ):
            result = dispatcher.send_publication_to_groups(publication, groups)

        self.assertFalse(result['success'])
        self.assertTrue(result['partial'])
        self.assertTrue(result['deliveries'][0]['success'])
        self.assertFalse(result['deliveries'][1]['success'])
        publication.mark_as_published.assert_called_once_with()


class IncomingOfferPersistenceTests(TestCase):
    def test_startup_links_are_ignored_and_new_links_are_deduplicated(self):
        baseline = {'https://meli.la/Old123': ''}
        record_startup_baseline(baseline, 'Grupo de Vendas')

        created = record_new_offers(
            {
                'https://meli.la/Old123': '',
                'https://meli.la/New123': 'CUPOM123',
            },
            'Grupo de Vendas',
        )

        self.assertEqual(len(created), 1)
        self.assertEqual(created[0].source_link, 'https://meli.la/New123')
        self.assertEqual(created[0].coupon, 'CUPOM123')
        self.assertEqual(
            IncomingAffiliateOffer.objects.get(source_link='https://meli.la/Old123').status,
            IncomingOfferStatus.IGNORED,
        )
        self.assertEqual(
            len(record_new_offers({'https://meli.la/New123': 'CUPOM123'}, 'Grupo de Vendas')),
            0,
        )

    def test_interrupted_processing_is_not_retried_automatically(self):
        record = IncomingAffiliateOffer.objects.create(
            source_link='https://meli.la/Interrupted123',
            source_group='Grupo de Vendas',
            status=IncomingOfferStatus.PROCESSING,
        )
        IncomingAffiliateOffer.objects.filter(pk=record.pk).update(
            updated_at=timezone.now() - timedelta(minutes=30)
        )

        updated = mark_stale_processing_as_uncertain()

        record.refresh_from_db()
        self.assertEqual(updated, 1)
        self.assertEqual(record.status, IncomingOfferStatus.UNCERTAIN)

    @override_settings(
        AFFILIATE_BOT_SOURCE_GROUP='Promozone #46',
        AFFILIATE_BOT_TARGET_GROUP='Santana_Indica',
        AFFILIATE_BOT_DAILY_LIMIT=20,
    )
    def test_incoming_offer_endpoint_returns_monitor_state(self):
        IncomingAffiliateOffer.objects.create(
            source_link='https://meli.la/Endpoint123',
            source_group='Promozone #46',
            status=IncomingOfferStatus.PENDING,
        )
        IncomingAffiliateOffer.objects.create(
            source_link='https://meli.la/Endpoint456',
            source_group='Outra origem',
            status=IncomingOfferStatus.PENDING,
        )
        IncomingAffiliateOffer.objects.create(
            source_link='https://meli.la/Endpoint789',
            source_group='Origem removida',
            status=IncomingOfferStatus.PUBLISHED,
            published_at=timezone.now(),
        )
        WhatsAppGroup.objects.create(name='Promozone #46', role=WhatsAppGroupRole.SOURCE)
        WhatsAppGroup.objects.create(name='Outra origem', role=WhatsAppGroupRole.SOURCE)
        WhatsAppGroup.objects.create(
            name='Santana_Indica',
            jid='123@g.us',
            role=WhatsAppGroupRole.DESTINATION,
        )
        WhatsAppGroupConfiguration.objects.create(pk=1)
        request = APIRequestFactory().get('/api/publications/incoming-offers/')

        response = PublicationViewSet.as_view({'get': 'incoming_offers'})(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['source_group'], 'Outra origem')
        self.assertEqual(response.data['source_groups'], ['Outra origem', 'Promozone #46'])
        self.assertEqual(response.data['target_groups'], ['Santana_Indica'])
        self.assertEqual(response.data['daily_limit'], 20)
        self.assertEqual(response.data['statuses'][IncomingOfferStatus.PENDING], 2)
        self.assertEqual(response.data['today_sent'], 1)

    @override_settings(
        AFFILIATE_BOT_SOURCE_GROUP='Origem antiga',
        AFFILIATE_BOT_TARGET_GROUP='Destino antigo',
    )
    def test_whatsapp_group_configuration_persists_multiple_destinations(self):
        payload = {
            'groups': [
                {'name': 'Origem 1', 'jid': '', 'role': 'source'},
                {'name': 'Origem 2', 'jid': '', 'role': 'source'},
                {'name': 'Destino 1', 'jid': '111@g.us', 'role': 'destination'},
                {'name': 'Destino 2', 'jid': '222@g.us', 'role': 'destination'},
            ],
        }
        request = APIRequestFactory().put(
            '/api/publications/whatsapp-groups/',
            payload,
            format='json',
        )

        response = PublicationViewSet.as_view({'put': 'whatsapp_groups'})(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['source_groups'], ['Origem 1', 'Origem 2'])
        self.assertEqual(response.data['source_group'], 'Origem 1')
        self.assertEqual(response.data['target_groups'], ['Destino 1', 'Destino 2'])
        self.assertEqual(WhatsAppGroup.objects.count(), 4)
        self.assertTrue(WhatsAppGroupConfiguration.objects.filter(pk=1).exists())

        empty_request = APIRequestFactory().put(
            '/api/publications/whatsapp-groups/',
            {'groups': []},
            format='json',
        )
        empty_response = PublicationViewSet.as_view({'put': 'whatsapp_groups'})(empty_request)
        self.assertEqual(empty_response.data['groups'], [])
        self.assertEqual(WhatsAppGroup.objects.count(), 0)

    def test_whatsapp_group_configuration_accepts_multiple_sources(self):
        request = APIRequestFactory().put(
            '/api/publications/whatsapp-groups/',
            {
                'groups': [
                    {'name': 'Origem 1', 'role': 'source'},
                    {'name': 'Origem 2', 'role': 'source'},
                ],
            },
            format='json',
        )

        response = PublicationViewSet.as_view({'put': 'whatsapp_groups'})(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['source_groups'], ['Origem 1', 'Origem 2'])
        self.assertEqual(WhatsAppGroup.objects.count(), 2)

    def test_whatsapp_group_configuration_prevents_source_destination_loop(self):
        request = APIRequestFactory().put(
            '/api/publications/whatsapp-groups/',
            {
                'groups': [
                    {'name': 'Grupo espelhado', 'jid': '123@g.us', 'role': 'source'},
                    {'name': 'Grupo espelhado', 'jid': '123@g.us', 'role': 'destination'},
                ],
            },
            format='json',
        )

        response = PublicationViewSet.as_view({'put': 'whatsapp_groups'})(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(WhatsAppGroup.objects.count(), 0)

    def test_dispatch_next_with_empty_queue_returns_informational_response(self):
        request = APIRequestFactory().post('/api/publications/dispatch-next/', {}, format='json')

        response = PublicationViewSet.as_view({'post': 'dispatch_next'})(request)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['dispatched'])
        self.assertIn('Não há oferta aprovada', response.data['message'])
