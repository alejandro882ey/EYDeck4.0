import pandas as pd
import re
from datetime import datetime, timedelta
import sys
import os

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dashboard_django.settings')
import django
django.setup()

from core_dashboard.models import RevenueEntry, Client, Area, SubArea, Contract
from django.db import transaction
from decimal import Decimal

def _load_file(file_path, expected_columns, max_header_rows=10, sheet_name=None):
    """
    Loads a file and dynamically finds the header row based on expected columns.
    Can dynamically find the sheet if sheet_name is None or not found.
    """
    print(f"Attempting to load file: {file_path} (Sheet: {sheet_name}) and find header with expected columns: {expected_columns}", file=sys.stderr)

    # For Excel files, try to find the sheet dynamically if sheet_name is not provided or not found
    if file_path.endswith(('.xls', '.xlsx', '.xlsb')):
        xl = pd.ExcelFile(file_path, engine='openpyxl' if file_path.endswith(('.xls', '.xlsx')) else 'pyxlsb')
        
        sheets_to_try = []
        if sheet_name and sheet_name in xl.sheet_names:
            sheets_to_try.append(sheet_name)
        else:
            sheets_to_try.extend(xl.sheet_names) # Try all sheets if specific one not found or not provided

        for current_sheet_name in sheets_to_try:
            try:
                # Read the file without a header initially, reading enough rows to find the header
                temp_df = xl.parse(current_sheet_name, header=None, nrows=max_header_rows + 1)
                
                # Iterate through potential header rows
                found_header_row = -1
                for i in range(min(max_header_rows, len(temp_df))):
                    current_header = temp_df.iloc[i].astype(str).tolist()
                    # Check if all expected columns are present in the current header candidate
                    if all(col in current_header for col in expected_columns):
                        found_header_row = i
                        print(f"Found header for expected columns in sheet '{current_sheet_name}' at row {found_header_row}", file=sys.stderr)
                        # Reload the file with the identified header row and sheet
                        df = xl.parse(current_sheet_name, header=found_header_row)
                        # Clean column names (remove leading/trailing spaces)
                        df.columns = df.columns.str.strip()
                        print(f"Successfully loaded {file_path} (Sheet: {current_sheet_name}) with header at row {found_header_row}. Columns: {df.columns.tolist()}", file=sys.stderr)
                        return df
            except Exception as e:
                print(f"Error parsing sheet '{current_sheet_name}': {e}", file=sys.stderr)
        
        raise ValueError(f"Could not find a sheet containing all expected columns {expected_columns} in file {file_path} within the first {max_header_rows} rows of any sheet.")
    
    # Original CSV loading logic (if not Excel)
    elif file_path.endswith('.csv'):
        try:
            temp_df = pd.read_csv(file_path, header=None, encoding='utf-8', nrows=max_header_rows + 1)
        except UnicodeDecodeError:
            temp_df = pd.read_csv(file_path, header=None, encoding='latin1', nrows=max_header_rows + 1)
        
        # Iterate through potential header rows
        found_header_row = -1
        for i in range(min(max_header_rows, len(temp_df))):
            current_header = temp_df.iloc[i].astype(str).tolist()
            if all(col in current_header for col in expected_columns):
                found_header_row = i
                break

        if found_header_row == -1:
            raise ValueError(f"Could not find a header row containing all expected columns {expected_columns} in file {file_path} within the first {max_header_rows} rows. Found columns in first row: {temp_df.iloc[0].tolist()}")

        # Reload the file with the identified header row
        try:
            df = pd.read_csv(file_path, header=found_header_row, encoding='utf-8')
        except UnicodeDecodeError:
            df = pd.read_csv(file_path, header=found_header_row, encoding='latin1')
        
        # Clean column names (remove leading/trailing spaces)
        df.columns = df.columns.str.strip()

        print(f"Successfully loaded {file_path} with header at row {found_header_row}. Columns: {df.columns.tolist()}", file=sys.stderr)
        return df
    else:
        raise ValueError(f"Unsupported file type: {file_path}. Only .csv, .xls, .xlsx, .xlsb are supported.")


