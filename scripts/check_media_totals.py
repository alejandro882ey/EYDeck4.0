import os, sys
BASE_DIR = r'c:\Users\CK624GF\OneDrive - EY\Documents\2025\dashboard_django'
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','dashboard_django.settings')
django.setup()
from core_dashboard.modules.cobranzas.services import CobranzasService
svc=CobranzasService()
info=svc.get_latest_file_info()
print('Latest info:', info)
if info:
    col,bill=svc.get_totals_from_file(info['path'])
    print('Computed collected_total:', col)
    print('Computed billed_total (ignored by dashboard):', bill)
else:
    print('No processed file found.')
