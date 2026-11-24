"""
Views de Publicações Promocionais e Disparo WhatsApp
Especificação V1.0 - Seção 3.11 (GET /api/publications/)
"""

import os
import subprocess
import tempfile
import time
import urllib.request
from collections import Counter
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.db.models import Count, Max, Q
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import (
    IncomingAffiliateOffer,
    IncomingOfferStatus,
    Publication,
    PublicationDelivery,
    PublicationDeliveryStatus,
    PublicationStatus,
    WhatsAppGroup,
    WhatsAppGroupConfiguration,
    WhatsAppGroupRole,
)
from .group_config import (
    GROUP_JID_PATTERN,
    get_destination_groups,
    get_source_group_names,
    get_whatsapp_groups,
)
from .serializers import (
    GeneratePublicationSerializer,
    IncomingAffiliateOfferSerializer,
    PublicationDeliverySerializer,
    PublicationSerializer,
)
from .services import WhatsAppDispatcherService
from apps.catalog.models import ProductOffer, ProductStatus


class PublicationViewSet(viewsets.ModelViewSet):
    """
    Gerenciamento de publicações preparadas para canais autorizados (WhatsApp).
    Endpoints:
    - GET /api/publications/
    - POST /api/publications/generate/
    - POST /api/publications/{id}/publish/
    - GET /api/publications/whatsapp-config/
    - POST /api/publications/test-whatsapp/
    - POST /api/publications/dispatch-next/
    """
    queryset = Publication.objects.all()
    serializer_class = PublicationSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        channel = self.request.query_params.get('channel')
        status_filter = self.request.query_params.get('status')
        if channel:
            queryset = queryset.filter(channel=channel)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset

    @action(detail=False, methods=['get'], url_path='incoming-offers')
    def incoming_offers(self, request):
        groups = get_whatsapp_groups()
        source_groups = get_source_group_names(groups)
        offers = IncomingAffiliateOffer.objects.filter(
            source_group__in=source_groups,
        ).exclude(
            Q(error_message__icontains='social')
            | Q(error_message__icontains='/social/')
        ).exclude(
            source_link__icontains='/social/'
        ).select_related('product').order_by('-received_at')
        counts = Counter(offers.values_list('status', flat=True))
        statuses = {
            status_value: counts.get(status_value, 0)
            for status_value, _ in IncomingOfferStatus.choices
        }
        today_sent = IncomingAffiliateOffer.objects.filter(
            status__in=(IncomingOfferStatus.PUBLISHED, IncomingOfferStatus.UNCERTAIN),
            published_at__date=timezone.localdate(),
        ).count()
        serializer = IncomingAffiliateOfferSerializer(offers[:150], many=True)
        return Response({
            'source_groups': source_groups,
            'source_group': source_groups[0] if source_groups else '',
            'target_groups': [
                group['name'] for group in get_destination_groups(groups)
            ],
            'daily_limit': getattr(settings, 'AFFILIATE_BOT_DAILY_LIMIT', 20),
            'today_sent': today_sent,
            'statuses': statuses,
            'bot_running': self._is_bot_running(),
            'chrome_connected': self._is_chrome_connected(),
            'results': serializer.data,
        })

    _bot_proc_cache = {'checked_at': 0.0, 'running': False}

    def _is_bot_running(self):
        lock_path = Path(tempfile.gettempdir()) / 'SantanaAfiliadosBot' / 'whatsapp-offer-monitor.lock'
        if lock_path.exists():
            try:
                f = lock_path.open('a+b')
                if os.name == 'nt':
                    import msvcrt
                    f.seek(0)
                    msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                    msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
                f.close()
            except Exception:
                return True

        # Fallback: se o monitor foi iniciado em outra sessão/TEMP no Windows,
        # verifica diretamente se existe um processo Python executando o comando.
        now = time.monotonic()
        if now - self._bot_proc_cache['checked_at'] < 5.0:
            return self._bot_proc_cache['running']

        running = False
        if os.name == 'nt':
            try:
                out = subprocess.check_output(
                    [
                        'powershell',
                        '-NoProfile',
                        '-Command',
                        "(Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -like '*monitor_whatsapp_offers*' } | Measure-Object).Count",
                    ],
                    text=True,
                    timeout=3,
                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
                )
                running = int((out or '0').strip() or '0') > 0
            except Exception:
                running = False

        self._bot_proc_cache['checked_at'] = now
        self._bot_proc_cache['running'] = running
        return running

    def _is_chrome_connected(self):
        try:
            req = urllib.request.Request('http://127.0.0.1:9222/json/version')
            with urllib.request.urlopen(req, timeout=0.8) as resp:
                return resp.status == 200
        except Exception:
            return False

    @action(detail=False, methods=['get'], url_path='dashboard')
    def dashboard(self, request):
        groups = get_whatsapp_groups()
        source_groups = get_source_group_names(groups)
        dest_groups = [g['name'] for g in get_destination_groups(groups)]

        all_offers = IncomingAffiliateOffer.objects.exclude(
            Q(error_message__icontains='social')
            | Q(error_message__icontains='/social/')
        ).exclude(
            source_link__icontains='/social/'
        )
        total_offers = all_offers.count()
        counts = Counter(all_offers.values_list('status', flat=True))

        total_deliveries = PublicationDelivery.objects.count()
        deliveries_success = PublicationDelivery.objects.filter(status=PublicationDeliveryStatus.SUCCESS).count()
        deliveries_failed = PublicationDelivery.objects.filter(status=PublicationDeliveryStatus.FAILED).count()
        deliveries_uncertain = PublicationDelivery.objects.filter(status=PublicationDeliveryStatus.UNCERTAIN).count()

        incoming_affiliate_urls = set(
            all_offers.exclude(affiliate_url='').values_list('affiliate_url', flat=True)
        )
        product_affiliate_urls = set(
            ProductOffer.objects.exclude(affiliate_url='').values_list('affiliate_url', flat=True)
        )
        affiliates_count = len(incoming_affiliate_urls | product_affiliate_urls)
        today = timezone.localdate()
        today_sent = PublicationDelivery.objects.filter(
            status=PublicationDeliveryStatus.SUCCESS,
            sent_at__date=today,
        ).count()

        group_stats_rows = (
            PublicationDelivery.objects.values('target_group_name')
            .annotate(
                total_success=Count('id', filter=Q(status=PublicationDeliveryStatus.SUCCESS)),
                today_success=Count(
                    'id',
                    filter=Q(status=PublicationDeliveryStatus.SUCCESS, sent_at__date=today),
                ),
                total_failed=Count('id', filter=Q(status=PublicationDeliveryStatus.FAILED)),
                last_sent_at=Max('sent_at', filter=Q(status=PublicationDeliveryStatus.SUCCESS)),
            )
        )
        dest_group_set = set(dest_groups)
        stats_by_name = {
            row['target_group_name']: {
                'group_name': row['target_group_name'],
                'today_success': row['today_success'],
                'total_success': row['total_success'],
                'total_failed': row['total_failed'],
                'last_sent_at': row['last_sent_at'].isoformat() if row['last_sent_at'] else None,
            }
            for row in group_stats_rows
            if row['target_group_name']
            and (row['target_group_name'] in dest_group_set or row['total_success'] > 0)
        }
        for dest_name in dest_groups:
            stats_by_name.setdefault(
                dest_name,
                {
                    'group_name': dest_name,
                    'today_success': 0,
                    'total_success': 0,
                    'total_failed': 0,
                    'last_sent_at': None,
                },
            )
        posts_by_group = sorted(
            stats_by_name.values(),
            key=lambda item: (-item['total_success'], -item['today_success'], item['group_name'].casefold()),
        )

        from datetime import timedelta
        from .affiliate_watcher import (
            current_publish_window_status,
            daily_publication_count,
            get_enabled_stores,
            parse_store_daily_quotas,
        )
        from .models import StoreClickStats
        from .product_urls import (
            STORE_AMAZON,
            STORE_MERCADOLIVRE,
            STORE_SHOPEE,
            STORE_TIKTOK,
            get_store_display_name,
        )
        click_stats_map = {
            row.store: row for row in StoreClickStats.objects.all()
        }
        store_quotas = parse_store_daily_quotas()
        enabled_stores = get_enabled_stores()
        window_status = current_publish_window_status()
        offers_published_today_total = daily_publication_count()

        store_metrics = []
        total_clicks_all = 0
        total_orders_all = 0
        for store_key in (STORE_MERCADOLIVRE, STORE_AMAZON, STORE_SHOPEE, STORE_TIKTOK):
            store_offers = all_offers.filter(store=store_key)
            store_counts = Counter(store_offers.values_list('status', flat=True))
            store_incoming_aff = set(
                store_offers.exclude(affiliate_url='').values_list('affiliate_url', flat=True)
            )
            store_product_aff = set(
                ProductOffer.objects.filter(store=store_key)
                .exclude(affiliate_url='')
                .values_list('affiliate_url', flat=True)
            )
            store_deliveries_qs = PublicationDelivery.objects.filter(
                Q(incoming_offer__store=store_key)
                | Q(incoming_offer__isnull=True, publication__product__store=store_key)
            )
            store_offers_today = store_offers.filter(
                status__in=(IncomingOfferStatus.PUBLISHED, IncomingOfferStatus.UNCERTAIN),
                published_at__date=today,
            ).count()
            click_row = click_stats_map.get(store_key)
            clicks_val = click_row.clicks_month if click_row else 0
            orders_val = click_row.orders_month if click_row else 0
            total_clicks_all += clicks_val
            total_orders_all += orders_val
            store_metrics.append({
                'store': store_key,
                'label': get_store_display_name(store_key),
                'enabled': store_key in enabled_stores,
                'offers_found': store_offers.count(),
                'pending_offers': store_counts.get(IncomingOfferStatus.PENDING, 0),
                'published_offers': store_counts.get(IncomingOfferStatus.PUBLISHED, 0),
                'offers_published_today': store_offers_today,
                'skipped_offers': store_counts.get(IncomingOfferStatus.SKIPPED, 0),
                'affiliates_generated': len(store_incoming_aff | store_product_aff),
                'deliveries_today': store_deliveries_qs.filter(
                    status=PublicationDeliveryStatus.SUCCESS,
                    sent_at__date=today,
                ).count(),
                'deliveries_total': store_deliveries_qs.filter(
                    status=PublicationDeliveryStatus.SUCCESS,
                ).count(),
                'clicks_month': clicks_val,
                'orders_month': orders_val,
                'clicks_synced_at': (
                    click_row.last_synced_at.isoformat()
                    if click_row and click_row.last_synced_at
                    else None
                ),
                'clicks_error': click_row.sync_error if click_row else '',
                'daily_quota': store_quotas.get(store_key),
            })

        since_24h = timezone.now() - timedelta(hours=24)
        top_24h_qs = (
            all_offers.filter(
                status=IncomingOfferStatus.PUBLISHED,
                published_at__gte=since_24h,
            )
            .select_related('product')
            .annotate(
                deliveries_count=Count(
                    'deliveries',
                    filter=Q(deliveries__status=PublicationDeliveryStatus.SUCCESS),
                )
            )
            .order_by('-deliveries_count', '-published_at')[:6]
        )
        top_offers_24h = []
        for offer in top_24h_qs:
            prod = offer.product
            price_val = float(prod.price) if prod and prod.price is not None else None
            orig_val = float(prod.original_price) if prod and prod.original_price is not None else None
            discount_pct = 0
            if price_val and orig_val and orig_val > price_val:
                discount_pct = round(((orig_val - price_val) / orig_val) * 100)
            top_offers_24h.append({
                'id': offer.id,
                'title': prod.title if prod else offer.source_link,
                'thumbnail': prod.thumbnail if prod else '',
                'store': offer.store,
                'store_label': get_store_display_name(offer.store),
                'price': price_val,
                'original_price': orig_val,
                'discount_pct': discount_pct,
                'deliveries_count': offer.deliveries_count,
                'affiliate_url': offer.affiliate_url or (prod.affiliate_url if prod else ''),
                'published_at': offer.published_at.isoformat() if offer.published_at else None,
            })

        clicks_per_delivery = (
            round(total_clicks_all / deliveries_success, 2)
            if deliveries_success > 0
            else 0.0
        )

        recent_deliveries = PublicationDelivery.objects.select_related('publication__product').order_by('-sent_at')[:20]
        recent_offers = all_offers.select_related('product').order_by('-received_at')[:15]

        return Response({
            'bot_status': {
                'running': self._is_bot_running(),
                'chrome_connected': self._is_chrome_connected(),
                'daily_limit': getattr(settings, 'AFFILIATE_BOT_DAILY_LIMIT', 20),
                'today_sent': today_sent,
                'offers_published_today': offers_published_today_total,
            },
            'window_status': window_status,
            'clicks_summary': {
                'total_clicks': total_clicks_all,
                'total_orders': total_orders_all,
                'clicks_per_delivery': clicks_per_delivery,
            },
            'metrics': {
                'total_offers': total_offers,
                'pending_offers': counts.get(IncomingOfferStatus.PENDING, 0),
                'published_offers': counts.get(IncomingOfferStatus.PUBLISHED, 0),
                'failed_offers': counts.get(IncomingOfferStatus.FAILED, 0),
                'ignored_offers': counts.get(IncomingOfferStatus.IGNORED, 0),
                'affiliates_generated': affiliates_count,
                'total_deliveries': total_deliveries,
                'deliveries_success': deliveries_success,
                'deliveries_failed': deliveries_failed,
                'deliveries_uncertain': deliveries_uncertain,
            },
            'store_metrics': store_metrics,
            'top_offers_24h': top_offers_24h,
            'groups': {
                'sources': source_groups,
                'destinations': dest_groups,
            },
            'posts_by_group': posts_by_group,
            'recent_deliveries': PublicationDeliverySerializer(recent_deliveries, many=True).data,
            'recent_offers': IncomingAffiliateOfferSerializer(recent_offers, many=True).data,
        })

    @action(detail=False, methods=['post'], url_path='sync-clicks')
    def sync_clicks(self, request):
        from .click_sync import sync_official_click_stats

        try:
            results = sync_official_click_stats()
            return Response({'ok': True, 'results': results})
        except Exception as exc:
            return Response(
                {'ok': False, 'error': str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=['get'], url_path='deliveries')
    def deliveries(self, request):
        queryset = PublicationDelivery.objects.select_related('publication__product', 'incoming_offer').order_by('-sent_at')
        status_param = request.query_params.get('status')
        group_param = request.query_params.get('group')
        if status_param:
            queryset = queryset.filter(status=status_param)
        if group_param:
            queryset = queryset.filter(target_group_name__icontains=group_param)
        serializer = PublicationDeliverySerializer(queryset[:150], many=True)
        return Response({
            'total': queryset.count(),
            'results': serializer.data,
        })

    @action(detail=False, methods=['get'], url_path='affiliate-links')
    def affiliate_links(self, request):
        offers_with_link = IncomingAffiliateOffer.objects.filter(
            Q(affiliate_url__gt='') | Q(product__affiliate_url__gt='')
        ).select_related('product').order_by('-updated_at')
        
        items = []
        seen_urls = set()
        for offer in offers_with_link[:150]:
            affiliate_url = offer.affiliate_url or (
                offer.product.affiliate_url if offer.product else ''
            )
            if not affiliate_url:
                continue
            seen_urls.add(affiliate_url)
            items.append({
                'id': offer.id,
                'product_title': offer.product.title if offer.product else 'Produto não identificado',
                'item_id': offer.product.item_id if offer.product else '',
                'source_link': offer.source_link,
                'product_url': offer.product.product_url if offer.product else '',
                'affiliate_url': affiliate_url,
                'generated_at': offer.processed_at or offer.updated_at,
                'validation_status': 'Validado no Mercado Livre' if offer.status in (IncomingOfferStatus.PUBLISHED, IncomingOfferStatus.PREPARED) else 'Pendente de validação',
                'is_valid': offer.status in (IncomingOfferStatus.PUBLISHED, IncomingOfferStatus.PREPARED),
                'offer_status': offer.status,
            })
        if len(items) < 150:
            legacy_publications = Publication.objects.filter(
                product__affiliate_url__gt=''
            ).select_related('product').order_by('-created_at')
            for publication in legacy_publications:
                affiliate_url = publication.product.affiliate_url
                if affiliate_url in seen_urls:
                    continue
                seen_urls.add(affiliate_url)
                items.append({
                    'id': f'publication-{publication.id}',
                    'product_title': publication.product.title,
                    'item_id': publication.product.item_id,
                    'source_link': publication.product.product_url,
                    'product_url': publication.product.product_url,
                    'affiliate_url': affiliate_url,
                    'generated_at': publication.published_at or publication.created_at,
                    'validation_status': 'Link oficial salvo no Mercado Livre',
                    'is_valid': True,
                    'offer_status': publication.status,
                })
                if len(items) >= 150:
                    break
        return Response({
            'total': len(items),
            'results': items,
        })

    @action(detail=False, methods=['get', 'put'], url_path='whatsapp-groups')
    def whatsapp_groups(self, request):
        if request.method == 'GET':
            groups = get_whatsapp_groups()
            source_groups = get_source_group_names(groups)
            return Response({
                'groups': groups,
                'source_groups': source_groups,
                'source_group': source_groups[0] if source_groups else '',
                'target_groups': [
                    group['name'] for group in get_destination_groups(groups)
                ],
            })

        payload = request.data.get('groups')
        if not isinstance(payload, list):
            return Response(
                {'error': 'Envie uma lista de grupos no campo groups.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        normalized = []
        seen_jids = set()
        seen_names = set()
        for index, item in enumerate(payload):
            if not isinstance(item, dict):
                return Response(
                    {'error': f'O grupo na posição {index + 1} está inválido.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            name = item.get('name', '').strip() if isinstance(item.get('name'), str) else ''
            jid = item.get('jid', '').strip() if isinstance(item.get('jid'), str) else ''
            role = item.get('role', '')
            if not name or len(name) > 128:
                return Response(
                    {'error': f'Informe um nome válido para o grupo na posição {index + 1}.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if role not in WhatsAppGroupRole.values:
                return Response(
                    {'error': f'Selecione se “{name}” é origem ou destino.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            from .affiliate_watcher import is_blocked_send_group
            if role in (WhatsAppGroupRole.DESTINATION, WhatsAppGroupRole.BOTH) and is_blocked_send_group(name):
                return Response(
                    {'error': f'O grupo “{name}” está bloqueado para envio de ofertas.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if role == WhatsAppGroupRole.DESTINATION and not jid:
                return Response(
                    {'error': f'Informe o JID de destino para o grupo “{name}”.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if jid and not GROUP_JID_PATTERN.fullmatch(jid):
                return Response(
                    {'error': f'O JID de “{name}” deve estar no formato 123456789@g.us.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            normalized_name = name.casefold()
            if normalized_name in seen_names:
                return Response(
                    {'error': f'O nome “{name}” foi cadastrado mais de uma vez.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            seen_names.add(normalized_name)
            if jid in seen_jids:
                return Response(
                    {'error': f'O JID {jid} foi cadastrado mais de uma vez.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if jid:
                seen_jids.add(jid)
            send_authorized = (
                bool(item.get('send_authorized', False))
                if role in (WhatsAppGroupRole.DESTINATION, WhatsAppGroupRole.BOTH)
                else False
            )
            normalized.append({
                'name': name,
                'jid': jid or None,
                'role': role,
                'send_authorized': send_authorized,
            })

        with transaction.atomic():
            WhatsAppGroup.objects.all().delete()
            WhatsAppGroupConfiguration.objects.update_or_create(pk=1)
            WhatsAppGroup.objects.bulk_create(
                [WhatsAppGroup(**group) for group in normalized]
            )

        groups = get_whatsapp_groups()
        source_groups = get_source_group_names(groups)
        return Response({
            'groups': groups,
            'source_groups': source_groups,
            'source_group': source_groups[0] if source_groups else '',
            'target_groups': [
                group['name'] for group in get_destination_groups(groups)
            ],
        })

    @action(detail=False, methods=['post'], url_path='generate')
    def generate(self, request):
        """
        Gera um rascunho de publicação formatado com aviso legal e benefícios.
        """
        serializer = GeneratePublicationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product_id = serializer.validated_data['product_id']
        custom_benefit = serializer.validated_data.get('custom_benefit')

        product = get_object_or_404(ProductOffer, pk=product_id)
        msg_text = Publication.generate_message_text(product, custom_benefit)

        publication = Publication.objects.create(
            product=product,
            title="OFERTA DO DIA!",
            message_text=msg_text,
            status=PublicationStatus.PENDING_APPROVAL
        )

        return Response(
            PublicationSerializer(publication).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'], url_path='publish')
    def publish(self, request, pk=None):
        """
        Executa o disparo para o grupo de WhatsApp via gateway configurado
        e registra a publicação no histórico oficial.
        """
        publication = self.get_object()

        # Validação mandatória da Seção 2.4 e 4.2
        if not publication.product.affiliate_url:
            return Response(
                {'error': 'A publicação exige um link de afiliado oficial preenchido no produto.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if publication.product.status != ProductStatus.APPROVED:
            return Response(
                {'error': 'O produto associado precisa estar aprovado antes da publicação.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        dispatcher = WhatsAppDispatcherService()
        groups = [
            group for group in get_destination_groups()
            if group.get('jid')
        ]
        if not groups:
            return Response(
                {'error': 'Cadastre ao menos um grupo de destino com JID válido.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        result = dispatcher.send_publication_to_groups(publication, groups)

        if not result.get('success'):
            if result.get('partial'):
                return Response(
                    {
                        'partial': True,
                        'message': result.get('error'),
                        'dispatch': result,
                        'publication': PublicationSerializer(publication).data,
                    },
                    status=207,
                )
            return Response(
                {
                    'error': result.get('error', 'Falha no disparo para o WhatsApp.'),
                    'details': result
                },
                status=status.HTTP_502_BAD_GATEWAY
            )

        return Response({
            'message': result.get('message', 'Oferta publicada com sucesso no canal autorizado.'),
            'dispatch': result,
            'publication': PublicationSerializer(publication).data
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='whatsapp-config')
    def whatsapp_config(self, request):
        """
        Retorna o status atual da configuração do gateway de WhatsApp.
        """
        dispatcher = WhatsAppDispatcherService()
        return Response(dispatcher.get_status(), status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='test-whatsapp')
    def test_whatsapp(self, request):
        """
        Envia mensagem de teste para o grupo configurado.
        """
        destination_groups = [
            group for group in get_destination_groups()
            if group.get('jid')
        ]
        requested_group = request.data.get('group_id')
        if requested_group:
            destination_groups = [
                group for group in destination_groups
                if group['jid'] == requested_group
            ]
        if not destination_groups:
            return Response(
                {'error': 'Cadastre e selecione ao menos um grupo de destino com JID válido.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        custom_text = request.data.get('message')
        dispatcher = WhatsAppDispatcherService()
        result = dispatcher.send_test_message(
            target_group=destination_groups[0]['jid'],
            custom_text=custom_text,
        )

        status_code = status.HTTP_200_OK if result.get('success') else status.HTTP_400_BAD_REQUEST
        return Response(result, status=status_code)

    @action(detail=False, methods=['post'], url_path='dispatch-next')
    def dispatch_next(self, request):
        """
        Encontra a próxima oferta aprovada com link de afiliado e executa o disparo.
        """
        # 1. Procura publicações existentes pendentes de envio
        pending_pub = Publication.objects.filter(
            status=PublicationStatus.PENDING_APPROVAL,
            product__status=ProductStatus.APPROVED
        ).exclude(product__affiliate_url='').first()

        if not pending_pub:
            # 2. Procura produto aprovado com link que ainda não tenha publicação
            candidate_product = ProductOffer.objects.filter(
                status=ProductStatus.APPROVED
            ).exclude(affiliate_url='').filter(
                publications__isnull=True
            ).order_by('-score').first()

            if candidate_product:
                msg_text = Publication.generate_message_text(candidate_product)
                pending_pub = Publication.objects.create(
                    product=candidate_product,
                    title="OFERTA DO DIA!",
                    message_text=msg_text,
                    status=PublicationStatus.PENDING_APPROVAL
                )

        if not pending_pub:
            return Response(
                {
                    'dispatched': False,
                    'message': (
                        'Não há oferta aprovada com link de afiliado na fila. '
                        'Acompanhe o monitor do WhatsApp para registrar novas ofertas.'
                    ),
                },
                status=status.HTTP_200_OK,
            )

        groups = [
            group for group in get_destination_groups()
            if group.get('jid')
        ]
        if not groups:
            return Response(
                {'error': 'Cadastre ao menos um grupo de destino com JID válido.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        dispatcher = WhatsAppDispatcherService()
        result = dispatcher.send_publication_to_groups(pending_pub, groups)

        if not result.get('success'):
            if result.get('partial'):
                return Response(
                    {
                        'partial': True,
                        'message': result.get('error'),
                        'dispatch': result,
                        'publication': PublicationSerializer(pending_pub).data,
                    },
                    status=207,
                )
            return Response(
                {'error': result.get('error', 'Falha ao disparar próxima oferta.'), 'details': result},
                status=status.HTTP_502_BAD_GATEWAY
            )

        return Response({
            'message': 'Próxima oferta disparada com sucesso!',
            'dispatch': result,
            'publication': PublicationSerializer(pending_pub).data
        }, status=status.HTTP_200_OK)
