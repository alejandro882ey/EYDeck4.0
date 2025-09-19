#!/usr/bin/env python
"""
Test script for the updated exchange rate module
This script tests the new column structure support
"""

import os
import sys
import pandas as pd
from datetime import datetime

# Add the project directory to Python path
sys.path.append(os.path.dirname(__file__))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dashboard_django.settings')
import django
django.setup()

from core_dashboard.modules.exchange_rate_module import ExchangeRateProcessor, get_exchange_rate_data

def test_exchange_rate_module():
    """Test the exchange rate module with the new file structure"""
    
    file_path = os.path.join(os.path.dirname(__file__), 'dolar excel', 'Historial_TCBinance.xlsx')
    
    print(f"Testing exchange rate module with file: {file_path}")
    print(f"File exists: {os.path.exists(file_path)}")
    
    try:
        # Test direct pandas reading first
        print("\n--- Testing direct pandas read ---")
        df_direct = pd.read_excel(file_path)
        print(f"Direct read successful!")
        print(f"Columns: {df_direct.columns.tolist()}")
        print(f"Shape: {df_direct.shape}")
        print(f"First few rows:")
        print(df_direct.head(3))
        
        # Test our processor
        print("\n--- Testing ExchangeRateProcessor ---")
        processor = ExchangeRateProcessor(file_path)
        
        # Test load_exchange_rate_data
        df_processed = processor.load_exchange_rate_data()
        if df_processed is not None:
            print(f"Processed data shape: {df_processed.shape}")
            print(f"Processed columns: {df_processed.columns.tolist()}")
            print(f"Last 3 dates: {df_processed['Fecha'].tail(3).dt.strftime('%Y-%m-%d').tolist()}")
            print(f"Last differential: {df_processed['Differential_Percentage'].iloc[-1]:.2f}%")
        else:
            print("Failed to process data")
            
        # Test get_chart_data
        print("\n--- Testing get_chart_data ---")
        chart_data = processor.get_chart_data()
        print(f"Chart data keys: {list(chart_data.keys())}")
        print(f"Number of data points: {len(chart_data['dates'])}")
        if chart_data['dates']:
            print(f"Date range: {chart_data['dates'][0]} to {chart_data['dates'][-1]}")
            print(f"Latest rates - Oficial: {chart_data['last_oficial']}, Paralelo: {chart_data['last_paralelo']}")
            print(f"Latest differential: {chart_data['last_differential']:.2f}%")
        
        # Test convenience function
        print("\n--- Testing convenience function ---")
        convenience_data = get_exchange_rate_data(file_path)
        print(f"Convenience function returned {len(convenience_data['dates'])} data points")
        
        return True
        
    except Exception as e:
        print(f"Error during testing: {str(e)}")
        if "Permission denied" in str(e):
            print("Note: The Excel file appears to be open. Please close it and try again.")
        return False

if __name__ == "__main__":
    print("Exchange Rate Module Test")
    print("=" * 50)
    
    success = test_exchange_rate_module()
    
    if success:
        print("\n✅ Test completed successfully!")
    else:
        print("\n❌ Test failed. Check the error messages above.")
