import pandas as pd
import openpyxl
from openpyxl import load_workbook

def read_calculated_values():
    """
    Read the calculated values from Excel formulas
    """
    
    source_file = r"C:\Users\CK624GF\OneDrive - EY\Documents\2025\Reports\Acumulado Detalle de perdida cambiaria FY26 a Agosto 29-08-2025.xlsx"
    final_dataset = r"C:\Users\CK624GF\OneDrive - EY\Documents\2025\dashboard_django\media\historico_de_final_database\2025-08-29\Final_Database_2025-08-29.csv"
    
    print("=== READING CALCULATED VALUES FROM EXCEL ===\n")
    
    try:
        # Method: Using pandas with data_only=True to get calculated values
        print("1. Reading Excel file with calculated values:")
        
        # Read with pandas (this should get calculated values)
        df = pd.read_excel(source_file, engine='openpyxl')
        
        perdida_col = 'Perdida al tipo de cambio Monitor'
        if perdida_col in df.columns:
            print(f"   Found column: '{perdida_col}'")
            
            # Convert to numeric, handling any issues
            df[perdida_col] = pd.to_numeric(df[perdida_col], errors='coerce')
            
            # Get the exact rows you mentioned (rows 2-218 in Excel = index 0-216 in pandas)
            subset_df = df.iloc[0:217].copy()  # First 217 rows
            
            total_sum = subset_df[perdida_col].sum()
            absolute_sum = abs(total_sum)
            
            print(f"   Total rows processed: {len(subset_df)}")
            print(f"   Non-null values: {subset_df[perdida_col].notna().sum()}")
            print(f"   Sum (with sign): ${total_sum:,.2f}")
            print(f"   Absolute sum: ${absolute_sum:,.2f}")
            
            # Show statistics
            print(f"\n   Statistics:")
            print(f"   Min: ${subset_df[perdida_col].min():,.2f}")
            print(f"   Max: ${subset_df[perdida_col].max():,.2f}")
            print(f"   Mean: ${subset_df[perdida_col].mean():,.2f}")
            
            # Count positive vs negative values
            positive_values = subset_df[subset_df[perdida_col] > 0][perdida_col]
            negative_values = subset_df[subset_df[perdida_col] < 0][perdida_col]
            
            print(f"\n   Positive values: {len(positive_values)} (sum: ${positive_values.sum():,.2f})")
            print(f"   Negative values: {len(negative_values)} (sum: ${negative_values.sum():,.2f})")
            
            # Check if the absolute sum matches your expected $205,550
            expected = 205550
            difference = absolute_sum - expected
            print(f"\n2. Comparison with expected $205,550:")
            print(f"   Expected: ${expected:,.2f}")
            print(f"   Actual (absolute): ${absolute_sum:,.2f}")
            print(f"   Difference: ${difference:,.2f}")
            
            # If close to expected, show the exact match rows
            if abs(difference) < 150000:  # Within reasonable range
                print(f"   ✓ Values are in expected range")
            else:
                print(f"   ⚠ Large difference detected")
            
            # Show top 10 largest absolute values with engagement info
            print(f"\n3. Top 10 largest absolute values:")
            abs_subset = subset_df.copy()
            abs_subset['abs_perdida'] = abs_subset[perdida_col].abs()
            top_values = abs_subset.nlargest(10, 'abs_perdida')
            
            for idx, row in top_values.iterrows():
                engagement = str(row.get('Engagement', 'N/A'))
                client = str(row.get('Cliente', 'N/A'))
                value = row[perdida_col]
                print(f"     ${value:,.2f} - {client[:30]} | {engagement[:30]}")
        
        # Now compare with Final Dataset
        print(f"\n4. Comparison with Final Dataset:")
        
        final_df = pd.read_csv(final_dataset)
        if 'Perdida al tipo de cambio Monitor' in final_df.columns:
            final_df['Perdida al tipo de cambio Monitor'] = pd.to_numeric(final_df['Perdida al tipo de cambio Monitor'], errors='coerce')
            final_sum = final_df['Perdida al tipo de cambio Monitor'].sum()
            final_abs_sum = abs(final_sum)
            
            print(f"   Final dataset sum: ${final_sum:,.2f}")
            print(f"   Final dataset absolute: ${final_abs_sum:,.2f}")
            
            source_final_diff = absolute_sum - final_abs_sum
            print(f"   Difference (Source - Final): ${source_final_diff:,.2f}")
            
            # Check diferencial_final column too
            if 'diferencial_final' in final_df.columns:
                final_df['diferencial_final'] = pd.to_numeric(final_df['diferencial_final'], errors='coerce')
                diferencial_sum = final_df['diferencial_final'].sum()
                print(f"   Final diferencial_final sum: ${diferencial_sum:,.2f}")
                
                source_diferencial_diff = absolute_sum - diferencial_sum
                print(f"   Difference (Source - Diferencial): ${source_diferencial_diff:,.2f}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    read_calculated_values()
