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
    
    # First, let's see what managers are available
    print("\n=== Available managers ===")
    available_managers = service.get_available_managers()
    print(f"Total managers: {len(available_managers)}")
    
    # Look for Diana variants
    diana_matches = [m for m in available_managers if 'diana' in m.lower()]
    print(f"Diana matches: {diana_matches}")
    
    # Look for Cardenas variants
    cardenas_matches = [m for m in available_managers if 'cardenas' in m.lower()]
    print(f"Cardenas matches: {cardenas_matches}")
    
    if diana_matches:
        manager_name = diana_matches[0]
        print(f"\nUsing manager name: '{manager_name}'")
        
        # Test the actual service method
        print("\n=== Testing service method ===")
        kpis = service.get_manager_kpis(manager_name, selected_date)
        print(f"Service results: {kpis}")
    else:
        print("No Diana match found. Let's see some sample manager names:")
        for i, manager in enumerate(available_managers[:10]):
            print(f"  {i+1}. '{manager}'")

if __name__ == "__main__":
    debug_diana_dates()
