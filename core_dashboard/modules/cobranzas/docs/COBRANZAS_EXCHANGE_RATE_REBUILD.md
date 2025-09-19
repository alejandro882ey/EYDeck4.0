# Cobranzas Preview — Exchange Rate Daily Evolution (Rebuild Guide)

Objective

- Rebuild the `Exchange Rate Daily Evolution (Tasa Oficial, Tasa Binance, Tasa Sintetica)` chart for the Cobranzas Preview page (`/cobranzas/preview/`). Ensure Tasa Oficial and Tasa Binance come from `Historial_TCBinance.xlsx`. Compute Tasa Sintetica only on `Fecha de Cobro` dates using the exact formula and selection rules below. Provide strict verification tests so calculated values are numerically close to the provided example values.

Scope clarifications

- All changes and charts referenced are strictly in the Cobranzas Preview. No changes to Macro cards or other modules are implied or required.
- Tasa Sintetica series should be plotted only up to the latest `Fecha de Cobro` present in the processed Cobranzas dataset.

Data sources

- Processed Cobranzas DataFrame (from `media/cobranzas/...` processed file). Required columns:
  - `Fecha de Cobro` (date)
  - `Monto en Dólares de la Factura` (float)
  - `Monto en Bolívares de la Factura` (float)
  - `Tipo de Cambio Usado en la Emisión de la Factura BCV` (float)
  - One or more `Monto equivalente en USD de los VES Cobrados` columns (deduplicated by the extractor as `Monto equivalente ...`, `Monto equivalente ..._1`, `Monto equivalente ..._2`)
  - `Tipo de Cambio del día del pago recibido en Cuenta Bancaria BCV` and `... Monitor` (float)
- `Historial_TCBinance.xlsx` (path: `dolar excel/Historial_TCBinance.xlsx`)
  - Required columns: Date, Tasa_Oficial, Tasa_Binance (column headers may vary; normalize names at load time).

Algorithm (detailed)

Phase 1 — Load & normalize

1) Load processed DataFrame and parse `Fecha de Cobro` to date (no time component).
2) Normalize column names: strip whitespace and unify repeated `Monto equivalente en USD de los VES Cobrados` columns into identifiable candidates (e.g., `_ves_usd_candidates = [col for col in df.columns if 'Monto equivalente en USD' in col]`).
3) Load `Historial_TCBinance.xlsx`, parse dates, and produce `tasa_oficial_series` and `tasa_binance_series` indexed by calendar date.

Phase 2 — Select the correct VES-USD column per Fecha

Selection heuristic per Fecha of Cobro:

- Primary candidate: the first appearance of `Monto equivalente en USD de los VES Cobrados` that is adjacent (nearby column) to `Tipo de Cambio del día del pago recibido en Cuenta Bancaria BCV`.
- If the primary candidate contains no non-null values for rows of that Fecha, evaluate the second appearance (often adjacent to `Tipo de Cambio del día del pago recibido en Cuenta Bancaria Monitor`). If the second contains non-null values, use it for that Fecha.
- If neither candidate has values for that Fecha, treat the VES-USD-equivalent contribution as zero for denominator aggregation and log this decision.

Phase 3 — Compute Tasa Sintetica per Fecha of Cobro

For each unique `fecha` in sorted(processed_df['Fecha de Cobro'].unique()):

1) Subset rows_for_date = processed_df[processed_df['Fecha de Cobro'] == fecha]
2) Determine selected_ves_usd_col for this date using the heuristic above.
3) Compute Numerator_total:
   - Option A (recommended and matching your example):
     - per-row product = row['Monto en Dólares de la Factura'] * row['Tipo de Cambio Usado en la Emisión de la Factura BCV'] (if row value present); if BCV rate is missing at row level, use date-aggregated average BCV rate (mean of non-null BCV rates in rows_for_date) or fallback to the BCV day-of-payment column.
     - Numerator_total = sum(rows_for_date['Monto en Bolívares de la Factura'].fillna(0)) + sum(per-row product)
   - This mirrors your example where you had: 709,736.97 + (6,617.80 * 116.14)
