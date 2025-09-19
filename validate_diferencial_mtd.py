#!/usr/bin/env python
"""
Data validation and fix script for diferencial_mtd values.
This script ensures that for the first fiscal month (July), diferencial_mtd equals fytd_diferencial_final.
"""
import os
import django
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dashboard_django.settings')
django.setup()

from core_dashboard.models import RevenueEntry
from core_dashboard.utils import get_fiscal_month_year
from django.db.models import Sum
from datetime import date

def validate_and_fix_diferencial_mtd():
    """Validate and fix diferencial_mtd values for all fiscal months."""
    
    # Get all unique dates
    unique_dates = RevenueEntry.objects.values_list('date', flat=True).distinct().order_by('date')
    
    for report_date in unique_dates:
        entries = RevenueEntry.objects.filter(date=report_date)
        
        # Get fiscal period information
        fiscal_period = get_fiscal_month_year(report_date)
        fiscal_month_name = fiscal_period.split(' ')[0]
        is_first_fiscal_month = fiscal_month_name == 'Julio'
        
        print(f"\nProcessing {report_date} (Fiscal Period: {fiscal_period})")
        
        if is_first_fiscal_month:
            print("  First fiscal month - validating diferencial_mtd = fytd_diferencial_final")
            
            # For first month, diferencial_mtd should equal fytd_diferencial_final
            # or both should be null/0
            
            # Fix entries that have fytd_diferencial_final but different diferencial_mtd
            entries_to_fix = []
            for entry in entries:
                if entry.fytd_diferencial_final is not None:
                    if entry.diferencial_mtd != entry.fytd_diferencial_final:
                        entries_to_fix.append(entry)
                        entry.diferencial_mtd = entry.fytd_diferencial_final
                elif entry.diferencial_mtd is not None and entry.diferencial_mtd != 0:
                    # If no fytd_diferencial_final but has diferencial_mtd, set to 0
                    entries_to_fix.append(entry)
                    entry.diferencial_mtd = 0
            
            if entries_to_fix:
                print(f"    Fixing {len(entries_to_fix)} entries")
                for entry in entries_to_fix:
                    entry.save()
            else:
                print("    No fixes needed")
        
        # Calculate sums for verification
        total_diferencial_mtd = entries.aggregate(Sum('diferencial_mtd'))['diferencial_mtd__sum'] or 0
        total_fytd_diferencial_final = entries.aggregate(Sum('fytd_diferencial_final'))['fytd_diferencial_final__sum'] or 0
        
        print(f"    diferencial_mtd sum: ${total_diferencial_mtd:,.2f}")
        print(f"    fytd_diferencial_final sum: ${total_fytd_diferencial_final:,.2f}")
        
        if is_first_fiscal_month:
            if abs(total_diferencial_mtd - total_fytd_diferencial_final) < 0.01:
                print("    ✓ Values match correctly")
            else:
                print("    ✗ Values don't match - there may be an issue")

if __name__ == "__main__":
    validate_and_fix_diferencial_mtd()
    print("\nValidation and fix complete!")
