import os
import django
from datetime import datetime, timedelta
import pandas as pd

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dashboard_django.settings')
django.setup()

def examine_revenue_days_structure():
    # Load the Revenue Days Excel file directly
    excel_path = r"c:\Users\CK624GF\OneDrive - EY\Documents\2025\dashboard_django\media\manager_revenue_days\Revenue Days Manager_2025-07-11.xlsx"
    
    try:
        print("=== Loading Revenue Days Excel file ===")
        df = pd.read_excel(excel_path)
        print(f"Total rows: {len(df)}")
        print(f"Columns: {list(df.columns)}")
        
        # Show sample data
        print("\n=== Sample data (first 5 rows) ===")
        print(df.head())
        
        # Look for Diana in Employee column
        if 'Employee' in df.columns:
            diana_entries = df[df['Employee'].str.contains('Diana', case=False, na=False)]
            print(f"\n=== Diana entries ({len(diana_entries)}) ===")
            for idx, row in diana_entries.iterrows():
                employee = row.get('Employee', 'N/A')
                rank = row.get('Employee Rank', 'N/A')
                area = row.get('Employee Area', 'N/A')
                print(f"Employee: {employee}, Rank: {rank}, Area: {area}")
                
                # Look for ANSR-related columns
                for col in df.columns:
                    if 'ansr' in col.lower() or 'revenue' in col.lower() or 'billing' in col.lower():
                        print(f"  {col}: {row.get(col, 'N/A')}")
        
        # Look for all potential ANSR/revenue columns
        print("\n=== Potential ANSR/Revenue columns ===")
        for col in df.columns:
            if any(keyword in col.lower() for keyword in ['ansr', 'revenue', 'billing', 'total', 'fytd', 'ytd', 'mtd']):
                print(f"  {col}")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    examine_revenue_days_structure()