4) Compute Denominator_total = sum(rows_for_date['Monto en Dólares de la Factura'].fillna(0)) + sum(rows_for_date[selected_ves_usd_col].fillna(0))
5) If Denominator_total <= 0, mark candidate invalid and skip (or use previous valid tasa if present); log for audit.
6) Candidate_tasa = Numerator_total / Denominator_total

Phase 4 — Validation rule against Tasa Oficial

- For the `fecha` get tasa_oficial_for_date from the historical series (if exact date missing, use previous available date's tasa_oficial).
- If candidate_tasa < tasa_oficial_for_date then treat candidate as invalid and set tasa_sintetica_for_date = previous_valid_tasa_sintetica (carry-forward). If no previous valid exists, mark NaN and continue.
- Else accept candidate_tasa as new previous_valid_tasa_sintetica.

Phase 5 — Build plot-ready Tasa Sintetica series

- Create a date index from earliest historical date desired to last_processed_fecha (the max of processed_df['Fecha de Cobro']).
- For dates that equal an observed Fecha de Cobro, place computed tasa_sintetica_for_date (or NaN if invalid and no previous exists).
- For dates between two observed Fecha de Cobro values, forward-fill the last known tasa_sintetica for plotting continuity.
- Do NOT create values beyond last_processed_fecha — remain NaN after that date (no extrapolation).

Chart output

- Export arrays/dicts for plotting: dates[], tasa_oficial[], tasa_binance[], tasa_sintetica_plot_ready[]
- Plot markers for actual Fecha-of-Cobro observation points on the Tasa Sintetica line to indicate which points were actively computed and which are carry-forwarded.

Verification & tests (strict)

We must verify numerically that computed Tasa Sintetica for known dates is close to supplied examples. Create unit tests with a deterministic fixture that reproduces the example below.

Strict numerical checks (unit tests):

- Example 1 (2025-07-07):
  - Provided raw values in fixture:
    - Numerator components: `Monto en Bolívares de la Factura` = 709,736.97
    - `Monto en Dólares de la Factura` = 6,617.80
    - `Tipo de Cambio Usado en la Emisión de la Factura BCV` (average/row) = 116.14
    - VES-USD-equivalent selected column = 5,551.62
  - Calculation to assert: candidate_tasa = (709,736.97 + (6,617.80 * 116.14)) / (6,617.80 + 5,551.62)
  - Expected target ≈ 121.4. Test should assert: abs(calculated - expected) <= 0.5 OR relative error <= 0.5% (choose which is stricter/appropriate). Recommended: absolute tolerance 0.5.

- Example 2 (2025-07-16):
  - Use supplied fixture values that match that date; expected target ≈ 147.56. Assert within the same tolerance.

Additional tests

- Column selection test: with a fixture where first candidate is empty and second contains values, assert the pipeline picks the second candidate for denominator.
- Denominator zero handling: fixture causes denominator 0 -> assert code skips and logs.
- Carry-forward test: fixture where candidate < Tasa Oficial on a date -> assert tasa_sintetica uses previous valid value.
- Plot range test: ensure serie values are NaN after last processed Fecha.

Reproducibility & fixtures

- Create small CSV fixtures in `core_dashboard/modules/cobranzas/tests/fixtures/` for the two example dates and the necessary Historial rows. Tests should import these fixtures and compute tasa_sintetica deterministically.

Developer notes & implementation choices

- Use per-row multiplication USD_invoice * BCV_rate to compute the BCV-weighted contribution as it matches your example. Document this choice in code comments for future maintainers.
- If BCV rate is missing for a row, use a date-aggregated average of BCV rates for the same date as a fallback.
- The VES-USD column-selection heuristic must be robust to small header changes; use substring matching and column-neighborhood checks rather than strict positional indexing.

Edge cases

- Formula yields candidate lower than official rate for first observed date: decide whether to accept or mark NaN. The spec uses previous valid (none available) so mark NaN and surface a warning for user review.
- If historical rates are missing for dates needed, fallback to previous historical date's rate for comparison.

Acceptance criteria

- Unit tests for the two example dates pass within tolerance.
- The plotted Tasa Sintetica visually matches the expected order of magnitude and trend across the fixture dates.
- Column-selection and carry-forward behaviors verified by tests.


---

End of Exchange Rate rebuild guide for Cobranzas Preview.
