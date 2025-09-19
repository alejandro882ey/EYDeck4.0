import os,sys
sys.path.append(r'c:\Users\CK624GF\OneDrive - EY\Documents\2025\dashboard_django')
os.environ['DJANGO_SETTINGS_MODULE']='dashboard_django.settings'
import pandas as pd, unicodedata

def normalize_col(c):
    if c is None:
        return ''
    s = str(c).strip().lower()
    s = ''.join(ch for ch in unicodedata.normalize('NFD', s) if unicodedata.category(ch) != 'Mn')
    s = s.replace(' ', '').replace('\t','')
    return s

p=os.path.join('media','cobranzas','Cobranzas_2025-07-18.xlsx')
df=pd.read_excel(p)
print('cols:', list(df.columns))
cols_to_check = [col for col in df.columns if normalize_col(col) in ('cliente','socio','gerente')]
print('identifier cols:', cols_to_check)
mask=None
for cc in cols_to_check:
    s = pd.notnull(df[cc]) & (df[cc].astype(str).str.strip() != '')
    mask = s if mask is None else (mask | s)
print('mask true count:', mask.sum())
df_masked = df[mask]
print('rows after mask:', len(df_masked))
for c in df_masked.columns:
    nk=normalize_col(c)
    if ('montodendolares' in nk) or ('montoendolares' in nk) or ('montousd' in nk) or ('montoequivalente' in nk) or ('montoenusd' in nk) or ('ves' in nk):
        s = pd.to_numeric(df_masked[c], errors='coerce').fillna(0).sum()
        print('col matched:', c, 'normalized:', nk, 'sum:', s)

print('\nManual sums from inspection earlier:')
usd_sum = pd.to_numeric(df['Monto en Dólares de la Factura'], errors='coerce').fillna(0).sum() if 'Monto en Dólares de la Factura' in df.columns else 0.0

# Sum suffixed equivalent columns first, with fallback to the generic column
equiv_sum = 0.0
equiv_candidates = [
    'Monto equivalente en USD de los VES Cobrados (BCV)',
    'Monto equivalente en USD de los VES Cobrados (Monitor)',
    'Monto equivalente en USD de los VES Cobrados (Casa de Bolsa)'
]
found = False
for c in equiv_candidates:
    if c in df.columns:
        equiv_sum += pd.to_numeric(df[c], errors='coerce').fillna(0).sum()
        found = True

if not found and 'Monto equivalente en USD de los VES Cobrados' in df.columns:
    equiv_sum = pd.to_numeric(df['Monto equivalente en USD de los VES Cobrados'], errors='coerce').fillna(0).sum()

print('Monto en Dólares sum->', usd_sum)
print('Monto equivalente (combined) sum->', equiv_sum)
print('Combined manual->', usd_sum + equiv_sum)
