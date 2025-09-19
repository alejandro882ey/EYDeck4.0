Facturacion module — Development Log

Overview
--------
This document explains the creation, design decisions, current behavior, and future work for the `Facturacion` module added to `core_dashboard`.

Files added
-----------
- `core_dashboard/modules/facturacion/__init__.py` — package marker.
- `core_dashboard/modules/facturacion/utils.py` — lightweight extractor `extract_facturacion_sheet(uploaded_file)`.
- `core_dashboard/modules/facturacion/services.py` — main business logic in `FacturacionService`:
  - `process_uploaded_file(uploaded_file, original_filename=None)` — extract and normalize sheet, compute billed total, write processed workbook (`Facturacion_Latest.xlsx`).
  - `get_latest_file_info()` — return latest processed file path and metadata.
  - `get_totals_from_file(file_path, up_to_date=None)` — read processed file and compute billed total with date filtering and column filters.
  - `get_cumulative_billed_up_to(up_to_date)` — select best processed file for a target date and return billed total for that report date.
- `core_dashboard/modules/facturacion/views.py` — minimal JSON endpoints for upload, status, and clear (mirrors module pattern used in `Cobranzas`).
- `core_dashboard/modules/facturacion/urls.py` — route registration.
- `core_dashboard/modules/facturacion/tests.py` — unit tests for `process_uploaded_file` and `get_totals_from_file`.
- `core_dashboard/modules/facturacion/integration_tests.py` — integration-style test asserting cumulative result for a report date.

Design and implementation notes
-------------------------------
1. Overall goal
   - Provide a simple pipeline to allow users to upload Facturacion Excel reports and expose a single macro KPI `Facturacion (Billed YTD)` that shows the sum of the `Net Amount Local` column.
   - When a week filter is applied on the dashboard, the service should return the billed amount for the report whose `Accounting Cycle Date` equals the selected week's Friday (the report date). When `Accounting Cycle Date` is not available, fall back to using `Billing Doc Date` (<= filter date) to compute totals.

2. Data extraction
   - `utils.extract_facturacion_sheet` is intentionally simple: it reads the first sheet of the uploaded workbook and returns a DataFrame with stripped column names.
   - This approach is fast and works for well-formed workbooks. However, it is not as robust as the `Cobranzas` extractor which detects preambles and header rows. See "Careful areas".

3. Processing
   - `process_uploaded_file` keeps all columns but normalizes column names (stripped strings). It computes `billed_total` as the sum of `Net Amount Local` using a tolerant parsing approach (coerce to numeric with removal of commas and common currency chars).
   - It writes a processed workbook `Facturacion_Latest.xlsx` to `MEDIA_ROOT/facturacion/` and clears an internal cache file.
   - The method returns a dict with `billed_total`, rows processed and file metadata.

4. Date filtering behavior
   - `get_totals_from_file(file_path, up_to_date=None)` filters rows to `Fiscal Year` containing '2026' and `Engagement Country/Region` containing 'Venezuela' (case-insensitive). Then it applies date filtering:
     - If `up_to_date` is provided and `Accounting Cycle Date` column exists, the code selects rows where `Accounting Cycle Date == up_to_date` (report totals).
     - Else, if `Billing Doc Date` exists, it selects rows where `Billing Doc Date <= up_to_date` (daily-level totals up to that date).
   - After filtering, `Net Amount Local` is cleaned (parentheses handled as negative, removal of commas/currency symbols) and summed.

5. Cumulative selection
   - `get_cumulative_billed_up_to` searches for processed files in the `facturacion` media folder with filenames matching `facturacion_YYYY-MM-DD.*`. If one or more exist, it chooses the latest file date that is <= the requested `up_to_date` and computes totals from that file with the requested `up_to_date` as additional filter. Otherwise it falls back to the latest processed file.

Tests
-----
- Unit test `tests.py` covers `process_uploaded_file` and `get_totals_from_file` behavior for equality-based Accounting Cycle Date filtering.
- Integration-style test `integration_tests.py` verifies `get_cumulative_billed_up_to` returns 559,410.59 for 2025-07-11 using an in-memory Excel file.

Careful areas and possible bugs
------------------------------
1. Header detection and sheets
   - Real-world Facturacion files may contain preamble rows, merged headers, or column names that differ slightly (e.g. "NetAmountLocal", "Net Amount (Local)", "NET AMOUNT LOCAL"). The current extractor reads the first sheet and strips column names; it does not attempt to find the header row or normalize variants.
   - Recommendation: port the robust header-detection logic from `Cobranzas` (it detects preambles, finds header rows by scanning for key column names, reshapes merged headers, and returns a clean DataFrame). This will avoid missing or misnamed columns.

2. Date parsing and timezones
   - The code parses `Accounting Cycle Date` and `Billing Doc Date` with `pd.to_datetime(..., errors='coerce').dt.date`. If Excel cells are strings in unexpected formats or localized (e.g., day/month/year vs month/day/year), parsing may produce NaT and drop rows.
   - Recommendation: add heuristics for ambiguous dates (try both d/m/y and m/d/y patterns if parsing yields many NaT), or require normalized upload instructions.

3. Numeric formats
   - The `Net Amount Local` cleaning handles commas, dollar signs and parentheses, but there are many other locale formats (period vs comma as decimal separator, different currency symbols). Some inputs may include thousands separators or non-standard minus signs.
   - Recommendation: implement a small `parse_numeric` utility that tries multiple patterns (remove spaces, convert comma-as-decimal when needed, handle non-breaking spaces) and/or rely on `locale` configuration.

4. File naming and history
   - Currently the service writes `Facturacion_Latest.xlsx`; historical processed files are not preserved except if the uploaded original filename contains a date pattern and you choose to persist it manually.
   - Recommendation: preserve the original uploaded file with a timestamped name and optionally write processed versions that include the report date in the filename (e.g., `Facturacion_2025-07-11.xlsx`). This simplifies `get_cumulative_billed_up_to` and auditing.

5. Concurrency and caching
   - The module keeps an in-memory cache attribute and a small cache file path. If multiple uploads happen concurrently in the dev server, race conditions or stale cache reads may occur.
   - Recommendation: either avoid a persistent cache file or use robust locking mechanisms and clear the cache after processing.

6. Integration with dashboard
   - The dashboard now calls into `FacturacionService.get_cumulative_billed_up_to(friday_date)` when a week filter is applied. Ensure the date object passed is timezone-naive and matches the date-parsing behavior in the service. Also ensure the `Fiscal Year` and `Engagement Country/Region` filters align with your business rules.

Next steps
----------
1. Port Cobranzas extractor and numeric parsing utilities into `facturacion/utils.py` and replace the simple extractor.
2. Add more unit tests that cover:
   - Alternate column names for `Net Amount Local` and `Accounting Cycle Date`.
   - Files with preamble rows and merged headers.
   - Numeric formats with comma decimals and parentheses.
3. Change processing to persist processed files with report-date-prefixed filenames (e.g., `Facturacion_YYYY-MM-DD.xlsx`) and update `get_cumulative_billed_up_to` to prefer these.
4. Add logging at key steps (file discovered, rows filtered, rows dropped due to NaT/NaN) and an admin page that lists uploaded processed files and their billed totals for quick audit.

Contact
-------
If you want, I can start by porting the `Cobranzas` extractor into `facturacion/utils.py` and adding the first set of edge-case tests. This will reduce ingestion errors for real-world files.
