import re

from django.conf import settings

from .models import WhatsAppGroup, WhatsAppGroupConfiguration, WhatsAppGroupRole

GROUP_JID_PATTERN = re.compile(r'^[\d-]+@g\.us$')


def get_whatsapp_groups():
    groups = list(
        WhatsAppGroup.objects.values('id', 'name', 'jid', 'role', 'send_authorized').order_by('role', 'name')
    )
    if groups or WhatsAppGroupConfiguration.objects.filter(pk=1).exists():
        return groups

    source_name = getattr(settings, 'AFFILIATE_BOT_SOURCE_GROUP', '').strip()
    target_name = getattr(settings, 'AFFILIATE_BOT_TARGET_GROUP', '').strip()
    target_jid = getattr(settings, 'WHATSAPP_GROUP_ID', '').strip()
    if not GROUP_JID_PATTERN.fullmatch(target_jid):
        target_jid = None

    defaults = []
    if source_name:
        defaults.append({
            'id': None,
            'name': source_name,
            'jid': None,
            'role': WhatsAppGroupRole.SOURCE,
            'send_authorized': False,
        })
    if target_name:
        defaults.append({
            'id': None,
            'name': target_name,
            'jid': target_jid,
            'role': WhatsAppGroupRole.DESTINATION,
            'send_authorized': True,
        })
    return defaults


def get_source_group_names(groups=None):
    groups = groups if groups is not None else get_whatsapp_groups()
    return [
        group['name'].strip()
        for group in groups
        if group['role'] in (WhatsAppGroupRole.SOURCE, WhatsAppGroupRole.BOTH)
    ]


def get_source_group_name(groups=None):
    return next(iter(get_source_group_names(groups)), '')


def get_destination_groups(groups=None):
    groups = groups if groups is not None else get_whatsapp_groups()
    return [
        group for group in groups
        if group['role'] in (WhatsAppGroupRole.DESTINATION, WhatsAppGroupRole.BOTH)
        and group.get('send_authorized', False)
    ]
