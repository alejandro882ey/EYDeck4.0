import os
import django
from datetime import datetime, timedelta
import pandas as pd

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dashboard_django.settings')
django.setup()

from core_dashboard.modules.manager_revenue_days.analytics import ManagerAnalyticsService

def debug_diana_dates():
    service = ManagerAnalyticsService()
    
    # Get the date being used (2025-07-11 as mentioned by user)
    selected_date = datetime(2025, 7, 11).date()
    print(f"Selected date: {selected_date}")
    
    # Get the week range calculation
    friday_date = selected_date
    start_of_week = friday_date - timedelta(days=friday_date.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    print(f"Week range: {start_of_week} to {end_of_week}")
    
    # Get Diana's data with debugging
    manager_name = "Diana Cardenas"
    
    # Load Revenue Days data
    print("\n=== Loading Revenue Days data ===")
    revenue_data = service._get_revenue_days_data(manager_name)
    diana_entries = revenue_data[revenue_data['Manager Name'] == manager_name]
    print(f"Total Diana entries in Revenue Days: {len(diana_entries)}")
    
    if len(diana_entries) > 0:
        print("\nDiana's Revenue Days entries:")
        for idx, row in diana_entries.iterrows():
            print(f"  Date: {row.get('Week Ending', 'N/A')}, ANSR: {row.get('FYTD_ANSR_Sintetico', 'N/A')}, Country: {row.get('Employee Country/Region', 'N/A')}")
    
    # Test date filtering
    print(f"\n=== Filtering by date range: {start_of_week} to {end_of_week} ===")
    if 'Week Ending' in revenue_data.columns:
        revenue_data['Week Ending'] = pd.to_datetime(revenue_data['Week Ending']).dt.date
        date_filtered = revenue_data[
            (revenue_data['Week Ending'] >= start_of_week) & 
            (revenue_data['Week Ending'] <= end_of_week)
        ]
        print(f"Total entries in date range: {len(date_filtered)}")
        
        diana_date_filtered = date_filtered[date_filtered['Manager Name'] == manager_name]
        print(f"Diana entries in date range: {len(diana_date_filtered)}")
        
        if len(diana_date_filtered) > 0:
            print("\nDiana's filtered entries:")
            for idx, row in diana_date_filtered.iterrows():
                print(f"  Date: {row['Week Ending']}, FYTD ANSR: {row.get('FYTD_ANSR_Sintetico', 'N/A')}, MTD ANSR: {row.get('MTD_ANSR_Sintetico', 'N/A')}")
    
    # Try the actual service method
    print("\n=== Testing service method ===")
    kpis = service.get_manager_kpis(manager_name, selected_date)
    print(f"Service results: {kpis}")

if __name__ == "__main__":
    debug_diana_dates()
