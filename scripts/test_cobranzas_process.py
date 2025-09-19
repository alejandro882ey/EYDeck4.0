import os
import sys
from pathlib import Path

BASE_DIR = r'c:\Users\CK624GF\OneDrive - EY\Documents\2025\dashboard_django'
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dashboard_django.settings')
import django
django.setup()

from core_dashboard.modules.cobranzas.services import CobranzasService

sample = r'C:\Users\CK624GF\OneDrive - EY\Documents\2025\Reports\cobranzas\FY26_11Jul_ Semana del 07 al 11 de Julio - IGTF 3%.xlsx'
svc = CobranzasService()
print('Processing sample:', sample)
with open(sample, 'rb') as f:
    res = svc.process_uploaded_file(f, original_filename='FY26_11Jul.xlsx')
print('Process result:')
print(res)
latest = svc.get_latest_file_info()
print('Latest file info:')
print(latest)
if latest:
    col, bill = svc.get_totals_from_file(latest['path'])
    print('Computed totals -> collected:', col, 'billed:', bill)
else:
    print('No processed file found in media.')
