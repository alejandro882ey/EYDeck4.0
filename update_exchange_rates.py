import requests
import pandas as pd
from datetime import datetime
import os

# Configuration
# The script now looks for the Excel file in the same directory as the script itself.
EXCEL_FILE_PATH = os.path.join(os.path.dirname(__file__), 'Historial_TCBinance.xlsx')
OFICIAL_API_URL = "https://ve.dolarapi.com/v1/dolares/oficial"
PARALELO_API_URL = "https://ve.dolarapi.com/v1/dolares/paralelo"

def fetch_rate(api_url):
    """Fetches the exchange rate from the specified API."""
    try:
        # SSL verification is disabled due to SSLCertVerificationError in the execution environment.
        response = requests.get(api_url, verify=False)
        response.raise_for_status()  # Raise an exception for bad status codes
        data = response.json()
        return data.get('promedio')
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from {api_url}: {e}")
        return None
    except ValueError:
        print(f"Error parsing JSON from {api_url}")
        return None

def update_excel_file():
    """Fetches the latest exchange rates and updates the Excel file."""
    print("Fetching latest exchange rates...")
    oficial_rate = fetch_rate(OFICIAL_API_URL)
    paralelo_rate = fetch_rate(PARALELO_API_URL)

    if oficial_rate is None or paralelo_rate is None:
        print("Could not fetch one or both exchange rates. Aborting update.")
        return

    today_date = datetime.now().strftime('%#m/%#d/%Y') # Format for Windows, without leading zeros

    new_data = {
        'Fecha': [today_date],
        'Tasa Paralelo (USD/VES)': [paralelo_rate],
        'Tasa Oficial (USD/VES)': [oficial_rate]
    }
    new_df = pd.DataFrame(new_data)

    print(f"New data to append: \n{new_df.to_string(index=False)}")


    try:
        # Check if the file exists to avoid creating a new one with wrong headers
        if os.path.exists(EXCEL_FILE_PATH):
            # Use openpyxl to append data without overwriting
            with pd.ExcelWriter(EXCEL_FILE_PATH, engine='openpyxl', mode='a', if_sheet_exists='overlay') as writer:
                 # Find the last row in the existing sheet
                workbook = writer.book
                sheet_name = 'Sheet1' # Assuming the data is on Sheet1
                if sheet_name not in workbook.sheetnames:
                     # if sheet does not exist, create it with headers
                     new_df.to_excel(writer, sheet_name=sheet_name, index=False, header=True)
                else:
                    worksheet = workbook[sheet_name]
                    last_row = worksheet.max_row
                    # Append the new data without the header
                    new_df.to_excel(writer, sheet_name=sheet_name, startrow=last_row, index=False, header=False)

            print(f"Successfully appended new rates to {EXCEL_FILE_PATH}")
        else:
            # If the file doesn't exist, create it with the header
            new_df.to_excel(EXCEL_FILE_PATH, index=False, engine='openpyxl')
            print(f"Created new file and saved rates at {EXCEL_FILE_PATH}")

    except Exception as e:
        print(f"Error updating Excel file: {e}")


if __name__ == "__main__":
    update_excel_file()