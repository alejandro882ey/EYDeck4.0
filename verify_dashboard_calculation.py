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

# Check what the dashboard calculation will show
entries = RevenueEntry.objects.filter(date=date(2025, 7, 11))

# This is the calculation from views.py
macro_diferencial_mtd = abs(entries.aggregate(Sum('diferencial_mtd'))['diferencial_mtd__sum'] or 0)

print(f'Dashboard will show for Perdida Diferencial MTD: ${macro_diferencial_mtd:,.2f}')

# Compare with FYTD value
macro_diferencial_final = entries.aggregate(Sum('fytd_diferencial_final'))['fytd_diferencial_final__sum'] or 0
print(f'FYTD Diferencial Final sum: ${macro_diferencial_final:,.2f}')

print(f'Values match: {abs(macro_diferencial_mtd - abs(macro_diferencial_final)) < 0.01}')
