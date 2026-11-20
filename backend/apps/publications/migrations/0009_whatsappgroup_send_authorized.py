from django.db import migrations, models


def authorize_existing_destination_groups(apps, schema_editor):
    WhatsAppGroup = apps.get_model('publications', 'WhatsAppGroup')
    blocked = {'geral', 'sti geral'}
    for group in WhatsAppGroup.objects.filter(role__in=('destination', 'both')):
        normalized = ' '.join((group.name or '').strip().lower().split())
        if normalized in blocked or 'sti geral' in normalized:
            continue
        group.send_authorized = True
        group.save(update_fields=['send_authorized'])


class Migration(migrations.Migration):

    dependencies = [
        ('publications', '0008_alter_whatsappgroup_role'),
    ]

    operations = [
        migrations.AddField(
            model_name='whatsappgroup',
            name='send_authorized',
            field=models.BooleanField(default=False, verbose_name='Envio autorizado'),
        ),
        migrations.RunPython(
            authorize_existing_destination_groups,
            migrations.RunPython.noop,
        ),
    ]
