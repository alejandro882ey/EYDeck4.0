import os
import re
import pandas as pd
import datetime
import logging
from django.conf import settings
from .utils import extract_facturacion_sheet

logger = logging.getLogger(__name__)


class FacturacionService:
    def __init__(self):
        self.media_folder = os.path.join(settings.MEDIA_ROOT, 'facturacion')
        os.makedirs(self.media_folder, exist_ok=True)
        self._cache_file = os.path.join(self.media_folder, 'facturacion_combined_cache.pkl')
        self._cached_df = None
        self._cached_mtime = None
        # optional code-hash detection to invalidate caches when module code changes
        try:
            from core_dashboard.modules.shared.cache_utils import compute_files_hash, gather_module_files
            module_dir = os.path.dirname(__file__)
            files = gather_module_files(module_dir)
            self._code_hash = compute_files_hash(files)
        except Exception:
            self._code_hash = ''

    def process_uploaded_file(self, uploaded_file, original_filename=None):
        """Process uploaded Facturacion file and save a normalized version to media/facturacion.
        Returns dict with success, message, output_path, rows_processed, billed_total
        """
        try:
            filename = original_filename or getattr(uploaded_file, 'name', 'Facturacion_upload.xlsx')
            df = extract_facturacion_sheet(uploaded_file)
            if df is None:
                return {'success': False, 'error': 'Could not extract Facturacion sheet from uploaded file'}

            # Keep all columns, but normalize names
            normalized = df.copy()
            normalized.columns = [str(c).strip() for c in normalized.columns]

            # Compute billed total (sum of 'Net Amount Local' if present)
            billed_total = None
            if 'Net Amount Local' in normalized.columns:
                try:
                    billed_total = normalized['Net Amount Local'].replace({',': ''}, regex=True).astype(float).sum()
                except Exception:
                    # Fallback: try coercion
                    billed_total = pd.to_numeric(normalized['Net Amount Local'], errors='coerce').fillna(0).sum()

            # Write processed file
            if original_filename and original_filename.startswith('Facturacion_'):
                output_filename = 'Facturacion_Latest.xlsx'
            else:
                output_filename = 'Facturacion_Latest.xlsx'

            output_path = os.path.join(self.media_folder, output_filename)
            try:
                normalized.to_excel(output_path, index=False, sheet_name='Facturacion')
            except Exception as e:
                logger.exception('Failed to write processed Facturacion file')

            # Invalidate caches (best-effort)
            self._cached_df = None
            try:
                if os.path.exists(self._cache_file):
                    os.remove(self._cache_file)
            except Exception:
                pass

            return {
                'success': True,
                'message': 'Facturacion processed successfully',
                'output_path': output_path,
                'rows_processed': len(normalized),
                'billed_total': billed_total,
                'file_info': {
                    'original_name': filename,
                    'output_name': output_filename,
                    'size': os.path.getsize(output_path) if os.path.exists(output_path) else None
                }
            }

        except Exception as e:
            logger.exception('Error processing Facturacion file')
            return {'success': False, 'error': str(e)}

    def get_latest_file_info(self):
        files = [os.path.join(self.media_folder, f) for f in os.listdir(self.media_folder) if f.lower().endswith(('.xlsx', '.xls'))]
        if not files:
            return None
        latest = max(files, key=os.path.getmtime)
        return {
            'path': latest,
            'filename': os.path.basename(latest),
            'last_modified': os.path.getmtime(latest)
        }

    def get_cumulative_billed_up_to(self, up_to_date):
        """Find the most appropriate processed Facturacion file for `up_to_date`.
        Strategy:
        - If there are processed files named like 'Facturacion_YYYY-MM-DD.xlsx', pick the file with the largest date <= up_to_date and return its billed total (filtering by Accounting Cycle Date <= up_to_date as a safety).
        - If no dated files are found or none <= up_to_date, fall back to the latest processed file and compute totals from it using up_to_date filtering.
        """
        try:
            files = [f for f in os.listdir(self.media_folder) if f.lower().endswith(('.xlsx', '.xls'))]
            pattern = re.compile(r'facturacion[_-](\d{4}-\d{2}-\d{2})', re.IGNORECASE)
            candidates = []
            for fname in files:
                m = pattern.search(fname)
                if m:
                    try:
                        file_date = datetime.datetime.strptime(m.group(1), '%Y-%m-%d').date()
                        candidates.append((file_date, os.path.join(self.media_folder, fname)))
                    except Exception:
                        continue

            # Choose best candidate <= up_to_date
            chosen_path = None
            if candidates:
                candidates.sort(key=lambda x: x[0])
                for fd, p in reversed(candidates):
                    if fd <= up_to_date:
                        chosen_path = p
                        break

            if not chosen_path:
                # fallback to latest file
                info = self.get_latest_file_info()
                if info:
                    chosen_path = info['path']

            if not chosen_path:
                return 0.0

            return float(self.get_totals_from_file(chosen_path, up_to_date=up_to_date) or 0.0)
        except Exception as e:
            logger.exception('Error computing cumulative billed up to date')
            return 0.0

    def get_totals_from_file(self, file_path, up_to_date=None):
        """Read a processed Facturacion file (the saved normalized workbook) and return billed total filtered by up_to_date.
        The file is cumulative FYTD; the method will filter rows where Fiscal Year == 2026 and Engagement Country/Region == 'Venezuela',
        then sum 'Net Amount Local' for Accounting Cycle Date <= up_to_date (if provided).
        """
        try:
            df = pd.read_excel(file_path, sheet_name='Facturacion')
            df.columns = [str(c).strip() for c in df.columns]

            # Apply basic filters
            if 'Fiscal Year' in df.columns:
                df = df[df['Fiscal Year'].astype(str).str.contains('2026')]

            if 'Engagement Country/Region' in df.columns:
                df = df[df['Engagement Country/Region'].astype(str).str.contains('Venezuela', case=False, na=False)]

            if 'Net Amount Local' not in df.columns:
                return 0.0

            # Date filtering behavior:
            # - For week-report filters, the Accounting Cycle Date represents the report date.
            #   When an up_to_date is provided we should take rows where Accounting Cycle Date == up_to_date
            #   (i.e. the totals for that report).
            # - If Accounting Cycle Date is not available, fall back to Billing Doc Date and include rows
            #   up to that date (daily-level date field).
            if up_to_date is not None:
                try:
                    if 'Accounting Cycle Date' in df.columns:
                        df['Accounting Cycle Date'] = pd.to_datetime(df['Accounting Cycle Date'], errors='coerce').dt.date
                        df = df[df['Accounting Cycle Date'] == up_to_date]
                    elif 'Billing Doc Date' in df.columns:
                        df['Billing Doc Date'] = pd.to_datetime(df['Billing Doc Date'], errors='coerce').dt.date
                        df = df[df['Billing Doc Date'] <= up_to_date]
                except Exception:
                    # If parsing fails, continue without date filtering
                    pass

            # Clean numeric characters (commas, currency symbols, parentheses) and coerce to numeric
            net_series = df['Net Amount Local'].astype(str)
            # remove common currency characters and parentheses, and convert parentheses to negative
            net_series = net_series.str.replace('\(', '-', regex=True)
            net_series = net_series.str.replace('[\$,]', '', regex=True)
            billed_total = pd.to_numeric(net_series, errors='coerce').fillna(0).sum()
            return float(billed_total)
        except Exception as e:
            logger.exception('Error reading totals from Facturacion file')
            return 0.0

    def get_all_processed_df(self):
        """Return a combined DataFrame of all processed facturacion files, using persistent cache when available.

        This is a lightweight implementation to align caching behavior with other modules. If no files exist,
        returns an empty DataFrame.
        """
        import pandas as pd
        files = []
        if os.path.exists(self.media_folder):
            files = [os.path.join(self.media_folder, f) for f in os.listdir(self.media_folder) if f.lower().endswith(('.xlsx', '.xls'))]
            files = sorted(files, key=lambda p: os.path.getmtime(p))

        max_mtime = None
        for p in files:
            try:
                m = os.path.getmtime(p)
                if max_mtime is None or m > max_mtime:
                    max_mtime = m
            except Exception:
                continue

        # attempt to load persistent cache if present
        try:
            if os.path.exists(self._cache_file):
                try:
                    import pickle
                    with open(self._cache_file, 'rb') as fh:
                        cached = pickle.load(fh)
                    # support tuples (max_mtime, code_hash, df) or legacy (max_mtime, df)
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

                        if cached_mtime == max_mtime and (not self._code_hash or cached_code_hash == self._code_hash):
                            self._cached_df = cached_df
                            self._cached_mtime = cached_mtime
                            return self._cached_df.copy()
                except Exception:
                    pass
        except Exception:
            pass

        # Build minimal combined DF by concatenating processed workbooks (sheet 'Facturacion' or first sheet)
        combined = []
        for p in files:
            try:
                try:
                    dfx = pd.read_excel(p, sheet_name='Facturacion')
                except Exception:
                    dfx = pd.read_excel(p)
                combined.append(dfx)
            except Exception:
                continue

        if not combined:
            df_final = pd.DataFrame()
        else:
            df_final = pd.concat(combined, ignore_index=True)

        # write persistent cache (best-effort)
        try:
            import pickle
            tmp = self._cache_file + '.tmp'
            with open(tmp, 'wb') as fh:
                try:
                    pickle.dump((max_mtime, getattr(self, '_code_hash', '') or '', df_final), fh)
                except Exception:
                    pickle.dump((max_mtime, df_final), fh)
            try:
                os.replace(tmp, self._cache_file)
            except Exception:
                os.rename(tmp, self._cache_file)
        except Exception:
            pass

        self._cached_df = df_final.copy() if not df_final.empty else df_final
        self._cached_mtime = max_mtime
        return df_final