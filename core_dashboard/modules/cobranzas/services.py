import os
import logging
import pandas as pd
from django.conf import settings
from .utils import extract_cobranzas_sheet, format_file_size
from core_dashboard.utils import get_fiscal_month_year
# optional shared cache utilities for code-versioning
try:
    from core_dashboard.modules.shared.cache_utils import compute_files_hash, gather_module_files
except Exception:
    compute_files_hash = None
    gather_module_files = None

logger = logging.getLogger(__name__)


class CobranzasService:
    def __init__(self):
        self.media_folder = os.path.join(settings.MEDIA_ROOT, 'cobranzas')
        os.makedirs(self.media_folder, exist_ok=True)
        # Simple in-memory cache to avoid re-reading Excel files on every request.
        # _cached_df stores the concatenated processed DataFrame. _cached_mtime stores
        # the latest modification time among files that produced the cached DataFrame.
        self._cached_df = None
        self._cached_mtime = None
        # persistent cache path (pickle). Stored in media_folder for simplicity.
        self._cache_file = os.path.join(self.media_folder, 'cobranzas_combined_cache.pkl')
        # compute code hash for this module (short digest) to invalidate cache when code changes
        try:
            if gather_module_files and compute_files_hash:
                module_dir = os.path.dirname(__file__)
                files = gather_module_files(module_dir)
                self._code_hash = compute_files_hash(files)
            else:
                # fallback: build a simple hash from .py file mtimes+size under this module dir
                try:
                    import hashlib
                    module_dir = os.path.dirname(__file__)
                    acc = []
                    for root, _, files in os.walk(module_dir):
                        for f in files:
                            if f.endswith('.py'):
                                p = os.path.join(root, f)
                                try:
                                    st = os.stat(p)
                                    acc.append(f"{os.path.relpath(p,module_dir)}:{st.st_mtime}:{st.st_size}")
                                except Exception:
                                    continue
                    h = hashlib.md5('\n'.join(acc).encode('utf-8')).hexdigest() if acc else ''
                    self._code_hash = h
                except Exception:
                    self._code_hash = ''
        except Exception:
            self._code_hash = ''

    def _find_preferred_equiv_col(self, df):
        """If multiple 'equivalente' columns exist, prefer the one immediately to the right of an exchange-rate (BCV) column.

        Returns column name or None.
        """
        import unicodedata
        def norm(c):
            if c is None:
                return ''
            s = str(c).strip().lower()
            s = ''.join(ch for ch in unicodedata.normalize('NFD', s) if unicodedata.category(ch) != 'Mn')
            return s.replace(' ', '').replace('\t','')

        cols = list(df.columns)
        norm_cols = [norm(c) for c in cols]

        # tokens for exchange rate columns
        exch_tokens = ['bcv','tipadecambio','tipadecambiobcv','tipooficial','tipodecambio','tipodecambiobcv',
                       'monitor','casadebolsa','casadebolsa','casadebosa']
        equiv_tokens = ['montoequivalente','montoenusd','equivalente','equivalenteusd','montoequivalenteenusd','montoequivalenteenusddelosvescobrados']

        # find indexes of equiv columns
        equiv_idxs = [i for i, nc in enumerate(norm_cols) if any(t in nc for t in equiv_tokens)]
        if not equiv_idxs:
            return None

        # find index of exchange-rate column
        exch_idx = None
        for i, nc in enumerate(norm_cols):
            if any(t in nc for t in exch_tokens):
                exch_idx = i
                break

        # If we have exchange index, prefer equiv column immediately to its right (exch_idx+1), else first equiv
        if exch_idx is not None:
            candidate_idx = exch_idx + 1
            if candidate_idx < len(cols) and candidate_idx in equiv_idxs:
                return cols[candidate_idx]

        # fallback: return first equiv column found
        return cols[equiv_idxs[0]]

    def process_uploaded_file(self, uploaded_file, original_filename=None):
        try:
            filename = original_filename or uploaded_file.name
            df = extract_cobranzas_sheet(uploaded_file)
            if df is None or df.empty:
                return {'success': False, 'error': 'Could not extract Cobranzas sheet from uploaded file'}

            # Normalize column names (strip and lower) and remove accents for matching
            import unicodedata
            def normalize_col(c):
                if c is None:
                    return ''
                s = str(c).strip().lower()
                s = ''.join(ch for ch in unicodedata.normalize('NFD', s) if unicodedata.category(ch) != 'Mn')
                s = s.replace(' ', '').replace('\t', '')
                return s

            def find_preferred_equiv_col(df):
                """If multiple 'equivalente' columns exist, prefer the one immediately to the right of an exchange-rate (BCV) column.

                Returns column name or None.
                """
                import unicodedata
                def norm(c):
                    if c is None:
                        return ''
                    s = str(c).strip().lower()
                    s = ''.join(ch for ch in unicodedata.normalize('NFD', s) if unicodedata.category(ch) != 'Mn')
                    return s.replace(' ', '').replace('\t','')

                cols = list(df.columns)
                norm_cols = [norm(c) for c in cols]

                # tokens for exchange rate columns
                exch_tokens = ['bcv','tipadecambio','tipadecambiobcv','tipooficial','tipodecambio','tipodecambiobcv']
                equiv_tokens = ['montoequivalente','montoenusd','equivalente','equivalenteusd','montoequivalenteenusd','montoequivalenteenusddelosvescobrados']

                # find indexes of equiv columns
                equiv_idxs = [i for i, nc in enumerate(norm_cols) if any(t in nc for t in equiv_tokens)]
                if not equiv_idxs:
                    return None

                # find index of exchange-rate column
                exch_idx = None
                for i, nc in enumerate(norm_cols):
                    if any(t in nc for t in exch_tokens):
                        exch_idx = i
                        break

                # If we have exchange index, prefer equiv column immediately to its right (exch_idx+1), else first equiv
                if exch_idx is not None:
                    candidate_idx = exch_idx + 1
                    if candidate_idx < len(cols) and candidate_idx in equiv_idxs:
                        return cols[candidate_idx]

                # fallback: return first equiv column found
                return cols[equiv_idxs[0]]

            normalized_cols = {c: normalize_col(c) for c in df.columns}

            # Keep original columns but map normalized name for matching
            df_cols_map = {normalize_col(c): c for c in df.columns}

            # Expected integration columns mapping
            # Mapping of desired logical columns to normalized keys
            mapping = {
                'Cliente': ['cliente', 'client'],
                'Socio': ['socio', 'partner'],
                'Gerente': ['gerente', 'manager'],
                'Engagement': ['engagement', 'engagementid', 'idcliente', 'idclient'],
                'Fecha de Cobro': ['fechadecobro', 'fechadecobros', 'fecha'],
                'Banco Receptor de los Fondos': ['bancoreceptordelosfondos', 'banco', 'bancoreceptor'],
                'Monto en Dólares de la Factura': ['montodendolaresdelafactura', 'montodendolares', 'montoendolares', 'montousd', 'montoendolaresdelafactura'],
                'Monto en Bolívares de la Factura': ['montoenbolivaresdelafactura', 'montoenbolivares', 'montobs'],
                'Monto equivalente en USD de los VES Cobrados': ['montoequivalenteenusddelosvescobrados', 'montoequivalenteusd', 'montoenusd']
            }

            # Create a normalized dataframe with the needed columns if present, keeping original column names
            normalized = pd.DataFrame()
            for target, variants in mapping.items():
                found_col = None
                for v in variants:
                    if v in df_cols_map:
                        found_col = df_cols_map[v]
                        break
                if found_col:
                    normalized[target] = df[found_col]
                else:
                    # try fuzzy contains
                    candidate = None
                    for k, orig in df_cols_map.items():
                        for v in variants:
                            if v in k:
                                candidate = orig
                                break
                        if candidate:
                            break
                    if candidate:
                        normalized[target] = df[candidate]
                    else:
                        normalized[target] = None

            # Save the normalized dataframe to media folder with dated or standard name
            if original_filename and original_filename.startswith('Cobranzas_'):
                output_filename = original_filename
            else:
                output_filename = 'Cobranzas_Latest.xlsx'

            # Filter out footer/non-table rows: require that at least one of Cliente/Socio/Gerente is present
            cols_check = [c for c in ['Cliente', 'Socio', 'Gerente'] if c in normalized.columns]
            if cols_check:
                # keep rows where at least one of Cliente/Socio/Gerente is present (footer rows have them empty)
                mask = None
                for col in cols_check:
                    s = pd.notnull(normalized[col]) & (normalized[col].astype(str).str.strip() != '')
                    mask = s if mask is None else (mask | s)
                if mask is not None:
                    normalized = normalized[mask].copy()

            # Create distinct suffixed equivalent columns and map detected equivalence columns into them.
            # Define canonical suffixed column names to avoid duplicates and indicate source.
            bcv_rate_col = 'Tipo de Cambio del día del pago recibido en Cuenta Bancaria BCV'
            bcv_equiv_col = 'Monto equivalente en USD de los VES Cobrados (BCV)'
            monitor_rate_col = 'Tipo de Cambio del día del pago recibido en Cuenta Bancaria Monitor'
            monitor_equiv_col = 'Monto equivalente en USD de los VES Cobrados (Monitor)'
            casa_rate_col = 'Tipo de Cambio del día del pago recibido en Cuenta Bancaria Casa de Bolsa'
            casa_equiv_col = 'Monto equivalente en USD de los VES Cobrados (Casa de Bolsa)'

            desired_cols_in_order = [
                bcv_rate_col, bcv_equiv_col,
                monitor_rate_col, monitor_equiv_col,
                casa_rate_col, casa_equiv_col
            ]

            # Ensure columns exist (create None column if missing)
            for dc in desired_cols_in_order:
                if dc not in normalized.columns:
                    normalized[dc] = None

            # Map detected equivalence columns from the original df into the suffixed columns when possible.
            # Strategy: inspect original df column order, find exchange-rate columns (bcv/monitor/casadebolsa) and
            # if the next column looks like an 'equivalente' column, copy its values into the corresponding suffixed column.
            try:
                orig_cols = list(df.columns)
                norm_orig = [normalize_col(c) for c in orig_cols]
                exch_tokens_local = ['bcv', 'monitor', 'casadebolsa', 'casadebolsa', 'tipadecambio', 'tipodecambio']
                equiv_tokens_local = ['montoequivalente', 'montoenusd', 'equivalente', 'equivalenteusd', 'montoequivalenteenusd']

                for i, nc in enumerate(norm_orig):
                    # detect BCV
                    if any(t in nc for t in ['bcv', 'tipadecambiobcv']):
                        # check next column for equivalence
                        j = i + 1
                        if j < len(orig_cols) and any(t in norm_orig[j] for t in equiv_tokens_local):
                            normalized[bcv_equiv_col] = df[orig_cols[j]]
                    # detect Monitor
                    if any(t in nc for t in ['monitor']):
                        j = i + 1
                        if j < len(orig_cols) and any(t in norm_orig[j] for t in equiv_tokens_local):
                            normalized[monitor_equiv_col] = df[orig_cols[j]]
                    # detect Casa de Bolsa
                    if any(t in nc for t in ['casadebolsa', 'casa de bolsa', 'casadebosa']):
                        j = i + 1
                        if j < len(orig_cols) and any(t in norm_orig[j] for t in equiv_tokens_local):
                            normalized[casa_equiv_col] = df[orig_cols[j]]

                # If any suffixed equivalence column is still empty, try to fill it from a generic equivalence column detected in normalized
                generic_equiv_name = None
                for cand in ['Monto equivalente en USD de los VES Cobrados', 'Monto equivalente en USD de los VES Cobrados ']:
                    if cand in normalized.columns:
                        generic_equiv_name = cand
                        break
                if generic_equiv_name:
                    for target in [bcv_equiv_col, monitor_equiv_col, casa_equiv_col]:
                        if normalized[target].isnull().all():
                            normalized[target] = normalized[generic_equiv_name]
            except Exception:
                # best-effort mapping; ignore errors and leave suffixed columns as created
                pass

            # Reorder columns: desired first (in order), then the rest in their existing order (excluding duplicates)
            other_cols = [c for c in normalized.columns if c not in desired_cols_in_order]
            normalized = normalized[desired_cols_in_order + other_cols]

            output_path = os.path.join(self.media_folder, output_filename)
            try:
                normalized.to_excel(output_path, index=False, sheet_name='Cobranzas')
            except Exception:
                # fallback without sheet_name for older engines
                normalized.to_excel(output_path, index=False)

            # Compute totals for integration: sum of USD columns (coerce and sum)
            # Robust numeric parsing for currency strings
            def parse_numeric_value(v):
                if v is None:
                    return 0.0
                if isinstance(v, (int, float)):
                    return float(v)
                s = str(v).strip()
                # Remove currency symbols and whitespace
                s = s.replace('$', '').replace('US$', '').replace('Bs.', '').replace('\xa0', '').strip()
                # Common formats: '1,234.56' or '1.234,56' (European)
                # Heuristics: if there are both '.' and ',' and last separator is ',', treat ',' as decimal
                try:
                    if s.count(',') > 0 and s.count('.') > 0:
                        if s.rfind(',') > s.rfind('.'):
                            s = s.replace('.', '').replace(',', '.')
                        else:
                            s = s.replace(',', '')
                    else:
                        # If only commas and commas look like thousand separators (len>3), remove them
                        if s.count(',') > 0 and all(part.isdigit() for part in s.split(',')) and len(s.split(',')[-1]) != 3:
                            s = s.replace(',', '.')
                        else:
                            s = s.replace(',', '')
                    return float(s)
                except Exception:
                    # Fallback: extract digits, dot and minus
                    import re
                    m = re.findall(r'[-\d.,]+', s)
                    if not m:
                        return 0.0
                    t = m[0]
                    t = t.replace(',', '')
                    try:
                        return float(t)
                    except Exception:
                        return 0.0

            def sum_column_variants(df, keys):
                total = 0.0
                for k in df.columns:
                    nk = normalize_col(k)
                    for key in keys:
                        if key in nk:
                            # sum parsed numeric values per cell to avoid pandas coercion issues
                            col_total = 0.0
                            for cell in df[k].tolist():
                                col_total += parse_numeric_value(cell)
                            total += col_total
                            break
                return total

            # Prefer calculating totals by reading back the saved processed file (ensures consistent parsing)
            try:
                collected_total, billed_total = self.get_totals_from_file(output_path)
            except Exception:
                collected_total = sum_column_variants(normalized, ['montodendolares', 'montoendolares', 'montousd', 'montoequivalenteusd'])
                billed_total = sum_column_variants(normalized, ['totalfactura', 'montonetopagado', 'montofactura', 'montoenbolivares', 'montoenbolivaresdelafactura'])

            result = {
                'success': True,
                'message': 'Cobranzas processed successfully',
                'output_file': output_filename,
                'output_path': output_path,
                'rows_processed': len(normalized),
                'collected_total': collected_total,
                'billed_total': billed_total,
                'file_info': {
                    'original_name': filename,
                    'size': format_file_size(getattr(uploaded_file, 'size', 0))
                }
            }

            # Invalidate persistent and in-memory cache because a new processed file was saved
            try:
                self._cached_df = None
                self._cached_mtime = None
                if os.path.exists(self._cache_file):
                    try:
                        os.remove(self._cache_file)
                    except Exception:
                        # best-effort removal; ignore errors
                        pass
            except Exception:
                # silently ignore cache-clearing errors
                pass

            return result

        except Exception as e:
            logger.error(f"Error processing Cobranzas file: {e}")
            return {'success': False, 'error': str(e)}

    def get_latest_file_info(self):
        # Find the most recent xlsx/xls file in the media folder
        if not os.path.exists(self.media_folder):
            return None
        files = [f for f in os.listdir(self.media_folder) if f.lower().endswith(('.xlsx', '.xls'))]
        if not files:
            return None
        files_with_mtime = [(f, os.path.getmtime(os.path.join(self.media_folder, f))) for f in files]
        latest_file = sorted(files_with_mtime, key=lambda x: x[1])[-1][0]
        output_path = os.path.join(self.media_folder, latest_file)
        stat = os.stat(output_path)
        return {
            'filename': latest_file,
            'path': output_path,
            'size': stat.st_size,
            'modified': stat.st_mtime
        }

    def get_totals_from_file(self, file_path):
        """Return (collected_total, billed_total) computed from the given processed Excel file."""
        try:
            try:
                df = pd.read_excel(file_path, sheet_name='Cobranzas')
            except Exception:
                df = pd.read_excel(file_path)

            # normalize column matching
            import unicodedata
            def normalize_col(c):
                if c is None:
                    return ''
                s = str(c).strip().lower()
                s = ''.join(ch for ch in unicodedata.normalize('NFD', s) if unicodedata.category(ch) != 'Mn')
                s = s.replace(' ', '').replace('\t', '')
                return s

            total_collected = 0.0
            total_billed = 0.0

            # Filter out footer rows if Cliente/Socio/Gerente columns exist
            cols_to_check = [col for col in df.columns if normalize_col(col) in ('cliente', 'socio', 'gerente')]
            if cols_to_check:
                mask = None
                for cc in cols_to_check:
                    s = pd.notnull(df[cc]) & (df[cc].astype(str).str.strip() != '')
                    mask = s if mask is None else (mask | s)
                if mask is not None:
                    df = df[mask]

            # Use preferred equivalent column when multiple exist
            preferred_equiv = self._find_preferred_equiv_col(df)

            # Attempt to compute VES->USD conversion using BCV invoice rate when present
            # Prefer the exact header 'Monto en Bolívares de la Factura' (normalized) if present
            col_bcv = None
            col_ves = None
            target_ves_norm = normalize_col('Monto en Bolívares de la Factura')
            for c in df.columns:
                nk = normalize_col(c)
                if any(x in nk for x in ('tipadecambio', 'tipadecambiobcv', 'bcv', 'tipooficial')) and col_bcv is None:
                    col_bcv = c
                # prefer exact normalized header match first
                if col_ves is None and nk == target_ves_norm:
                    col_ves = c
            # fallback: token-based detection if exact header wasn't found
            if col_ves is None:
                for c in df.columns:
                    nk = normalize_col(c)
                    if any(x in nk for x in ('montoenbolivares', 'montobs', 'montoenbolivaresdelafactura')):
                        col_ves = c
                        break

            for c in df.columns:
                nk = normalize_col(c)
                # Sum invoice USD columns
                if ('montodendolares' in nk) or ('montoendolares' in nk) or ('montousd' in nk):
                    total_collected += pd.to_numeric(df[c], errors='coerce').fillna(0).sum()
            # add VES->USD via BCV if available
            if col_ves and col_bcv:
                try:
                    ves_vals = pd.to_numeric(df[col_ves], errors='coerce').fillna(0)
                    bcv_vals = pd.to_numeric(df[col_bcv], errors='coerce').fillna(0)
                    # per-row safe division (avoid divide by zero)
                    conv = (ves_vals / bcv_vals.replace({0: pd.NA})).fillna(0)
                    total_collected += conv.sum()
                except Exception:
                    pass
            # fallback: add preferred equivalence column if BCV conversion not applied
            if preferred_equiv:
                try:
                    total_collected += pd.to_numeric(df[preferred_equiv], errors='coerce').fillna(0).sum()
                except Exception:
                    pass
                # Billing detection remains but will be ignored at dashboard level (we keep it for compatibility)
                if any(k in nk for k in ['totalfactura', 'montonetopagado', 'montofactura', 'montoenbolivares']):
                    total_billed += pd.to_numeric(df[c], errors='coerce').fillna(0).sum()

            return float(total_collected), float(total_billed)
        except Exception as e:
            logger.error(f"Error reading totals from file {file_path}: {e}")
            return 0.0, 0.0

    def get_breakdown_from_file(self, file_path):
        """Return (usd_total, ves_equiv_total, ves_bolivares_total) from the processed Excel file."""
        try:
            try:
                df = pd.read_excel(file_path, sheet_name='Cobranzas')
            except Exception:
                df = pd.read_excel(file_path)

            import unicodedata
            def normalize_col(c):
                if c is None:
                    return ''
                s = str(c).strip().lower()
                s = ''.join(ch for ch in unicodedata.normalize('NFD', s) if unicodedata.category(ch) != 'Mn')
                s = s.replace(' ', '').replace('\t', '')
                return s

            usd_total = 0.0
            ves_equiv_total = 0.0
            ves_bolivares_total = 0.0
            # Filter out footer rows if Cliente/Socio/Gerente columns exist
            cols_to_check = [col for col in df.columns if normalize_col(col) in ('cliente', 'socio', 'gerente')]
            if cols_to_check:
                mask = None
                for cc in cols_to_check:
                    s = pd.notnull(df[cc]) & (df[cc].astype(str).str.strip() != '')
                    mask = s if mask is None else (mask | s)
                if mask is not None:
                    df = df[mask]

            preferred_equiv = self._find_preferred_equiv_col(df)
            # identify BCV rate and VES amount columns; prefer the exact header 'Monto en Bolívares de la Factura'
            col_bcv = None
            col_ves = None
            target_ves_norm = normalize_col('Monto en Bolívares de la Factura')
            for c in df.columns:
                nk = normalize_col(c)
                if any(x in nk for x in ('tipadecambio', 'tipadecambiobcv', 'bcv', 'tipooficial')) and col_bcv is None:
                    col_bcv = c
                if col_ves is None and nk == target_ves_norm:
                    col_ves = c
            if col_ves is None:
                for c in df.columns:
                    nk = normalize_col(c)
                    if any(x in nk for x in ('montoenbolivares', 'montobs', 'montoenbolivaresdelafactura')):
                        col_ves = c
                        break

            for c in df.columns:
                nk = normalize_col(c)
                if ('montodendolares' in nk) or ('montoendolares' in nk) or ('montousd' in nk):
                    usd_total += pd.to_numeric(df[c], errors='coerce').fillna(0).sum()
                # broaden matching to include generic 'bolivares'/'bolivar' tokens
                if any(t in nk for t in ('montoenbolivares', 'montobs', 'montoenbolivaresdelafactura', 'bolivares', 'bolivar')):
                    ves_bolivares_total += pd.to_numeric(df[c], errors='coerce').fillna(0).sum()

            # If we detected a specific col_ves earlier (preferred canonical header), prefer its sum
            if col_ves:
                try:
                    ves_bolivares_total = float(pd.to_numeric(df[col_ves], errors='coerce').fillna(0).sum())
                except Exception:
                    pass

            # Compute ves_equiv_total using BCV invoice rate when possible (row-wise conversion)
            if col_ves and col_bcv:
                try:
                    ves_vals = pd.to_numeric(df[col_ves], errors='coerce').fillna(0)
                    bcv_vals = pd.to_numeric(df[col_bcv], errors='coerce').fillna(0)
                    conv = (ves_vals / bcv_vals.replace({0: pd.NA})).fillna(0)
                    ves_equiv_total += conv.sum()
                except Exception:
                    pass
            # fallback: preferred equivalence column
            if preferred_equiv:
                try:
                    ves_equiv_total += pd.to_numeric(df[preferred_equiv], errors='coerce').fillna(0).sum()
                except Exception:
                    pass

            return float(usd_total), float(ves_equiv_total), float(ves_bolivares_total)
        except Exception as e:
            logger.error(f"Error reading breakdown from file {file_path}: {e}")
            return 0.0, 0.0, 0.0

    def get_breakdown_from_latest(self):
        info = self.get_latest_file_info()
        if not info:
            return 0.0, 0.0, 0.0
        return self.get_breakdown_from_file(info['path'])

    def get_all_processed_df(self):
        """Return a combined normalized DataFrame for all processed files (empty DF if none)."""
        # reuse logic from get_daily_collections_and_rates but expose as helper
        files = []
        if os.path.exists(self.media_folder):
            files = [os.path.join(self.media_folder, f) for f in os.listdir(self.media_folder) if f.lower().endswith(('.xlsx', '.xls'))]
            files = sorted(files, key=lambda p: os.path.getmtime(p))

        # compute max mtime to determine cache validity
        max_mtime = None
        for p in files:
            try:
                m = os.path.getmtime(p)
                if max_mtime is None or m > max_mtime:
                    max_mtime = m
            except Exception:
                continue

        # Return cached dataframe when nothing changed
        try:
            # prefer in-memory cache
            if self._cached_df is not None and self._cached_mtime == max_mtime:
                logger.debug('Using in-memory Cobranzas cache')
                return self._cached_df.copy()
            # try persistent cache if available. Load it when in-memory cache isn't present
            # or when the mtimes don't match. Also load when there are no processed files
            # (max_mtime is None) but a persistent cache exists.
            if os.path.exists(self._cache_file) and (self._cached_mtime is None or self._cached_mtime != max_mtime):
                try:
                    import pickle
                    with open(self._cache_file, 'rb') as fh:
                        cached = pickle.load(fh)
                    # cached is expected to be a tuple (max_mtime, code_hash, df) or legacy (max_mtime, df)
                    if isinstance(cached, tuple):
                        if len(cached) == 3:
                            cached_mtime, cached_code_hash, cached_df = cached
                        elif len(cached) == 2:
                            cached_mtime, cached_df = cached
                            cached_code_hash = ''
                        else:
                            cached_mtime = None
                            cached_df = None
                            cached_code_hash = ''

                        # validate both mtime and code-hash (if available). If code_hash is empty we only rely on mtime
                        # If code hash is present and mismatches current code, invalidate persistent cache
                        if cached_code_hash and self._code_hash and cached_code_hash != self._code_hash:
                            try:
                                os.remove(self._cache_file)
                                logger.info('Removed stale persistent cobranzas cache due to code changes')
                            except Exception:
                                logger.warning('Failed to remove stale cobranzas cache file')
                        elif cached_mtime == max_mtime and (not self._code_hash or cached_code_hash == self._code_hash):
                            # populate in-memory cache and return copy
                            self._cached_df = cached_df
                            self._cached_mtime = cached_mtime
                            logger.info(f'Loaded persistent cobranzas cache from {self._cache_file}')
                            return self._cached_df.copy()
                except Exception as exc:
                    logger.warning(f'Failed to load persistent cobranzas cache: {exc}')
        except Exception:
            # If any cache check fails, fall back to rebuild
            pass

        combined = []
        for p in files:
            try:
                try:
                    dfx = pd.read_excel(p, sheet_name='Cobranzas')
                except Exception:
                    dfx = pd.read_excel(p)
            except Exception:
                continue

            import unicodedata
            def norm(c):
                if c is None:
                    return ''
                s = str(c).strip().lower()
                s = ''.join(ch for ch in unicodedata.normalize('NFD', s) if unicodedata.category(ch) != 'Mn')
                return s.replace(' ', '').replace('\t', '')

            cols_map = {norm(c): c for c in dfx.columns}
            # detect date column
            col_fecha = cols_map.get('fechadecobro') or cols_map.get('fecha') or cols_map.get('fechadecobros')
            if col_fecha is None:
                for k, orig in cols_map.items():
                    if 'fecha' in k or 'cobro' in k:
                        col_fecha = orig
                        break
            if col_fecha is None:
                continue

            def find_col(tokens):
                for k, orig in cols_map.items():
                    for t in tokens:
                        if t in k:
                            return orig
                return None

            col_monto_usd = find_col(['montodendolares','montoendolares','montousd','dolares','dolar'])
            col_monto_ves = find_col(['montoenbolivares','montobs','bolivares','bolivar'])
            # find potential equivalent columns; prefer the one adjacent to exchange-rate
            col_monto_equiv_usd = find_col(['montoequivalente','montoenusd','equivalente','equivalenteusd','equivalenteenusd'])
            # If multiple columns exist, prefer the one next to the exchange-rate column
            try:
                preferred = self._find_preferred_equiv_col(dfx)
                if preferred:
                    col_monto_equiv_usd = preferred
            except Exception:
                pass
            col_tipo_bcv = find_col(['bcv','tipadecambio','tipadecambiobcv','tipooficial','bancoreceptor'])
            col_tipo_monitor = find_col(['monitor','binance','paralelo','tipadecambiomonitor','tipadecambio'])

            dfx = dfx.copy()
            # Filter out footer/non-table rows: require at least one of Cliente/Socio/Gerente
            cols_check = [orig for k, orig in cols_map.items() if k in ('cliente', 'socio', 'gerente')]
            if cols_check:
                # keep rows where at least one identifier column is present
                mask = None
                for col in cols_check:
                    s = pd.notnull(dfx[col]) & (dfx[col].astype(str).str.strip() != '')
                    mask = s if mask is None else (mask | s)
                if mask is not None:
                    dfx = dfx[mask].copy()

            dfx[col_fecha] = pd.to_datetime(dfx[col_fecha], errors='coerce')
            dfx = dfx.dropna(subset=[col_fecha])
            dfx['fecha_day'] = dfx[col_fecha].dt.strftime('%Y-%m-%d')

            def tonum(col):
                if col is None:
                    return pd.Series([0]*len(dfx))
                return pd.to_numeric(dfx[col], errors='coerce').fillna(0)

            monto_usd = tonum(col_monto_usd)
            monto_ves = tonum(col_monto_ves)
            monto_equiv_usd = tonum(col_monto_equiv_usd)
            tipo_bcv = tonum(col_tipo_bcv)
            tipo_monitor = tonum(col_tipo_monitor)

            usd_equiv_from_ves = []
            usd_equiv_total_per_row = []
            for i in range(len(dfx)):
                m_usd = float(monto_usd.iloc[i]) if len(monto_usd)>i else 0.0
                m_ves = float(monto_ves.iloc[i]) if len(monto_ves)>i else 0.0
                m_equiv = float(monto_equiv_usd.iloc[i]) if len(monto_equiv_usd)>i else 0.0
                t_bcv = float(tipo_bcv.iloc[i]) if len(tipo_bcv)>i else 0.0
                t_monitor_val = float(tipo_monitor.iloc[i]) if len(tipo_monitor)>i else 0.0

                # Preferred conversion: use invoice-level BCV rate when available
                if t_bcv and t_bcv > 0:
                    usd_from_ves = (m_ves / t_bcv)
                # If BCV invoice rate not available, prefer explicit provided equivalent column
                elif m_equiv and m_equiv > 0:
                    usd_from_ves = m_equiv
                # If neither available, fall back to monitor/parallel rate conversion
                elif t_monitor_val and t_monitor_val > 0:
                    usd_from_ves = (m_ves / t_monitor_val)
                else:
                    usd_from_ves = 0.0

                usd_equiv_from_ves.append(usd_from_ves)
                usd_equiv_total_per_row.append(m_usd + usd_from_ves)

            dfx['_monto_usd'] = monto_usd.values if len(monto_usd)==len(dfx) else 0
            dfx['_monto_ves'] = monto_ves.values if len(monto_ves)==len(dfx) else 0
            dfx['_usd_from_ves'] = pd.Series(usd_equiv_from_ves, index=dfx.index)
            dfx['_usd_total_row'] = pd.Series(usd_equiv_total_per_row, index=dfx.index)
            dfx['_tipo_bcv'] = tipo_bcv.values if len(tipo_bcv)==len(dfx) else 0
            dfx['_tipo_monitor'] = tipo_monitor.values if len(tipo_monitor)==len(dfx) else 0

            combined.append(dfx)

        if not combined:
            df_final = pd.DataFrame()
        else:
            df_final = pd.concat(combined, ignore_index=True)

        # update cache
        try:
            self._cached_df = df_final.copy()
            self._cached_mtime = max_mtime
            # write persistent cache
            try:
                import pickle
                # atomic write: write to temp file then replace
                tmp = self._cache_file + '.tmp'
                with open(tmp, 'wb') as fh:
                    # include code hash in the cache tuple for invalidation on code updates
                    try:
                        code_hash = getattr(self, '_code_hash', '') or ''
                        pickle.dump((max_mtime, code_hash, self._cached_df), fh)
                    except Exception:
                        # fallback to legacy format if pickling with code_hash fails
                        pickle.dump((max_mtime, self._cached_df), fh)
                try:
                    os.replace(tmp, self._cache_file)
                except Exception:
                    # fallback to rename
                    os.rename(tmp, self._cache_file)
                logger.info(f'Wrote persistent cobranzas cache to {self._cache_file}')
            except Exception:
                # non-fatal if caching to disk fails
                pass
        except Exception:
            self._cached_df = None
            self._cached_mtime = None

        return df_final

    def get_cumulative_breakdown(self):
        """Return cumulative (usd_total, ves_equiv_total, ves_bolivares_total) across all processed files."""
        df = self.get_all_processed_df()
        if df.empty:
            return 0.0, 0.0, 0.0
        usd_total = float(df['_monto_usd'].sum()) if '_monto_usd' in df.columns else 0.0
        ves_equiv_total = float(df['_usd_from_ves'].sum()) if '_usd_from_ves' in df.columns else 0.0
        # Prefer explicit internal '_monto_ves' when present
        if '_monto_ves' in df.columns:
            try:
                ves_bolivares_total = float(pd.to_numeric(df['_monto_ves'], errors='coerce').fillna(0).sum())
                return usd_total, ves_equiv_total, ves_bolivares_total
            except Exception:
                pass
        # ves_bolivares_total not always present; attempt to infer from detected columns (broaden tokens)
        ves_cols = [c for c in df.columns if any(t in c.lower() for t in ('montoenbolivares', 'montobs', 'bolivares', 'bolivar'))]
        if ves_cols:
            ves_bolivares_total = float(pd.to_numeric(df[ves_cols[0]], errors='coerce').fillna(0).sum())
        else:
            ves_bolivares_total = 0.0
        return usd_total, ves_equiv_total, ves_bolivares_total

    def get_cumulative_collected_total(self):
        """Return cumulative collected total (USD invoice + USD-equivalent from VES) across all processed files."""
        df = self.get_all_processed_df()
        if df.empty:
            return 0.0
        if '_usd_total_row' in df.columns:
            return float(df['_usd_total_row'].sum())
        # fallback
        usd, ves_equiv, _ = self.get_cumulative_breakdown()
        return float((usd or 0.0) + (ves_equiv or 0.0))

    def get_cumulative_collected_up_to(self, date_str):
        """Sum collected totals from processed files with names like Cobranzas_YYYY-MM-DD.xlsx up to date_str (inclusive).

        date_str should be 'YYYY-MM-DD'. Returns float.
        """
        import re
        from datetime import datetime
        total = 0.0
        if not os.path.exists(self.media_folder):
            return 0.0
        files = [f for f in os.listdir(self.media_folder) if f.lower().endswith(('.xlsx', '.xls'))]
        pattern = re.compile(r'cobranzas[_-](\d{4}-\d{2}-\d{2})', re.IGNORECASE)
        try:
            cutoff = datetime.strptime(date_str, '%Y-%m-%d').date()
        except Exception:
            return 0.0
        for fn in files:
            m = pattern.search(fn)
            if m:
                try:
                    fd = datetime.strptime(m.group(1), '%Y-%m-%d').date()
                except Exception:
                    continue
                if fd <= cutoff:
                    p = os.path.join(self.media_folder, fn)
                    try:
                        collected, _ = self.get_totals_from_file(p)
                        total += float(collected or 0.0)
                    except Exception:
                        continue
        return float(total)

    def get_available_report_dates(self):
        """Return a list of available processed report dates (dicts with keys: date, filename, label, path, mtime).

        The method looks for files in the media folder matching patterns like
        'Cobranzas_YYYY-MM-DD.xlsx'. For files without that pattern it falls back to
        the file modification date as the report date.
        """
        import re
        import datetime
        results = []
        if not os.path.exists(self.media_folder):
            return results
        for fn in os.listdir(self.media_folder):
            if not fn.lower().endswith(('.xlsx', '.xls')):
                continue
            path = os.path.join(self.media_folder, fn)
            date_str = None
            mtime = None
            try:
                mtime = os.path.getmtime(path)
            except Exception:
                mtime = None
            m = re.search(r'cobranzas[_-](\d{4}-\d{2}-\d{2})', fn, re.IGNORECASE)
            if m:
                date_str = m.group(1)
                label = date_str
            else:
                # fallback: use mtime if available
                if mtime:
                    try:
                        date_str = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')
                        label = f"{date_str} ({fn})"
                    except Exception:
                        date_str = None
                        label = fn
                else:
                    label = fn

            if date_str:
                results.append({'date': date_str, 'filename': fn, 'label': label, 'path': path, 'mtime': mtime})

        # sort by date ascending
        try:
            results = sorted(results, key=lambda x: x['date'])
        except Exception:
            pass
        return results

    def get_processed_file_date(self, file_path):
        """Return the representative date (YYYY-MM-DD) for a processed file by reading its date column's max value.

        Returns None if no date can be inferred.
        """
        try:
            import pandas as pd
            try:
                df = pd.read_excel(file_path, sheet_name='Cobranzas')
            except Exception:
                df = pd.read_excel(file_path)
            if df is None or df.empty:
                return None
            # find likely date column
            cols = [c for c in df.columns if 'fecha' in str(c).lower() or 'cobro' in str(c).lower()]
            if not cols:
                # try any datetime-like column
                for c in df.columns:
                    try:
                        s = pd.to_datetime(df[c], errors='coerce')
                        if s.notnull().any():
                            cols = [c]
                            break
                    except Exception:
                        continue
            if not cols:
                return None
            col = cols[0]
            s = pd.to_datetime(df[col], errors='coerce')
            if s is None or s.dropna().empty:
                return None
            maxd = s.max()
            if pd.isna(maxd):
                return None
            return pd.to_datetime(maxd).strftime('%Y-%m-%d')
        except Exception:
            return None

    def get_mtd_breakdown_for_date(self, report_date):
        """Return (usd_mtd, ves_equiv_mtd, ves_bolivares_mtd) for the fiscal month that contains report_date."""
        df = self.get_all_processed_df()
        if df.empty:
            return 0.0, 0.0, 0.0
        # determine fiscal period label for the report_date
        try:
            fiscal_label = get_fiscal_month_year(pd.to_datetime(report_date))
        except Exception:
            # if invalid date, return zeros
            return 0.0, 0.0, 0.0

        # compute fiscal label per row
        def row_fiscal_label(ts):
            try:
                return get_fiscal_month_year(pd.to_datetime(ts))
            except Exception:
                return None

        df = df.copy()
        df['_fiscal_period'] = df['fecha_day'].apply(lambda x: row_fiscal_label(x))
        sel = df[df['_fiscal_period'] == fiscal_label]
        if sel.empty:
            return 0.0, 0.0, 0.0

        usd_mtd = float(sel['_monto_usd'].sum()) if '_monto_usd' in sel.columns else 0.0
        ves_equiv_mtd = float(sel['_usd_from_ves'].sum()) if '_usd_from_ves' in sel.columns else 0.0
        # Prefer internal '_monto_ves' if present; otherwise broaden token match
        if '_monto_ves' in sel.columns:
            try:
                ves_bolivares_mtd = float(pd.to_numeric(sel['_monto_ves'], errors='coerce').fillna(0).sum())
            except Exception:
                ves_bolivares_mtd = 0.0
        else:
            ves_cols = [c for c in sel.columns if any(t in c.lower() for t in ('montoenbolivares', 'montobs', 'bolivares', 'bolivar'))]
            if ves_cols:
                ves_bolivares_mtd = float(pd.to_numeric(sel[ves_cols[0]], errors='coerce').fillna(0).sum())
            else:
                ves_bolivares_mtd = 0.0
        return usd_mtd, ves_equiv_mtd, ves_bolivares_mtd

    def get_daily_collections_and_rates(self):
        """Return daily series for collections and exchange rates aggregated across all processed files.

        This aggregates every processed file in the module media folder so charts and totals include
        historic weekly reports (not only the latest file).
        """

        # Use cached combined DataFrame to avoid re-reading Excel files repeatedly
        df = self.get_all_processed_df()
        if df.empty:
            return {'dates': [], 'daily_usd': [], 'daily_ves_equiv_usd': [], 'tasa_oficial': [], 'tasa_binance': [], 'tasa_sintetica': []}

        # Ensure fecha_day exists (older cached data should have it)
        if 'fecha_day' not in df.columns:
            # Attempt to create fecha_day from existing date-like columns
            date_cols = [c for c in df.columns if 'fecha' in str(c).lower() or 'cobro' in str(c).lower()]
            if date_cols:
                df[date_cols[0]] = pd.to_datetime(df[date_cols[0]], errors='coerce')
                df = df.dropna(subset=[date_cols[0]])
                df['fecha_day'] = df[date_cols[0]].dt.strftime('%Y-%m-%d')
            else:
                return {'dates': [], 'daily_usd': [], 'daily_ves_equiv_usd': [], 'tasa_oficial': [], 'tasa_binance': [], 'tasa_sintetica': []}

        grouped = df.groupby('fecha_day')
        dates = sorted(list(grouped.groups.keys()))
        daily_usd = []
        daily_ves_equiv_usd = []
        tasa_oficial_map = {}
        tasa_binance_map = {}
        tasa_sintetica_map = {}

        for d in dates:
            g = grouped.get_group(d)
            sum_usd = float(g['_monto_usd'].sum()) if '_monto_usd' in g.columns else 0.0
            # prefer explicit provided usd-equivalent column where present, else computed
            # but since we normalized per-file, we use '_usd_from_ves'
            sum_usd_from_ves = float(g['_usd_from_ves'].sum())
            sum_ves = float(g['_monto_ves'].sum())
            sum_usd_total = float(g['_usd_total_row'].sum())

            oficiales = g['_tipo_bcv'][g['_tipo_bcv']>0]
            monitors = g['_tipo_monitor'][g['_tipo_monitor']>0]
            tasa_oficial_map[d] = float(oficiales.mean()) if len(oficiales)>0 else None
            tasa_binance_map[d] = float(monitors.mean()) if len(monitors)>0 else None

            if sum_usd_total > 0:
                tasa_sint = sum_ves / sum_usd_total
            else:
                tasa_sint = None

            tasa_sintetica_map[d] = tasa_sint

            daily_usd.append(sum_usd)
            daily_ves_equiv_usd.append(sum_usd_from_ves)

        # Now pull exchange file to fill missing dates and provide official/parallel rates when absent
        try:
            from core_dashboard.modules.exchange_rate_module import get_exchange_rate_data
            exch = get_exchange_rate_data()
            exch_map_oficial = {d: v for d, v in zip(exch['dates'], exch['tasa_oficial'])}
            exch_map_paral = {d: v for d, v in zip(exch['dates'], exch['tasa_paralelo'])}
        except Exception:
            exch_map_oficial = {}
            exch_map_paral = {}

        # Build final aligned arrays over union of dates (include exchange-only dates)
        all_dates = sorted(set(dates) | set(exch_map_oficial.keys()))
        final_dates = []
        final_daily_usd = []
        final_daily_ves_equiv = []
        final_oficial = []
        final_binance = []
        final_sintetica = []

        last_of = None
        last_pa = None
        last_sint = None

        for d in all_dates:
            final_dates.append(d)
            if d in dates:
                idx = dates.index(d)
                final_daily_usd.append(daily_usd[idx])
                final_daily_ves_equiv.append(daily_ves_equiv_usd[idx])
                of = tasa_oficial_map.get(d)
                pa = tasa_binance_map.get(d)
                sint = tasa_sintetica_map.get(d)
            else:
                final_daily_usd.append(0.0)
                final_daily_ves_equiv.append(0.0)
                of = None; pa = None; sint = None

            if of is None:
                of = exch_map_oficial.get(d)
            if pa is None:
                pa = exch_map_paral.get(d)

            try:
                if of is None or not (of and of>0):
                    of = last_of
            except Exception:
                of = last_of
            try:
                if pa is None or not (pa and pa>0):
                    pa = last_pa
            except Exception:
                pa = last_pa

            if sint is None:
                if of and pa:
                    sint = (of + pa) / 2.0
                elif of:
                    sint = of
                elif pa:
                    sint = pa
                else:
                    sint = last_sint

            final_oficial.append(of if of is not None else 0.0)
            final_binance.append(pa if pa is not None else 0.0)
            final_sintetica.append(sint if sint is not None else 0.0)

            if of and of>0:
                last_of = of
            if pa and pa>0:
                last_pa = pa
            if sint and sint>0:
                last_sint = sint

        return {
            'dates': final_dates,
            'daily_usd': final_daily_usd,
            'daily_ves_equiv_usd': final_daily_ves_equiv,
            'tasa_oficial': final_oficial,
            'tasa_binance': final_binance,
            'tasa_sintetica': final_sintetica
        }

    def clear_processed_files(self):
        cleared = []
        if os.path.exists(self.media_folder):
            for fn in os.listdir(self.media_folder):
                p = os.path.join(self.media_folder, fn)
                if os.path.isfile(p):
                    os.remove(p)
                    cleared.append(fn)
        # Clear cache as well
        try:
            self._cached_df = None
            self._cached_mtime = None
            if os.path.exists(self._cache_file):
                os.remove(self._cache_file)
        except Exception:
            pass
        return {'success': True, 'message': f'Cleared {len(cleared)} files', 'cleared_files': cleared}

    def get_collected_total_from_latest(self):
        info = self.get_latest_file_info()
        if not info:
            return 0.0
        collected, _ = self.get_totals_from_file(info['path'])
        try:
            return float(collected or 0.0)
        except Exception:
            return 0.0
