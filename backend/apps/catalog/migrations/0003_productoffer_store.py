from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0002_alter_productoffer_category_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='productoffer',
            name='store',
            field=models.CharField(
                db_index=True,
                default='mercadolivre',
                max_length=32,
                verbose_name='Loja / Marketplace',
            ),
        ),
    ]
