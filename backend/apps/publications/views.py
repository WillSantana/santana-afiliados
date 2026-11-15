"""
Views de Publicações Promocionais e Disparo WhatsApp
Especificação V1.0 - Seção 3.11 (GET /api/publications/)
"""

from collections import Counter

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import (
    IncomingAffiliateOffer,
    IncomingOfferStatus,
    Publication,
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
        serializer = IncomingAffiliateOfferSerializer(offers[:100], many=True)
        return Response({
            'source_groups': source_groups,
            'source_group': source_groups[0] if source_groups else '',
            'target_groups': [
                group['name'] for group in get_destination_groups(groups)
            ],
            'daily_limit': getattr(settings, 'AFFILIATE_BOT_DAILY_LIMIT', 20),
            'today_sent': today_sent,
            'statuses': statuses,
            'results': serializer.data,
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
            normalized.append({'name': name, 'jid': jid or None, 'role': role})

        source_keys = {
            (group['name'].casefold(), group['jid'])
            for group in normalized
            if group['role'] == WhatsAppGroupRole.SOURCE
        }
        destination_groups = [
            group for group in normalized
            if group['role'] == WhatsAppGroupRole.DESTINATION
        ]
        if any(
            (destination['name'].casefold(), destination['jid']) in source_keys
            or any(
                source_name == destination['name'].casefold()
                or (source_jid and source_jid == destination['jid'])
                for source_name, source_jid in source_keys
            )
            for destination in destination_groups
        ):
            return Response(
                {'error': 'O grupo de origem não pode ser cadastrado também como destino.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

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
