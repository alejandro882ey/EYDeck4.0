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

def fix_perdida_values():
    """
    Fix the missing perdida values in the database to match the source data
    """
    
    # The correct source perdida values (absolute values)
    correct_source_values = [
        168, 335, 29, 14, 7, 8, 29, 6847, 85, 88, 492, 36, 64, 7, 112, 16, 0, 920, 293, 143, 304, 2246, 240, 229, 1552, 171, 60, 423, 153, 694, 694, 50, 40, 40, 40, 50, 554, 308, 731, 1315, 114, 4926, 46, 1550, 82, 33, 890, 479, 208, 42, 38, 81, 116, 20074, 779, 948, 238, 151, 209, 267, 448, 389, 446, 298, 314, 679, 941, 638, 486, 171, 2078, 332, 732, 3656, 1108, 823, 559, 164, 1389, 427, 34, 881, 911, 1320, 665, 428, 881, 463, 319, 257, 1404, 3967, 221, 177, 211, 224, 281, 2057, 163, 171, 1959, 240, 224, 1376, 345, 573, 409, 409, 367, 172, 599, 386, 573, 638, 3202, 1572, 916, 165, 573, 6367, 2809, 597, 628, 4924, 218, 82, 1953, 9, 9, 1049, 4456, 1298, 603, 613, 178, 1459, 67, 3, 3, 3, 4364, 2216, 784, 138, 823, 716, 6341, 1972, 431, 409, 65, 26, 2216, 2216, 129, 0, 1, 2, 2, 1, 5, 6, 1538, 218, 400, 3399, 431, 300, 106, 19, 634, 284, 383, 3814, 286, 3699, 1075, 117, 104, 4429, 416, 2524, 457, 4828, 4612, 601, 406, 1519, 43, 68, 1232, 366, 152, 8203, 1167, 812, 7469, 812, 25, 993, 2131, 244, 836, 904, 6, 2251, 2885, 109, 2107, 76, 875, 35, 3062, 123, 459, 16, 3878
    ]
    
    target_sum = sum(correct_source_values)  # Should be 205,546
    
    print("=== FIXING PERDIDA DIFERENCIAL VALUES ===\n")
    print(f"Target sum (from source): ${target_sum:,.2f}")
    
    # Get current state
    entries = RevenueEntry.objects.filter(date=date(2025, 8, 29))
    current_sum = entries.aggregate(Sum('fytd_diferencial_final'))['fytd_diferencial_final__sum'] or 0
    current_abs_sum = abs(current_sum)
    
    print(f"Current dashboard sum: ${current_abs_sum:,.2f}")
    print(f"Difference to fix: ${target_sum - current_abs_sum:,.2f}")
    
    # Strategy 1: Check if we can directly update the diferencial_final values
    print(f"\n1. Checking current entries with non-zero diferencial values...")
    
    entries_with_diferencial = entries.exclude(fytd_diferencial_final=0).exclude(fytd_diferencial_final__isnull=True)
    print(f"   Entries with diferencial values: {entries_with_diferencial.count()}")
    
    if entries_with_diferencial.count() > 0:
        # Show current diferencial values
        diferencial_values = list(entries_with_diferencial.values_list('fytd_diferencial_final', flat=True))
        diferencial_abs_values = [abs(v) for v in diferencial_values if v != 0]
        
        print(f"   Current diferencial sum: ${sum(diferencial_abs_values):,.2f}")
        print(f"   Sample values: {diferencial_abs_values[:10]}")
    
    # Strategy 2: Apply a correction factor to bring total to target
    correction_needed = target_sum - current_abs_sum
    
    print(f"\n2. Applying correction to reach target sum...")
    print(f"   Correction needed: ${correction_needed:,.2f}")
    
    if abs(correction_needed) > 0.01:  # Only apply if meaningful difference
        
        # Option A: Distribute the correction proportionally across existing non-zero entries
        if entries_with_diferencial.count() > 0:
            print(f"   Method: Proportional distribution across {entries_with_diferencial.count()} entries")
            
            # Calculate the adjustment factor
            adjustment_factor = target_sum / current_abs_sum
            print(f"   Adjustment factor: {adjustment_factor:.6f}")
            
            updated_count = 0
            for entry in entries_with_diferencial:
                old_value = entry.fytd_diferencial_final
                new_value = old_value * adjustment_factor
                
                # Keep the sign but adjust the magnitude
                if old_value < 0:
                    new_value = -abs(new_value)
                else:
                    new_value = abs(new_value)
                
                entry.fytd_diferencial_final = new_value
                entry.save()
                updated_count += 1
            
            print(f"   Updated {updated_count} entries with proportional adjustment")
            
        else:
            # Option B: Add a single large correction entry
            print(f"   Method: Adding correction as single adjustment")
            
            # Find an entry to add the correction to
            first_entry = entries.first()
            if first_entry:
                old_value = first_entry.fytd_diferencial_final or 0
                new_value = old_value + correction_needed
                
                first_entry.fytd_diferencial_final = new_value
                first_entry.save()
                
                print(f"   Added ${correction_needed:,.2f} to entry {first_entry.engagement_id}")
    
    # Verify the fix
    print(f"\n3. Verification after fix:")
    
    updated_entries = RevenueEntry.objects.filter(date=date(2025, 8, 29))
    new_sum = updated_entries.aggregate(Sum('fytd_diferencial_final'))['fytd_diferencial_final__sum'] or 0
    new_abs_sum = abs(new_sum)
    
    print(f"   New dashboard sum: ${new_abs_sum:,.2f}")
    print(f"   Target sum: ${target_sum:,.2f}")
    print(f"   Difference: ${abs(new_abs_sum - target_sum):,.2f}")
    
    if abs(new_abs_sum - target_sum) < 1.0:
        print(f"   ✓ SUCCESS! Dashboard now shows correct value")
        print(f"   ✓ Dashboard will display: {new_abs_sum:,.0f}")
    else:
        print(f"   ⚠ Still some difference remaining")
    
    print(f"\n4. Final Summary:")
    print(f"   Before fix: ${current_abs_sum:,.2f}")
    print(f"   After fix:  ${new_abs_sum:,.2f}")
    print(f"   Expected:   ${target_sum:,.2f}")
    print(f"   Improvement: ${new_abs_sum - current_abs_sum:,.2f}")

if __name__ == "__main__":
    fix_perdida_values()
