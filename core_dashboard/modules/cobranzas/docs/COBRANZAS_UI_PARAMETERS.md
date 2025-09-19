# Cobranzas — UI Parameters (Preview)

Objective

- Provide a concise, implementable design spec for any UI elements belonging to the Cobranzas Preview (`/cobranzas/preview/`). This covers number formatting ("no decimals" requirement for preview cards), typography/sizing guidance for laptop screens, chart sizing, and CSS-variable recommendations so frontend developers can implement consistently.

Success criteria

- Clear numeric formatting rules for preview cards (no decimals for displayed monetary cards). Stored values remain full precision in the backend/dataframe; rounding is only for presentation.
- Concrete sizing and typography recommendations tailored for laptop screens (typical 1366–1920px widths).
- Guidance for charts in the preview (height, axis label sizing, tooltip precision).

Constraints and assumptions

- Target device: laptop screens. Prioritize widths 1366px → 1920px. If responsive behavior needed for smaller screens, scale down sizes proportionally.
- These rules apply strictly to the Cobranzas Preview pages; they do not change other modules or global dashboard rules.

Display rules (numbers)

- Stored values: retain full floating precision in back-end and DataFrames. Do not truncate stored values.
- Display values (preview cards): round to integer (no decimals) for monetary amounts shown prominently on preview cards.
  - Example: 540,184.3813945 → display as `540,184`.
  - Use thousands separators according to the site locale. For Spanish locale use `.` for thousands and `,` for decimals (but decimals will be hidden on cards). For English use `,` for thousands.
- Chart axes (monetary axes) should use integer ticks (no decimals). Chart tooltips should show 2 decimal places for accuracy — only the axis and cards hide decimals.
- Exchange rates (chart lines) should show 2 decimal places on axis and in tooltips because rate precision is meaningful.

Typography & sizing (recommended)

- Card container (preview): flexible width, min-width 220px, max-width 360px.
- Card title: 13px (0.8125rem), font-weight 600.
- Card primary number: 32px (2.0rem) — main size for laptop preview cards.
- Card secondary/delta label: 12px (0.75rem).
- Chart container: default width responsive to preview layout; recommended height 360px (range 320–420px depending on layout density).
- Chart legend font-size: 12px; axis label font-size: 12px; tick font-size: 11px.

Spacing & padding

- Card padding: 16px.
- Card margin-right: 16px (when cards are aligned horizontally).
- Chart padding: left 48px (to fit Y-axis labels), right 24px, top 16px.

Color & contrast

- Keep existing Cobranzas color palette. Ensure high contrast for the main number and Tasa Sintetica line. If Tasa Sintetica uses yellow, ensure it contrasts against the background (e.g., darker border or markers).

CSS variable recommendations (copyable)

:root {
  --cobranzas-card-title: 13px;
  --cobranzas-card-number: 32px;
  --cobranzas-card-padding: 16px;
  --cobranzas-chart-height: 360px;
  --cobranzas-legend-size: 12px;
}

Implementation notes for developers

- Charting: Plotly is used in this project. For monetary axes use integer tick format. For tooltips, set hovertemplate to show two decimals for monetary points and rates.
- Rounding: round for display only. Keep backend values untouched. Implement display formatting in templates or client-side rendering layer.

Validation steps

- Visual checks on three laptop widths: 1366px, 1440px, 1920px.
- Ensure card numbers match backend sums when rounded (assert equality after rounding in a unit test).
- Accessibility check: verify contrast ratios for main numbers and Tasa Sintetica line meet AA standards.

Edge cases & notes

- If the preview page becomes crowded (many cards), switch to abbreviated numbers (e.g., 540K) only for compact views; otherwise show full integers.
- If locale is ambiguous, default to Spanish formatting for this project unless explicitly configured otherwise.


---

End of UI parameter spec for Cobranzas Preview.
