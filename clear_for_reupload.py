#!/usr/bin/env python3
"""
Script to clear all uploaded data and cache for re-uploading with billing support
"""

import os
import sys
import shutil
import django
from pathlib import Path

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dashboard_django.settings')
django.setup()

from core_dashboard.models import RevenueEntry, Client, Area, SubArea, Contract, UploadHistory, ExchangeRate

def clear_all_data():
    """Clear all data from database and cache files."""
    print("Clearing all database data and cache...")
    
    # Clear all model data
    RevenueEntry.objects.all().delete()
    print("✓ Cleared RevenueEntry data")
    
    UploadHistory.objects.all().delete()
    print("✓ Cleared UploadHistory data")
    
    ExchangeRate.objects.all().delete()
    print("✓ Cleared ExchangeRate data")
    
    # Clear foreign key related data
    Contract.objects.all().delete()
    print("✓ Cleared Contract data")
    
    SubArea.objects.all().delete()
    print("✓ Cleared SubArea data")
    
    Area.objects.all().delete()
    print("✓ Cleared Area data")
    
    Client.objects.all().delete()
    print("✓ Cleared Client data")
    
    # Clear media files (uploaded files and processed data)
    media_root = Path("media")
    if media_root.exists():
        try:
            shutil.rmtree(media_root)
            print("✓ Cleared media directory")
        except Exception as e:
            print(f"! Media directory partially cleared (some files may be in use): {e}")
    
    # Clear specific cache files
    cache_files = [
        "historical_data.csv",
        "*.pyc"
    ]
    
    for pattern in cache_files:
        for file_path in Path(".").glob(f"**/{pattern}"):
            try:
                file_path.unlink()
                print(f"✓ Cleared cache file: {file_path}")
            except Exception as e:
                print(f"! Could not clear cache file {file_path}: {e}")
    
    print("\n🎉 All data and cache cleared successfully!")
    print("📝 Ready for re-upload with billing column support!")
    print("🔸 The new upload will include both:")
    print("   - Cobranzas (Collected YTD) from FYTD_ARCollectedAmt - FYTD_ARCollectedTaxAmt")
    print("   - Facturacion (Billed YTD) from FYTD_TotalBilledAmt")

if __name__ == "__main__":
    clear_all_data()
