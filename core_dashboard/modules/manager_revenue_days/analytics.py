"""
Manager Analytics Service
========================

Service for calculating Manager-specific KPIs and analytics.
Handles ANSR calculations, hours tracking, perdida diferencial, and revenue days data.
"""

import os
import pandas as pd
import logging
from decimal import Decimal
from django.conf import settings
from django.db.models import Sum, Count, Q
from datetime import datetime, timedelta
from core_dashboard.models import RevenueEntry

logger = logging.getLogger(__name__)


class ManagerAnalyticsService:
    """
    Service class for Manager analytics calculations.
    
    Provides comprehensive analytics for individual managers including:
    - ANSR YTD/MTD calculations
    - Charged Hours YTD/MTD
    - Perdida Diferencial YTD/MTD
    - Client and Engagement counts
    - Revenue Days data from Manager Revenue Days reports
    - Top clients and engagements rankings
    """
    
    def __init__(self):
        """Initialize the Manager Analytics service."""
        self.media_folder = os.path.join(settings.MEDIA_ROOT, 'manager_revenue_days')
        
    def get_manager_kpis(self, manager_name, selected_date=None):
        """
        Calculate comprehensive KPIs for a specific manager.
        
        Args:
            manager_name (str): Name of the manager
            selected_date (date, optional): Date for MTD calculations
            
        Returns:
            dict: Complete manager analytics data
        """
        try:
            logger.info(f"Calculating Manager KPIs for: {manager_name}")
            
            # Get revenue entries for this manager, filtered by selected date if provided
            manager_entries = RevenueEntry.objects.filter(
                engagement_manager=manager_name
            )
            
            # Apply date filtering like the main dashboard does
            if selected_date:
                # Find the week that contains the selected date
                # Assuming selected_date is a Friday (end of week)
                friday_date = selected_date
                start_of_week = friday_date - timedelta(days=friday_date.weekday())
                end_of_week = start_of_week + timedelta(days=6)
                manager_entries = manager_entries.filter(date__range=[start_of_week, end_of_week])
                logger.info(f"Filtered entries for week {start_of_week} to {end_of_week}: {manager_entries.count()} entries")
            else:
                # If no date provided, use the most recent week available
                from django.db.models.functions import TruncWeek
                available_weeks_raw = RevenueEntry.objects.annotate(
                    calculated_week=TruncWeek('date')
                ).values_list('calculated_week', flat=True).distinct().order_by('calculated_week')
                
                if available_weeks_raw:
                    most_recent_week_start = list(available_weeks_raw)[-1]
                    friday_date = most_recent_week_start + timedelta(days=4)
                    start_of_week = friday_date - timedelta(days=friday_date.weekday())
                    end_of_week = start_of_week + timedelta(days=6)
                    manager_entries = manager_entries.filter(date__range=[start_of_week, end_of_week])
                    logger.info(f"Using most recent week {start_of_week} to {end_of_week}: {manager_entries.count()} entries")
            
            if not manager_entries.exists():
                logger.warning(f"No revenue entries found for manager: {manager_name}")
                return None
            
            # Calculate basic KPIs
            kpis = self._calculate_basic_kpis(manager_entries, selected_date)
            
            # Calculate perdida diferencial
            perdida_data = self._calculate_perdida_diferencial(manager_entries, selected_date)
            kpis.update(perdida_data)
            
            # Get client and engagement counts
            counts_data = self._calculate_counts(manager_entries)
            kpis.update(counts_data)
            
            # Get Revenue Days data
            revenue_days_data = self._get_revenue_days_data(manager_name)
            kpis.update(revenue_days_data)
            
            # Get top clients and engagements
            rankings_data = self._get_rankings_data(manager_entries)
            kpis.update(rankings_data)
            
            logger.info(f"Successfully calculated Manager KPIs for {manager_name}")
            return kpis
            
        except Exception as e:
            logger.error(f"Error calculating Manager KPIs for {manager_name}: {str(e)}")
            return None
    
    def _calculate_basic_kpis(self, manager_entries, selected_date):
        """Calculate ANSR and Hours KPIs."""
        try:
            # ANSR YTD (from fytd_ansr_sintetico)
            fytd_ansr = manager_entries.aggregate(
                total=Sum('fytd_ansr_sintetico')
            )['total'] or 0
            
            # ANSR MTD (from mtd_ansr_amt)
            mtd_ansr = manager_entries.aggregate(
                total=Sum('mtd_ansr_amt')
            )['total'] or 0
            
            # Hours YTD (from fytd_charged_hours)
            fytd_hours = manager_entries.aggregate(
                total=Sum('fytd_charged_hours')
            )['total'] or 0
            
            # Hours MTD (from mtd_charged_hours)
            mtd_hours = manager_entries.aggregate(
                total=Sum('mtd_charged_hours')
            )['total'] or 0
            
            return {
                'manager_fytd_ansr_value': float(fytd_ansr),
                'manager_mtd_ansr_value': float(mtd_ansr),
                'manager_fytd_charged_hours': float(fytd_hours),
                'manager_mtd_charged_hours': float(mtd_hours),
            }
            
        except Exception as e:
            logger.error(f"Error calculating basic KPIs: {str(e)}")
            return {
                'manager_fytd_ansr_value': 0,
                'manager_mtd_ansr_value': 0,
                'manager_fytd_charged_hours': 0,
                'manager_mtd_charged_hours': 0,
            }
    
    def _calculate_perdida_diferencial(self, manager_entries, selected_date):
        """Calculate Perdida Diferencial YTD and MTD."""
        try:
            # Perdida Diferencial YTD (from fytd_diferencial_final)
            perdida_ytd = manager_entries.aggregate(
                total=Sum('fytd_diferencial_final')
            )['total'] or 0
            
            # Perdida Diferencial MTD (from diferencial_mtd)
            perdida_mtd = manager_entries.aggregate(
                total=Sum('diferencial_mtd')
            )['total'] or 0
            
            return {
                'manager_perdida_ytd': float(perdida_ytd),
                'manager_perdida_mtd': float(perdida_mtd),
            }
            
        except Exception as e:
            logger.error(f"Error calculating perdida diferencial: {str(e)}")
            return {
                'manager_perdida_ytd': 0,
                'manager_perdida_mtd': 0,
            }
    
    def _calculate_counts(self, manager_entries):
        """Calculate client and engagement counts."""
        try:
            # Number of unique clients
            num_clients = manager_entries.values('client').distinct().count()
            
            # Number of unique engagements
            num_engagements = manager_entries.values('engagement').distinct().count()
            
            return {
                'num_clients': num_clients,
                'num_engagements': num_engagements,
            }
            
        except Exception as e:
            logger.error(f"Error calculating counts: {str(e)}")
            return {
                'num_clients': 0,
                'num_engagements': 0,
            }
    
    def _get_revenue_days_data(self, manager_name):
        """Get Revenue Days data from the latest Manager Revenue Days file."""
        try:
            # Find the latest Manager Revenue Days file
            if not os.path.exists(self.media_folder):
                logger.warning(f"Manager Revenue Days folder not found: {self.media_folder}")
                return {'revenue_days': 0}
            
            # Get all Manager Revenue Days files
            files = [f for f in os.listdir(self.media_folder) if f.endswith('.xlsx')]
            
            if not files:
                logger.warning("No Manager Revenue Days files found")
                return {'revenue_days': 0}
            
            # Use the most recent file (or specific dated file if available)
            latest_file = sorted(files)[-1]  # Get the latest alphabetically
            file_path = os.path.join(self.media_folder, latest_file)
            
            logger.info(f"Reading Revenue Days from: {latest_file}")
            
            # Read the Excel file with standard header (row 0)
            df = pd.read_excel(file_path, sheet_name='RevenueDays', header=0)
            
            # Filter for Venezuela only
            if 'Employee Country/Region' in df.columns:
                df = df[df['Employee Country/Region'].str.contains('Venezuela', case=False, na=False)]
                logger.info(f"Filtered for Venezuela: {len(df)} entries")
            
            # Find the manager in the Employee column
            manager_row = df[df['Employee'].str.contains(manager_name, case=False, na=False)]
            
            if manager_row.empty:
                logger.warning(f"Manager {manager_name} not found in Revenue Days file")
                return {'revenue_days': 0}
            
            # Get Revenue Days from 'Total Revenue Days' column
            if 'Total Revenue Days' in df.columns:
                revenue_days = manager_row['Total Revenue Days'].iloc[0]
            else:
                logger.warning("'Total Revenue Days' column not found")
                return {'revenue_days': 0}
            
            # Handle NaN values
            if pd.isna(revenue_days):
                revenue_days = 0
            
            return {
                'revenue_days': float(revenue_days)
            }
            
        except Exception as e:
            logger.error(f"Error getting Revenue Days data: {str(e)}")
            return {'revenue_days': 0}
    
    def get_available_managers(self):
        """Get list of available managers from the Manager Revenue Days file."""
        try:
            # Find the latest Manager Revenue Days file
            if not os.path.exists(self.media_folder):
                logger.warning(f"Manager Revenue Days folder not found: {self.media_folder}")
                return []
            
            # Get all Manager Revenue Days files
            files = [f for f in os.listdir(self.media_folder) if f.endswith('.xlsx')]
            
            if not files:
                logger.warning("No Manager Revenue Days files found")
                return []
            
            # Use the most recent file
            latest_file = sorted(files)[-1]
            file_path = os.path.join(self.media_folder, latest_file)
            
            # Read the Excel file with standard header (row 0)
            df = pd.read_excel(file_path, sheet_name='RevenueDays', header=0)
            
            # Get all employees from the Employee column
            if 'Employee' not in df.columns:
                logger.warning("'Employee' column not found in Revenue Days file")
                return []
            
            # Filter for Venezuela only
            if 'Employee Country/Region' in df.columns:
                df = df[df['Employee Country/Region'].str.contains('Venezuela', case=False, na=False)]
                logger.info(f"Filtered for Venezuela: {len(df)} entries")
            else:
                logger.warning("'Employee Country/Region' column not found - no country filtering applied")
            
            # Filter to get only managers (those with "Manager" in their rank)
            if 'Employee Rank' in df.columns:
                manager_rows = df[df['Employee Rank'].str.contains('Manager', case=False, na=False)]
                managers = manager_rows['Employee'].tolist()
            else:
                # If no rank column, return all employees
                managers = df['Employee'].dropna().tolist()
            
            # Clean and sort manager names
            managers = [str(m).strip() for m in managers if pd.notna(m) and str(m).strip()]
            managers = sorted(list(set(managers)))  # Remove duplicates and sort
            
            logger.info(f"Found {len(managers)} managers in Revenue Days file (Venezuela only)")
            return managers
            
        except Exception as e:
            logger.error(f"Error getting available managers: {str(e)}")
            return []
    
    def _get_rankings_data(self, manager_entries):
        """Get top clients and engagements rankings."""
        try:
            # Top 5 Clients by Revenue (using fytd_ansr_sintetico)
            top_clients = manager_entries.values('client__name').annotate(
                revenue=Sum('fytd_ansr_sintetico')
            ).order_by('-revenue')[:5]
            
            # All clients ranking for flip functionality
            all_clients = manager_entries.values('client__name').annotate(
                revenue=Sum('fytd_ansr_sintetico'),
                mtd_hours=Sum('mtd_charged_hours')
            ).order_by('-revenue')
            
            # Top 5 Engagements by Perdida Diferencial
            top_engagements = manager_entries.values('engagement').annotate(
                perdida=Sum('fytd_diferencial_final')
            ).order_by('-perdida')[:5]
            
            # All engagements ranking for flip functionality
            all_engagements = manager_entries.values('engagement').annotate(
                perdida=Sum('fytd_diferencial_final')
            ).order_by('-perdida')
            
            return {
                'top_clients': [
                    {
                        'client_name': item['client__name'],
                        'revenue': float(item['revenue'] or 0)
                    }
                    for item in top_clients
                ],
                'all_clients': [
                    {
                        'client_name': item['client__name'],
                        'revenue': float(item['revenue'] or 0),
                        'mtd_hours': float(item['mtd_hours'] or 0)
                    }
                    for item in all_clients
                ],
                'top_engagements': [
                    {
                        'engagement_name': item['engagement'],
                        'perdida': float(item['perdida'] or 0)
                    }
                    for item in top_engagements
                ],
                'all_engagements': [
                    {
                        'engagement_name': item['engagement'],
                        'perdida': float(item['perdida'] or 0)
                    }
                    for item in all_engagements
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting rankings data: {str(e)}")
            return {
                'top_clients': [],
                'all_clients': [],
                'top_engagements': [],
                'all_engagements': []
            }
    
    def get_all_managers(self):
        """Get list of all available managers."""
        try:
            managers = RevenueEntry.objects.values_list(
                'engagement_manager', flat=True
            ).distinct().exclude(
                engagement_manager__isnull=True
            ).exclude(
                engagement_manager__exact=''
            ).order_by('engagement_manager')
            
            return list(managers)
            
        except Exception as e:
            logger.error(f"Error getting managers list: {str(e)}")
            return []
