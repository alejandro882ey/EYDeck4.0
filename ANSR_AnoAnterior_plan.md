ANSR Año Anterior Implementation Plan

Goal
----
Read the Excel file `media/Resultados ANSR PY25 v2.xlsx`, sheet `PY25 POR PPED`, and use the data to compute "Año Anterior" amounts for ANSR MTD and ANSR YTD to display on the Macro cards in `dashboard.html`.

High-level summary
------------------
- The Excel sheet `PY25 POR PPED` contains rows with column `MES` (month names in Spanish) and `ANSR` (ANSR values for PY25). For the report date (e.g. 2025-09-12) we must:
  - Map the report date to the fiscal month index according to the project's fiscal calendar (fiscal year starts in July). The same mapping used for the goal tracker should be reused.
  - Compute previous-year MTD: sum of `ANSR` for the month corresponding to the report month name (e.g., 'Septiembre').
  - Compute previous-year YTD: cumulative sum of `ANSR` across the fiscal-year-to-date range (from fiscal-year start up to report month). For example, for September with fiscal-year starting in July, YTD is sum of July + August + September rows.
  - Return formatted numbers and a numeric value to the dashboard view. Also expose percentages vs the current dashboard values.

Deliverables
------------
1. A small service module: `core_dashboard/modules/ansr_prev_year/services.py` with public functions:
   - load_ansr_file(filepath=None) -> DataFrame
   - get_prev_year_ansr_for_report(report_date: date, scope: 'M'|'Y', filepath=None) -> float
   - get_prev_year_ansr_for_report_with_breakdown(report_date: date, filepath=None) -> dict with {
       'ansr_mtd': float,
       'ansr_ytd': float,
       'month_name': str,  # Spanish month used
       'months_included': list[str]
     }
   - Internally cache parsed DataFrame (LRU / simple module-level cache) and allow forced reload.

2. Integrate into dashboard view:
   - In the place where Macro cards are computed, call service.get_prev_year_ansr_for_report(report_date, scope) and add the values to the template context as `prev_year_ansr_mtd`, `prev_year_ansr_ytd`, and percentages `prev_year_ansr_mtd_pct` and `prev_year_ansr_ytd_pct` computed as: current_value / prev_year_value * 100 (guarding divide-by-zero).
   - Also compute color class based on percentage thresholds: <50% -> 'bg-danger', <95% -> 'bg-warning', >=95% -> 'bg-success'. Use existing CSS conventions for progress bars if present.

3. Template changes in `core_dashboard/templates/core_dashboard/dashboard.html`:
   - For Macro ANSR MTD and ANSR YTD cards, under the existing progress bar show the text: "Año Anterior: $1,865,742.06" formatted with `format_number` filter.
   - Use the percentage (capped at 100% for bar width or allow >100% if desired) to set the width of the progress bar and apply the color class computed server-side or computed in-template using percentage.
   - Keep existing click/preview behavior intact. Do not change the top-level layout or card data attributes except adding small spans.

4. Tests and QA
   - Add unit tests under `tests/` validating Excel parsing and fiscal-month mapping logic (happy path + missing month names + empty file + divide-by-zero) using pytest/django test runner.
   - Run linter and a local runserver smoke test on port 8001.

Technical details & contract
---------------------------
- Inputs:
  - `report_date` (datetime.date) used to determine fiscaled month and cumulative ranges.
  - `filepath` optional; default: settings.MEDIA_ROOT + '/Resultados ANSR PY25 v2.xlsx'. Use Django `settings` to construct the path.
- Outputs:
  - Floats: ANSR amounts (unrounded) and formatted strings. Values are returned in same currency as sheet (assumed numeric floats). The template will format numbers.
  - Percentages: current_value / prev_year_value * 100. If prev_year_value is 0, percentage should be None or 0 and indicator color should be 'bg-danger' (or neutral) and bar width 0.

