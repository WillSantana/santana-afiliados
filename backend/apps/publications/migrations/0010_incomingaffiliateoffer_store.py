from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('publications', '0009_whatsappgroup_send_authorized'),
    ]

    operations = [
        migrations.AddField(
            model_name='incomingaffiliateoffer',
            name='store',
            field=models.CharField(
                db_index=True,
                default='mercadolivre',
                max_length=32,
                verbose_name='Loja de origem',
            ),
        ),
    ]
