import os,sys
sys.path.append(r'c:\Users\CK624GF\OneDrive - EY\Documents\2025\dashboard_django')
os.environ['DJANGO_SETTINGS_MODULE']='dashboard_django.settings'
import pandas as pd
p=os.path.join('media','cobranzas','Cobranzas_2025-07-18.xlsx')
print('loading',p)
df=pd.read_excel(p)
print('columns:', list(df.columns))
print('rows:', len(df))
print('head:\n', df.head().to_string())
# show null counts for Cliente/Socio/Gerente
for c in ['Cliente','Socio','Gerente']:
    print(c, 'exists?', c in df.columns, 'nulls:', df[c].isnull().sum() if c in df.columns else 'no col')
# show candidate money columns sums
for col in df.columns:
    lc=col.lower()
    if any(tok in lc for tok in ['monto','usd','dolar','ves','equivalente']):
        print('col:',col,'sum->', pd.to_numeric(df[col], errors='coerce').fillna(0).sum())
# show rows where Cliente/Socio/Gerente all empty
cols_chk=[c for c in ['Cliente','Socio','Gerente'] if c in df.columns]
if cols_chk:
    mask = ~( (df[cols_chk].notnull()) & (df[cols_chk].astype(str).apply(lambda x: x.str.strip()!='')) ).any(axis=1)
    print('rows with all Cliente/Socio/Gerente empty:', mask.sum())
    print('sample of such rows:')
    print(df[mask].head().to_string())
