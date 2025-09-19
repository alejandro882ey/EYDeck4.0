import sys
import os
import pandas as pd

# Ensure project root is on sys.path so we can import Django app modules
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# If DJANGO_SETTINGS_MODULE isn't set in the environment, set a sensible default
if 'DJANGO_SETTINGS_MODULE' not in os.environ:
    os.environ['DJANGO_SETTINGS_MODULE'] = 'dashboard_django.settings'

from core_dashboard.modules.cobranzas.services import CobranzasService

def inspect_file(path):
    print(f"Inspecting: {path}")
    df = pd.read_excel(path)
    print("Columns:")
    for i,c in enumerate(df.columns.tolist()):
        print(f"  {i}: {c}")
    print(f"Rows: {len(df)}")
    # Identifier mask
    id_cols = [c for c in df.columns if str(c).strip().lower() in ('cliente','socio','gerente')]
    print(f"Identifier columns detected: {id_cols}")
    if not id_cols:
        # try fuzzy
        for candidate in ('cliente','socio','gerente'):
            for c in df.columns:
                if candidate in str(c).lower():
                    id_cols.append(c)
    mask = df[id_cols].notna().any(axis=1) if id_cols else pd.Series([True]*len(df))
    print(f"Rows kept by identifier mask: {mask.sum()} / {len(df)}")

    svc = CobranzasService()
    pref = svc._find_preferred_equiv_col(df)
    print(f"Preferred equivalent column (service): {pref}")

    # Find invoice USD-like columns and equiv columns
    invoice_tokens = ['monto', 'dolares', 'dólares', 'dólar']
    equiv_tokens = ['equivalente', 'equivalen', 'ves', 'usd', 'bolívares', 'bolivares']
    invoice_cols = [c for c in df.columns if all(tok in str(c).lower() for tok in ['monto']) and ('dolar' in str(c).lower() or 'dólar' in str(c).lower())]
    equiv_cols = [c for c in df.columns if 'equiva' in str(c).lower() or ('equivalente' in str(c).lower())]
    # fallback heuristics
    if not invoice_cols:
        for c in df.columns:
            lc = str(c).lower()
            if 'monto' in lc and ('dolar' in lc or 'usd' in lc):
                invoice_cols.append(c)
    if not equiv_cols:
        for c in df.columns:
            if 'equiva' in str(c).lower() or ('equivalente' in str(c).lower()) or ('ves' in str(c).lower() and 'usd' in str(c).lower()):
                equiv_cols.append(c)

    print(f"Invoice-like columns: {invoice_cols}")
    print(f"Equivalent-like columns: {equiv_cols}")

    def safe_sum(s):
        try:
            return pd.to_numeric(s, errors='coerce').fillna(0).sum()
        except Exception:
            return None

    print("Sums on full file:")
    for c in invoice_cols:
        print(f"  {c}: {safe_sum(df[c])}")
    for c in equiv_cols:
        print(f"  {c}: {safe_sum(df[c])}")
    if pref:
        print(f"Sum of preferred equivalent column: {safe_sum(df[pref])}")

    print("Sums on masked rows (identifier present):")
    for c in invoice_cols:
        print(f"  {c}: {safe_sum(df.loc[mask, c])}")
    for c in equiv_cols:
        print(f"  {c}: {safe_sum(df.loc[mask, c])}")
    if pref:
        print(f"Sum of preferred equivalent column (masked): {safe_sum(df.loc[mask, pref])}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: inspect_cobranzas_file.py <path-to-file>')
        sys.exit(1)
    inspect_file(sys.argv[1])
