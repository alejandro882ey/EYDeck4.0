import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dashboard_django.settings')
django.setup()

from core_dashboard.models import RevenueEntry
from django.db.models import Sum

# Check managers containing Cardenas
print("Checking for Diana Cardenas in database...")
diana_entries = RevenueEntry.objects.filter(engagement_manager__icontains='cardenas')
print(f'Found {diana_entries.count()} entries for Cardenas managers')

if diana_entries.exists():
    sample = diana_entries.first()
    print(f'Sample manager name: "{sample.engagement_manager}"')
    print(f'Sample FYTD ANSR: {sample.fytd_ansr_sintetico}')
    print(f'Sample MTD ANSR: {sample.mtd_ansr_amt}')
    print(f'Sample date: {sample.date}')
    
    # Get totals
    totals = diana_entries.aggregate(fytd=Sum('fytd_ansr_sintetico'), mtd=Sum('mtd_ansr_amt'))
    print(f'Total FYTD ANSR: ${totals["fytd"]:,.2f}' if totals["fytd"] else 'Total FYTD ANSR: $0.00')
    print(f'Total MTD ANSR: ${totals["mtd"]:,.2f}' if totals["mtd"] else 'Total MTD ANSR: $0.00')
    
    # Show all unique manager names containing cardenas
    unique_managers = diana_entries.values_list('engagement_manager', flat=True).distinct()
    print(f'Unique manager names: {list(unique_managers)}')
else:
    print('No entries found for Cardenas')

# Also check what's available in Revenue Days managers
from core_dashboard.modules.manager_revenue_days import ManagerAnalyticsService

analytics = ManagerAnalyticsService()
revenue_managers = analytics.get_available_managers()
print(f'\nRevenue Days managers containing "cardenas":')
for manager in revenue_managers:
    if 'cardenas' in manager.lower():
        print(f'  - {manager}')
