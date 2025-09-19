"""
Collection Data Processing Module

This module handles processing of collection-related data from Final_Database.csv files,
specifically for the Cobranzas (Collected YTD) and Facturacion (Billed YTD) card functionality.

Functions:
- process_collection_data: Calculates collection metrics including FYTD_CollectTotalAmt
- process_billing_data: Handles billing data for FYTD_TotalBilledAmt
- validate_collection_columns: Validates required collection columns are present
- validate_billing_columns: Validates required billing columns are present
"""

import pandas as pd
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_collection_columns(df):
    """
    Validates that the required collection columns are present in the DataFrame.
    
    Args:
        df (pd.DataFrame): Input DataFrame to validate
        
    Returns:
        bool: True if all required columns are present, False otherwise
        
    Raises:
        ValueError: If required columns are missing
    """
    required_columns = ['FYTD_ARCollectedAmt', 'FYTD_ARCollectedTaxAmt']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        logger.error(f"Missing required collection columns: {missing_columns}")
        raise ValueError(f"Required collection columns missing: {missing_columns}")
    
    logger.info("All required collection columns are present")
    return True

def validate_billing_columns(df):
    """
    Validates that the required billing columns are present in the DataFrame.
    
    Args:
        df (pd.DataFrame): Input DataFrame to validate
        
    Returns:
        bool: True if all required columns are present, False otherwise
        
    Raises:
        ValueError: If required columns are missing
    """
    required_columns = ['FYTD_TotalBilledAmt']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        logger.error(f"Missing required billing columns: {missing_columns}")
        raise ValueError(f"Required billing columns missing: {missing_columns}")
    
    logger.info("All required billing columns are present")
    return True

def process_billing_data(df):
    """
    Processes billing data by ensuring FYTD_TotalBilledAmt is properly formatted.
    
    This function:
    1. Validates required columns are present
    2. Ensures FYTD_TotalBilledAmt is numeric
    3. Handles any missing/null values appropriately
    
    Args:
        df (pd.DataFrame): Input DataFrame containing billing data
        
    Returns:
        pd.DataFrame: DataFrame with processed FYTD_TotalBilledAmt column
        
    Raises:
        ValueError: If required columns are missing
    """
    logger.info("Starting billing data processing...")
    
    # Validate required columns exist
    validate_billing_columns(df)
    
    # Ensure column is numeric, handling any non-numeric values
    df['FYTD_TotalBilledAmt'] = pd.to_numeric(df['FYTD_TotalBilledAmt'], errors='coerce')
    
    # Fill NaN values with 0 for calculation
    df['FYTD_TotalBilledAmt'] = df['FYTD_TotalBilledAmt'].fillna(0)
    
    logger.info(f"Processed FYTD_TotalBilledAmt for {len(df)} records")
    logger.info(f"Total FYTD_TotalBilledAmt sum: ${df['FYTD_TotalBilledAmt'].sum():,.2f}")
    
    return df

def process_collection_data(df):
    """
    Processes collection data by calculating the FYTD_CollectTotalAmt column.
    
    This function:
    1. Validates required columns are present
    2. Calculates FYTD_CollectTotalAmt = FYTD_ARCollectedAmt - FYTD_ARCollectedTaxAmt
    3. Handles any missing/null values appropriately
    
    Args:
        df (pd.DataFrame): Input DataFrame containing collection data
        
    Returns:
        pd.DataFrame: DataFrame with added FYTD_CollectTotalAmt column
        
    Raises:
        ValueError: If required columns are missing
    """
    logger.info("Starting collection data processing...")
    
    # Validate required columns exist
    validate_collection_columns(df)
    
    # Ensure columns are numeric, handling any non-numeric values
    df['FYTD_ARCollectedAmt'] = pd.to_numeric(df['FYTD_ARCollectedAmt'], errors='coerce')
    df['FYTD_ARCollectedTaxAmt'] = pd.to_numeric(df['FYTD_ARCollectedTaxAmt'], errors='coerce')
    
    # Fill NaN values with 0 for calculation
    df['FYTD_ARCollectedAmt'] = df['FYTD_ARCollectedAmt'].fillna(0)
    df['FYTD_ARCollectedTaxAmt'] = df['FYTD_ARCollectedTaxAmt'].fillna(0)
    
    # Calculate FYTD_CollectTotalAmt = FYTD_ARCollectedAmt - FYTD_ARCollectedTaxAmt
    df['FYTD_CollectTotalAmt'] = df['FYTD_ARCollectedAmt'] - df['FYTD_ARCollectedTaxAmt']
    
    logger.info(f"Calculated FYTD_CollectTotalAmt for {len(df)} records")
    logger.info(f"Total FYTD_CollectTotalAmt sum: ${df['FYTD_CollectTotalAmt'].sum():,.2f}")
    
    return df

def get_collection_metrics(df):
    """
    Calculate collection-related metrics for dashboard display.
    
    Args:
        df (pd.DataFrame): DataFrame with collection data
        
    Returns:
        dict: Collection metrics including totals and sums
    """
    if 'FYTD_CollectTotalAmt' not in df.columns:
        logger.warning("FYTD_CollectTotalAmt column not found. Processing collection data first.")
        df = process_collection_data(df)
    
    metrics = {
        'total_collected_amount': df['FYTD_CollectTotalAmt'].sum(),
        'total_collected_gross': df['FYTD_ARCollectedAmt'].sum() if 'FYTD_ARCollectedAmt' in df.columns else 0,
        'total_collected_tax': df['FYTD_ARCollectedTaxAmt'].sum() if 'FYTD_ARCollectedTaxAmt' in df.columns else 0,
        'record_count': len(df)
    }
    
    logger.info(f"Collection metrics calculated: {metrics}")
    return metrics

def get_billing_metrics(df):
    """
    Calculate billing-related metrics for dashboard display.
    
    Args:
        df (pd.DataFrame): DataFrame with billing data
        
    Returns:
        dict: Billing metrics including totals and sums
    """
    if 'FYTD_TotalBilledAmt' not in df.columns:
        logger.warning("FYTD_TotalBilledAmt column not found. Processing billing data first.")
        df = process_billing_data(df)
    
    metrics = {
        'total_billed_amount': df['FYTD_TotalBilledAmt'].sum(),
        'record_count': len(df)
    }
    
    logger.info(f"Billing metrics calculated: {metrics}")
    return metrics
