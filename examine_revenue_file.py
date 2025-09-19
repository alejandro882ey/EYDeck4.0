import os
import django
from datetime import datetime, timedelta
import pandas as pd

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dashboard_django.settings')
django.setup()

def examine_revenue_days_file():
    # Load the Revenue Days Excel file directly
    excel_path = r"c:\Users\CK624GF\OneDrive - EY\Documents\2025\dashboard_django\media\manager_revenue_days\Revenue Days Manager_2025-07-11.xlsx"
    
    try:
        print("=== Loading Revenue Days Excel file ===")
        df = pd.read_excel(excel_path)
        print(f"Total rows: {len(df)}")
        print(f"Columns: {list(df.columns)}")
        
        # Filter for Venezuela first
        if 'Employee Country/Region' in df.columns:
            venezuela_df = df[df['Employee Country/Region'] == 'Venezuela']
            print(f"Venezuela entries: {len(venezuela_df)}")
        else:
            venezuela_df = df
            print("No Employee Country/Region column found")
        
        # Look for Diana Cardenas
        diana_df = venezuela_df[venezuela_df['Manager Name'] == 'Cardenas, Diana']
        print(f"Diana entries: {len(diana_df)}")
        
        if len(diana_df) > 0:
            print("\n=== Diana's entries ===")
            for idx, row in diana_df.iterrows():
                week_ending = row.get('Week Ending', 'N/A')
                fytd_ansr = row.get('FYTD_ANSR_Sintetico', 'N/A')
                mtd_ansr = row.get('MTD_ANSR_Sintetico', 'N/A')
                print(f"Week Ending: {week_ending}, FYTD ANSR: {fytd_ansr}, MTD ANSR: {mtd_ansr}")
        
        # Check for the specific date we're looking for (2025-07-11)
        target_date = datetime(2025, 7, 11).date()
        print(f"\n=== Looking for week containing {target_date} ===")
        
        if 'Week Ending' in df.columns:
            df['Week Ending'] = pd.to_datetime(df['Week Ending']).dt.date
            
            # Check what weeks are available around that time
            july_weeks = df[
                (df['Week Ending'] >= datetime(2025, 7, 1).date()) & 
                (df['Week Ending'] <= datetime(2025, 7, 31).date())
            ]
            
            unique_july_weeks = july_weeks['Week Ending'].unique()
            print(f"July 2025 weeks available: {sorted(unique_july_weeks)}")
            
            # Check Diana's entries for July
            diana_july = july_weeks[july_weeks['Manager Name'] == 'Cardenas, Diana']
            print(f"\nDiana's July entries: {len(diana_july)}")
            
            for idx, row in diana_july.iterrows():
                week_ending = row['Week Ending']
                fytd_ansr = row.get('FYTD_ANSR_Sintetico', 'N/A')
                mtd_ansr = row.get('MTD_ANSR_Sintetico', 'N/A')
                print(f"Week Ending: {week_ending}, FYTD ANSR: {fytd_ansr}, MTD ANSR: {mtd_ansr}")
    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    examine_revenue_days_file()
