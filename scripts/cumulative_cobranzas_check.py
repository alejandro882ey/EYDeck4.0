import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
if 'DJANGO_SETTINGS_MODULE' not in os.environ:
    os.environ['DJANGO_SETTINGS_MODULE'] = 'dashboard_django.settings'

from core_dashboard.modules.cobranzas.services import CobranzasService

svc = CobranzasService()

def check(date_str):
    total = svc.get_cumulative_collected_up_to(date_str)
    print(f"Cumulative collected up to {date_str}: {total}")

if __name__ == '__main__':
    check('2025-07-11')
    check('2025-07-18')
