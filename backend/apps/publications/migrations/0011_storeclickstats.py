from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('publications', '0010_incomingaffiliateoffer_store'),
    ]

    operations = [
        migrations.CreateModel(
            name='StoreClickStats',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('store', models.CharField(max_length=32, unique=True, verbose_name='Loja / Marketplace')),
                ('clicks_today', models.PositiveIntegerField(default=0, verbose_name='Cliques hoje')),
                ('clicks_month', models.PositiveIntegerField(default=0, verbose_name='Cliques no período/mês')),
                ('orders_month', models.PositiveIntegerField(default=0, verbose_name='Pedidos no período/mês')),
                ('last_synced_at', models.DateTimeField(blank=True, null=True, verbose_name='Última sincronização')),
                ('sync_error', models.TextField(blank=True, verbose_name='Último aviso de sincronização')),
            ],
            options={
                'verbose_name': 'Cliques oficiais por loja',
                'verbose_name_plural': 'Cliques oficiais por loja',
            },
        ),
    ]
