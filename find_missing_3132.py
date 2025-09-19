import pandas as pd
import numpy as np

def find_missing_3132():
    """
    Find what's causing the $3,132 difference between source ($205,546) and final dataset ($202,414)
    """
    
    # Correct source data from user
    source_perdida_values = [
        -168, -335, -29, -14, -7, -8, -29, -6847, -85, -88, -492, -36, -64, -7, -112, -16, 0, -920, -293, -143, -304, -2246, -240, -229, -1552, -171, -60, -423, -153, -694, -694, -50, -40, -40, -40, -50, -554, -308, -731, -1315, -114, -4926, -46, -1550, -82, -33, -890, -479, -208, -42, -38, -81, -116, -20074, -779, -948, -238, -151, -209, -267, -448, -389, -446, -298, -314, -679, -941, -638, -486, -171, -2078, 332, -732, -3656, -1108, -823, -559, -164, -1389, -427, 34, -881, -911, -1320, -665, -428, -881, -463, -319, -257, -1404, -3967, -221, -177, -211, -224, -281, -2057, -163, -171, -1959, -240, -224, -1376, -345, 573, 409, 409, -367, -172, -599, -386, -573, -638, -3202, -1572, 916, -165, -573, 6367, -2809, -597, -628, -4924, -218, -82, -1953, -9, -9, -1049, -4456, -1298, -603, -613, -178, -1459, -67, -3, -3, -3, -4364, -2216, -784, -138, -823, -716, -6341, -1972, -431, -409, -65, -26, -2216, -2216, -129, 0, -1, -2, -2, -1, -5, -6, -1538, -218, -400, -3399, -431, -300, -106, -19, -634, -284, -383, -3814, -286, -3699, -1075, -117, 104, -4429, -416, -2524, 457, -4828, -4612, -601, -406, -1519, -43, -68, -1232, -366, -152, -8203, -1167, -812, -7469, -812, 25, -993, -2131, -244, -836, -904, -6, -2251, -2885, -109, -2107, -76, -875, -35, -3062, -123, -459, -16, -3878
    ]
    
    source_sum = abs(sum(source_perdida_values))
    target_difference = 3132  # $205,546 - $202,414
    
    print("=== FINDING THE $3,132 MISSING AMOUNT ===\n")
    print(f"Source data sum: ${source_sum:,.2f}")
    print(f"Current dashboard: $202,414.00")
    print(f"Missing amount: ${target_difference:,.2f}")
    
    # Read the Final Dataset to compare
    final_dataset = r"C:\Users\CK624GF\OneDrive - EY\Documents\2025\dashboard_django\media\historico_de_final_database\2025-08-29\Final_Database_2025-08-29.csv"
    
    try:
        final_df = pd.read_csv(final_dataset)
        
        print(f"\n1. Final Dataset Analysis:")
        print(f"   Total rows: {len(final_df)}")
        
        if 'Perdida al tipo de cambio Monitor' in final_df.columns:
            final_df['Perdida al tipo de cambio Monitor'] = pd.to_numeric(final_df['Perdida al tipo de cambio Monitor'], errors='coerce')
            final_perdida_sum = abs(final_df['Perdida al tipo de cambio Monitor'].sum())
            
            print(f"   Final 'Perdida al tipo de cambio Monitor' sum: ${final_perdida_sum:,.2f}")
            
            # Get the actual values from final dataset
            final_perdida_values = final_df['Perdida al tipo de cambio Monitor'].dropna().tolist()
            
            print(f"   Number of non-null perdida values: {len(final_perdida_values)}")
            print(f"   Source values count: {len(source_perdida_values)}")
            
            # Check if the final dataset has all the source values
            print(f"\n2. Comparing Individual Values:")
            
            # Convert to sets for comparison (taking absolute values and rounding to handle precision)
            source_rounded = set(round(abs(v), 2) for v in source_perdida_values if v != 0)
            final_rounded = set(round(abs(v), 2) for v in final_perdida_values if v != 0)
            
            missing_in_final = source_rounded - final_rounded
            extra_in_final = final_rounded - source_rounded
            
            print(f"   Unique source values (non-zero): {len(source_rounded)}")
            print(f"   Unique final values (non-zero): {len(final_rounded)}")
            print(f"   Values in source but not in final: {len(missing_in_final)}")
            print(f"   Values in final but not in source: {len(extra_in_final)}")
            
            if missing_in_final:
                print(f"\n   Missing values (first 20):")
                missing_list = sorted(list(missing_in_final), reverse=True)[:20]
                missing_sum = sum(missing_list)
                for val in missing_list:
                    print(f"     ${val:,.2f}")
                print(f"   Sum of missing values: ${missing_sum:,.2f}")
                
                if abs(missing_sum - target_difference) < 100:
                    print(f"   *** FOUND THE ISSUE! Missing values sum ≈ ${target_difference:,.2f} ***")
            
            # Check for data processing issues
            print(f"\n3. Data Processing Analysis:")
            
            # Check if there are any rows with zero or null perdida values that should have values
            zero_perdida_rows = final_df[final_df['Perdida al tipo de cambio Monitor'] == 0]
            null_perdida_rows = final_df[final_df['Perdida al tipo de cambio Monitor'].isna()]
            
            print(f"   Rows with zero perdida: {len(zero_perdida_rows)}")
            print(f"   Rows with null perdida: {len(null_perdida_rows)}")
            
            if len(zero_perdida_rows) > 0:
                print(f"   Sample zero perdida engagements:")
                for i, row in zero_perdida_rows.head(5).iterrows():
                    eng_id = row.get('EngagementID', 'N/A')
                    engagement = row.get('Engagement', 'N/A')
                    print(f"     {eng_id}: {engagement}")
        
        # Check diferencial_final column
        if 'diferencial_final' in final_df.columns:
            final_df['diferencial_final'] = pd.to_numeric(final_df['diferencial_final'], errors='coerce')
            diferencial_sum = final_df['diferencial_final'].sum()
            
            print(f"\n4. Diferencial Final Analysis:")
            print(f"   Diferencial final sum: ${diferencial_sum:,.2f}")
            print(f"   Difference from source: ${abs(source_sum - diferencial_sum):,.2f}")
    
    except Exception as e:
        print(f"Error reading final dataset: {e}")
        import traceback
        traceback.print_exc()
    
    # Provide solution steps
    print(f"\n5. SOLUTION STEPS:")
    print(f"   1. The source data should sum to ${source_sum:,.2f}")
    print(f"   2. Current dashboard shows $202,414.00")
    print(f"   3. We need to add ${target_difference:,.2f} to the dashboard")
    print(f"   4. This suggests either:")
    print(f"      - Some source records are not being imported")
    print(f"      - Values are being modified during processing")
    print(f"      - EngagementID mapping issues")
    print(f"      - Data transformation errors in the pipeline")

if __name__ == "__main__":
    find_missing_3132()
