#!/usr/bin/env python
import os
import django
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dashboard_django.settings')
django.setup()

from core_dashboard.models import RevenueEntry
from django.db.models import Sum
from datetime import date

# Check August MTD value as it would appear in dashboard
august_entries = RevenueEntry.objects.filter(date=date(2025, 8, 8))
macro_diferencial_mtd = abs(august_entries.aggregate(Sum('diferencial_mtd'))['diferencial_mtd__sum'] or 0)

print(f'Dashboard will show for Perdida Diferencial MTD (August): ${macro_diferencial_mtd:,.2f}')

# Show what it was before the fix (should be different)
print(f'FYTD Diferencial Final sum (August): ${august_entries.aggregate(Sum("fytd_diferencial_final"))["fytd_diferencial_final__sum"] or 0:,.2f}')

# Verify July values are still correct
july_entries = RevenueEntry.objects.filter(date=date(2025, 8, 1))  # Last July report
july_mtd = abs(july_entries.aggregate(Sum('diferencial_mtd'))['diferencial_mtd__sum'] or 0)
july_fytd = july_entries.aggregate(Sum('fytd_diferencial_final'))['fytd_diferencial_final__sum'] or 0

print(f'\nJuly end (2025-08-01):')
print(f'Dashboard MTD: ${july_mtd:,.2f}')
print(f'FYTD Total: ${july_fytd:,.2f}')
print(f'July values match: {abs(july_mtd - abs(july_fytd)) < 0.01}')
