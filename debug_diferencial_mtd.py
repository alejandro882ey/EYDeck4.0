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

# Get all unique values and their counts
from django.db.models import Q

# Check all combinations more carefully
total_entries = entries.count()
mtd_not_null = entries.filter(diferencial_mtd__isnull=False).count()
final_not_null = entries.filter(fytd_diferencial_final__isnull=False).count()

print(f"Total entries: {total_entries}")
print(f"Entries with non-null diferencial_mtd: {mtd_not_null}")
print(f"Entries with non-null fytd_diferencial_final: {final_not_null}")

# Get actual sums
total_diferencial_mtd = 0
total_fytd_diferencial_final = 0
mtd_count = 0
final_count = 0

for entry in entries:
    if entry.diferencial_mtd is not None:
        total_diferencial_mtd += entry.diferencial_mtd
        mtd_count += 1
    if entry.fytd_diferencial_final is not None:
        total_fytd_diferencial_final += entry.fytd_diferencial_final
        final_count += 1

print(f"\nActual counts:")
print(f"diferencial_mtd non-null entries: {mtd_count}")
print(f"fytd_diferencial_final non-null entries: {final_count}")
print(f"diferencial_mtd sum: {total_diferencial_mtd}")
print(f"fytd_diferencial_final sum: {total_fytd_diferencial_final}")

# Show sample records with both values
print("\nSample entries with both values:")
sample_entries = entries.filter(diferencial_mtd__isnull=False, fytd_diferencial_final__isnull=False)[:5]
for i, entry in enumerate(sample_entries):
    print(f"Entry {i+1}: MTD={entry.diferencial_mtd}, Final={entry.fytd_diferencial_final}, Match={entry.diferencial_mtd == entry.fytd_diferencial_final}")

# Check if we need to update all entries with fytd_diferencial_final to have matching diferencial_mtd
print(f"\nEntries that need fixing (have final but MTD doesn't match):")
mismatch_count = 0
for entry in entries.filter(fytd_diferencial_final__isnull=False):
    if entry.diferencial_mtd != entry.fytd_diferencial_final:
        mismatch_count += 1
        if mismatch_count <= 5:  # Show first 5 mismatches
            print(f"ID {entry.id}: MTD={entry.diferencial_mtd}, Final={entry.fytd_diferencial_final}")

print(f"Total mismatched entries: {mismatch_count}")

# Fix all mismatches for the first month
if mismatch_count > 0:
    print(f"\nFixing {mismatch_count} mismatched entries...")
    fixed_count = 0
    for entry in entries.filter(fytd_diferencial_final__isnull=False):
        if entry.diferencial_mtd != entry.fytd_diferencial_final:
            entry.diferencial_mtd = entry.fytd_diferencial_final
            entry.save()
            fixed_count += 1
    
    print(f"Fixed {fixed_count} entries")
    
    # Recalculate sums
    total_diferencial_mtd_after = sum([e.diferencial_mtd or 0 for e in entries])
    total_fytd_diferencial_final_after = sum([e.fytd_diferencial_final or 0 for e in entries])
    
    print(f"\nAfter fix:")
    print(f"diferencial_mtd sum: {total_diferencial_mtd_after}")
    print(f"fytd_diferencial_final sum: {total_fytd_diferencial_final_after}")
    print(f"Values match: {abs(total_diferencial_mtd_after - total_fytd_diferencial_final_after) < 0.01}")
