#!/usr/bin/env python
import os
import django
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dashboard_django.settings')
django.setup()

from core_dashboard.models import RevenueEntry
from core_dashboard.utils import get_fiscal_month_year
from datetime import date, timedelta

# Get all unique dates
dates = RevenueEntry.objects.values_list('date', flat=True).distinct().order_by('date')

print("Current report dates and their fiscal periods:")
for report_date in dates:
    fiscal_period = get_fiscal_month_year(report_date)
    day_of_week = report_date.strftime('%A')
    print(f"{report_date} ({day_of_week}) - Fiscal Period: {fiscal_period}")

print("\nAnalyzing fiscal month boundaries...")

# Analyze the pattern to understand when fiscal months change
previous_fiscal_period = None
for report_date in dates:
    fiscal_period = get_fiscal_month_year(report_date)
    if previous_fiscal_period and previous_fiscal_period != fiscal_period:
        print(f"Fiscal month change: {previous_fiscal_period} -> {fiscal_period} on {report_date}")
    previous_fiscal_period = fiscal_period
