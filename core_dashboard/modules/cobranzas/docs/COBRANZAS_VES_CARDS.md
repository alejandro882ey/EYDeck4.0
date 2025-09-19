# Cobranzas Preview — VES Cards (Design & Implementation Guide)

Objective

- Add two VES-related cards to the Cobranzas Preview page (`/cobranzas/preview/`):
  - `Cobranzas VES MTD (equivalente a USD)` — month-to-date VES totals converted to USD-equivalent using per-row BCV invoice rates.
  - `Cobranzas VES (equivalente a USD)` — aggregated VES totals (YTD or full preview aggregation as required) converted to USD-equivalent.

Important scope clarification

- These cards are part of the Cobranzas Preview only. They are not Macro dashboard cards and do not alter or assume behavior from any Facturacion module or other global dashboards.

Success criteria

- Preview displays two new cards with USD-equivalent values derived from `Monto en Bolívares de la Factura`.
- Conversion uses per-row `Tipo de Cambio Usado en la Emisión de la Factura BCV` when available; fallback rules are documented.
- Formatting follows `COBRANZAS_UI_PARAMETERS.md` (no decimals on main preview cards; tooltips show decimals).

Required input columns from the processed Cobranzas file

- `Fecha de Cobro` (datetime.date)
- `Monto en Bolívares de la Factura` (float) — THIS column is the authoritative source for the raw VES amount shown under the VES card. The implementation must prefer this header (case/space/accent-insensitive match) when present.
- `Monto en Dólares de la Factura` (float)
- `Tipo de Cambio Usado en la Emisión de la Factura BCV` (float) — rate used in the invoice

Conversion logic (per-row)

- For each processed row, compute row_usd_equiv_from_ves = (Monto en Bolívares de la Factura) / (Tipo de Cambio Usado en la Emisión de la Factura BCV)
  - If `Tipo de Cambio Usado...` is missing for a row, fallback to:
    1) the per-row `Tipo de Cambio del día del pago recibido en Cuenta Bancaria BCV` (if available), or
    2) the date-aggregated average of `Tipo de Cambio Usado...` for the same `Fecha de Cobro` (if multiple rows), or
    3) log the missing row and treat its VES as 0 in the converted sum (or surface an alert to operator).
- Then aggregate per-window (MTD or preview YTD) as sum(row_usd_equiv_from_ves).

MTD vs preview aggregation

- `Cobranzas VES MTD (equivalente a USD)` — sum row_usd_equiv_from_ves for rows where `Fecha de Cobro.month == latest_report_month` and `Fecha de Cobro.year == latest_report_year`.
- `Cobranzas VES (equivalente a USD)` — default to YTD (from fiscal year start to latest Fecha de Cobro). If you prefer full dataset aggregation replace YTD with full-dataset aggregation (document preference).

Presentation

- Place the VES cards within the Preview layout below or adjacent to the existing USD-collected cards.
- Primary number: USD-equivalent rounded to integer (follow `COBRANZAS_UI_PARAMETERS` rules).
- Secondary label: show raw VES total (optional) beneath with the same rounding rules.

Validation & tests

- Unit test: for a small DataFrame fixture with 3 rows compute expected per-row usd equivalents and assert the aggregation equals the function output.
- Integration test: for sample processed file (e.g., the one used in development logs) calculate the two card values and assert they are consistent with a manual spreadsheet calculation.

Edge cases

- Zero or missing exchange rates: rows with missing required rate are treated according to fallback rules (prefer BCV day-of-payment; else date average; else log and skip).
- Multiple BCV-rate columns with slightly different headers: normalize header names and prefer exact `Tipo de Cambio Usado en la Emisión de la Factura BCV` when present.

Developer notes

- Keep data precision in back-end. The rounding rule is only for display.
- Add small audit logs when falling back on alternative rates to make debugging easier.


---

End of VES cards guide for Cobranzas Preview.
