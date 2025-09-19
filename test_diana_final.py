import sys, os, django
from datetime import date
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dashboard_django.settings')
django.setup()
from core_dashboard.modules.manager_revenue_days import ManagerAnalyticsService

analytics = ManagerAnalyticsService()
diana_kpis = analytics.get_manager_kpis('Cardenas, Diana', date(2025, 7, 11))

if diana_kpis:
    print('Diana Cardenas KPIs:')
    print(f'  FYTD ANSR: ${diana_kpis["manager_fytd_ansr_value"]:,.2f}')
    print(f'  MTD ANSR: ${diana_kpis["manager_mtd_ansr_value"]:,.2f}')
    print(f'  FYTD Hours: {diana_kpis["manager_fytd_charged_hours"]:,.1f}')
    print(f'  MTD Hours: {diana_kpis["manager_mtd_charged_hours"]:,.1f}')
    print(f'  Revenue Days: {diana_kpis["revenue_days"]:,.1f}')
    print(f'  Clients: {diana_kpis["num_clients"]}')
    print(f'  Engagements: {diana_kpis["num_engagements"]}')
    
    # Check if values match expected
    expected_fytd_ansr = 1895
    expected_mtd_ansr = 2322
    
    print(f'\nExpected vs Actual:')
    print(f'  FYTD ANSR - Expected: ${expected_fytd_ansr:,.2f}, Actual: ${diana_kpis["manager_fytd_ansr_value"]:,.2f}')
    print(f'  MTD ANSR - Expected: ${expected_mtd_ansr:,.2f}, Actual: ${diana_kpis["manager_mtd_ansr_value"]:,.2f}')
    
    if abs(diana_kpis["manager_fytd_ansr_value"] - expected_fytd_ansr) < 1:
        print('  FYTD ANSR matches expected value! ✓')
    else:
        print('  FYTD ANSR does not match expected value')
        
    if abs(diana_kpis["manager_mtd_ansr_value"] - expected_mtd_ansr) < 1:
        print('  MTD ANSR matches expected value! ✓')
    else:
        print('  MTD ANSR does not match expected value')
else:
    print('Failed to get Diana Cardenas KPIs')
