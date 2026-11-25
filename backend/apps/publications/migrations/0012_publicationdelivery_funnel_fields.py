from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('publications', '0011_storeclickstats'),
    ]

    operations = [
        migrations.AddField(
            model_name='publicationdelivery',
            name='is_bait',
            field=models.BooleanField(default=False, verbose_name='Oferta isca (captação VIP)'),
        ),
        migrations.AddField(
            model_name='publicationdelivery',
            name='tracking_channel',
            field=models.CharField(
                default='standard',
                max_length=32,
                verbose_name='Canal / Sub-ID de rastreamento',
            ),
        ),
    ]
