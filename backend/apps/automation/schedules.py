"""
Configuração do Celery Beat para o Motor de Automação
Especificação V1.2 - Seções 3.1, 11.2 e 11.3
"""

from celery.schedules import crontab

AUTOMATION_BEAT_SCHEDULE = {
    # 6 Ciclos Diários de Pesquisa de Produtos: 08h, 10h, 12h, 14h, 16h e 18h
    'pesquisa-produtos-seis-vezes-dia': {
        'task': 'apps.automation.tasks.run_product_search',
        'schedule': crontab(
            minute=0,
            hour='8,10,12,14,16,18'
        ),
        'args': (0,),
    },

    # Monitoramento de Preços a cada 2 horas na janela diurna (08:30 às 20:30)
    'monitoramento-precos-janela-diurna': {
        'task': 'apps.automation.tasks.run_price_monitoring',
        'schedule': crontab(
            minute=30,
            hour='8,10,12,14,16,18,20'
        ),
        'args': (40,),
    },
}
