from datetime import timedelta
from decimal import Decimal
from io import StringIO
from unittest.mock import ANY, Mock, patch

from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIRequestFactory

from apps.catalog.models import ProductOffer, ProductStatus
from .affiliate_watcher import (
    AffiliateAutomationError,
    build_incoming_offer_message,
    extract_coupon,
    extract_short_links,
    mark_stale_processing_as_uncertain,
    open_automation_browser,
    open_whatsapp_group,
    process_offer,
    record_new_offers,
    record_startup_baseline,
)
from .models import (
    IncomingAffiliateOffer,
    IncomingOfferStatus,
    Publication,
    PublicationStatus,
    WhatsAppGroup,
    WhatsAppGroupConfiguration,
    WhatsAppGroupRole,
)
from .product_urls import extract_item_id, is_marketplace_url, parse_brl_price
from .services import WhatsAppDispatcherService
from .views import PublicationViewSet
from .management.commands.monitor_whatsapp_offers import Command as MonitorWhatsAppOffersCommand


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

        self.assertIn('🔥 *Fone Bluetooth*', message)
        self.assertIn('Mercado Livre', message)
        self.assertIn('~De R$ 199,90~ → *Por R$ 129,90*', message)
        self.assertIn('35% OFF', message)
        self.assertIn('Cupom: OFERTA20', message)
        self.assertIn('🛒 https://meli.la/AbC123', message)

    @override_settings(AFFILIATE_BOT_CHROME_DEBUGGER_ADDRESS='0.0.0.0:9222')
    def test_debugger_must_not_bind_to_network_interfaces(self):
        with self.assertRaisesMessage(AffiliateAutomationError, 'host local'):
            open_automation_browser()

    @patch('selenium.webdriver.support.ui.WebDriverWait')
    def test_group_selection_clicks_the_conversation_container(self, mock_wait):
        group_name = 'Grupo de ofertas'
        current_group = {'name': ''}

        header = Mock()
        header.get_attribute.return_value = group_name
        label = Mock()
        label.get_attribute.return_value = group_name
        row = Mock()
        label.find_element.return_value = row
        row.click.side_effect = lambda: current_group.update(name=group_name)

        def find_elements(_by, selector):
            if selector == '#main header [data-testid="conversation-info-header-chat-title"]':
                return [header] if current_group['name'] else []
            if selector == '#pane-side [title]':
                return [label]
            return []

        browser = Mock()
        browser.find_elements.side_effect = find_elements
        mock_wait.return_value.until.side_effect = lambda condition: condition(browser)

        open_whatsapp_group(browser, group_name)

        label.click.assert_not_called()
        row.click.assert_called_once_with()
        label.find_element.assert_called_once_with(
            'xpath',
            './ancestor::*[@data-testid="cell-frame-container"][1]',
        )

    @patch('selenium.webdriver.support.ui.WebDriverWait')
    def test_group_selection_retries_once_when_chat_does_not_open(self, mock_wait):
        from selenium.common.exceptions import TimeoutException

        group_name = 'Grupo de ofertas'
        current_group = {'name': ''}

        header = Mock()
        header.get_attribute.return_value = group_name
        label = Mock()
        label.get_attribute.return_value = group_name
        row = Mock()
        label.find_element.return_value = row

        def find_elements(_by, selector):
            if selector == '#main header [data-testid="conversation-info-header-chat-title"]':
                return [header] if current_group['name'] else []
            if selector == '#pane-side [title]':
                return [label]
            return []

        browser = Mock()
        browser.find_elements.side_effect = find_elements
        browser.execute_script.side_effect = lambda _script, _target: current_group.update(
            name=group_name
        )
        wait = mock_wait.return_value
        wait.until.side_effect = [
            TimeoutException(),
            lambda condition: condition(browser),
        ]

        open_whatsapp_group(browser, group_name)

        row.click.assert_called_once_with()
        browser.execute_script.assert_called_once_with('arguments[0].click()', row)

    @patch('selenium.webdriver.support.ui.WebDriverWait')
    def test_group_selection_uses_enter_as_final_search_fallback(self, mock_wait):
        from selenium.common.exceptions import TimeoutException
        from selenium.webdriver.common.keys import Keys

        group_name = 'Grupo de ofertas'
        state = {'name': '', 'search_started': False}

        header = Mock()
        header.get_attribute.return_value = group_name
        label = Mock()
        label.get_attribute.return_value = group_name
        label.is_displayed.return_value = True
        row = Mock()
        label.find_element.return_value = row
        search = Mock()
        search.click.side_effect = lambda: state.update(search_started=True)

        def send_search_key(*keys):
            if Keys.ENTER in keys:
                state['name'] = group_name

        search.send_keys.side_effect = send_search_key

        def find_elements(_by, selector):
            if selector == '#main header [data-testid="conversation-info-header-chat-title"]':
                return [header] if state['name'] else []
            if selector == '#pane-side [title]':
                return [label] if state['search_started'] else []
            if selector == '#side div[contenteditable="true"]':
                return [search]
            return []

        browser = Mock()
        browser.find_elements.side_effect = find_elements
        wait = mock_wait.return_value
        wait.until.side_effect = [
            label,
            TimeoutException(),
            TimeoutException(),
            lambda condition: condition(browser),
        ]

        open_whatsapp_group(browser, group_name)

        self.assertIn(Keys.ENTER, [entry.args[0] for entry in search.send_keys.call_args_list])
        row.click.assert_called_once_with()


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
    def test_prepare_offer_validates_affiliate_and_does_not_send(self):
        offer = IncomingAffiliateOffer.objects.create(
            source_link='https://meli.la/Original123',
            source_group='Grupo de origem',
        )
        details = {
            'item_id': 'MLB1234567890',
            'title': 'Liquidificador de teste',
            'price': Decimal('129.90'),
            'original_price': Decimal('199.90'),
            'product_url': 'https://produto.mercadolivre.com.br/MLB-1234567890-item',
            'thumbnail': 'https://http2.mlstatic.com/test.jpg',
        }
        affiliate_url = 'https://meli.la/Affiliate123'
        browser = Mock()

        with (
            patch(
                'apps.publications.affiliate_watcher.resolve_product_page',
                return_value=details,
            ) as resolve_product_page,
            patch(
                'apps.publications.affiliate_watcher.generate_affiliate_link',
                return_value=affiliate_url,
            ),
            patch(
                'apps.publications.affiliate_watcher.publish_offer_in_whatsapp',
            ) as publish_offer,
        ):
            result = process_offer(
                offer,
                browser,
                'whatsapp-tab',
                'affiliate-tab',
                ['Grupo de destino'],
                publish=False,
            )

        offer.refresh_from_db()
        self.assertIn('Oferta preparada sem envio', result)
        self.assertEqual(offer.status, IncomingOfferStatus.PREPARED)
        self.assertEqual(resolve_product_page.call_count, 2)
        self.assertEqual(offer.product.affiliate_url, affiliate_url)
        self.assertEqual(offer.publication.status, PublicationStatus.APPROVED)
        self.assertIsNone(offer.published_at)
        publish_offer.assert_not_called()

    def test_prepare_offer_rejects_affiliate_link_for_another_product(self):
        offer = IncomingAffiliateOffer.objects.create(
            source_link='https://meli.la/Original456',
            source_group='Grupo de origem',
        )
        details = {
            'item_id': 'MLB1234567890',
            'title': 'Liquidificador de teste',
            'price': Decimal('129.90'),
            'original_price': None,
            'product_url': 'https://produto.mercadolivre.com.br/MLB-1234567890-item',
            'thumbnail': '',
        }
        wrong_details = {**details, 'item_id': 'MLB9876543210'}

        with (
            patch(
                'apps.publications.affiliate_watcher.resolve_product_page',
                side_effect=[details, wrong_details],
            ),
            patch(
                'apps.publications.affiliate_watcher.generate_affiliate_link',
                return_value='https://meli.la/Affiliate456',
            ),
            patch(
                'apps.publications.affiliate_watcher._store_product_and_publication',
            ) as store_offer,
        ):
            result = process_offer(
                offer,
                Mock(),
                'whatsapp-tab',
                'affiliate-tab',
                [],
                publish=False,
            )

        offer.refresh_from_db()
        self.assertIn('anúncio diferente', result)
        self.assertEqual(offer.status, IncomingOfferStatus.FAILED)
        store_offer.assert_not_called()

    def test_sending_a_prepared_offer_reuses_the_validated_affiliate_link(self):
        product = ProductOffer.objects.create(
            item_id='MLB1234567890',
            title='Liquidificador de teste',
            price=Decimal('129.90'),
            product_url='https://produto.mercadolivre.com.br/MLB-1234567890-item',
            affiliate_url='https://meli.la/Affiliate789',
            status=ProductStatus.APPROVED,
        )
        publication = Publication.objects.create(
            product=product,
            title='SANTANA INDICA',
            message_text='Oferta de teste',
            status=PublicationStatus.APPROVED,
        )
        offer = IncomingAffiliateOffer.objects.create(
            source_link='https://meli.la/Original789',
            source_group='Grupo de origem',
            product=product,
            publication=publication,
            status=IncomingOfferStatus.PREPARED,
        )

        with (
            patch(
                'apps.publications.affiliate_watcher.generate_affiliate_link',
            ) as generate_affiliate_link,
            patch(
                'apps.publications.affiliate_watcher.publish_offer_in_whatsapp',
                return_value=['Grupo de destino'],
            ) as publish_offer,
        ):
            result = process_offer(
                offer,
                Mock(),
                'whatsapp-tab',
                'affiliate-tab',
                ['Grupo de destino'],
            )

        offer.refresh_from_db()
        publication.refresh_from_db()
        self.assertIn('Oferta publicada', result)
        self.assertEqual(offer.status, IncomingOfferStatus.PUBLISHED)
        self.assertEqual(publication.status, PublicationStatus.PUBLISHED)
        generate_affiliate_link.assert_not_called()
        publish_offer.assert_called_once_with(
            ANY,
            'whatsapp-tab',
            ['Grupo de destino'],
            publication.message_text,
            product.affiliate_url,
        )

    @override_settings(AFFILIATE_BOT_DAILY_LIMIT=20)
    def test_one_shot_send_skips_rescan_for_an_existing_pending_offer(self):
        offer = IncomingAffiliateOffer.objects.create(
            source_link='https://meli.la/Pending123',
            source_group='Grupo de origem',
        )
        groups = [
            {'name': 'Grupo de origem', 'role': WhatsAppGroupRole.SOURCE},
            {'name': 'Grupo de destino', 'role': WhatsAppGroupRole.DESTINATION},
        ]
        browser = Mock()
        browser.current_window_handle = 'whatsapp-tab'
        command = MonitorWhatsAppOffersCommand()
        command.stdout = StringIO()

        with (
            patch(
                'apps.publications.management.commands.monitor_whatsapp_offers.get_whatsapp_groups',
                return_value=groups,
            ),
            patch(
                'apps.publications.management.commands.monitor_whatsapp_offers.get_source_group_names',
                return_value=['Grupo de origem'],
            ),
            patch(
                'apps.publications.management.commands.monitor_whatsapp_offers.get_destination_groups',
                return_value=[{'name': 'Grupo de destino'}],
            ),
            patch(
                'apps.publications.management.commands.monitor_whatsapp_offers.acquire_process_lock',
                return_value='lock',
            ),
            patch(
                'apps.publications.management.commands.monitor_whatsapp_offers.release_process_lock',
            ),
            patch(
                'apps.publications.management.commands.monitor_whatsapp_offers.prune_old_offer_records',
                return_value=0,
            ),
            patch(
                'apps.publications.management.commands.monitor_whatsapp_offers.mark_stale_processing_as_uncertain',
                return_value=0,
            ),
            patch(
                'apps.publications.management.commands.monitor_whatsapp_offers.open_automation_browser',
                return_value=browser,
            ),
            patch(
                'apps.publications.management.commands.monitor_whatsapp_offers.read_group_offers',
                return_value={},
            ) as read_group_offers,
            patch(
                'apps.publications.management.commands.monitor_whatsapp_offers.record_startup_baseline',
            ),
            patch(
                'apps.publications.management.commands.monitor_whatsapp_offers.daily_publication_count',
                return_value=0,
            ),
            patch(
                'apps.publications.management.commands.monitor_whatsapp_offers.wait_for_publish_window',
            ),
            patch(
                'apps.publications.management.commands.monitor_whatsapp_offers.process_offer',
                side_effect=lambda pending, *_args, **_kwargs: (
                    IncomingAffiliateOffer.objects.filter(pk=pending.pk).update(
                        status=IncomingOfferStatus.PUBLISHED
                    )
                    and 'Oferta enviada'
                ),
            ) as process_offer,
        ):
            command.handle(
                once=True,
                send=True,
                prepare_only=False,
                source_group=None,
                retry_failed=False,
            )

        self.assertEqual(read_group_offers.call_count, 1)
        process_offer.assert_called_once()
        offer.refresh_from_db()
        self.assertEqual(offer.status, IncomingOfferStatus.PUBLISHED)

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
        preparation = IncomingAffiliateOffer.objects.create(
            source_link='https://meli.la/InterruptedPreparation123',
            source_group='Grupo de Vendas',
            status=IncomingOfferStatus.PREPARING,
        )
        IncomingAffiliateOffer.objects.filter(
            pk__in=(record.pk, preparation.pk),
        ).update(
            updated_at=timezone.now() - timedelta(minutes=30)
        )

        updated = mark_stale_processing_as_uncertain()

        record.refresh_from_db()
        preparation.refresh_from_db()
        self.assertEqual(updated, 2)
        self.assertEqual(record.status, IncomingOfferStatus.UNCERTAIN)
        self.assertEqual(preparation.status, IncomingOfferStatus.FAILED)
        self.assertIn('nenhuma mensagem foi enviada', preparation.error_message)

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
            send_authorized=True,
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
                {'name': 'Destino 1', 'jid': '111@g.us', 'role': 'destination', 'send_authorized': True},
                {'name': 'Destino 2', 'jid': '222@g.us', 'role': 'destination', 'send_authorized': True},
                {'name': 'Destino Novo Sem Autorizacao', 'jid': '333@g.us', 'role': 'destination'},
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
        self.assertEqual(WhatsAppGroup.objects.count(), 5)
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

    def test_group_match_and_blocked_send_groups(self):
        from apps.publications.affiliate_watcher import _is_group_match, is_blocked_send_group

        self.assertFalse(_is_group_match('Geral', 'Catira Geral Nova Contagem'))
        self.assertFalse(_is_group_match('STI Geral', 'Catira Geral Nova Contagem'))
        self.assertFalse(_is_group_match('Vendas', 'Grupo de Vendas'))
        self.assertTrue(_is_group_match('Catira Geral Nova Contagem', 'Catira Geral Nova Contagem'))
        self.assertTrue(_is_group_match('COMPRAS & VENDAS PRESENCIAL & ONLINE', 'COMPRAS & VENDAS PRESENCIAL'))

        self.assertTrue(is_blocked_send_group('Geral'))
        self.assertTrue(is_blocked_send_group('STI Geral'))
        self.assertFalse(is_blocked_send_group('Catira Geral Nova Contagem'))

    def test_whatsapp_group_configuration_rejects_blocked_destination(self):
        request = APIRequestFactory().put(
            '/api/publications/whatsapp-groups/',
            {
                'groups': [
                    {'name': 'STI Geral', 'jid': '999@g.us', 'role': 'destination', 'send_authorized': True},
                ],
            },
            format='json',
        )
        response = PublicationViewSet.as_view({'put': 'whatsapp_groups'})(request)
        self.assertEqual(response.status_code, 400)

    def test_balanced_target_groups_prioritizes_groups_with_fewer_posts(self):
        from apps.publications.affiliate_watcher import select_balanced_target_groups
        from apps.publications.models import PublicationDelivery, PublicationDeliveryStatus

        product = ProductOffer.objects.create(
            item_id='MLB999000111',
            category='other',
            title='Produto Balanceamento',
            price='99.90',
            product_url='https://www.mercadolivre.com.br/p/MLB999000111',
            affiliate_url='https://meli.la/Bal123',
            status=ProductStatus.APPROVED,
        )
        pub = Publication.objects.create(
            product=product,
            title='Oferta',
            message_text='Texto',
            status=PublicationStatus.APPROVED,
        )
        for _ in range(5):
            PublicationDelivery.objects.create(
                publication=pub,
                target_group_name='Grupo Cheio',
                affiliate_url='https://meli.la/Bal123',
                status=PublicationDeliveryStatus.SUCCESS,
            )
        PublicationDelivery.objects.create(
            publication=pub,
            target_group_name='Grupo Medio',
            affiliate_url='https://meli.la/Bal123',
            status=PublicationDeliveryStatus.SUCCESS,
        )

        priority, overflow = select_balanced_target_groups(
            ['Grupo Cheio', 'Grupo Medio', 'Grupo Novo'],
            max_lead=2,
        )
        self.assertEqual(priority, ['Grupo Novo', 'Grupo Medio'])
        self.assertEqual(overflow, ['Grupo Cheio'])

    def test_offer_quality_filter_and_queue_prioritization(self):
        from apps.publications.affiliate_watcher import (
            evaluate_offer_quality,
            select_next_pending_offer,
        )

        # Sem desconto e sem cupom -> bloqueia
        ok, reason = evaluate_offer_quality({'price': 80.0, 'original_price': None, 'rating': 4.8})
        self.assertFalse(ok)
        self.assertIn('sem desconto', reason.lower())

        # Desconto baixo (10%) sem cupom -> bloqueia
        ok, reason = evaluate_offer_quality({'price': 90.0, 'original_price': 100.0, 'rating': 4.8})
        self.assertFalse(ok)
        self.assertIn('10% off', reason.lower())

        # Preço abaixo de R$ 20 -> bloqueia mesmo com desconto
        ok, reason = evaluate_offer_quality({'price': 15.0, 'original_price': 30.0, 'rating': 4.8})
        self.assertFalse(ok)
        self.assertIn('abaixo do mínimo', reason.lower())

        # Nota abaixo de 4.0 -> bloqueia
        ok, reason = evaluate_offer_quality({'price': 100.0, 'original_price': 150.0, 'rating': 3.5})
        self.assertFalse(ok)
        self.assertIn('avaliação', reason.lower())

        # 20% OFF + preço >= 20 + nota >= 4.0 -> aprova
        ok, _ = evaluate_offer_quality({'price': 80.0, 'original_price': 100.0, 'rating': 4.7})
        self.assertTrue(ok)

        # Sem desconto mas com cupom -> aprova
        ok, _ = evaluate_offer_quality({'price': 80.0, 'original_price': None, 'rating': None}, coupon='MELI10')
        self.assertTrue(ok)

        # Fila prioriza maior % OFF / cupom
        low = IncomingAffiliateOffer.objects.create(
            source_link='https://meli.la/Low1',
            source_group='Origem',
            original_message='Confira este produto',
        )
        best = IncomingAffiliateOffer.objects.create(
            source_link='https://meli.la/Best1',
            source_group='Origem',
            original_message='Oferta relâmpago 45% OFF!',
            coupon='PROMO10',
        )
        picked = select_next_pending_offer(IncomingAffiliateOffer.objects.filter(pk__in=[low.pk, best.pk]))
        self.assertEqual(picked.pk, best.pk)

    def test_build_incoming_offer_message_format(self):
        from apps.publications.affiliate_watcher import build_incoming_offer_message

        msg = build_incoming_offer_message(
            {
                'title': 'Fone Bluetooth Baseus',
                'price': 89.90,
                'original_price': 199.90,
                'rating': 4.8,
            },
            'MELI10',
            'https://meli.la/Teste123',
        )
        self.assertIn('55% OFF NO MERCADO LIVRE', msg)
        self.assertIn('~R$ 199,90~ → *R$ 89,90*', msg)
        self.assertIn('MELI10', msg)
        self.assertIn('https://meli.la/Teste123', msg)
        self.assertLessEqual(len(msg.splitlines()), 6)

    def test_multistore_amazon_link_extraction_and_copy(self):
        from apps.publications.affiliate_watcher import (
            build_incoming_offer_message,
            extract_offer_links,
        )
        from apps.publications.product_urls import (
            STORE_AMAZON,
            STORE_MERCADOLIVRE,
            detect_store_from_url,
            extract_amazon_asin,
            extract_amazon_item_id,
        )

        text = (
            'Oferta ML https://meli.la/AbC123 e oferta Amazon '
            'https://amzn.to/4xYzAbC e direto https://www.amazon.com.br/dp/B09G9FPHY6?ref=abc'
        )
        links = extract_offer_links(text)
        self.assertIn('https://meli.la/AbC123', links)
        self.assertIn('https://amzn.to/4xYzAbC', links)
        self.assertIn('https://www.amazon.com.br/dp/B09G9FPHY6', links)

        self.assertEqual(detect_store_from_url('https://meli.la/AbC123'), STORE_MERCADOLIVRE)
        self.assertEqual(detect_store_from_url('https://amzn.to/4xYzAbC'), STORE_AMAZON)
        self.assertEqual(extract_amazon_asin('https://www.amazon.com.br/dp/B09G9FPHY6?tag=abc-20'), 'B09G9FPHY6')
        self.assertEqual(extract_amazon_item_id('https://www.amazon.com.br/dp/B09G9FPHY6'), 'AMZNB09G9FPHY6')
        self.assertTrue(ProductOffer.is_valid_listing_permalink('https://www.amazon.com.br/dp/B09G9FPHY6'))

        amazon_msg = build_incoming_offer_message(
            {
                'title': 'Echo Dot 5ª Geração',
                'price': 299.00,
                'original_price': 429.00,
                'rating': 4.9,
                'store': STORE_AMAZON,
            },
            '',
            'https://amzn.to/4xYzAbC',
        )
        self.assertIn('NA AMAZON', amazon_msg)
        self.assertIn('30% OFF', amazon_msg)
        self.assertIn('https://amzn.to/4xYzAbC', amazon_msg)

    def test_store_and_group_per_store_balancing(self):
        from apps.publications.affiliate_watcher import (
            select_balanced_target_groups,
            select_next_pending_offer,
        )
        from apps.publications.models import PublicationDelivery, PublicationDeliveryStatus
        from apps.publications.product_urls import STORE_AMAZON, STORE_MERCADOLIVRE

        # 1. Fila prioriza loja com menos envios publicados hoje (Amazon 0 vs ML 2)
        for idx in range(2):
            IncomingAffiliateOffer.objects.create(
                source_link=f'https://meli.la/PubML{idx}',
                source_group='Origem',
                store=STORE_MERCADOLIVRE,
                status=IncomingOfferStatus.PUBLISHED,
                published_at=timezone.now(),
            )
        pending_ml = IncomingAffiliateOffer.objects.create(
            source_link='https://meli.la/PendML',
            source_group='Origem',
            store=STORE_MERCADOLIVRE,
            original_message='50% OFF!',
        )
        pending_amz = IncomingAffiliateOffer.objects.create(
            source_link='https://amzn.to/PendAMZ',
            source_group='Origem',
            store=STORE_AMAZON,
            original_message='20% OFF!',
        )
        picked = select_next_pending_offer(
            IncomingAffiliateOffer.objects.filter(pk__in=[pending_ml.pk, pending_amz.pk])
        )
        self.assertEqual(picked.pk, pending_amz.pk)

        # 2. Equilíbrio por grupo é contado separadamente por loja
        prod_ml = ProductOffer.objects.create(
            item_id='MLB888111222',
            store=STORE_MERCADOLIVRE,
            category='other',
            title='Prod ML',
            price='100.00',
            product_url='https://www.mercadolivre.com.br/p/MLB888111222',
            affiliate_url='https://meli.la/ML888',
            status=ProductStatus.APPROVED,
        )
        pub_ml = Publication.objects.create(
            product=prod_ml,
            title='ML',
            message_text='ML',
            status=PublicationStatus.APPROVED,
        )
        for _ in range(5):
            PublicationDelivery.objects.create(
                publication=pub_ml,
                target_group_name='Grupo A',
                affiliate_url='https://meli.la/ML888',
                status=PublicationDeliveryStatus.SUCCESS,
            )
        # No ML, Grupo A tem 5 e Grupo B tem 0 -> prioriza Grupo B
        prio_ml, over_ml = select_balanced_target_groups(['Grupo A', 'Grupo B'], store=STORE_MERCADOLIVRE, max_lead=1)
        self.assertEqual(prio_ml, ['Grupo B'])
        self.assertEqual(over_ml, ['Grupo A'])

        # Na Amazon, ambos têm 0 -> ambos entram igualmente!
        prio_amz, over_amz = select_balanced_target_groups(['Grupo A', 'Grupo B'], store=STORE_AMAZON, max_lead=1)
        self.assertEqual(prio_amz, ['Grupo A', 'Grupo B'])
        self.assertEqual(over_amz, [])

    @override_settings(AFFILIATE_BOT_ENABLED_STORES='mercadolivre,amazon,shopee')
    def test_shopee_link_extraction_copy_and_store_quotas(self):
        from apps.publications.affiliate_watcher import (
            build_incoming_offer_message,
            extract_offer_links,
            parse_store_daily_quotas,
        )
        from apps.publications.product_urls import (
            STORE_SHOPEE,
            detect_store_from_url,
            extract_shopee_item_id,
        )

        text = (
            'Achado Shopee https://s.shopee.com.br/3L9abcXYZ '
            'e direto https://shopee.com.br/Produto-Top-i.12345.67890?sp_atk=1'
        )
        links = extract_offer_links(text)
        self.assertIn('https://s.shopee.com.br/3L9abcXYZ', links)
        self.assertIn('https://shopee.com.br/Produto-Top-i.12345.67890', links)
        self.assertEqual(detect_store_from_url('https://s.shopee.com.br/3L9abcXYZ'), STORE_SHOPEE)
        self.assertEqual(extract_shopee_item_id('https://shopee.com.br/Produto-Top-i.12345.67890'), 'SHP12345_67890')
        self.assertTrue(ProductOffer.is_valid_listing_permalink('https://shopee.com.br/product/12345/67890'))

        quotas = parse_store_daily_quotas('mercadolivre=10, amazon=10, shopee=8')
        self.assertEqual(quotas, {'mercadolivre': 10, 'amazon': 10, 'shopee': 8})

        msg = build_incoming_offer_message(
            {
                'title': 'Mini Aspirador Portátil USB',
                'price': 39.90,
                'original_price': 79.90,
                'store': STORE_SHOPEE,
            },
            '',
            'https://s.shopee.com.br/3L9abcXYZ',
        )
        self.assertIn('NA SHOPEE', msg)
        self.assertIn('50% OFF', msg)
        self.assertIn('https://s.shopee.com.br/3L9abcXYZ', msg)

    @override_settings(
        AFFILIATE_BOT_SHOPEE_APP_ID='123456',
        AFFILIATE_BOT_SHOPEE_SECRET='secretkey',
    )
    def test_shopee_open_api_signature_header(self):
        import hashlib
        from apps.publications.shopee_provider import (
            build_shopee_open_api_headers,
            has_shopee_open_api_credentials,
        )

        self.assertTrue(has_shopee_open_api_credentials())
        payload = '{"query":"{test}"}'
        headers = build_shopee_open_api_headers(payload, timestamp=1700000000)
        expected_sig = hashlib.sha256(f'1234561700000000{payload}secretkey'.encode('utf-8')).hexdigest()
        self.assertEqual(
            headers['Authorization'],
            f'SHA256 Credential=123456,Timestamp=1700000000,Signature={expected_sig}',
        )

    @override_settings(AFFILIATE_BOT_ENABLED_STORES='mercadolivre,amazon,shopee,tiktok')
    def test_tiktok_link_extraction_copy_and_permalink(self):
        from apps.publications.affiliate_watcher import (
            build_incoming_offer_message,
            extract_offer_links,
        )
        from apps.publications.product_urls import (
            STORE_TIKTOK,
            detect_store_from_url,
            extract_tiktok_item_id,
        )

        text = (
            'Oferta TikTok https://vt.tiktok.com/ZSY123AbC/ '
            'e produto https://shop.tiktok.com/view/product/1729384756123456789?region=BR'
        )
        links = extract_offer_links(text)
        self.assertIn('https://vt.tiktok.com/ZSY123AbC', links)
        self.assertIn('https://shop.tiktok.com/view/product/1729384756123456789', links)
        self.assertEqual(detect_store_from_url('https://vt.tiktok.com/ZSY123AbC'), STORE_TIKTOK)
        self.assertEqual(
            extract_tiktok_item_id('https://shop.tiktok.com/view/product/1729384756123456789'),
            'TTK1729384756123456789',
        )
        self.assertTrue(
            ProductOffer.is_valid_listing_permalink('https://shop.tiktok.com/view/product/1729384756123456789')
        )

        msg = build_incoming_offer_message(
            {
                'title': 'Escova Secadora 3 em 1',
                'price': 59.90,
                'original_price': 119.80,
                'store': STORE_TIKTOK,
            },
            '',
            'https://vt.tiktok.com/ZSY123AbC',
        )
        self.assertIn('NO TIKTOK SHOP', msg)
        self.assertIn('50% OFF', msg)
        self.assertIn('https://vt.tiktok.com/ZSY123AbC', msg)
