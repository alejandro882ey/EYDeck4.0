#!/usr/bin/env python
import os
import django
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dashboard_django.settings')
django.setup()

from core_dashboard.models import RevenueEntry
from core_dashboard.utils import get_fiscal_month_year
from datetime import date

def test_fiscal_month_logic(test_date):
    """Test the fiscal month logic for a given date"""
    
    # Get current fiscal period
    current_fiscal_period = get_fiscal_month_year(test_date)
    print(f"Testing date: {test_date}")
    print(f"Current fiscal period: {current_fiscal_period}")
    
    # Get all unique dates and find the last one from previous fiscal month
    all_dates = RevenueEntry.objects.values_list('date', flat=True).distinct().order_by('date')
    
    last_report_prev_fiscal_month = None
    for report_date in all_dates:
        if report_date >= test_date:
            break
        report_fiscal_period = get_fiscal_month_year(report_date)
        if report_fiscal_period != current_fiscal_period:
            last_report_prev_fiscal_month = report_date
    
    print(f"Last report from previous fiscal month: {last_report_prev_fiscal_month}")
    
    if last_report_prev_fiscal_month:
        # Get some sample data to show the difference calculation
        last_month_entries = RevenueEntry.objects.filter(
            date=last_report_prev_fiscal_month
        ).values('engagement_id', 'fytd_diferencial_final')[:5]
        
        current_month_entries = RevenueEntry.objects.filter(
            date=test_date
        ).values('engagement_id', 'fytd_diferencial_final')[:5]
        
        print("\nSample MTD calculations:")
        current_dict = {e['engagement_id']: e['fytd_diferencial_final'] or 0 for e in current_month_entries}
        last_dict = {e['engagement_id']: e['fytd_diferencial_final'] or 0 for e in last_month_entries}
        
        for eng_id in list(current_dict.keys())[:3]:
            current_val = current_dict.get(eng_id, 0)
            last_val = last_dict.get(eng_id, 0)
            mtd_val = current_val - last_val
            print(f"  Engagement {eng_id}: Current={current_val}, Previous={last_val}, MTD={mtd_val}")
        
        # Calculate total MTD
        total_current = sum([e['fytd_diferencial_final'] or 0 for e in RevenueEntry.objects.filter(date=test_date).values('fytd_diferencial_final')])
        total_last = sum([e['fytd_diferencial_final'] or 0 for e in RevenueEntry.objects.filter(date=last_report_prev_fiscal_month).values('fytd_diferencial_final')])
        total_mtd = total_current - total_last
        
        print(f"\nTotal calculations:")
        print(f"  Current fiscal month total: ${total_current:,.2f}")
        print(f"  Previous fiscal month total: ${total_last:,.2f}")
        print(f"  Calculated MTD: ${total_mtd:,.2f}")
    else:
        print("No previous fiscal month data found")

# Test with the first August report
test_fiscal_month_logic(date(2025, 8, 8))
