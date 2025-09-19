import os
import django
from datetime import datetime, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dashboard_django.settings')
django.setup()

from core_dashboard.models import RevenueEntry

def debug_diana_database():
    manager_name = "Cardenas, Diana"
    selected_date = datetime(2025, 7, 11).date()
    
    print(f"=== Database Analysis for {manager_name} ===")
    print(f"Selected date: {selected_date}")
    
    # Get all entries for Diana
    all_diana_entries = RevenueEntry.objects.filter(engagement_manager=manager_name)
    print(f"Total Diana entries in database: {all_diana_entries.count()}")
    
    if all_diana_entries.count() > 0:
        # Show unique dates
        unique_dates = all_diana_entries.values_list('date', flat=True).distinct().order_by('date')
        print(f"Unique dates for Diana: {list(unique_dates)}")
        
        # Calculate week range for 2025-07-11
        friday_date = selected_date
        start_of_week = friday_date - timedelta(days=friday_date.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        print(f"Week range: {start_of_week} to {end_of_week}")
        
        # Filter for the specific week
        week_entries = all_diana_entries.filter(date__range=[start_of_week, end_of_week])
        print(f"Entries in week range: {week_entries.count()}")
        
        if week_entries.count() > 0:
            print("\n=== Week entries details ===")
            for entry in week_entries[:10]:  # Show first 10
                print(f"Date: {entry.date}, Client: {entry.client}, Engagement: {entry.engagement}")
                print(f"  FYTD ANSR: {entry.fytd_ansr_sintetico}, MTD ANSR: {entry.mtd_ansr_amt}")
                print(f"  FYTD Hours: {entry.fytd_charged_hours}, MTD Hours: {entry.mtd_charged_hours}")
                print()
            
            # Calculate totals
            from django.db.models import Sum
            totals = week_entries.aggregate(
                fytd_ansr_total=Sum('fytd_ansr_sintetico'),
                mtd_ansr_total=Sum('mtd_ansr_amt'),
                fytd_hours_total=Sum('fytd_charged_hours'),
                mtd_hours_total=Sum('mtd_charged_hours')
            )
            print("=== Week totals ===")
            print(f"FYTD ANSR Total: ${totals['fytd_ansr_total']:.2f}")
            print(f"MTD ANSR Total: ${totals['mtd_ansr_total']:.2f}")
            print(f"FYTD Hours Total: {totals['fytd_hours_total']}")
            print(f"MTD Hours Total: {totals['mtd_hours_total']}")
            
        # Also check what the expected values should be based on all data
        print("\n=== All-time totals (for comparison) ===")
        all_totals = all_diana_entries.aggregate(
            fytd_ansr_total=Sum('fytd_ansr_sintetico'),
            mtd_ansr_total=Sum('mtd_ansr_amt'),
            fytd_hours_total=Sum('fytd_charged_hours'),
            mtd_hours_total=Sum('mtd_charged_hours')
        )
        print(f"All-time FYTD ANSR: ${all_totals['fytd_ansr_total']:.2f}")
        print(f"All-time MTD ANSR: ${all_totals['mtd_ansr_total']:.2f}")
        print(f"All-time FYTD Hours: {all_totals['fytd_hours_total']}")
        print(f"All-time MTD Hours: {all_totals['mtd_hours_total']}")
        
        # Check for the exact date 2025-07-11
        exact_date_entries = all_diana_entries.filter(date=selected_date)
        print(f"\n=== Entries for exact date {selected_date}: {exact_date_entries.count()} ===")
        if exact_date_entries.count() > 0:
            exact_totals = exact_date_entries.aggregate(
                fytd_ansr_total=Sum('fytd_ansr_sintetico'),
                mtd_ansr_total=Sum('mtd_ansr_amt')
            )
            print(f"Exact date FYTD ANSR: ${exact_totals['fytd_ansr_total']:.2f}")
            print(f"Exact date MTD ANSR: ${exact_totals['mtd_ansr_total']:.2f}")

if __name__ == "__main__":
    debug_diana_database()
