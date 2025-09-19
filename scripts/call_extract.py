from pathlib import Path
import sys, os
BASE_DIR = r'c:\Users\CK624GF\OneDrive - EY\Documents\2025\dashboard_django'
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dashboard_django.settings')
import django
django.setup()

from core_dashboard.modules.cobranzas.utils import extract_cobranzas_sheet

sample = r'C:\Users\CK624GF\OneDrive - EY\Documents\2025\Reports\cobranzas\FY26_11Jul_ Semana del 07 al 11 de Julio - IGTF 3%.xlsx'
with open(sample, 'rb') as f:
    df = extract_cobranzas_sheet(f)

print('Returned DataFrame type:', type(df))
if df is None:
    print('No DataFrame returned')
    sys.exit(0)

print('Columns:', df.columns.tolist())
print('Dtypes:\n', df.dtypes)
print('Head:\n', df.head(15))

key_usd_col = 'Monto en Dólares de la Factura'
# prefer suffixed equivalents, but fall back to generic if necessary
eq_candidates = [
    'Monto equivalente en USD de los VES Cobrados (BCV)',
    'Monto equivalente en USD de los VES Cobrados (Monitor)',
    'Monto equivalente en USD de los VES Cobrados (Casa de Bolsa)',
    'Monto equivalente en USD de los VES Cobrados',
    'Monto equivalente en USD de los VES Cobrados '
]

print('\nNon-null values sample for invoice USD column:')
if key_usd_col in df.columns:
    print(df[key_usd_col].dropna().tolist()[:10])
else:
    print('Invoice USD column not present')

print('\nDetected equivalence columns present:')
present_eqs = [c for c in eq_candidates if c in df.columns]
print(present_eqs)
