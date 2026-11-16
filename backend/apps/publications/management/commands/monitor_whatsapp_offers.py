import logging
import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.publications.affiliate_watcher import (
    AffiliateAutomationError,
    acquire_process_lock,
    daily_publication_count,
    disconnect_automation_browser,
    open_automation_browser,
    process_offer,
    prune_old_offer_records,
    mark_stale_processing_as_uncertain,
    read_group_offers,
    record_new_offers,
    record_startup_baseline,
    release_process_lock,
    wait_for_publish_window,
)
from apps.publications.group_config import (
    get_destination_groups,
    get_source_group_names,
    get_whatsapp_groups,
)
from apps.publications.models import IncomingAffiliateOffer, IncomingOfferStatus

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Monitora grupos WhatsApp e republica ofertas meli.la automaticamente.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--send',
            action='store_true',
            help='Ativa o envio automático pelo WhatsApp Web. Sem esta opção, apenas registra novos links.',
        )
        parser.add_argument(
            '--once',
            action='store_true',
            help='Faz uma leitura, processa no máximo uma oferta e encerra.',
        )
        parser.add_argument(
            '--prepare-only',
            action='store_true',
            help='Prepara uma oferta pendente e valida o afiliado, sem enviar ao WhatsApp.',
        )
        parser.add_argument(
            '--source-group',
            help='Limita esta execução a uma origem configurada pelo nome exato.',
        )
        parser.add_argument(
            '--retry-failed',
            action='store_true',
            help='Recoloca na fila falhas ocorridas antes de tentar enviar.',
        )

    def handle(self, *args, **options):
        groups = get_whatsapp_groups()
        source_groups = get_source_group_names(groups)
        if options['source_group']:
            if options['source_group'] not in source_groups:
                raise CommandError(
                    f'A origem “{options["source_group"]}” não está configurada.'
                )
            source_groups = [options['source_group']]
        target_groups = [
            group['name'] for group in get_destination_groups(groups)
        ]
        daily_limit = getattr(settings, 'AFFILIATE_BOT_DAILY_LIMIT', 20)
        poll_interval = getattr(settings, 'AFFILIATE_BOT_POLL_INTERVAL_SECONDS', 10)

        if not source_groups:
            raise CommandError('Cadastre ao menos um grupo de origem na configuração do WhatsApp.')
        if options['send'] and not target_groups:
            raise CommandError('Cadastre ao menos um grupo de destino antes de ativar o envio.')
        if options['prepare_only'] and options['send']:
            raise CommandError('--prepare-only não pode ser usado junto com --send.')
        if options['prepare_only'] and not options['once']:
            raise CommandError('--prepare-only exige --once para limitar a operação a uma oferta.')
        if not 1 <= daily_limit <= 100:
            raise CommandError('AFFILIATE_BOT_DAILY_LIMIT deve estar entre 1 e 100.')
        if poll_interval < 3:
            raise CommandError('AFFILIATE_BOT_POLL_INTERVAL_SECONDS deve ser no mínimo 3.')

        lock_file = None
        browser = None
        try:
            lock_file = acquire_process_lock()
            if options['retry_failed']:
                retried = IncomingAffiliateOffer.objects.filter(
                    source_group__in=source_groups,
                    status=IncomingOfferStatus.FAILED
                ).update(
                    status=IncomingOfferStatus.PENDING,
                    error_message='',
                    processed_at=None,
                    updated_at=timezone.now(),
                )
                self.stdout.write(f'{retried} oferta(s) retornaram à fila.')

            pruned = prune_old_offer_records()
            if pruned:
                self.stdout.write(f'{pruned} registro(s) terminal(is) antigos foram removidos.')
            uncertain = mark_stale_processing_as_uncertain()
            if uncertain:
                self.stdout.write(
                    self.style.WARNING(
                        f'{uncertain} oferta(s) interrompida(s) anteriormente foram marcadas '
                        'como incertas e não serão reenviadas.'
                    )
                )

            browser = open_automation_browser()
            whatsapp_tab = browser.current_window_handle
            seen_links_by_group = {}
            for source_group in source_groups:
                initial_offers = read_group_offers(browser, source_group)
                record_startup_baseline(initial_offers, source_group)
                seen_links_by_group[source_group] = set(initial_offers)
            self.stdout.write(
                self.style.SUCCESS(
                    f'Monitorando {len(source_groups)} origem(ns): '
                    f'{", ".join(source_groups)} → '
                    f'{", ".join(target_groups) if target_groups else "nenhum destino cadastrado"}; '
                    f'teto diário: {daily_limit}.'
                )
            )
            if options['send']:
                self.stdout.write('Envio automático ativado via WhatsApp Web/Selenium.')
                browser.switch_to.new_window('tab')
                affiliate_tab = browser.current_window_handle
            elif options['prepare_only']:
                self.stdout.write(
                    'Modo de preparação: o produto e o link afiliado serão validados; '
                    'nenhuma mensagem será enviada.'
                )
                browser.switch_to.new_window('tab')
                affiliate_tab = browser.current_window_handle
            else:
                affiliate_tab = None
                self.stdout.write(
                    self.style.WARNING(
                        'Modo de observação: nenhum link será gerado e nenhuma mensagem será enviada. '
                        'Use --send para ativar o fluxo automático.'
                    )
                )

            skip_rescan = (
                options['once']
                and (options['send'] or options['prepare_only'])
                and IncomingAffiliateOffer.objects.filter(
                    source_group__in=source_groups,
                    status__in=(
                        (IncomingOfferStatus.PENDING, IncomingOfferStatus.PREPARED)
                        if options['send']
                        else (IncomingOfferStatus.PENDING,)
                    ),
                ).exists()
            )
            if skip_rescan:
                self.stdout.write(
                    'Já existe uma oferta pendente; usando a leitura inicial para validar as origens.'
                )

            while True:
                configured_groups = get_whatsapp_groups()
                configured_sources = get_source_group_names(configured_groups)
                if options['source_group']:
                    configured_sources = [
                        source for source in configured_sources
                        if source == options['source_group']
                    ]
                if not configured_sources:
                    raise CommandError(
                        'Todos os grupos de origem foram removidos. Configure ao menos uma origem.'
                    )
                active_sources = set(configured_sources)
                seen_links_by_group = {
                    group: links for group, links in seen_links_by_group.items()
                    if group in active_sources
                }
                if not skip_rescan:
                    for source_group in configured_sources:
                        browser.switch_to.window(whatsapp_tab)
                        if source_group not in seen_links_by_group:
                            initial_offers = read_group_offers(browser, source_group)
                            record_startup_baseline(initial_offers, source_group)
                            seen_links_by_group[source_group] = set(initial_offers)
                            self.stdout.write(
                                self.style.WARNING(
                                    f'Nova origem “{source_group}”; links atuais registrados como histórico.'
                                )
                            )
                            continue

                        offers = read_group_offers(browser, source_group)
                        seen_links = seen_links_by_group[source_group]
                        unseen_offers = {
                            link: coupon
                            for link, coupon in offers.items()
                            if link not in seen_links
                        }
                        seen_links.update(unseen_offers)
                        new_offers = record_new_offers(unseen_offers, source_group)
                        for offer in new_offers:
                            self.stdout.write(
                                f'Novo link registrado em “{source_group}”: {offer.source_link}'
                            )

                if options['send'] or options['prepare_only']:
                    processed = 0
                    while not options['once'] or processed == 0:
                        if options['send'] and daily_publication_count() >= daily_limit:
                            self.stdout.write('Teto diário alcançado; links novos ficam na fila.')
                            break
                        configured_sources = get_source_group_names(get_whatsapp_groups())
                        if options['source_group']:
                            configured_sources = [
                                source for source in configured_sources
                                if source == options['source_group']
                            ]
                        statuses_to_process = (
                            (IncomingOfferStatus.PENDING, IncomingOfferStatus.PREPARED)
                            if options['send']
                            else (IncomingOfferStatus.PENDING,)
                        )
                        pending = IncomingAffiliateOffer.objects.filter(
                            source_group__in=configured_sources,
                            status__in=statuses_to_process,
                        ).order_by('received_at', 'id').first()
                        if not pending:
                            break

                        configured_groups = get_whatsapp_groups()
                        target_groups = [
                            group['name']
                            for group in get_destination_groups(configured_groups)
                        ]
                        if options['send'] and not target_groups:
                            raise CommandError(
                                'Nenhum grupo de destino está configurado; envio interrompido.'
                            )
                        if options['send']:
                            wait_for_publish_window()
                        self.stdout.write(f'Processando oferta recebida: {pending.source_link}')
                        result = process_offer(
                            pending,
                            browser,
                            whatsapp_tab,
                            affiliate_tab,
                            target_groups,
                            publish=options['send'],
                        )
                        self.stdout.write(result)
                        processed += 1
                        pending.refresh_from_db()
                        if pending.status in (
                            IncomingOfferStatus.FAILED,
                            IncomingOfferStatus.UNCERTAIN,
                        ):
                            raise AffiliateAutomationError(
                                f'{pending.error_message or result} Monitor pausado para evitar repetição.'
                            )

                if options['once']:
                    break
                time.sleep(poll_interval)
        except AffiliateAutomationError as exc:
            raise CommandError(str(exc)) from exc
        except KeyboardInterrupt:
            self.stdout.write('\nMonitor interrompido pelo usuário.')
        finally:
            try:
                if browser:
                    disconnect_automation_browser(browser)
            finally:
                release_process_lock(lock_file)
