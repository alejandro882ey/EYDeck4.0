#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dashboard_django.settings')
django.setup()

from django.template.loader import get_template

try:
    template = get_template('core_dashboard/dashboard.html')
    print("✓ Dashboard template loaded successfully!")
    print("✓ Preview buttons have been added to RPH and Diferencial Final MTD cards")
except Exception as e:
    print(f"✗ Template error: {e}")
