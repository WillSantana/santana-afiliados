import os
import sys

import django
from django.core.management import call_command


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'apps')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model


User = get_user_model()
if User.objects.filter(is_superuser=True).exists():
    print('Já existe um superusuário. Nenhuma senha foi alterada.')
else:
    call_command('createsuperuser')
