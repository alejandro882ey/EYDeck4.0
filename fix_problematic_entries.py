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

# Find entries that have diferencial_mtd but no fytd_diferencial_final
problematic_entries = entries.filter(diferencial_mtd__isnull=False, fytd_diferencial_final__isnull=True)
print(f'Entries with diferencial_mtd but no fytd_diferencial_final: {problematic_entries.count()}')

if problematic_entries.exists():
    print("Sample problematic entries:")
    for entry in problematic_entries[:5]:
        print(f"ID {entry.id}: MTD={entry.diferencial_mtd}, Final={entry.fytd_diferencial_final}")
    
    # Fix by setting diferencial_mtd to 0 for entries without fytd_diferencial_final
    print(f"\nFixing {problematic_entries.count()} entries by setting diferencial_mtd to 0...")
    
    updated_count = 0
    for entry in problematic_entries:
        entry.diferencial_mtd = 0  # For first month, if no final value, MTD should be 0
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

# Double-check by counting entries
mtd_not_null = entries.filter(diferencial_mtd__isnull=False, diferencial_mtd__gt=0).count()
final_not_null = entries.filter(fytd_diferencial_final__isnull=False, fytd_diferencial_final__gt=0).count()
print(f'\nNon-zero diferencial_mtd entries: {mtd_not_null}')
print(f'Non-zero fytd_diferencial_final entries: {final_not_null}')
