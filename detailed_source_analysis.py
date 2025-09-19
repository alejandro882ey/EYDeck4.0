import pandas as pd
import os

def detailed_source_analysis():
    """
    Detailed analysis of the source file to understand the data structure
    """
    
    source_file = r"C:\Users\CK624GF\OneDrive - EY\Documents\2025\Reports\Acumulado Detalle de perdida cambiaria FY26 a Agosto 29-08-2025.xlsx"
    
    print("=== DETAILED SOURCE FILE ANALYSIS ===\n")
    
    try:
        # Read source file
        source_df = pd.read_excel(source_file)
        
        print("1. Source File Overview:")
        print(f"   Total rows: {len(source_df)}")
        print(f"   Total columns: {len(source_df.columns)}")
        
        # Check the engagement column
        if 'Engagement' in source_df.columns:
            print(f"\n2. Engagement Column Analysis:")
            print(f"   Unique engagements: {source_df['Engagement'].nunique()}")
            print(f"   Sample engagements:")
            for eng in source_df['Engagement'].unique()[:10]:
                print(f"     - {eng}")
        
        # Analyze the perdida column
        perdida_col = 'Perdida al tipo de cambio Monitor'
        if perdida_col in source_df.columns:
            print(f"\n3. '{perdida_col}' Analysis:")
            
            # Convert to numeric
            source_df[perdida_col] = pd.to_numeric(source_df[perdida_col], errors='coerce')
            
            total_sum = source_df[perdida_col].sum()
            positive_sum = source_df[source_df[perdida_col] > 0][perdida_col].sum()
            negative_sum = source_df[source_df[perdida_col] < 0][perdida_col].sum()
            
            print(f"   Total sum: ${total_sum:,.2f}")
            print(f"   Positive values sum: ${positive_sum:,.2f}")
            print(f"   Negative values sum: ${negative_sum:,.2f}")
            print(f"   Absolute sum: ${abs(total_sum):,.2f}")
            
            # Check for null values
            null_count = source_df[perdida_col].isna().sum()
            print(f"   Null/NaN values: {null_count}")
            
            # Value distribution
            print(f"\n   Value distribution:")
            print(f"   Min: ${source_df[perdida_col].min():,.2f}")
            print(f"   Max: ${source_df[perdida_col].max():,.2f}")
            print(f"   Mean: ${source_df[perdida_col].mean():,.2f}")
            
            # Show top 10 largest absolute values
            print(f"\n   Top 10 largest absolute values:")
            abs_df = source_df.copy()
            abs_df['abs_perdida'] = abs_df[perdida_col].abs()
            top_values = abs_df.nlargest(10, 'abs_perdida')
            
            for idx, row in top_values.iterrows():
                engagement = row.get('Engagement', 'N/A')
                value = row[perdida_col]
                print(f"     ${value:,.2f} - {engagement}")
        
        # Check for date information
        date_columns = [col for col in source_df.columns if 'fecha' in col.lower() or 'date' in col.lower()]
        if date_columns:
            print(f"\n4. Date Columns: {date_columns}")
            for col in date_columns[:2]:  # Show first 2 date columns
                if source_df[col].dtype == 'object':
                    print(f"   {col} - sample values: {source_df[col].dropna().head(3).tolist()}")
        
        # Check MES column if exists
        if 'MES' in source_df.columns:
            print(f"\n5. MES Column Analysis:")
            print(f"   Unique months: {source_df['MES'].unique()}")
            
            # Sum by month
            monthly_sum = source_df.groupby('MES')[perdida_col].sum()
            print(f"   Monthly sums:")
            for month, sum_val in monthly_sum.items():
                print(f"     {month}: ${sum_val:,.2f}")
        
    except Exception as e:
        print(f"Error in analysis: {e}")

if __name__ == "__main__":
    detailed_source_analysis()
