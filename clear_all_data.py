#!/usr/bin/env python3
"""
Script to clear all uploaded data and cache for fresh start
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
    print("Clearing all database data...")
    
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
            print(f"✗ Error clearing media directory: {e}")
    
    # Clear __pycache__ directories
    for root, dirs, files in os.walk("."):
        for dir_name in dirs:
            if dir_name == "__pycache__":
                cache_path = os.path.join(root, dir_name)
                try:
                    shutil.rmtree(cache_path)
                    print(f"✓ Cleared cache: {cache_path}")
                except Exception as e:
                    print(f"✗ Error clearing cache {cache_path}: {e}")
    
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
                print(f"✗ Error clearing cache file {file_path}: {e}")
    
    print("\n🎉 All data and cache cleared successfully!")
    print("You can now upload the 2025-07-11 report fresh.")
    
    # Remove the sample data creation script
    try:
        os.remove("create_sample_collection_data.py")
        print("✓ Removed sample data creation script")
    except:
        pass

if __name__ == "__main__":
    clear_all_data()
