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

# Check all combinations of null/non-null values
mtd_null_final_null = entries.filter(diferencial_mtd__isnull=True, fytd_diferencial_final__isnull=True).count()
mtd_null_final_not_null = entries.filter(diferencial_mtd__isnull=True, fytd_diferencial_final__isnull=False).count()
mtd_not_null_final_null = entries.filter(diferencial_mtd__isnull=False, fytd_diferencial_final__isnull=True).count()
mtd_not_null_final_not_null = entries.filter(diferencial_mtd__isnull=False, fytd_diferencial_final__isnull=False).count()

print(f"MTD null, Final null: {mtd_null_final_null}")
print(f"MTD null, Final not null: {mtd_null_final_null}")
print(f"MTD not null, Final null: {mtd_not_null_final_null}")
print(f"MTD not null, Final not null: {mtd_not_null_final_not_null}")

# For the first month, ALL entries with non-null fytd_diferencial_final should have diferencial_mtd = fytd_diferencial_final
print("\nFixing ALL entries for first month...")

# Update all entries to have diferencial_mtd = fytd_diferencial_final where fytd_diferencial_final is not null
entries_to_fix = entries.filter(fytd_diferencial_final__isnull=False)
print(f"Entries with non-null fytd_diferencial_final: {entries_to_fix.count()}")

updated_count = 0
for entry in entries_to_fix:
    entry.diferencial_mtd = entry.fytd_diferencial_final
    entry.save()
    updated_count += 1

print(f"Updated {updated_count} entries")

# Verify the fix
print("\nAfter comprehensive fix:")
total_diferencial_mtd = sum([e.diferencial_mtd or 0 for e in entries])
total_fytd_diferencial_final = sum([e.fytd_diferencial_final or 0 for e in entries])

print(f'Sum of diferencial_mtd: {total_diferencial_mtd}')
print(f'Sum of fytd_diferencial_final: {total_fytd_diferencial_final}')
print(f'Values match: {abs(total_diferencial_mtd - total_fytd_diferencial_final) < 0.01}')

# Also fix entries where both are null (set both to 0)
null_entries = entries.filter(diferencial_mtd__isnull=True, fytd_diferencial_final__isnull=True)
if null_entries.exists():
    print(f"\nSetting {null_entries.count()} entries with both null values to 0")
    for entry in null_entries:
        entry.diferencial_mtd = 0
        if entry.fytd_diferencial_final is None:
            entry.fytd_diferencial_final = 0
        entry.save()
