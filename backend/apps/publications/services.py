"""
Serviço de Disparo Automático para WhatsApp
Suporta Evolution API, Z-API e Webhooks Genéricos
Especificação V1.0 - Seções 3.8 e 4.5
"""

import logging
import requests
from django.conf import settings
from django.utils import timezone
from .models import Publication, PublicationStatus

logger = logging.getLogger(__name__)


class WhatsAppDispatcherService:
    """
    Controlador de integração e disparo de mensagens promocionais para WhatsApp.
    """

    def __init__(self):
        self.enabled = getattr(settings, 'WHATSAPP_API_ENABLED', False)
        self.api_url = getattr(settings, 'WHATSAPP_API_URL', '').strip()
        self.token = getattr(settings, 'WHATSAPP_API_TOKEN', '').strip()
        self.group_id = getattr(settings, 'WHATSAPP_GROUP_ID', '').strip()
        self.gateway_type = getattr(settings, 'WHATSAPP_GATEWAY_TYPE', 'evolution').lower()

    def get_status(self):
        """
        Retorna o estado operacional da integração WhatsApp.
        """
        return {
            'enabled': self.enabled,
            'gateway_type': self.gateway_type,
            'api_url': self.api_url,
            'has_token': bool(self.token),
            'group_id': self.group_id,
            'ready_for_dispatch': bool(self.enabled and self.api_url and (self.group_id or self.token)),
        }

    def send_publication(self, publication: Publication, target_group: str = None) -> dict:
        """
        Dispara a oferta (foto + copy persuasiva com link) para o grupo de WhatsApp.
        """
        destination = (target_group or self.group_id or '').strip()
        image_url = publication.product.thumbnail or ''
        message_text = publication.message_text

        # Modo Simulação / Demonstração
        if not self.enabled:
            logger.info(
                f"[SIMULAÇÃO WHATSAPP] Publicação #{publication.id} marcada como publicada. "
                f"WHATSAPP_API_ENABLED está desativado no .env."
            )
            publication.mark_as_published()
            return {
                'success': True,
                'simulated': True,
                'message': (
                    'Oferta registrada e marcada como publicada no histórico (Modo Simulação). '
                    'Para envio automático real aos grupos, ative WHATSAPP_API_ENABLED=True no arquivo .env.'
                ),
                'destination': destination or 'Grupo padrão',
                'publication_id': publication.id
            }

        # Validação de Pré-requisitos para envio real
        if not self.api_url:
            return {
                'success': False,
                'simulated': False,
                'error': 'A variável WHATSAPP_API_URL não está configurada no arquivo .env.'
            }

        if not destination:
            return {
                'success': False,
                'simulated': False,
                'error': 'Nenhum grupo de WhatsApp configurado (defina WHATSAPP_GROUP_ID no .env ou informe o ID do grupo).'
            }

        # Montagem do Payload conforme o Gateway Escolhido
        try:
            if self.gateway_type == 'zapi':
                headers = {
                    'Content-Type': 'application/json',
                    'Client-Token': self.token,
                }
                payload = {
                    'phone': destination,
                    'image': image_url,
                    'caption': message_text,
                }
            elif self.gateway_type == 'generic':
                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.token}' if self.token else '',
                }
                payload = {
                    'number': destination,
                    'message': message_text,
                    'image': image_url,
                }
            else:
                # Padrão: Evolution API (v1 / v2)
                headers = {
                    'Content-Type': 'application/json',
                    'apikey': self.token,
                }
                payload = {
                    'number': destination,
                    'mediatype': 'image',
                    'mimetype': 'image/jpeg',
                    'caption': message_text,
                    'media': image_url,
                    'fileName': f"oferta_{publication.product.item_id}.jpg"
                }

            logger.info(f"Disparando oferta #{publication.id} para WhatsApp via {self.gateway_type} ({destination})...")

            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=18
            )

            if response.status_code in (200, 201):
                publication.mark_as_published()
                resp_data = response.json() if 'application/json' in response.headers.get('Content-Type', '') else {}
                return {
                    'success': True,
                    'simulated': False,
                    'message': f'Oferta publicada com sucesso no grupo de WhatsApp via {self.gateway_type.upper()}!',
                    'destination': destination,
                    'gateway_response': resp_data,
                    'publication_id': publication.id
                }
            else:
                err_snippet = response.text[:300]
                logger.error(f"Erro ao disparar no WhatsApp ({response.status_code}): {err_snippet}")
                return {
                    'success': False,
                    'simulated': False,
                    'error': f"O Gateway {self.gateway_type.upper()} retornou erro HTTP {response.status_code}: {err_snippet}",
                    'status_code': response.status_code
                }

        except requests.RequestException as e:
            logger.error(f"Falha de conexão com a API do WhatsApp: {str(e)}")
            return {
                'success': False,
                'simulated': False,
                'error': f"Falha ao conectar com o gateway do WhatsApp em {self.api_url}: {str(e)}"
            }

    def send_test_message(self, target_group: str = None, custom_text: str = None) -> dict:
        """
        Dispara uma mensagem de teste para verificar a integridade da conexão.
        """
        destination = (target_group or self.group_id or '').strip()
        test_text = custom_text or (
            "⚡ *Santana Afiliados Bot • Teste de Conexão*\n\n"
            "Olá! O gateway de envio automático de ofertas para grupos de WhatsApp "
            "foi conectado com sucesso à plataforma!\n\n"
            f"📅 _Data/Hora do Teste: {timezone.now().strftime('%d/%m/%Y %H:%M:%S')}_\n"
            "🚀 _Status: Operacional e pronto para novos envios._"
        )

        if not self.enabled:
            return {
                'success': True,
                'simulated': True,
                'message': (
                    'Teste registrado em Modo Simulação. Para enviar mensagens reais aos grupos, '
                    'habilite WHATSAPP_API_ENABLED=True no arquivo .env.'
                ),
                'destination': destination or 'Grupo padrão',
                'preview_text': test_text
            }

        if not self.api_url or not destination:
            return {
                'success': False,
                'error': 'Defina WHATSAPP_API_URL e WHATSAPP_GROUP_ID no arquivo .env antes de testar.'
            }

        try:
            # Em envio de texto simples, a URL pode ser sendText ou a mesma configurada
            text_url = self.api_url.replace('/sendMedia/', '/sendText/').replace('/send-image', '/send-text')
            
            if self.gateway_type == 'zapi':
                headers = {'Content-Type': 'application/json', 'Client-Token': self.token}
                payload = {'phone': destination, 'message': test_text}
            else:
                headers = {'Content-Type': 'application/json', 'apikey': self.token}
                payload = {'number': destination, 'text': test_text}

            response = requests.post(text_url, json=payload, headers=headers, timeout=12)
            if response.status_code in (200, 201):
                return {
                    'success': True,
                    'simulated': False,
                    'message': f'Mensagem de teste enviada com sucesso para {destination}!',
                    'gateway_response': response.json() if 'application/json' in response.headers.get('Content-Type', '') else {}
                }
            else:
                return {
                    'success': False,
                    'error': f"Erro HTTP {response.status_code} do Gateway: {response.text[:250]}"
                }
        except Exception as e:
            return {
                'success': False,
                'error': f"Falha de comunicação: {str(e)}"
            }
