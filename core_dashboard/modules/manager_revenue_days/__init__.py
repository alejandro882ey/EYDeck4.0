"""
Manager Revenue Days Module
==========================

This module handles the processing and storage of Manager Revenue Days reports.
It provides isolated functionality for uploading Excel files and extracting 
the 'RevenueDays' sheet to be stored in the media folder as 'Revenue Days Manager'.

Key Features:
- Excel file upload processing
- RevenueDays sheet extraction
- Isolated file storage (no database integration)
- Independent from main revenue tracking system

Author: EY Analytics Engine
Version: 1.0
"""

from .services import ManagerRevenueDaysService
from .utils import extract_revenue_days_sheet
from .analytics import ManagerAnalyticsService

__all__ = ['ManagerRevenueDaysService', 'extract_revenue_days_sheet', 'ManagerAnalyticsService']