def build_merged_df(engagement_df, revenue_df, week_ending_date):
    """
    Build the merged dataframe used for import and dashboard cards from engagement and revenue dataframes.
    This function centralizes the logic so it can be tested in isolation.

    Returns: merged_df (pandas.DataFrame)
    """
    # Ensure numeric types for key financial and hours columns
    numeric_cols = [
        "FYTD_ChargedHours", "FYTD_DirectCostAmt", "FYTD_ANSRAmt",
        "MTD_ChargedHours", "MTD_DirectCostAmt", "MTD_ANSRAmt", "CP_ANSRAmt",
        "FYTD_ARCollectedAmt", "FYTD_ARCollectedTaxAmt",  # Collection columns
        "FYTD_TotalBilledAmt"  # Billing column
    ]

    for col in numeric_cols:
        if col in engagement_df.columns:
            engagement_df[col] = pd.to_numeric(engagement_df[col], errors='coerce')

    # Process collection/billing using existing modules (these functions operate on engagement_df)
    try:
        from core_dashboard.modules.collection_module import process_collection_data, process_billing_data
        engagement_df = process_collection_data(engagement_df)
        engagement_df = process_billing_data(engagement_df)
    except Exception:
        # If collection module isn't available in test environment, ignore
        pass

    # Start merged_df as a copy of engagement_df (we no longer use external dif file)
    merged_df = engagement_df.copy()

    # Prefer the exact Perdida header if present, otherwise fall back to fuzzy detection
    exact_perda = 'Perdida Dif. Camb.'
    if exact_perda in engagement_df.columns:
        perda_col = exact_perda
        merged_df['diferencial_final'] = pd.to_numeric(merged_df.get(perda_col), errors='coerce')
    else:
        perda_col_candidates = [c for c in engagement_df.columns if 'Perdida' in c and ('Dif' in c or 'Camb' in c or 'tipo de cambio' in c)]
        if perda_col_candidates:
            perda_col = perda_col_candidates[0]
            merged_df['diferencial_final'] = pd.to_numeric(merged_df.get(perda_col), errors='coerce')
        else:
            merged_df['diferencial_final'] = 0.0

    # Exceptional date 2025-07-11: force zeros if requested
    try:
        if week_ending_date == pd.to_datetime('2025-07-11').date():
            merged_df['diferencial_final'] = 0.0
    except Exception:
        pass

    # Keep sign convention (previous code negated the monitor column)
    merged_df['diferencial_final'] = -pd.to_numeric(merged_df['diferencial_final'], errors='coerce').fillna(0.0)

    # Ensure FYTD_ANSR_Sintetico comes from Engagement synthetic if present
    synth_col_candidates = [col for col in engagement_df.columns if 'FYTD_ANSRAmt' in col and 'Sintet' in col]
    if synth_col_candidates:
        synth_col = synth_col_candidates[0]
        merged_df['FYTD_ANSR_Sintetico'] = pd.to_numeric(merged_df.get(synth_col), errors='coerce')
    else:
        if 'FYTD_ANSRAmt' in merged_df.columns:
            merged_df['FYTD_ANSR_Sintetico'] = pd.to_numeric(merged_df.get('FYTD_ANSRAmt'), errors='coerce')
        else:
            merged_df['FYTD_ANSR_Sintetico'] = None

    # Add Periodo Fiscal placeholder if not present
    if 'Periodo Fiscal' not in merged_df.columns:
        from core_dashboard.utils import get_fiscal_month_year
        merged_df['Periodo Fiscal'] = get_fiscal_month_year(week_ending_date)

    return merged_df


