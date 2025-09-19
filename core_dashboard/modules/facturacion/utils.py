import pandas as pd
import openpyxl


def extract_facturacion_sheet(uploaded_file):
    """Simple extractor placeholder for Facturacion files.
    Strategy: try to read the first sheet with pandas.read_excel and return DataFrame.
    The real implementation should detect headers and handle preambles similar to Cobranzas.extract_cobranzas_sheet.
    """
    uploaded_file.seek(0)
    try:
        df = pd.read_excel(uploaded_file, sheet_name=0)
        # Normalize column names
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception:
        return None
