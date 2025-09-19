# Cobranzas Preview — MTD and YTD Rules (Spec)

Objective

- Define authoritative rules for computing Month-To-Date (MTD) and Year-To-Date (YTD) totals for the Cobranzas Preview page (`/cobranzas/preview/`). Ensure behavior matches weekly-upload cadence: when the last weekly report of a month is processed, MTD should reflect only that month and not continue accumulating from previous months.

Success criteria

- MTD for the preview correctly sums rows for the running month of the latest `Fecha de Cobro` processed.
- YTD aggregates across the fiscal year to the latest `Fecha de Cobro` processed.
- Tests assert that in the first month of data (e.g., July) MTD == YTD; by the next month (August) MTD differs and equals only that month.

Rules & definitions

- Authority date: `Fecha de Cobro` is the authoritative date used for any bucketing.
- Latest report date: the maximum `Fecha de Cobro` present in the processed Cobranzas dataset.
- Fiscal year: default to calendar year unless a custom fiscal calendar is configured. If fiscal year differs from calendar, provide configuration for fiscal-year start.

MTD calculation

- Determine latest_report_date = processed_df['Fecha de Cobro'].max()
- MTD window = rows where `row['Fecha de Cobro'].year == latest_report_date.year` AND `row['Fecha de Cobro'].month == latest_report_date.month`.
- MTD value = aggregate (sum) of the same contributions used for YTD but restricted to the MTD window (e.g., invoice USD + selected VES-USD equivalents, or the new VES->USD conversion depending on which card).

YTD calculation

- YTD window = rows where `row['Fecha de Cobro'] >= fiscal_year_start_date` AND `row['Fecha de Cobro'] <= latest_report_date`.
- YTD value = aggregate (sum) of the same contributions used by MTD but across the YTD window.

Weekly-report nuance

- Because uploads are weekly, the preview should treat the latest processed date as the snapshot timestamp. For example:
  - If dataset contains rows for 2025-07-07 and 2025-07-11 (July only), latest_report_date is 2025-07-11. MTD == YTD and equals sum of July rows.
  - When new rows for August are uploaded (e.g., 2025-08-05), latest_report_date is in August. MTD sums rows in August only; YTD sums July+August.

Validation tests and examples

- Minimal test fixture (rows):
  - 2025-07-07 -> amount A
  - 2025-07-11 -> amount B
  - 2025-08-05 -> amount C
  - Expected behavior:
    - For snapshot at 2025-07-11: MTD == YTD == A + B
    - For snapshot at 2025-08-05: MTD == C ; YTD == A + B + C

Edge cases

- If dataset has multiple rows with the same Fecha but different times, ensure date-only comparison for month bucketing.
- If fiscal year start is not January 1, compute YTD from configured fiscal start date.

Developer notes

- Keep MTD and YTD computations using the same aggregation function to avoid discrepancies.
- Provide a small endpoint or debug script (scripts/check_mtd_ytd.py) that prints values for manual verification during development.


---

End of MTD/YTD rules document for Cobranzas Preview.
