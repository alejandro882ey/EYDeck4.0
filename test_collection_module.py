#!/usr/bin/env python3
"""
Test script for collection module functionality
"""

import pandas as pd
import sys
import os

# Add the Django project directory to sys.path
django_project_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, django_project_path)

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dashboard_django.settings')

import django
django.setup()

# Import the collection module
from core_dashboard.modules.collection_module import process_collection_data, get_collection_metrics

def test_collection_module():
    """Test the collection module with sample data."""
    print("Testing collection module...")
    
    # Create sample test data
    test_data = {
        'EngagementID': ['ENG001', 'ENG002', 'ENG003'],
        'Client': ['Client A', 'Client B', 'Client C'],
        'FYTD_ARCollectedAmt': [100000, 150000, 75000],
        'FYTD_ARCollectedTaxAmt': [15000, 22500, 11250]
    }
    
    df = pd.DataFrame(test_data)
    print("Original data:")
    print(df.to_string())
    print()
    
    # Process collection data
    try:
        processed_df = process_collection_data(df)
        print("After processing:")
        print(processed_df[['EngagementID', 'FYTD_ARCollectedAmt', 'FYTD_ARCollectedTaxAmt', 'FYTD_CollectTotalAmt']].to_string())
        print()
        
        # Get metrics
        metrics = get_collection_metrics(processed_df)
        print("Collection metrics:")
        for key, value in metrics.items():
            print(f"  {key}: {value}")
        print()
        
        # Verify calculations
        expected_total = (100000 - 15000) + (150000 - 22500) + (75000 - 11250)
        actual_total = processed_df['FYTD_CollectTotalAmt'].sum()
        
        print(f"Expected total: {expected_total}")
        print(f"Actual total: {actual_total}")
        print(f"Test passed: {expected_total == actual_total}")
        
        return True
        
    except Exception as e:
        print(f"Test failed with error: {e}")
        return False

if __name__ == "__main__":
    success = test_collection_module()
    sys.exit(0 if success else 1)
