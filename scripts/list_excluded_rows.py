import os
import sys
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
if 'DJANGO_SETTINGS_MODULE' not in os.environ:
    os.environ['DJANGO_SETTINGS_MODULE'] = 'dashboard_django.settings'


def list_excluded(path):
    print(f"\nChecking excluded rows in: {path}")
    df = pd.read_excel(path)
    # detect identifier columns
    id_cols = [c for c in df.columns if str(c).strip().lower() in ('cliente','socio','gerente')]
    if not id_cols:
        for candidate in ('cliente','socio','gerente'):
            for c in df.columns:
                if candidate in str(c).lower():
                    id_cols.append(c)
    if not id_cols:
        print('No identifier columns found; nothing excluded by identifier mask')
        return
    mask = df[id_cols].notna().any(axis=1)
    excluded = df.loc[~mask].copy()
    if excluded.empty:
        print('No excluded rows')
        return
    # find invoice and equiv columns heuristically
    invoice_cols = [c for c in df.columns if 'monto' in str(c).lower() and ('dolar' in str(c).lower() or 'usd' in str(c).lower())]
    equiv_cols = [c for c in df.columns if 'equiva' in str(c).lower() or ('ves' in str(c).lower() and 'usd' in str(c).lower())]
    print(f"Found invoice cols: {invoice_cols}")
    print(f"Found equiv cols: {equiv_cols}")
    # show excluded rows that have non-zero values in these cols
    def nonzero_row(r):
        for c in invoice_cols + equiv_cols:
            try:
                if float(pd.to_numeric(r[c], errors='coerce') or 0) != 0:
                    return True
            except Exception:
                pass
        return False
    excluded_nonzero = excluded[excluded.apply(nonzero_row, axis=1)]
    print(f"Excluded rows count: {len(excluded)}; with nonzero amounts: {len(excluded_nonzero)}")
    if not excluded_nonzero.empty:
        print(excluded_nonzero[[*id_cols, *invoice_cols, *equiv_cols]].to_string(index=False))

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print('Usage: list_excluded_rows.py <file1> [file2] ...')
        sys.exit(1)
    for p in sys.argv[1:]:
        list_excluded(p)
