import pandas as pd
import os

def analyze_perdida_difference():
    """
    Analyze the difference between the source file and the Final Dataset
    for the 'Perdida al tipo de cambio Monitor' column
    """
    
    # Paths
    source_file = r"C:\Users\CK624GF\OneDrive - EY\Documents\2025\Reports\Acumulado Detalle de perdida cambiaria FY26 a Agosto 29-08-2025.xlsx"
    final_dataset = r"C:\Users\CK624GF\OneDrive - EY\Documents\2025\dashboard_django\media\historico_de_final_database\2025-08-29\Final_Database_2025-08-29.csv"
    
    print("=== ANALYZING PERDIDA DIFERENCIAL DISCREPANCY ===\n")
    
    # Read source file
    try:
        print("1. Reading source file...")
        source_df = pd.read_excel(source_file)
        print(f"   Source file columns: {list(source_df.columns)}")
        
        # Look for the perdida column in source
        perdida_columns = [col for col in source_df.columns if 'perdida' in col.lower() or 'cambio' in col.lower()]
        print(f"   Columns with 'perdida' or 'cambio': {perdida_columns}")
        
        if perdida_columns:
            # Look specifically for 'Perdida al tipo de cambio Monitor'
            perdida_col = 'Perdida al tipo de cambio Monitor'
            if perdida_col in source_df.columns:
                # Convert to numeric, handling any string values
                source_df[perdida_col] = pd.to_numeric(source_df[perdida_col], errors='coerce')
                source_sum = source_df[perdida_col].sum()
                print(f"   Source '{perdida_col}' sum: ${source_sum:,.2f}")
                
                # Check for non-numeric values
                non_numeric = source_df[perdida_col].isna().sum()
                print(f"   Non-numeric values converted to NaN: {non_numeric}")
            else:
                print(f"   'Perdida al tipo de cambio Monitor' not found! Available: {perdida_columns}")
                return
        else:
            print("   No perdida column found in source file!")
            return
            
    except Exception as e:
        print(f"   Error reading source file: {e}")
        return
    
    # Read final dataset
    try:
        print("\n2. Reading Final Dataset...")
        final_df = pd.read_csv(final_dataset)
        print(f"   Final dataset columns: {list(final_df.columns)}")
        
        # Check for perdida columns
        if 'Perdida al tipo de cambio Monitor' in final_df.columns:
            # Convert to numeric to handle any string values
            final_df['Perdida al tipo de cambio Monitor'] = pd.to_numeric(final_df['Perdida al tipo de cambio Monitor'], errors='coerce')
            final_perdida_sum = final_df['Perdida al tipo de cambio Monitor'].sum()
            print(f"   Final 'Perdida al tipo de cambio Monitor' sum: ${final_perdida_sum:,.2f}")
        else:
            print("   'Perdida al tipo de cambio Monitor' column not found!")
            return
            
        if 'diferencial_final' in final_df.columns:
            # Convert to numeric to handle any string values
            final_df['diferencial_final'] = pd.to_numeric(final_df['diferencial_final'], errors='coerce')
            diferencial_sum = final_df['diferencial_final'].sum()
            print(f"   Final 'diferencial_final' sum: ${diferencial_sum:,.2f}")
        else:
            print("   'diferencial_final' column not found!")
            
    except Exception as e:
        print(f"   Error reading final dataset: {e}")
        return
    
    # Calculate differences
    print("\n3. Analysis Results:")
    print(f"   Source file sum: ${source_sum:,.2f}")
    print(f"   Final dataset perdida sum: ${final_perdida_sum:,.2f}")
    print(f"   Final dataset diferencial sum: ${diferencial_sum:,.2f}")
    
    perdida_diff = source_sum - final_perdida_sum
    diferencial_diff = source_sum - diferencial_sum
    
    print(f"\n   Difference (Source - Final Perdida): ${perdida_diff:,.2f}")
    print(f"   Difference (Source - Final Diferencial): ${diferencial_diff:,.2f}")
    
    # Count records
    print(f"\n4. Record Counts:")
    print(f"   Source file rows: {len(source_df)}")
    print(f"   Final dataset rows: {len(final_df)}")
    
    # Check for duplicates or missing EngagementIDs
    if 'EngagementID' in source_df.columns and 'EngagementID' in final_df.columns:
        source_ids = set(source_df['EngagementID'].unique())
        final_ids = set(final_df['EngagementID'].unique())
        
        missing_in_final = source_ids - final_ids
        extra_in_final = final_ids - source_ids
        
        print(f"\n5. EngagementID Analysis:")
        print(f"   Unique IDs in source: {len(source_ids)}")
        print(f"   Unique IDs in final: {len(final_ids)}")
        print(f"   Missing in final: {len(missing_in_final)}")
        print(f"   Extra in final: {len(extra_in_final)}")
        
        if missing_in_final:
            print(f"   First 10 missing IDs: {list(missing_in_final)[:10]}")
            
            # Calculate sum of missing records
            missing_df = source_df[source_df['EngagementID'].isin(missing_in_final)]
            if len(missing_df) > 0:
                missing_sum = missing_df[perdida_col].sum()
                print(f"   Sum of missing records: ${missing_sum:,.2f}")
            else:
                print("   No missing records found")
        
        if extra_in_final:
            print(f"   First 10 extra IDs: {list(extra_in_final)[:10]}")

if __name__ == "__main__":
    analyze_perdida_difference()
