import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dashboard_django.settings')
django.setup()

from core_dashboard.models import RevenueEntry
from django.db.models import Sum

# Check Diana Cardenas entries in detail
diana_entries = RevenueEntry.objects.filter(engagement_manager='Cardenas, Diana').order_by('date')
print(f"Total entries for 'Cardenas, Diana': {diana_entries.count()}")

print("\nFirst 5 entries:")
for entry in diana_entries[:5]:
    print(f"Date: {entry.date}, FYTD: {entry.fytd_ansr_sintetico}, MTD: {entry.mtd_ansr_amt}, Contract: {entry.contract.name if entry.contract else 'N/A'}")

# Check if there are entries with specific values mentioned by user
entries_with_1895 = diana_entries.filter(fytd_ansr_sintetico=1895)
entries_with_2322 = diana_entries.filter(mtd_ansr_amt=2322)

print(f"\nEntries with FYTD=1895: {entries_with_1895.count()}")
print(f"Entries with MTD=2322: {entries_with_2322.count()}")

# Check entries for specific date 2025-07-11
date_entries = diana_entries.filter(date='2025-07-11')
print(f"\nEntries for 2025-07-11: {date_entries.count()}")

if date_entries.exists():
    print("2025-07-11 entries:")
    for entry in date_entries:
        print(f"  FYTD: {entry.fytd_ansr_sintetico}, MTD: {entry.mtd_ansr_amt}, Contract: {entry.contract.name if entry.contract else 'N/A'}")
    
    # Sum for this date
    totals = date_entries.aggregate(fytd=Sum('fytd_ansr_sintetico'), mtd=Sum('mtd_ansr_amt'))
    print(f"  Date totals - FYTD: ${totals['fytd']:.2f}, MTD: ${totals['mtd']:.2f}")

# Test the analytics service with Diana
print("\n--- Testing Analytics Service ---")
from core_dashboard.modules.manager_revenue_days import ManagerAnalyticsService
from datetime import date

analytics = ManagerAnalyticsService()
diana_kpis = analytics.get_manager_kpis('Cardenas, Diana', date(2025, 7, 11))

if diana_kpis:
    print(f"Analytics Service Results:")
    print(f"  FYTD ANSR: ${diana_kpis['manager_fytd_ansr_value']:.2f}")
    print(f"  MTD ANSR: ${diana_kpis['manager_mtd_ansr_value']:.2f}")
else:
    print("Analytics service returned None")
