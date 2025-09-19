"""
Exchange Rate Differential Trends Module

This module handles processing of exchange rate data from the Historial_TCBinance.xlsx file
and generates data for the Exchange Rate Differential Trends chart.

The chart displays:
- Tasa Oficial (Blue line)
- Tasa Paralelo (Red line) 
- Percentage gap/differential (Yellow bars)

Follows the guiding principle: "Improve and Adjust, Never change the integrity of the code."
"""


import pandas as pd
import os
from datetime import datetime
import logging
# requests and BytesIO removed: module reads local Excel file only

logger = logging.getLogger(__name__)

class ExchangeRateProcessor:
    """Processes exchange rate data for dashboard visualization"""
    
    def __init__(self, file_path=None):
        """
        Initialize the processor with the Excel file path
        Args:
            file_path (str): Path to Historial_TCBinance.xlsx file
        """
        # Default to local file path if not provided
        if file_path is None:
            file_path = r"C:\Users\CK624GF\OneDrive - EY\Documents\2025\dashboard_django\dolar excel\Historial_TCBinance.xlsx"
        self.file_path = file_path
        
    def load_exchange_rate_data(self):
        """
        Load and validate exchange rate data from local Excel file
        Returns:
            pandas.DataFrame: Processed exchange rate data or None if error
        """
        try:
            if not os.path.exists(self.file_path):
                logger.warning(f"Exchange rate file not found: {self.file_path}")
                return None
            df = pd.read_excel(self.file_path)
            
            # Validate expected columns - check for both old and new column names
            expected_columns_new = ['Fecha', 'Tasa binance (USD/VES)', 'Tasa Oficial (USD/VES)']
            expected_columns_old = ['Fecha', 'Tasa Paralelo (USD/VES)', 'Tasa Oficial (USD/VES)']
            
            # Determine which column set to use
            if all(col in df.columns for col in expected_columns_new):
                parallel_column = 'Tasa binance (USD/VES)'
                logger.info(f"Using new column structure with 'Tasa binance (USD/VES)'")
            elif all(col in df.columns for col in expected_columns_old):
                parallel_column = 'Tasa Paralelo (USD/VES)'
                logger.info(f"Using old column structure with 'Tasa Paralelo (USD/VES)'")
            else:
                logger.error(f"Missing expected columns in {self.file_path}. Expected either: {expected_columns_new} or {expected_columns_old}")
                logger.error(f"Found columns: {df.columns.tolist()}")
                return None
            
            # Clean and process data
            df = df.copy()
            
            # Enhanced date parsing to handle multiple formats
            def parse_date_flexible(date_str):
                """Parse dates in multiple formats"""
                if pd.isna(date_str):
                    return pd.NaT
                
                date_str = str(date_str).strip()
                
                # Try different date formats
                formats_to_try = [
                    '%m/%d/%Y',      # 7/1/2025
                    '%Y-%m-%d',      # 2025-09-03
                    '%Y-%m-%d %H:%M:%S',  # 2025-09-03 15:12:49
                    '%d/%m/%Y',      # 01/07/2025
                    '%Y/%m/%d'       # 2025/07/01
                ]
                
                for fmt in formats_to_try:
                    try:
                        return pd.to_datetime(date_str, format=fmt)
                    except ValueError:
                        continue
                
                # If none of the specific formats work, try pandas' general parser
                try:
                    return pd.to_datetime(date_str, errors='raise')
                except:
                    logger.warning(f"Could not parse date: {date_str}")
                    return pd.NaT
            
            # Apply flexible date parsing
            df['Fecha'] = df['Fecha'].apply(parse_date_flexible)

            # Normalize timezone: convert all timestamps to UTC (tz-aware) to avoid
            # errors when mixing tz-naive and tz-aware datetimes in comparisons/sorting.
            # Using utc=True converts naive timestamps to UTC-aware and converts
            # aware timestamps to UTC as well.
            df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce', utc=True)
            
            # Remove rows with invalid dates
            valid_dates_before = len(df)
            df = df.dropna(subset=['Fecha'])
            valid_dates_after = len(df)
            
            if valid_dates_before != valid_dates_after:
                logger.warning(f"Dropped {valid_dates_before - valid_dates_after} rows with invalid dates")
            
            # Ensure numeric columns are float
            df[parallel_column] = pd.to_numeric(df[parallel_column], errors='coerce')
            df['Tasa Oficial (USD/VES)'] = pd.to_numeric(df['Tasa Oficial (USD/VES)'], errors='coerce')
            
            # Remove rows with missing rate data
            df = df.dropna(subset=[parallel_column, 'Tasa Oficial (USD/VES)'])
            
            # Sort by date
            df = df.sort_values('Fecha')
            
            # Calculate percentage differential using the dynamic column name
            df['Differential_Percentage'] = (
                (df[parallel_column] - df['Tasa Oficial (USD/VES)']) / 
                df['Tasa Oficial (USD/VES)'] * 100
            )
            
            logger.info(f"Successfully loaded {len(df)} exchange rate records")
            return df
            
        except Exception as e:
            logger.error(f"Error loading exchange rate data: {str(e)}")
            if "Permission denied" in str(e):
                logger.error(f"File may be open in Excel. Please close the file and try again: {self.file_path}")
            return None
    
    def get_chart_data(self):
        """
        Get processed data ready for chart rendering
        
        Returns:
            dict: Chart data with dates, rates, and differentials
        """
        df = self.load_exchange_rate_data()
        
        if df is None or df.empty:
            return {
                'dates': [],
                'tasa_oficial': [],
                'tasa_paralelo': [], 
                'differential_percentage': [],
                'last_oficial': 0,
                'last_paralelo': 0,
                'last_differential': 0,
                'last_date': ''
            }
        
        # Determine which parallel column is being used
        parallel_column = None
        if 'Tasa binance (USD/VES)' in df.columns:
            parallel_column = 'Tasa binance (USD/VES)'
        elif 'Tasa Paralelo (USD/VES)' in df.columns:
            parallel_column = 'Tasa Paralelo (USD/VES)'
        else:
            logger.error("No valid parallel rate column found")
            return {
                'dates': [],
                'tasa_oficial': [],
                'tasa_paralelo': [], 
                'differential_percentage': [],
                'last_oficial': 0,
                'last_paralelo': 0,
                'last_differential': 0,
                'last_date': ''
            }
        
        # Convert dates to string format for JSON serialization
        dates = df['Fecha'].dt.strftime('%Y-%m-%d').tolist()
        tasa_oficial = df['Tasa Oficial (USD/VES)'].tolist()
        tasa_paralelo = df[parallel_column].tolist()
        differential_percentage = df['Differential_Percentage'].tolist()
        
        # Get latest values
        last_oficial = float(df['Tasa Oficial (USD/VES)'].iloc[-1]) if not df.empty else 0
        last_paralelo = float(df[parallel_column].iloc[-1]) if not df.empty else 0
        last_differential = float(df['Differential_Percentage'].iloc[-1]) if not df.empty else 0
        last_date = df['Fecha'].iloc[-1].strftime('%Y-%m-%d') if not df.empty else ''
        
        return {
            'dates': dates,
            'tasa_oficial': tasa_oficial,
            'tasa_paralelo': tasa_paralelo,
            'differential_percentage': differential_percentage,
            'last_oficial': last_oficial,
            'last_paralelo': last_paralelo,
            'last_differential': last_differential,
            'last_date': last_date
        }
    
    def get_summary_stats(self):
        """
        Get summary statistics for the exchange rate data
        
        Returns:
            dict: Summary statistics
        """
        df = self.load_exchange_rate_data()
        
        if df is None or df.empty:
            return {
                'total_records': 0,
                'date_range': '',
                'avg_differential': 0,
                'max_differential': 0,
                'min_differential': 0
            }
        
        date_range = f"{df['Fecha'].min().strftime('%Y-%m-%d')} to {df['Fecha'].max().strftime('%Y-%m-%d')}"
        
        return {
            'total_records': len(df),
            'date_range': date_range,
            'avg_differential': float(df['Differential_Percentage'].mean()),
            'max_differential': float(df['Differential_Percentage'].max()),
            'min_differential': float(df['Differential_Percentage'].min())
        }


def get_exchange_rate_data(file_path=None):
    """
    Convenience function to get exchange rate chart data
    
    Args:
        file_path (str): Optional path to Excel file
        
    Returns:
        dict: Chart data ready for template rendering
    """
    processor = ExchangeRateProcessor(file_path)
    return processor.get_chart_data()


def get_exchange_rate_summary(file_path=None):
    """
    Convenience function to get exchange rate summary statistics
    
    Args:
        file_path (str): Optional path to Excel file
        
    Returns:
        dict: Summary statistics
    """
    processor = ExchangeRateProcessor(file_path)
    return processor.get_summary_stats()
