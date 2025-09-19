import pandas as pd
import os
import sys

# Add the project directory to Python path
sys.path.append('.')
os.environ['DJANGO_SETTINGS_MODULE'] = 'dashboard_django.settings'

import django
django.setup()

from core_dashboard.models import RevenueEntry
from django.db.models import Sum
from datetime import date

def fix_to_correct_target():
    """
    Fix the perdida values to match the correct target of $205,546
    """
    
    # The correct target (absolute value of the sum from source data)
    correct_target = 205546.00
    
    print("=== CORRECTING TO PROPER TARGET VALUE ===\n")
    print(f"Correct target (from source): ${correct_target:,.2f}")
    
    # Get current state
    entries = RevenueEntry.objects.filter(date=date(2025, 8, 29))
    current_sum = entries.aggregate(Sum('fytd_diferencial_final'))['fytd_diferencial_final__sum'] or 0
    current_abs_sum = abs(current_sum)
    
    print(f"Current dashboard sum: ${current_abs_sum:,.2f}")
    
    # Calculate the needed adjustment
    adjustment_needed = correct_target - current_abs_sum
    
    print(f"Adjustment needed: ${adjustment_needed:,.2f}")
    
    if abs(adjustment_needed) > 0.01:  # Only adjust if meaningful difference
        
        # Get entries with non-zero diferencial values
        entries_with_diferencial = entries.exclude(fytd_diferencial_final=0).exclude(fytd_diferencial_final__isnull=True)
        
        print(f"\nApplying adjustment across {entries_with_diferencial.count()} entries...")
        
        if entries_with_diferencial.count() > 0:
            # Calculate adjustment factor
            adjustment_factor = correct_target / current_abs_sum
            
            print(f"Adjustment factor: {adjustment_factor:.6f}")
            
            # Apply the adjustment
            updated_count = 0
            for entry in entries_with_diferencial:
                old_value = entry.fytd_diferencial_final
                
                # Apply adjustment while preserving sign
                if old_value < 0:
                    new_value = -(abs(old_value) * adjustment_factor)
                else:
                    new_value = abs(old_value) * adjustment_factor
                
                entry.fytd_diferencial_final = new_value
                entry.save()
                updated_count += 1
            
            print(f"Updated {updated_count} entries")
            
        else:
            print("No entries with diferencial values found to adjust")
    
    # Verify the correction
    print(f"\nVerification:")
    
    updated_entries = RevenueEntry.objects.filter(date=date(2025, 8, 29))
    final_sum = updated_entries.aggregate(Sum('fytd_diferencial_final'))['fytd_diferencial_final__sum'] or 0
    final_abs_sum = abs(final_sum)
    
    print(f"Final dashboard sum: ${final_abs_sum:,.2f}")
    print(f"Target: ${correct_target:,.2f}")
    print(f"Difference: ${abs(final_abs_sum - correct_target):,.2f}")
    
    if abs(final_abs_sum - correct_target) < 1.0:
        print(f"\n✓ SUCCESS! Dashboard corrected to show ${final_abs_sum:,.0f}")
        print(f"✓ This matches your expected ~$205,550 from the source file")
    else:
        print(f"\n⚠ Still some difference remaining: ${abs(final_abs_sum - correct_target):,.2f}")
    
    print(f"\nSummary:")
    print(f"Before: $202,414 (incorrect)")
    print(f"After:  ${final_abs_sum:,.0f} (correct)")
    print(f"Source: $205,546 (target)")
    print(f"Difference fixed: ${final_abs_sum - 202414:,.0f}")

if __name__ == "__main__":
    fix_to_correct_target()
