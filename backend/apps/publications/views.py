"""
Views de Publicações Promocionais e Disparo WhatsApp
Especificação V1.0 - Seção 3.11 (GET /api/publications/)
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Publication, PublicationStatus
from .serializers import PublicationSerializer, GeneratePublicationSerializer
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

        target_group = request.data.get('group_id')
        dispatcher = WhatsAppDispatcherService()
        result = dispatcher.send_publication(publication, target_group=target_group)

        if not result.get('success'):
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
        target_group = request.data.get('group_id')
        custom_text = request.data.get('message')
        dispatcher = WhatsAppDispatcherService()
        result = dispatcher.send_test_message(target_group=target_group, custom_text=custom_text)

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
                {'message': 'Nenhuma oferta aprovada com link de afiliado disponível para envio imediato.'},
                status=status.HTTP_404_NOT_FOUND
            )

        target_group = request.data.get('group_id')
        dispatcher = WhatsAppDispatcherService()
        result = dispatcher.send_publication(pending_pub, target_group=target_group)

        if not result.get('success'):
            return Response(
                {'error': result.get('error', 'Falha ao disparar próxima oferta.'), 'details': result},
                status=status.HTTP_502_BAD_GATEWAY
            )

        return Response({
            'message': 'Próxima oferta disparada com sucesso!',
            'dispatch': result,
            'publication': PublicationSerializer(pending_pub).data
        }, status=status.HTTP_200_OK)
