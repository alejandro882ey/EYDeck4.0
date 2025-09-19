#!/usr/bin/env python
import os
import django
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dashboard_django.settings')
django.setup()

from core_dashboard.models import RevenueEntry
from datetime import date

# Check data for the first report date
entries = RevenueEntry.objects.filter(date=date(2025, 7, 11))
print(f'Total entries for 2025-07-11: {entries.count()}')

# Count entries where diferencial_mtd is None but fytd_diferencial_final is not None
problematic_entries = entries.filter(diferencial_mtd__isnull=True, fytd_diferencial_final__isnull=False)
print(f'Entries with null diferencial_mtd but non-null fytd_diferencial_final: {problematic_entries.count()}')

# Fix the data by updating diferencial_mtd to equal fytd_diferencial_final for the first month
if problematic_entries.exists():
    print("Fixing diferencial_mtd values for first month...")
    
    updated_count = 0
    for entry in problematic_entries:
        entry.diferencial_mtd = entry.fytd_diferencial_final
        entry.save()
        updated_count += 1
    
    print(f"Updated {updated_count} entries")
    
    # Verify the fix
    print("\nAfter fix:")
    total_diferencial_mtd = sum([e.diferencial_mtd or 0 for e in entries])
    total_fytd_diferencial_final = sum([e.fytd_diferencial_final or 0 for e in entries])
    
    print(f'Sum of diferencial_mtd: {total_diferencial_mtd}')
    print(f'Sum of fytd_diferencial_final: {total_fytd_diferencial_final}')
    print(f'Values match: {abs(total_diferencial_mtd - total_fytd_diferencial_final) < 0.01}')

else:
    print("No problematic entries found")