Edge cases & handling
---------------------
- Missing file: Return None for values and show "N/A" in the template. Log a warning.
- Missing months or mismatched month-name cases: Normalize month names (strip accents, lower-case) using a mapping from Spanish month names to month numbers. If a requested month is missing, treat its value as 0 and log.
- Multiple rows for the same month: sum them per month (groupby MES).
- Non-numeric ANSR values: coerce to numeric (pandas.to_numeric(errors='coerce')) and treat NaN as 0.
- Timezone/Report date: Use date only (not timezone-aware). Ensure date provided to service comes from the same `latest_report_date` value used in the template context.

Implementation steps (detailed)
-------------------------------
1. Create module skeleton
   - Add `core_dashboard/modules/ansr_prev_year/__init__.py` and `services.py` and `README.md` (done README.md).

2. Implement parsing & caching in services.py
   - Use pandas.read_excel(filepath, sheet_name='PY25 POR PPED')
   - Select columns `MES` and `ANSR` (case-insensitive). Create month-normalized column (map Spanish names to month numbers).
   - Group by month number and sum `ANSR` to get single value per month.
   - Create DataFrame/Series with months July(7) through June(6) mapped to fiscal order: [7,8,9,10,11,12,1,2,3,4,5,6].
   - Provide helper to get fiscal-month index for report_date and the months included.
   - Cache the result at module-level with file mtime check; allow force_reload.

3. Integrate to the dashboard view
   - Identify where `latest_report_date` is set in `core_dashboard/views.py` or equivalent (search). Add import and call to the new service using that date. Compute prev year amounts and add to context variables named prefixed with `prev_year_ansr_*`.
   - Compute percentages vs the current values that are already computed for the macro cards (the card values are in the template via variables; find their names in context, e.g., `macro_ansr_ytd`, `macro_ansr_mtd` or similar). If the code computes values inline in template, prefer to compute percentages in view and pass them in.

4. Template changes
   - Edit `core_dashboard/templates/core_dashboard/dashboard.html` where the two ANSR cards exist (search for card header text containing 'ANSR YTD' and 'ANSR MTD' or the macro-row first and second card blocks).
   - Under the progress bar element insert: <small>Año Anterior: ${{ prev_year_ansr_ytd|format_number }}</small> (same for MTD)
   - For the .progress .progress-bar width and class, either set style="width: {{ prev_year_ansr_ytd_pct|default:0 }}%" and class based on `prev_year_ansr_ytd_color` passed from view. Keep accessibility attributes (aria-valuenow) updated.

5. Add unit tests
   - Create `core_dashboard/modules/ansr_prev_year/tests.py` with tests that:
     - Load a small DataFrame created in-memory with the same columns and validate month mapping and cumulative sums.
     - Test percent computation logic including divide-by-zero handling.

6. Run lint and tests
   - Run project's test suite (pytest/django manage.py test). Fix any style or type issues.

Quality gates
-------------
- Build: not applicable (Python scripts). Ensure no syntax errors.
- Lint/Typecheck: run flake8/ruff if configured.
- Unit tests: ensure the new tests pass.
- Smoke test: run `python manage.py runserver 8001` and check the dashboard page; confirm numbers match the expected September 2025 example values.

Notes and assumptions
---------------------
- Assumed sheet name `PY25 POR PPED` and columns `MES` and `ANSR` present as per user note and attachment.
- Assumed fiscal year starts in July (per project context). The fiscal-period logic should match that used by existing goal tracker; if that code is centralized (e.g., `core_dashboard/utils.py` or `mtd_module.py`), prefer to reuse it. If not found, implement the mapping in this module.
- Formatting on template uses existing `format_number` filter and localization.

Follow-ups
----------
- Add logs when cache is invalidated or file missing.
- Add admin UI or management command to preview the computed prev-year ANSR values across partners and service lines for verification.
- Optionally support per-partner or per-service-line comparisons (advanced), wired to the partner selection on the dashboard.
