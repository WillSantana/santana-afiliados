import os
import sys
import django
from decimal import Decimal

# Setup Django environment
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'apps')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.catalog.models import ProductOffer, ProductStatus, CategoryChoices
from apps.publications.models import Publication, PublicationStatus
from apps.analytics.models import DailyMetricSnapshot
from django.utils import timezone

def seed():
    print("Populando catálogo com ofertas demonstrativas da Especificação...")

    demo_products = [
        {
            "item_id": "MLB123456789",
            "title": "Controle Sem Fio para Xbox Series X/S e PC",
            "category": CategoryChoices.TECHNOLOGY,
            "price": Decimal("149.90"),
            "original_price": Decimal("199.90"),
            "product_url": "https://lista.mercadolivre.com.br/controle-sem-fio-xbox",
            "affiliate_url": "",
            "thumbnail": "https://images.unsplash.com/photo-1600080972464-8e5f35f63d08?auto=format&fit=crop&w=600&q=80",
            "seller_id": "99887766",
            "seller_reputation": "green",
            "condition": "new",
            "status": ProductStatus.PENDING,
        },
        {
            "item_id": "MLB987654321",
            "title": "Fone de Ouvido Bluetooth Sem Fio com Cancelamento de Ruído",
            "category": CategoryChoices.TECHNOLOGY,
            "price": Decimal("89.90"),
            "original_price": Decimal("129.90"),
            "product_url": "https://lista.mercadolivre.com.br/fone-de-ouvido-bluetooth-sem-fio",
            "affiliate_url": "https://mercadolivre.com/sec/exemplo-fone",
            "thumbnail": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=600&q=80",
            "seller_id": "11223344",
            "seller_reputation": "green",
            "condition": "new",
            "status": ProductStatus.APPROVED,
        },
        {
            "item_id": "MLB554433221",
            "title": "Tênis Masculino Esportivo Corrida e Treino Amortecimento",
            "category": CategoryChoices.FASHION,
            "price": Decimal("179.90"),
            "original_price": Decimal("249.90"),
            "product_url": "https://lista.mercadolivre.com.br/tenis-masculino-esportivo-corrida",
            "affiliate_url": "",
            "thumbnail": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=600&q=80",
            "seller_id": "33445566",
            "seller_reputation": "green",
            "condition": "new",
            "status": ProductStatus.PENDING,
        },
        {
            "item_id": "MLB112233445",
            "title": "Organizador Doméstico Multiuso com Gavetas Práticas",
            "category": CategoryChoices.HOME,
            "price": Decimal("69.90"),
            "original_price": Decimal("89.90"),
            "product_url": "https://lista.mercadolivre.com.br/organizador-domestico-multiuso-gavetas",
            "affiliate_url": "",
            "thumbnail": "https://images.unsplash.com/photo-1584622650111-993a426fbf0a?auto=format&fit=crop&w=600&q=80",
            "seller_id": "55667788",
            "seller_reputation": "green",
            "condition": "new",
            "status": ProductStatus.PENDING,
        },
        {
            "item_id": "MLB667788990",
            "title": "Máquina Profissional de Cortar Cabelo e Barba Sem Fio",
            "category": CategoryChoices.BEAUTY,
            "price": Decimal("119.90"),
            "original_price": Decimal("159.90"),
            "product_url": "https://lista.mercadolivre.com.br/maquina-cortar-cabelo-barba-sem-fio",
            "affiliate_url": "https://mercadolivre.com/sec/exemplo-maquina",
            "thumbnail": "https://images.unsplash.com/photo-1621607512214-68297480165e?auto=format&fit=crop&w=600&q=80",
            "seller_id": "77889900",
            "seller_reputation": "green",
            "condition": "new",
            "status": ProductStatus.APPROVED,
        }
    ]

    for p_data in demo_products:
        item_id = p_data.pop('item_id')
        p, created = ProductOffer.objects.get_or_create(item_id=item_id, defaults=p_data)
        p.calculate_score()
        p.save()

    # Cria publicação demonstrativa para o produto aprovado
    prod_fone = ProductOffer.objects.filter(item_id="MLB987654321").first()
    if prod_fone:
        pub, created = Publication.objects.get_or_create(
            product=prod_fone,
            defaults={
                "title": "OFERTA DO DIA!",
                "message_text": Publication.generate_message_text(prod_fone),
                "channel": "whatsapp",
                "status": PublicationStatus.PUBLISHED,
                "clicks_count": 34,
                "published_at": timezone.now()
            }
        )

    # Cria snapshot de métricas
    today = timezone.now().date()
    DailyMetricSnapshot.objects.get_or_create(
        date=today,
        defaults={
            "products_found": 15,
            "products_approved": 2,
            "products_rejected": 1,
            "links_registered": 2,
            "offers_published": 1,
            "clicks": 34,
            "sales": 1,
            "estimated_commission": Decimal("8.00"),
            "approved_commission": Decimal("8.00"),
        }
    )

    print("Carga inicial concluída com sucesso!")

if __name__ == '__main__':
    seed()
