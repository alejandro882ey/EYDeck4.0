"""
Small helper to validate the new extraction logic without importing into Django.
Usage:
    python tools/validate_new_extraction.py <engagement_path> <dif_path> <revenue_path> <upload_date>

It will load files using process_uploaded_data._load_file and print whether required columns are found,
and a small sample of mapped values for FYTD_ANSR_Sintetico and Perdida differential.
"""
import sys
import pandas as pd
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from process_uploaded_data import _load_file


def main():
    if len(sys.argv) != 5:
        print("Usage: python tools/validate_new_extraction.py <engagement_path> <dif_path> <revenue_path> <upload_date>")
        return

    engagement_path, dif_path, revenue_path, upload_date = sys.argv[1:]
    week = pd.to_datetime(upload_date).date()

    engagement_expected_cols = [
        "EngagementID", "Engagement", "EngagementPartner", "EngagementManager",
        "Client", "EngagementServiceLine", "EngagementSubServiceLine",
        "FYTD_ChargedHours", "FYTD_DirectCostAmt", "FYTD_ANSRAmt",
        "MTD_ChargedHours", "MTD_DirectCostAmt", "MTD_ANSRAmt", "CP_ANSRAmt",
    ]
    dif_expected_cols = ["Socio", "Gerente", "Perdida al tipo de cambio Monitor", "Fecha de Cobro", "Engagement"]
    revenue_expected_cols = ["Employee Country/Region", "Employee"]

    engagement_df = _load_file(engagement_path, engagement_expected_cols, sheet_name='DATA ENG LIST')
    dif_df = _load_file(dif_path, dif_expected_cols, sheet_name='DATA DIFERENCIAL')
    revenue_df = _load_file(revenue_path, revenue_expected_cols, sheet_name='RevenueDays')

    print("Engagement columns:", engagement_df.columns.tolist())
    synth_cols = [c for c in engagement_df.columns if 'FYTD_ANSRAmt' in c and 'Sintet' in c]
    if synth_cols:
        print("Found synthetic ANSR column:", synth_cols[0])
        print(engagement_df[["EngagementID", synth_cols[0]]].head())
    else:
        print("Synthetic ANSR column not found; falling back to 'FYTD_ANSRAmt' if present")
        if 'FYTD_ANSRAmt' in engagement_df.columns:
            print(engagement_df[["EngagementID", 'FYTD_ANSRAmt']].head())

    # Check dif mappings
    print("Dif columns:", dif_df.columns.tolist())
    if 'Perdida al tipo de cambio Monitor' in dif_df.columns:
        print(dif_df[['Engagement', 'Perdida al tipo de cambio Monitor']].head())
    else:
        alt = [c for c in dif_df.columns if 'Perdida' in c]
        print('Alternative Perdida columns:', alt)

    # revenue days sample
    print('Revenue columns:', revenue_df.columns.tolist())
    print('Sample Venezuela rows:')
    country_col = next((col for col in revenue_df.columns if 'Employee Country/Region' in col), None)
    if country_col:
        vene = revenue_df[revenue_df[country_col].str.contains('Venezuela', case=False, na=False)]
        print(vene.head())

if __name__ == '__main__':
    main()
