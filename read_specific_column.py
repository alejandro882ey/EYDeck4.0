import pandas as pd
import openpyxl

def read_specific_column():
    """
    Read the specific column X (Perdida al tipo de cambio Monitor) from rows 2-218
    """
    
    source_file = r"C:\Users\CK624GF\OneDrive - EY\Documents\2025\Reports\Acumulado Detalle de perdida cambiaria FY26 a Agosto 29-08-2025.xlsx"
    
    print("=== READING SPECIFIC COLUMN X (PERDIDA AL TIPO DE CAMBIO MONITOR) ===\n")
    
    try:
        # Method 1: Using openpyxl to read specific cells
        print("1. Using openpyxl to read column X, rows 2-218:")
        
        workbook = openpyxl.load_workbook(source_file)
        sheet = workbook.active
        
        values = []
        for row in range(2, 219):  # rows 2 to 218 inclusive
            cell_value = sheet[f'X{row}'].value
            if cell_value is not None:
                try:
                    numeric_value = float(cell_value)
                    values.append(numeric_value)
                except:
                    print(f"   Non-numeric value in row {row}: {cell_value}")
            else:
                values.append(0.0)  # Treat None as 0
        
        total_sum = sum(values)
        print(f"   Total rows processed: {len(values)}")
        print(f"   Sum of column X (rows 2-218): ${total_sum:,.2f}")
        print(f"   Non-zero values: {sum(1 for v in values if v != 0)}")
        print(f"   Min value: ${min(values):,.2f}")
        print(f"   Max value: ${max(values):,.2f}")
        
        # Show first 10 non-zero values with their row numbers
        print(f"\n   First 10 non-zero values:")
        count = 0
        for i, value in enumerate(values):
            if value != 0 and count < 10:
                row_num = i + 2  # Add 2 because we started from row 2
                print(f"     Row {row_num}: ${value:,.2f}")
                count += 1
        
        workbook.close()
        
        # Method 2: Using pandas to verify
        print(f"\n2. Using pandas to verify (reading entire sheet):")
        
        df = pd.read_excel(source_file)
        print(f"   Total columns in sheet: {len(df.columns)}")
        print(f"   Column names: {list(df.columns)}")
        
        # Find the perdida column
        perdida_col = None
        for col in df.columns:
            if 'Perdida al tipo de cambio Monitor' in str(col):
                perdida_col = col
                break
        
        if perdida_col:
            print(f"   Found perdida column: '{perdida_col}'")
            
            # Get rows 1-217 (0-indexed, so rows 2-218 in Excel)
            subset_df = df.iloc[0:217]  # rows 1-217 (0-indexed)
            
            # Convert to numeric
            subset_df[perdida_col] = pd.to_numeric(subset_df[perdida_col], errors='coerce')
            
            pandas_sum = subset_df[perdida_col].sum()
            print(f"   Pandas sum (rows 1-217): ${pandas_sum:,.2f}")
            print(f"   Total rows in subset: {len(subset_df)}")
            print(f"   Non-null values: {subset_df[perdida_col].notna().sum()}")
            
            # Check if this matches your expected $205,550
            print(f"\n3. Comparison with expected value:")
            expected = 205550
            difference = abs(pandas_sum) - expected
            print(f"   Expected: ${expected:,.2f}")
            print(f"   Actual (absolute): ${abs(pandas_sum):,.2f}")
            print(f"   Difference: ${difference:,.2f}")
        else:
            print("   Perdida column not found!")
        
    except Exception as e:
        print(f"Error reading file: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    read_specific_column()
