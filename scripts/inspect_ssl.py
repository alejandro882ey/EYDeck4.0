import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dashboard_django.settings')
django.setup()

from core_dashboard.models import RevenueEntry
from core_dashboard.modules.sub_service_line_cards.services import SubServiceLineCardsService
from datetime import datetime, timedelta

vals = list(
    RevenueEntry.objects
    .values_list('engagement_sub_service_line', flat=True)
    .distinct()
    .exclude(engagement_sub_service_line__isnull=True)
    .exclude(engagement_sub_service_line__exact='')
    .order_by('engagement_sub_service_line')[:20]
)
print('SSL_VALUES', vals)
if vals:
    friday_date = datetime.strptime('2025-08-29', '%Y-%m-%d').date()
    # compute monday..sunday week containing friday_date
    start = friday_date - timedelta(days=friday_date.weekday())
    end = start + timedelta(days=6)
    svc = SubServiceLineCardsService()
    print('WEEK', start, end)
    print('SSL_TEST', svc.get_cards_for_ssl(vals[0], start_date=start, end_date=end))
