"""
Serviço de Disparo Automático para WhatsApp
Suporta Evolution API, Z-API e Webhooks Genéricos
Especificação V1.0 - Seções 3.8 e 4.5
"""

import logging
import requests
from urllib.parse import quote, urlsplit, urlunsplit
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

    def verify_evolution_destination(self, expected_group_name: str) -> dict:
        """
        Confirms the configured Evolution group ID resolves to the requested group name.
        """
        if self.gateway_type != 'evolution':
            raise ValueError('A automação exige WHATSAPP_GATEWAY_TYPE=evolution.')
        if not self.enabled or not self.api_url or not self.token or not self.group_id:
            raise ValueError(
                'Configure WHATSAPP_API_ENABLED=True, WHATSAPP_API_URL, '
                'WHATSAPP_API_TOKEN e WHATSAPP_GROUP_ID no .env.'
            )

        parsed = urlsplit(self.api_url)
        route_marker = '/message/sendMedia/'
        if route_marker not in parsed.path:
            raise ValueError(
                'WHATSAPP_API_URL precisa apontar para a rota Evolution '
                '/message/sendMedia/{instancia}.'
            )

        prefix, instance = parsed.path.rsplit(route_marker, 1)
        instance = instance.strip('/')
        if not instance or '/' in instance:
            raise ValueError('Não foi possível identificar a instância Evolution na WHATSAPP_API_URL.')

        groups_path = f'{prefix}/group/fetchAllGroups/{quote(instance, safe="")}'
        groups_url = urlunsplit((parsed.scheme, parsed.netloc, groups_path, 'getParticipants=false', ''))
        try:
            response = requests.get(
                groups_url,
                headers={'apikey': self.token, 'Accept': 'application/json'},
                timeout=15,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            logger.error('Não foi possível validar grupos na Evolution API: %s', exc)
            raise ValueError(
                'A Evolution API não permitiu validar o grupo de destino; envio automático bloqueado.'
            ) from exc

        groups = payload
        if isinstance(payload, dict):
            groups = payload.get('groups') or payload.get('data') or payload.get('response') or []
        if not isinstance(groups, list):
            raise ValueError('Resposta inesperada ao consultar grupos da Evolution API.')

        group = next(
            (
                item for item in groups
                if isinstance(item, dict)
                and (item.get('id') or item.get('remoteJid') or item.get('jid')) == self.group_id
            ),
            None,
        )
        if not group:
            raise ValueError(
                'WHATSAPP_GROUP_ID não corresponde a nenhum grupo retornado pela Evolution API.'
            )

        actual_name = (group.get('subject') or group.get('name') or '').strip()
        if actual_name.casefold() != expected_group_name.strip().casefold():
            resolved_name = actual_name or 'grupo sem nome'
            raise ValueError(
                f'O ID configurado aponta para “{resolved_name}”, '
                f'não para “{expected_group_name}”. Envio bloqueado.'
            )

        return {'group_id': self.group_id, 'group_name': actual_name}

    def send_publication(
        self,
        publication: Publication,
        target_group: str = None,
        mark_published: bool = True,
    ) -> dict:
        """
        Dispara a oferta (foto + copy persuasiva com link) para o grupo de WhatsApp.
        """
        destination = (target_group or self.group_id or '').strip()
        image_url = publication.product.thumbnail or ''
        message_text = publication.message_text
        send_url = self.api_url

        # Modo Simulação / Demonstração
        if not self.enabled:
            logger.info(
                f"[SIMULAÇÃO WHATSAPP] Publicação #{publication.id} marcada como publicada. "
                f"WHATSAPP_API_ENABLED está desativado no .env."
            )
            if mark_published:
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
                if image_url:
                    payload = {
                        'number': destination,
                        'mediatype': 'image',
                        'mimetype': 'image/jpeg',
                        'caption': message_text,
                        'media': image_url,
                        'fileName': f"oferta_{publication.product.item_id}.jpg"
                    }
                else:
                    send_url = self.api_url.replace(
                        '/message/sendMedia/',
                        '/message/sendText/',
                        1,
                    )
                    if send_url == self.api_url:
                        return {
                            'success': False,
                            'simulated': False,
                            'error': 'WHATSAPP_API_URL não permite enviar texto sem imagem pela Evolution API.',
                        }
                    payload = {'number': destination, 'text': message_text}

            logger.info(f"Disparando oferta #{publication.id} para WhatsApp via {self.gateway_type} ({destination})...")

            response = requests.post(
                send_url,
                json=payload,
                headers=headers,
                timeout=18
            )

            if response.status_code in (200, 201):
                if mark_published:
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

    def send_publication_to_groups(self, publication: Publication, groups: list) -> dict:
        if not groups:
            return {
                'success': False,
                'error': 'Cadastre pelo menos um grupo de destino nas configurações do WhatsApp.',
                'deliveries': [],
            }

        deliveries = []
        for group in groups:
            result = self.send_publication(
                publication,
                target_group=group.get('jid'),
                mark_published=False,
            )
            deliveries.append({
                'group_name': group['name'],
                'group_id': group.get('jid'),
                'success': result.get('success', False),
                'simulated': result.get('simulated', False),
                'error': result.get('error', ''),
            })
            if not result.get('success'):
                if any(delivery['success'] for delivery in deliveries):
                    publication.mark_as_published()
                    return {
                        'success': False,
                        'partial': True,
                        'error': (
                            f"Publicação enviada parcialmente; falha no grupo "
                            f"{group['name']}: {result.get('error', 'erro não informado')}"
                        ),
                        'deliveries': deliveries,
                        'publication_id': publication.id,
                    }
                return {
                    **result,
                    'deliveries': deliveries,
                }

        publication.mark_as_published()
        return {
            'success': True,
            'simulated': all(delivery['simulated'] for delivery in deliveries),
            'message': f'Oferta publicada para {len(deliveries)} grupo(s) de WhatsApp.',
            'deliveries': deliveries,
            'publication_id': publication.id,
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