if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python process_uploaded_data.py <engagement_path> <dif_path> <revenue_path> <upload_date_str>", file=sys.stderr)
        sys.exit(1)

    engagement_path = sys.argv[1]
    dif_path = sys.argv[2]
    revenue_path = sys.argv[3]
    upload_date_str = sys.argv[4]

    try:
        week_ending_date = pd.to_datetime(upload_date_str).date()

        # Define expected columns for each file type
        engagement_expected_cols = [
            "EngagementID", "Engagement", "EngagementPartner", "EngagementManager",
            "Client", "EngagementServiceLine", "EngagementSubServiceLine",
            "FYTD_ChargedHours", "FYTD_DirectCostAmt", "FYTD_ANSRAmt",
            "MTD_ChargedHours", "MTD_DirectCostAmt", "MTD_ANSRAmt", "CP_ANSRAmt",
            "FYTD_ARCollectedAmt", "FYTD_ARCollectedTaxAmt",  # Collection columns
            "FYTD_TotalBilledAmt"  # Billing column
        ]
        dif_expected_cols = [
            "Socio", "Gerente", "Perdida al tipo de cambio Monitor",
            "Fecha de Cobro", "Engagement"
        ]
        # For revenue, the original script skips 8 rows and then takes row 9 as header.
        # The key columns used later are 'Employee Country/Region' and 'Employee'.
        # We will look for these in the header.
        revenue_expected_cols = ["Employee Country/Region", "Employee"]

        # Load data using the dynamic header finding function, specifying sheet names
        engagement_df = _load_file(engagement_path, expected_columns=engagement_expected_cols, sheet_name='DATA ENG LIST')
        dif_df = _load_file(dif_path, expected_columns=dif_expected_cols, sheet_name='DATA DIFERENCIAL')
        revenue_df = _load_file(revenue_path, expected_columns=revenue_expected_cols, sheet_name='RevenueDays')

        # Filter columns
        # The _load_file function already ensures these columns are present.
        # We still filter to ensure order and only keep necessary columns.
        engagement_df = engagement_df[engagement_expected_cols]
        engagement_df["Duplicate EngagementID"] = engagement_df["EngagementID"].duplicated(keep=False).astype(int)
        engagement_df["Week"] = week_ending_date

        # Ensure numeric types for key financial and hours columns
        numeric_cols = [
            "FYTD_ChargedHours", "FYTD_DirectCostAmt", "FYTD_ANSRAmt",
            "MTD_ChargedHours", "MTD_DirectCostAmt", "MTD_ANSRAmt", "CP_ANSRAmt",
            "FYTD_ARCollectedAmt", "FYTD_ARCollectedTaxAmt",  # Collection columns
            "FYTD_TotalBilledAmt"  # Billing column
        ]

        for col in numeric_cols:
            engagement_df[col] = pd.to_numeric(engagement_df[col], errors='coerce')

        # Import and use collection module to process collection and billing data
        from core_dashboard.modules.collection_module import process_collection_data, process_billing_data
        engagement_df = process_collection_data(engagement_df)
        engagement_df = process_billing_data(engagement_df)


        # We no longer use the external DIF/Acumulado Diferencia file for diferencial values.
        # Instead, the Engagement List contains the required 'Perdida Dif. Camb.' column
        # which should feed all cards and charts that previously used the Monitor column.
        # If the engagement file lacks this column (e.g., the 2025-07-11 upload),
        # set the diferencial to 0 for those rows as a provisional behavior.

        # Merge keys are just the Engagement-level identifiers - we merge engagement_df with itself
        # to preserve structure (no external dif_df). Use a simple copy.
        merged_df = engagement_df.copy()

        # Detect Perdida column in engagement_df (look for 'Perdida Dif. Camb.' or similar)
        perda_col_candidates = [c for c in engagement_df.columns if 'Perdida' in c and ('Dif' in c or 'Camb' in c or 'tipo de cambio' in c)]
        if perda_col_candidates:
            perda_col = perda_col_candidates[0]
            print(f"Using engagement Perdida column: {perda_col}", file=sys.stderr)
            merged_df['diferencial_final'] = pd.to_numeric(merged_df.get(perda_col), errors='coerce')
        else:
            print("Engagement file does not contain a 'Perdida Dif. Camb.'-like column. Setting diferencial_final to 0.", file=sys.stderr)
            merged_df['diferencial_final'] = 0.0

        # For the known exceptional date 2025-07-11 the Engagement List lacks the Perdida column.
        # Enforce zeros for that date as requested.
        try:
            if week_ending_date == pd.to_datetime('2025-07-11').date():
                merged_df['diferencial_final'] = 0.0
        except Exception:
            pass

        # Negate sign to keep previous convention (previous code negated monitor column)
        merged_df['diferencial_final'] = -pd.to_numeric(merged_df['diferencial_final'], errors='coerce').fillna(0.0)

        # Ensure numeric types
        merged_df["FYTD_ANSRAmt"] = pd.to_numeric(merged_df["FYTD_ANSRAmt"], errors='coerce')
        merged_df["diferencial_final"] = pd.to_numeric(merged_df["diferencial_final"], errors='coerce')
        merged_df["diferencial_final"] = -merged_df["diferencial_final"]

        # Get the fiscal month and year for this upload
        from core_dashboard.utils import get_fiscal_month_year
        fiscal_period = get_fiscal_month_year(week_ending_date)
        fiscal_month_name = fiscal_period.split(' ')[0]
        fiscal_year = int(fiscal_period.split(' ')[1])

        # Add periodo_fiscal column
        merged_df["Periodo Fiscal"] = fiscal_period

        # Check if this is July (first month of fiscal year)
        is_first_fiscal_month = fiscal_month_name == 'Julio'

        # Calculate diferencial_mtd
        # For July (first month), just use the diferencial_final values directly
        if is_first_fiscal_month:
            print("Processing first fiscal month (July) - using diferencial_final as MTD", file=sys.stderr)
            merged_df["diferencial_mtd"] = merged_df["diferencial_final"]
            print(f"First month MTD sum: {merged_df['diferencial_mtd'].sum()}", file=sys.stderr)
        else:
            from django.db.models import Max
            from core_dashboard.models import RevenueEntry

            # Find the last report from the previous fiscal month
            # Get current fiscal period
            current_fiscal_period = get_fiscal_month_year(week_ending_date)
            
            # Get all unique dates and find the last one from previous fiscal month
            all_dates = RevenueEntry.objects.values_list('date', flat=True).distinct().order_by('date')
            
            last_report_prev_fiscal_month = None
            for report_date in all_dates:
                if report_date >= week_ending_date:
                    break
                report_fiscal_period = get_fiscal_month_year(report_date)
                if report_fiscal_period != current_fiscal_period:
                    last_report_prev_fiscal_month = report_date

            print(f"Current fiscal period: {current_fiscal_period}", file=sys.stderr)
            print(f"Last report date from previous fiscal month: {last_report_prev_fiscal_month}", file=sys.stderr)

            if last_report_prev_fiscal_month:
                print("Found previous fiscal month data", file=sys.stderr)
                # Get all entries from last report of previous fiscal month
                last_month_entries = RevenueEntry.objects.filter(
                    date=last_report_prev_fiscal_month
                ).values('engagement_id', 'fytd_diferencial_final')
                
                # Convert to dictionary for faster lookups
                last_month_diff_by_eng = {
                    entry['engagement_id']: entry['fytd_diferencial_final'] 
                    for entry in last_month_entries
                }
                
                # Calculate MTD for each row
                def calc_mtd(row):
                    eng_id = row['EngagementID']
                    curr_diff = row['diferencial_final'] or 0
                    prev_diff = last_month_diff_by_eng.get(eng_id, 0) or 0
                    mtd_value = curr_diff - prev_diff
                    return mtd_value

                # Apply the calculation and store results
                merged_df["diferencial_mtd"] = merged_df.apply(calc_mtd, axis=1)
                print(f"Subsequent fiscal month MTD sum: {merged_df['diferencial_mtd'].sum()}", file=sys.stderr)
            else:
                print("No previous fiscal month data found - using diferencial_final as MTD", file=sys.stderr)
                merged_df["diferencial_mtd"] = merged_df["diferencial_final"]
                print(f"MTD sum (no prev fiscal data): {merged_df['diferencial_mtd'].sum()}", file=sys.stderr)
        
        # Print summary for verification
        print(f"Final diferencial_mtd sum: {merged_df['diferencial_mtd'].sum()}", file=sys.stderr)
        print(f"Final diferencial_final sum: {merged_df['diferencial_final'].sum()}", file=sys.stderr)

        # Validation step for first fiscal month
        if is_first_fiscal_month:
            print("Validating first month: diferencial_mtd should equal diferencial_final", file=sys.stderr)
            # For first month, ensure diferencial_mtd matches diferencial_final
            # Handle null values properly
            for idx in merged_df.index:
                final_val = merged_df.at[idx, 'diferencial_final']
                mtd_val = merged_df.at[idx, 'diferencial_mtd']
                
                if pd.isna(final_val) and not pd.isna(mtd_val):
                    # If no final value but has MTD, set MTD to NaN
                    merged_df.at[idx, 'diferencial_mtd'] = None
                elif not pd.isna(final_val) and pd.isna(mtd_val):
                    # If has final value but no MTD, set MTD to final
                    merged_df.at[idx, 'diferencial_mtd'] = final_val
                elif not pd.isna(final_val) and not pd.isna(mtd_val) and final_val != mtd_val:
                    # If both exist but don't match, set MTD to final
                    merged_df.at[idx, 'diferencial_mtd'] = final_val
            
            # Verify after correction
            corrected_mtd_sum = merged_df['diferencial_mtd'].sum()
            corrected_final_sum = merged_df['diferencial_final'].sum()
            print(f"After validation - MTD sum: {corrected_mtd_sum}, Final sum: {corrected_final_sum}", file=sys.stderr)

        # Recalculate FYTD_ANSR_Sintetico
        # Note: New source mapping — FYTD_ANSR_Sintetico should be derived from the Engagement file.
        # The Engagement file provides 'FYTD_ANSRAmt (Sintético)' in most uploads. If that column
        # is missing (e.g., historic upload on 2025-07-11), fall back to 'FYTD_ANSRAmt'.
        synth_col_candidates = [col for col in engagement_df.columns if 'FYTD_ANSRAmt' in col and 'Sintet' in col]
        if synth_col_candidates:
            synth_col = synth_col_candidates[0]
            print(f"Using engagement synthetic ANSR column: {synth_col}", file=sys.stderr)
            # align into merged_df
            merged_df['FYTD_ANSR_Sintetico'] = merged_df[synth_col]
        else:
            # fallback to FYTD_ANSRAmt from engagement_df
            if 'FYTD_ANSRAmt' in merged_df.columns:
                merged_df['FYTD_ANSR_Sintetico'] = merged_df['FYTD_ANSRAmt']
            else:
                # As a last resort, set to NaN
                merged_df['FYTD_ANSR_Sintetico'] = None

        # If the engagement file for a specific upload date (provisional case 2025-07-11)
        # lacks the synthetic column but provides 'FYTD_ANSRAmt', keep that as provisional value.
        # Ensure numeric types and subtract diferencial_final where appropriate when needed
        try:
            merged_df['FYTD_ANSR_Sintetico'] = pd.to_numeric(merged_df['FYTD_ANSR_Sintetico'], errors='coerce')
        except Exception:
            pass

        # Find the column that contains 'Employee Country/Region'
        country_col = next((col for col in revenue_df.columns if "Employee Country/Region" in col), None)
        if country_col is None:
            raise KeyError("Could not find a column containing 'Employee Country/Region' in revenue_df.")

        # Filter for Venezuela
        venezuela_df = revenue_df[revenue_df[country_col].str.contains("Venezuela", case=False, na=False)]

        # Find the column that contains 'Employee' for merging
        employee_col = next((col for col in venezuela_df.columns if "Employee" in col), None)
        if employee_col is None:
            raise KeyError("Could not find a column containing 'Employee' in venezuela_df.")

        # Merge with merged_df using EngagementPartner and employee_col
        merged_df = pd.merge(
            merged_df,
            venezuela_df,
            left_on="EngagementPartner",
            right_on=employee_col,
            how="left"
        )


        # Calculated columns
        merged_df["Margin"] = merged_df["FYTD_ANSR_Sintetico"] - merged_df["FYTD_DirectCostAmt"]
        merged_df["Margin_%"] = merged_df["Margin"] / merged_df["FYTD_ANSR_Sintetico"]
        merged_df["RPH"] = merged_df["FYTD_ANSR_Sintetico"] / merged_df["FYTD_ChargedHours"]

        # Rename Venezuela columns with "P"
        for col in venezuela_df.columns:
            if col in merged_df.columns:
                merged_df.rename(columns={col: f"{col} P"}, inplace=True)

        print(f"DEBUG: merged_df columns after 'P' renaming: {merged_df.columns.tolist()}", file=sys.stderr)

        

        # Delete all columns after "25Billings FYTD P"
        # Find the index of "25Billings FYTD P"
        try:
            col_to_keep_until_index = merged_df.columns.get_loc("25Billings FYTD P")
            # Keep columns from the beginning up to and including "25Billings FYTD P"
            merged_df = merged_df.iloc[:, :col_to_keep_until_index + 1]
        except KeyError:
            print("Warning: '25Billings FYTD P' column not found. No columns will be deleted.", file=sys.stderr)

        print(f"DEBUG: merged_df columns after deletion: {merged_df.columns.tolist()}", file=sys.stderr)

        # Renaming based on specific column names as requested by user
        specific_rename_map = {
            "Total Revenue Days P": "Total Revenue Days P CP",
            "Billed Revenue Days P": "Billed Revenue Days P CP",
            "Unbilled Revenue Days P": "Unbilled Revenue Days P CP",
            "Total Revenue Days.1 P": "Total Revenue Days.1 P MTD",
            "Billed Revenue Days.1 P": "Billed Revenue Days.1 P MTD",
            "Unbilled Revenue Days.1 P": "Unbilled Revenue Days.1 P MTD",
            "Total Revenue Days.2 P": "Total Revenue Days.2 P FYTD",
            "Billed Revenue Days.2 P": "Billed Revenue Days.2 P FYTD",
            "Unbilled Revenue Days.2 P": "Unbilled Revenue Days.2 P FYTD",
            "Total Revenue Days.3 P": "Total Revenue Days.3 P 52WKS",
            "Billed Revenue Days.3 P": "Billed Revenue Days.3 P 52WKS",
            "Unbilled Revenue Days.3 P": "Unbilled Revenue Days.3 P 52WKS",
        }
        merged_df.rename(columns=specific_rename_map, inplace=True)
        print(f"DEBUG: merged_df columns after index-based renaming: {merged_df.columns.tolist()}", file=sys.stderr)

        # New deletion based on column index as requested
        # Columns 48 to 67 (inclusive) are 0-indexed 47 to 66
        columns_to_drop_start_idx = 47
        columns_to_drop_end_idx = 66

        if len(merged_df.columns) > columns_to_drop_start_idx:
            cols_to_drop = merged_df.columns[columns_to_drop_start_idx : columns_to_drop_end_idx + 1]
            merged_df.drop(columns=cols_to_drop, inplace=True)
        print(f"DEBUG: merged_df columns after final index-based deletion: {merged_df.columns.tolist()}", file=sys.stderr)

        # NOTE: The Final_Database CSV is no longer produced. The dashboard will read
        # values directly from the three input files (Engagement List, Dif file, Revenue Days).
        print("Skipping writing Final_Database CSV (legacy behavior).", file=sys.stderr)

    # --- Create and save partner revenue days mapping ---
        print("Creating partner revenue days mapping...", file=sys.stderr)
        revenue_days_col_index = 30 # Assuming column 31 is 0-indexed 30
        if len(merged_df.columns) > revenue_days_col_index:
            revenue_days_col_name = merged_df.columns[revenue_days_col_index]
            print(f"Using column '{revenue_days_col_name}' for revenue days.", file=sys.stderr)

            partner_revenue_days = {}
            for index, row in merged_df.iterrows():
                partner = row.get('EngagementPartner')
                revenue_days = row.get(revenue_days_col_name)
                if partner and pd.notna(revenue_days):
                    partner_revenue_days[partner] = revenue_days
            
                media_root = os.path.dirname(os.path.dirname(os.path.dirname(engagement_path))) if os.path.dirname(engagement_path) else os.path.dirname(os.path.dirname(engagement_path))
            json_output_path = os.path.join(media_root, 'revenue_days.json')

            try:
                import json
                with open(json_output_path, 'w') as f:
                    json.dump(partner_revenue_days, f, indent=4)
                print(f"Successfully saved partner revenue days to {json_output_path}", file=sys.stderr)
            except Exception as e:
                print(f"Error saving partner revenue days JSON: {e}", file=sys.stderr)
        else:
            print(f"Warning: Column at index {revenue_days_col_index} not found. Cannot create revenue days mapping.", file=sys.stderr)


        # --- Import data into Django models ---
        print("Starting data import into Django models...", file=sys.stderr)
        try:
            with transaction.atomic():
                # Clear existing data for the given week to prevent duplicates
                # Assuming 'Week' column in merged_df corresponds to 'date' in RevenueEntry
                # and we want to replace data for that specific week.
                # If 'Week' is a single date for the entire upload, then clear all data for that date.
                # If 'Week' can contain multiple dates, then clear based on unique dates in merged_df.
                # For simplicity, let's assume 'Week' is the upload_date_str for all entries.
                RevenueEntry.objects.filter(date=week_ending_date).delete()
                print(f"Cleared existing RevenueEntry data for week: {week_ending_date}", file=sys.stderr)

                for index, row in merged_df.iterrows():
                    # Get or create related objects
                    client_obj, _ = Client.objects.get_or_create(name=row['Client'])
                    area_obj, _ = Area.objects.get_or_create(name=row['EngagementServiceLine'])
                    sub_area_obj, _ = SubArea.objects.get_or_create(name=row['EngagementSubServiceLine'], area=area_obj)
                    # Contract might need more specific logic if it's not just by name
                    # For now, let's assume contract name is unique per client or can be created simply
                    contract_name = row.get('Engagement', None) # Use Engagement as contract name if available
                    contract_obj = None
                    if contract_name:
                        contract_obj, _ = Contract.objects.get_or_create(
                            client=client_obj, name=contract_name,
                            defaults={'value': 0, 'start_date': week_ending_date, 'end_date': week_ending_date}
                        )

                    # Create RevenueEntry instance
                    RevenueEntry.objects.create(
                        date=row['Week'],
                        client=client_obj,
                        contract=contract_obj,
                        area=area_obj,
                        sub_area=sub_area_obj,
                        revenue=None if pd.isna(row.get('FYTD_ANSRAmt')) else Decimal(row.get('FYTD_ANSRAmt')),
                        engagement_partner=row.get('EngagementPartner', ''),
                        engagement_manager=row.get('EngagementManager', ''),
                        collections=None if pd.isna(row.get('Billings FYTD P')) else Decimal(row.get('Billings FYTD P')),
                        billing=None if pd.isna(row.get('Billings CP P')) else Decimal(row.get('Billings CP P')),
                        bcv_rate=None if pd.isna(row.get('BCV Rate')) else Decimal(row.get('BCV Rate')),
                        monitor_rate=None if pd.isna(row.get('Monitor Rate')) else Decimal(row.get('Monitor Rate')),
                        engagement_id=row.get('EngagementID', ''),
                        engagement=row.get('Engagement', ''),
                        engagement_service_line=row.get('EngagementServiceLine', ''),
                        engagement_sub_service_line=row.get('EngagementSubServiceLine', ''),
                        fytd_charged_hours=None if pd.isna(row.get('FYTD_ChargedHours')) else row.get('FYTD_ChargedHours', 0.0),
                        fytd_direct_cost_amt=None if pd.isna(row.get('FYTD_DirectCostAmt')) else row.get('FYTD_DirectCostAmt', 0.0),
                        fytd_ansr_amt=None if pd.isna(row.get('FYTD_ANSRAmt')) else row.get('FYTD_ANSRAmt', 0.0),
                        mtd_charged_hours=None if pd.isna(row.get('MTD_ChargedHours')) else row.get('MTD_ChargedHours', 0.0),
                        mtd_direct_cost_amt=None if pd.isna(row.get('MTD_DirectCostAmt')) else row.get('MTD_DirectCostAmt', 0.0),
                        mtd_ansr_amt=None if pd.isna(row.get('MTD_ANSRAmt')) else row.get('MTD_ANSRAmt', 0.0),
                        cp_ansr_amt=None if pd.isna(row.get('CP_ANSRAmt')) else row.get('CP_ANSRAmt', 0.0),
                        duplicate_engagement_id=None if pd.isna(row.get('Duplicate EngagementID')) else row.get('Duplicate EngagementID', 0),
                        original_week_string=None if pd.isna(row.get('Week')) else row.get('Week').strftime('%Y-%m-%d'),
                        periodo_fiscal=row.get('Periodo Fiscal', ''), # Placeholder
                        fecha_cobro=None if pd.isna(row.get('Fecha de Cobro')) else row.get('Fecha de Cobro').strftime('%Y-%m-%d'),
                        dif_div=None if pd.isna(row.get('Dif_Div')) else row.get('Dif_Div', 0.0),
                        perdida_tipo_cambio_monitor=None if pd.isna(row.get('Perdida al tipo de cambio Monitor')) else row.get('Perdida al tipo de cambio Monitor', 0.0),
                        fytd_diferencial_final=None if pd.isna(row.get('diferencial_final')) else row.get('diferencial_final', 0.0),
                        diferencial_mtd=None if pd.isna(row.get('diferencial_mtd')) else row.get('diferencial_mtd', 0.0),
                        fytd_ansr_sintetico=None if pd.isna(row.get('FYTD_ANSR_Sintetico')) else row.get('FYTD_ANSR_Sintetico', 0.0),
                        total_revenue_days_p_cp=None if pd.isna(row.get('Total Revenue Days P CP')) else row.get('Total Revenue Days P CP', 0.0),
                        # Collection-related fields (DECOUPLED: these are now provided by the Cobranzas module)
                        fytd_ar_collected_amt=None if pd.isna(row.get('FYTD_ARCollectedAmt')) else row.get('FYTD_ARCollectedAmt', 0.0),
                        fytd_ar_collected_tax_amt=None if pd.isna(row.get('FYTD_ARCollectedTaxAmt')) else row.get('FYTD_ARCollectedTaxAmt', 0.0),
                        # fytd_collect_total_amt and fytd_total_billed_amt are deprecated for direct population
                        # and will be provided by the Cobranzas module. Set to None here to avoid legacy ties.
                        fytd_collect_total_amt=None,
                        # Billing-related fields
                        fytd_total_billed_amt=None,
                    )
            print("Data import into Django models completed successfully.", file=sys.stderr)
        except Exception as e:
            print(f"Error importing data into Django models: {e}", file=sys.stderr)
            sys.exit(1) # Exit with error code if import fails

    except Exception as e:
        print(f"Error during processing: {e}", file=sys.stderr)
        sys.exit(1)