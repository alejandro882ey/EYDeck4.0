"""
Script to print daily COBRANZAS aggregates using CobranzasService.
Run from the project root:
    python scripts\check_cobranzas_daily.py

This script loads Django settings and prints per-day USD and VES-equivalent totals.
"""
import os
import django
import json

# configure Django environment
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dashboard_django.settings')
try:
    django.setup()
except Exception:
    # attempt alternate settings path
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dashboard_django.settings')
    django.setup()

from core_dashboard.modules.cobranzas.services import CobranzasService

svc = CobranzasService()
series = svc.get_daily_collections_and_rates()

print('Dates:', len(series.get('dates', [])))
for d, u, v in zip(series.get('dates', []), series.get('daily_usd', []), series.get('daily_ves_equiv_usd', [])):
    print(f"{d}: USD={u:.2f}, VES_equiv_USD={v:.2f}, total={(u+v):.2f}")

# print sample for 2025-07-07 if present
sdate = '2025-07-07'
if sdate in series.get('dates', []):
    idx = series['dates'].index(sdate)
    print('\nSample for', sdate)
    print('USD:', series['daily_usd'][idx])
    print('VES_equiv_USD:', series['daily_ves_equiv_usd'][idx])
    print('Total:', series['daily_usd'][idx] + series['daily_ves_equiv_usd'][idx])
else:
    print('\nNo data for', sdate)

# optionally write JSON to media for inspection
out = os.path.join(svc.media_folder, 'cobranzas_daily_series.json')
with open(out, 'w', encoding='utf-8') as f:
    json.dump(series, f, ensure_ascii=False, indent=2)
print('\nWrote series to', out)
